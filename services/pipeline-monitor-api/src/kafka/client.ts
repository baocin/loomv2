import { Kafka, Admin, Consumer, Producer } from 'kafkajs'
import { config } from '../config'
import { logger } from '../utils/logger'

export class KafkaClient {
  private kafka: Kafka
  private admin: Admin | null = null
  private producer: Producer | null = null
  private consumers: Map<string, Consumer> = new Map()
  private streamConsumers: Map<string, { consumer: Consumer; refCount: number }> = new Map()
  
  // Use a single monitoring consumer group instead of creating new ones
  private monitoringConsumer: Consumer | null = null
  private readonly MONITOR_GROUP_ID = 'pipeline-monitor-api'

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

      // Create a single monitoring consumer
      this.monitoringConsumer = this.kafka.consumer({
        groupId: this.MONITOR_GROUP_ID,
        sessionTimeout: 30000,
        heartbeatInterval: 3000,
        maxWaitTimeInMs: 1000,
      })
      await this.monitoringConsumer.connect()

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

      if (this.monitoringConsumer) {
        await this.monitoringConsumer.disconnect()
        this.monitoringConsumer = null
      }

      for (const [groupId, consumer] of this.consumers) {
        await consumer.disconnect()
        this.consumers.delete(groupId)
      }

      // Clean up stream consumers
      for (const [topic, { consumer }] of this.streamConsumers) {
        try {
          await consumer.stop()
          await consumer.disconnect()
        } catch (error) {
          logger.error(`Error disconnecting stream consumer for topic ${topic}`, error)
        }
      }
      this.streamConsumers.clear()

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
      logger.error('Failed to list consumer groups', error)
      throw error
    }
  }

  async getConsumerGroupDetails(groupId: string) {
    if (!this.admin) throw new Error('Kafka admin not connected')

    try {
      const description = await this.admin.describeGroups([groupId])
      return description.groups[0]
    } catch (error) {
      logger.error(`Failed to describe group ${groupId}`, error)
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
    if (!this.admin) throw new Error('Kafka admin not connected')

    try {
      // Get the latest offset for the topic
      const offsets = await this.getTopicOffsets(topic)
      const partitionOffset = offsets.find(o => o.partition === partition)
      
      if (!partitionOffset || partitionOffset.high === '0') {
        return null
      }

      // Calculate the offset to fetch (latest - 1)
      const targetOffset = (BigInt(partitionOffset.high) - BigInt(1)).toString()

      // Use admin client to fetch the specific message
      const topicOffsets = [{
        topic,
        partitions: [{
          partition,
          offset: targetOffset
        }]
      }]

      // Unfortunately, KafkaJS doesn't provide a direct way to fetch a single message
      // without creating a consumer. For now, we'll return null to avoid creating
      // new consumer groups. The frontend can use the streaming API instead.
      logger.warn(`getLatestMessage is deprecated to avoid creating consumer groups. Use streaming API instead.`)
      return null
    } catch (error) {
      logger.error(`Failed to fetch latest message from ${topic}`, error)
      return null
    }
  }

  async streamMessages(
    topic: string,
    onMessage: (message: any) => void,
    fromBeginning = false
  ): Promise<() => Promise<void>> {
    // Reuse existing stream consumer if available
    const existingStream = this.streamConsumers.get(topic)
    if (existingStream) {
      existingStream.refCount++
      logger.info(`Reusing existing stream consumer for topic ${topic}, refCount: ${existingStream.refCount}`)
      
      return async () => {
        existingStream.refCount--
        if (existingStream.refCount <= 0) {
          logger.info(`Stopping stream consumer for topic ${topic}`)
          await existingStream.consumer.stop()
          await existingStream.consumer.disconnect()
          this.streamConsumers.delete(topic)
        }
      }
    }

    // Create a shared consumer group for streaming
    const groupId = `pipeline-monitor-stream-${topic}`
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

    try {
      await consumer.connect()
      await consumer.subscribe({ topic, fromBeginning })

      await consumer.run({
        eachMessage: async ({ message, partition }) => {
          try {
            const messageData = {
              key: message.key?.toString(),
              value: message.value ? JSON.parse(message.value.toString()) : null,
              timestamp: new Date(parseInt(message.timestamp)),
              offset: message.offset,
              partition: partition,
            }
            onMessage(messageData)
          } catch (error) {
            logger.error('Error processing message', error)
          }
        },
      })

      // Store the consumer for reuse
      this.streamConsumers.set(topic, { consumer, refCount: 1 })

      // Return cleanup function
      return async () => {
        const stream = this.streamConsumers.get(topic)
        if (stream) {
          stream.refCount--
          if (stream.refCount <= 0) {
            logger.info(`Stopping stream consumer for topic ${topic}`)
            await consumer.stop()
            await consumer.disconnect()
            this.streamConsumers.delete(topic)
          }
        }
      }
    } catch (error) {
      logger.error(`Failed to stream messages from ${topic}`, error)
      throw error
    }
  }

  async produceMessage(topic: string, message: any): Promise<void> {
    if (!this.producer) throw new Error('Producer not connected')

    try {
      await this.producer.send({
        topic,
        messages: [
          {
            key: message.key || null,
            value: JSON.stringify(message.value),
            timestamp: Date.now().toString(),
          },
        ],
      })
    } catch (error) {
      logger.error(`Failed to produce message to ${topic}`, error)
      throw error
    }
  }

  async getConsumerGroupSubscriptions(): Promise<Map<string, string[]>> {
    if (!this.admin) throw new Error('Kafka admin not connected')

    try {
      const groups = await this.admin.listGroups()
      const subscriptions = new Map<string, string[]>()

      for (const group of groups.groups) {
        try {
          const description = await this.admin.describeGroups([group.groupId])
          if (description.groups[0] && description.groups[0].members) {
            const topics = new Set<string>()
            for (const member of description.groups[0].members) {
              const assignment = member.memberAssignment
              if (assignment) {
                // Parse the member assignment to extract topics
                // This is a simplified version - actual parsing might be more complex
                // For now, we'll just add a placeholder
                logger.debug(`Member ${member.memberId} assignment parsing not implemented`)
              }
            }
            if (topics.size > 0) {
              subscriptions.set(group.groupId, Array.from(topics))
            }
          }
        } catch (error) {
          logger.debug(`Failed to describe group ${group.groupId}`, error)
        }
      }

      return subscriptions
    } catch (error) {
      logger.error('Failed to get consumer group subscriptions', error)
      throw error
    }
  }

  async getConsumerLag(groupId: string, topics?: string[]): Promise<any> {
    if (!this.admin) throw new Error('Kafka admin not connected')

    try {
      const groupOffsets = await this.admin.fetchOffsets({ groupId, topics })
      const lag: any[] = []

      for (const topicOffset of groupOffsets) {
        const topicHighWatermarks = await this.admin.fetchTopicOffsets(topicOffset.topic)

        for (const partition of topicOffset.partitions) {
          const highWatermark = topicHighWatermarks.find(
            hw => hw.partition === partition.partition
          )

          if (highWatermark && partition.offset) {
            const currentLag = parseInt(highWatermark.high) - parseInt(partition.offset)
            lag.push({
              topic: topicOffset.topic,
              partition: partition.partition,
              currentOffset: partition.offset,
              highWatermark: highWatermark.high,
              lag: currentLag
            })
          }
        }
      }

      return lag
    } catch (error) {
      logger.error(`Failed to calculate lag for group ${groupId}`, error)
      throw error
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
      const replicationFactor = topicInfo.partitions[0]?.replicas?.length || 1

      // Delete the topic
      await this.admin.deleteTopics({
        topics: [topic],
        timeout: 30000
      })

      // Wait a moment for deletion to propagate
      await new Promise(resolve => setTimeout(resolve, 2000))

      // Recreate the topic with same configuration
      await this.admin.createTopics({
        topics: [{
          topic,
          numPartitions,
          replicationFactor,
        }],
        waitForLeaders: true,
        timeout: 30000
      })

      logger.info(`Successfully recreated topic ${topic} with ${numPartitions} partitions`)
    } catch (error) {
      logger.error(`Failed to recreate topic ${topic}:`, error)
      throw error
    }
  }
}

export const kafkaClient = new KafkaClient()