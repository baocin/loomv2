import { KafkaClient } from './client'
import { KafkaTopicMetrics, ConsumerMetrics } from '../types'
import { logger } from '../utils/logger'

export class KafkaMetricsCollector {
  private kafkaClient: KafkaClient
  private metricsCache: Map<string, KafkaTopicMetrics> = new Map()
  private consumerCache: Map<string, ConsumerMetrics[]> = new Map()
  private lastUpdate: Date = new Date()

  constructor(kafkaClient: KafkaClient) {
    this.kafkaClient = kafkaClient
  }

  async collectTopicMetrics(): Promise<KafkaTopicMetrics[]> {
    try {
      const topics = await this.kafkaClient.getTopics()
      const metrics: KafkaTopicMetrics[] = []

      for (const topic of topics) {
        // Skip internal Kafka topics
        if (topic.startsWith('__') || topic.startsWith('_')) {
          continue
        }

        try {
          const topicMetrics = await this.getTopicMetrics(topic)
          metrics.push(topicMetrics)
          this.metricsCache.set(topic, topicMetrics)
        } catch (error) {
          logger.warn(`Failed to collect metrics for topic ${topic}`, error)

          // Use cached data if available
          const cached = this.metricsCache.get(topic)
          if (cached) {
            metrics.push({ ...cached, isActive: false })
          }
        }
      }

      this.lastUpdate = new Date()
      return metrics
    } catch (error) {
      logger.error('Failed to collect topic metrics', error)
      return Array.from(this.metricsCache.values())
    }
  }

  async collectConsumerMetrics(): Promise<ConsumerMetrics[]> {
    try {
      const groups = await this.kafkaClient.getConsumerGroups()
      const allMetrics: ConsumerMetrics[] = []

      for (const group of groups) {
        if (group.groupId.startsWith('__') || group.groupId.startsWith('_')) {
          continue
        }

        try {
          const consumerMetrics = await this.getConsumerGroupMetrics(group.groupId)
          allMetrics.push(...consumerMetrics)
        } catch (error) {
          logger.warn(`Failed to collect metrics for consumer group ${group.groupId}`, error)

          // Use cached data if available
          const cached = this.consumerCache.get(group.groupId)
          if (cached) {
            allMetrics.push(...cached)
          }
        }
      }

      return allMetrics
    } catch (error) {
      logger.error('Failed to collect consumer metrics', error)
      return []
    }
  }

  private async getTopicMetrics(topic: string): Promise<KafkaTopicMetrics> {
    const metadata = await this.kafkaClient.getTopicMetadata(topic)
    const offsets = await this.kafkaClient.getTopicOffsets(topic)

    if (!metadata) {
      throw new Error(`Topic ${topic} not found`)
    }

    // Calculate total messages across all partitions
    const messageCount = offsets.reduce((total, partition) => {
      return total + parseInt(partition.high) - parseInt(partition.low)
    }, 0)

    // Try to get the latest message to determine last message time
    let lastMessageTime: Date | undefined
    try {
      const latestMessage = await this.kafkaClient.getLatestMessage(topic)
      if (latestMessage?.timestamp) {
        lastMessageTime = latestMessage.timestamp
      }
    } catch (error) {
      // Ignore errors when fetching latest message
    }

    // Calculate if topic is active (has recent messages)
    const isActive = lastMessageTime ?
      (new Date().getTime() - lastMessageTime.getTime()) < 300000 : // 5 minutes
      messageCount > 0

    return {
      topic,
      lastMessageTime,
      messageCount,
      partitionCount: metadata.partitions.length,
      consumerLag: 0, // Will be calculated from consumer metrics
      producerRate: 0, // Would need historical data
      consumerRate: 0, // Would need historical data
      isActive,
    }
  }

  private async getConsumerGroupMetrics(groupId: string): Promise<ConsumerMetrics[]> {
    try {
      const offsets = await this.kafkaClient.getConsumerGroupOffsets(groupId)
      const metrics: ConsumerMetrics[] = []

      for (const topicOffset of offsets) {
        for (const partitionOffset of topicOffset.partitions) {
          // Get topic high water mark
          const topicOffsets = await this.kafkaClient.getTopicOffsets(topicOffset.topic)
          const partitionHighWaterMark = topicOffsets.find(
            p => p.partition === partitionOffset.partition
          )?.high || '0'

          const currentOffset = parseInt(partitionOffset.offset)
          const logEndOffset = parseInt(partitionHighWaterMark)
          const lag = Math.max(0, logEndOffset - currentOffset)

          metrics.push({
            groupId,
            topic: topicOffset.topic,
            partition: partitionOffset.partition,
            currentOffset,
            logEndOffset,
            lag,
            consumerId: `${groupId}-${partitionOffset.partition}`,
            host: 'unknown', // Would need consumer group description API
            lastHeartbeat: new Date(), // Approximate
          })
        }
      }

      this.consumerCache.set(groupId, metrics)
      return metrics
    } catch (error) {
      logger.error(`Failed to get consumer metrics for group ${groupId}`, error)
      return []
    }
  }

  getCachedTopicMetrics(): KafkaTopicMetrics[] {
    return Array.from(this.metricsCache.values())
  }

  getCachedConsumerMetrics(): ConsumerMetrics[] {
    return Array.from(this.consumerCache.values()).flat()
  }

  getLastUpdateTime(): Date {
    return this.lastUpdate
  }
}
