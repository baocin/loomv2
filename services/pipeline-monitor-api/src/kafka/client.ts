import { Kafka, Admin, Consumer, Producer } from 'kafkajs'
import { config } from '../config'
import { logger } from '../utils/logger'

export class KafkaClient {
  private kafka: Kafka
  private admin: Admin | null = null
  private producer: Producer | null = null
  private consumers: Map<string, Consumer> = new Map()

  constructor() {
    this.kafka = new Kafka({
      clientId: config.kafka.clientId,
      brokers: config.kafka.brokers,
      connectionTimeout: config.kafka.connectionTimeout,
      requestTimeout: config.kafka.requestTimeout,
    })
  }

  async connect(): Promise<void> {
    try {
      this.admin = this.kafka.admin()
      await this.admin.connect()

      this.producer = this.kafka.producer()
      await this.producer.connect()

      logger.info('Kafka client connected successfully')
    } catch (error) {
      logger.error('Failed to connect to Kafka', error)
      throw error
    }
  }

  async disconnect(): Promise<void> {
    try {
      if (this.admin) {
        await this.admin.disconnect()
        this.admin = null
      }

      if (this.producer) {
        await this.producer.disconnect()
        this.producer = null
      }

      for (const [groupId, consumer] of this.consumers) {
        await consumer.disconnect()
        this.consumers.delete(groupId)
      }

      logger.info('Kafka client disconnected')
    } catch (error) {
      logger.error('Error disconnecting from Kafka', error)
    }
  }

  async getTopics(): Promise<string[]> {
    if (!this.admin) throw new Error('Kafka admin not connected')

    try {
      const metadata = await this.admin.fetchTopicMetadata()
      return metadata.topics.map(topic => topic.name)
    } catch (error) {
      logger.error('Failed to fetch topics', error)
      throw error
    }
  }

  async getTopicMetadata(topicName: string) {
    if (!this.admin) throw new Error('Kafka admin not connected')

    try {
      const metadata = await this.admin.fetchTopicMetadata({ topics: [topicName] })
      return metadata.topics.find(topic => topic.name === topicName)
    } catch (error) {
      logger.error(`Failed to fetch metadata for topic ${topicName}`, error)
      throw error
    }
  }

  async getConsumerGroups(): Promise<any[]> {
    if (!this.admin) throw new Error('Kafka admin not connected')

    try {
      const groups = await this.admin.listGroups()
      return groups.groups
    } catch (error) {
      logger.error('Failed to fetch consumer groups', error)
      throw error
    }
  }

  async getConsumerGroupOffsets(groupId: string, topics?: string[]) {
    if (!this.admin) throw new Error('Kafka admin not connected')

    try {
      const offsets = await this.admin.fetchOffsets({ groupId, topics })
      return offsets
    } catch (error) {
      logger.error(`Failed to fetch offsets for group ${groupId}`, error)
      throw error
    }
  }

  async getTopicOffsets(topic: string) {
    if (!this.admin) throw new Error('Kafka admin not connected')

    try {
      const offsets = await this.admin.fetchTopicOffsets(topic)
      return offsets
    } catch (error) {
      logger.error(`Failed to fetch offsets for topic ${topic}`, error)
      throw error
    }
  }

  async createConsumer(groupId: string, topics: string[]): Promise<Consumer> {
    if (this.consumers.has(groupId)) {
      return this.consumers.get(groupId)!
    }

    const consumer = this.kafka.consumer({ groupId })
    await consumer.connect()
    await consumer.subscribe({ topics })

    this.consumers.set(groupId, consumer)
    return consumer
  }

  async getLatestMessage(topic: string, partition = 0): Promise<any> {
    const consumer = this.kafka.consumer({
      groupId: `monitor-${topic}-${Date.now()}`,
      maxWaitTimeInMs: 1000,
    })

    try {
      await consumer.connect()

      const offsets = await this.getTopicOffsets(topic)
      const latestOffset = offsets.find(o => o.partition === partition)?.high

      if (!latestOffset || latestOffset === '0') {
        return null
      }

      // Subscribe to topic from the end (latest messages only)
      await consumer.subscribe({ topic, fromBeginning: false })

      let latestMessage: any = null
      let messageCount = 0

      await consumer.run({
        eachMessage: async ({ message, topic: msgTopic, partition: msgPartition }) => {
          if (msgTopic === topic && msgPartition === partition) {
            latestMessage = {
              key: message.key?.toString(),
              value: message.value ? JSON.parse(message.value.toString()) : null,
              timestamp: new Date(parseInt(message.timestamp)),
              offset: message.offset,
              partition: msgPartition,
            }
            messageCount++
          }
        },
      })

      // Give it a moment to fetch the message
      await new Promise(resolve => setTimeout(resolve, 2000))

      return latestMessage
    } catch (error) {
      logger.error(`Failed to fetch latest message from ${topic}`, error)
      return null
    } finally {
      await consumer.disconnect()
    }
  }

