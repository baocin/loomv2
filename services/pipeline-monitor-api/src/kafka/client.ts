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
}