  async streamMessages(
    topic: string,
    onMessage: (message: any) => void,
    fromBeginning = false
  ): Promise<() => Promise<void>> {
    const groupId = `monitor-stream-${topic}-${Date.now()}`
    const consumer = this.kafka.consumer({
      groupId,
      sessionTimeout: 30000,
      heartbeatInterval: 3000,
      retry: {
        retries: 5,
        initialRetryTime: 300,
        factor: 0.2
      }
    })

    let isConnected = false
    let isRunning = true

    try {
      await consumer.connect()
      isConnected = true

      await consumer.subscribe({ topic, fromBeginning })

      // Start consumer but don't await - it runs in background
      const runPromise = consumer.run({
        eachMessage: async ({ message, topic: msgTopic, partition }) => {
          if (!isRunning) return

          try {
            const parsedMessage = {
              topic: msgTopic,
              partition,
              offset: message.offset,
              key: message.key?.toString(),
              value: message.value ? JSON.parse(message.value.toString()) : null,
              timestamp: new Date(parseInt(message.timestamp)),
              headers: message.headers
            }
            onMessage(parsedMessage)
          } catch (error) {
            logger.error('Failed to process streamed message', error)
          }
        },
      }).catch(error => {
        if (isRunning) {
          logger.error(`Consumer error for topic ${topic}`, error)
        }
      })

      // Return cleanup function
      return async () => {
        logger.info(`Stopping stream for topic ${topic}`)
        isRunning = false

        try {
          // Stop the consumer first
          await consumer.stop()

          // Then disconnect
          if (isConnected) {
            await consumer.disconnect()
            isConnected = false
          }

          logger.info(`Successfully stopped streaming messages from ${topic}`)
        } catch (error) {
          logger.error(`Error during consumer cleanup for topic ${topic}`, error)
          // Force disconnect on error
          try {
            await consumer.disconnect()
          } catch (disconnectError) {
            logger.error(`Force disconnect failed for topic ${topic}`, disconnectError)
          }
        }
      }
    } catch (error) {
      // Ensure cleanup on initial connection failure
      if (isConnected) {
        try {
          await consumer.disconnect()
        } catch (disconnectError) {
          logger.error(`Disconnect failed after connection error`, disconnectError)
        }
      }
      logger.error(`Failed to start streaming from ${topic}`, error)
      throw error
    }
  }

  async clearTopicPartition(topic: string, partition: number): Promise<void> {
    if (!this.admin) {
      throw new Error('Admin client not connected')
    }

    try {
      logger.warn(`DESTRUCTIVE: Attempting to clear topic ${topic} partition ${partition}`)

      // For kafkajs, we'll use a different approach since deleteRecords might not be available
      // We'll temporarily alter the topic configuration to have very short retention
      // then reset it back. This effectively clears old data.

      const originalConfigs = await this.admin.describeConfigs({
        resources: [{
          type: 2, // TOPIC
          name: topic
        }],
        includeSynonyms: false
      })

      // Set retention time to 1 millisecond to clear data
      await this.admin.alterConfigs({
        validateOnly: false,
        resources: [{
          type: 2, // TOPIC
          name: topic,
          configEntries: [
            { name: 'retention.ms', value: '1' },
            { name: 'segment.ms', value: '1' }
          ]
        }]
      })

      // Wait a moment for Kafka to process
      await new Promise(resolve => setTimeout(resolve, 1000))

      // Reset retention to original value or default (7 days)
      const originalRetention = originalConfigs.resources[0]?.configEntries.find(c => c.configName === 'retention.ms')
      const retentionValue = originalRetention?.configValue || '604800000' // 7 days default

      await this.admin.alterConfigs({
        validateOnly: false,
        resources: [{
          type: 2, // TOPIC
          name: topic,
          configEntries: [
            { name: 'retention.ms', value: retentionValue },
            { name: 'segment.ms', value: '604800000' } // Reset segment time too
          ]
        }]
      })

      logger.info(`Successfully cleared topic ${topic} partition ${partition} using retention policy`)

    } catch (error) {
      logger.error(`Failed to clear topic ${topic} partition ${partition}:`, error)
      // Don't throw - let the route handler continue with other partitions
      // throw error
    }
  }

  async recreateTopic(topic: string): Promise<void> {
    if (!this.admin) {
      throw new Error('Admin client not connected')
    }

    try {
      logger.warn(`DESTRUCTIVE: Deleting and recreating topic ${topic} to clear all data`)

      // Get current topic configuration before deletion
      const metadata = await this.admin.fetchTopicMetadata({ topics: [topic] })
      const topicInfo = metadata.topics.find(t => t.name === topic)

      if (!topicInfo) {
        throw new Error(`Topic ${topic} not found`)
      }

      const numPartitions = topicInfo.partitions.length
      const replicationFactor = topicInfo.partitions[0]?.replicas.length || 1

      // Get topic configurations
      const configs = await this.admin.describeConfigs({
        resources: [{
          type: 2, // TOPIC
          name: topic
        }],
        includeSynonyms: false
      })

      const topicConfigs = configs.resources[0]?.configEntries || []
      const configEntries: Array<{ name: string; value: string }> = []

      // Preserve important configurations
      for (const config of topicConfigs) {
        if (config.configValue && config.configName) {
          configEntries.push({
            name: config.configName,
            value: config.configValue
          })
        }
      }

      // Delete the topic
      logger.info(`Deleting topic ${topic}`)
      await this.admin.deleteTopics({ topics: [topic] })

      // Wait for deletion to complete
      await new Promise(resolve => setTimeout(resolve, 2000))

      // Recreate the topic with same configuration
      logger.info(`Recreating topic ${topic} with ${numPartitions} partitions`)
      await this.admin.createTopics({
        topics: [{
          topic,
          numPartitions,
          replicationFactor,
          configEntries
        }]
      })

      // Wait for creation to complete
      await new Promise(resolve => setTimeout(resolve, 1000))

      logger.info(`Successfully recreated topic ${topic} - all data cleared`)

    } catch (error) {
      logger.error(`Failed to recreate topic ${topic}:`, error)
      throw error
    }
  }
}
