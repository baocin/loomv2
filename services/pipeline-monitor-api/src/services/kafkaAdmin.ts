import { Kafka, Admin, GroupDescription } from 'kafkajs'
import { logger } from '../utils/logger'

interface ConsumerLagInfo {
  groupId: string
  topic: string
  partition: number
  currentOffset: string
  logEndOffset: string
  lag: string
}

interface ConsumerGroupLag {
  serviceName: string
  topic: string
  totalLag: number
  partitionCount: number
  lastUpdate: Date
}

export class KafkaAdminService {
  private kafka: Kafka
  private admin: Admin | null = null

  constructor() {
    const brokers = process.env.KAFKA_BOOTSTRAP_SERVERS || 'kafka:9092'

    this.kafka = new Kafka({
      clientId: 'pipeline-monitor-admin',
      brokers: brokers.split(','),
      connectionTimeout: 10000,
      requestTimeout: 30000,
    })
  }

  async connect(): Promise<void> {
    try {
      this.admin = this.kafka.admin()
      await this.admin.connect()
      logger.info('Kafka admin connected')
    } catch (error) {
      logger.error('Failed to connect Kafka admin:', error)
      throw error
    }
  }

  async disconnect(): Promise<void> {
    if (this.admin) {
      await this.admin.disconnect()
      this.admin = null
    }
  }

  async getConsumerGroupLag(groupId?: string): Promise<ConsumerGroupLag[]> {
    if (!this.admin) {
      await this.connect()
    }

    try {
      // Get all consumer groups or specific one
      let groupsList: { groupId: string }[]

      if (groupId) {
        groupsList = [{ groupId }]
      } else {
        const listResult = await this.admin!.listGroups()
        groupsList = listResult.groups
      }

      const lagResults: ConsumerGroupLag[] = []

      for (const group of groupsList) {
        try {
          // Get group description
          const groupDescriptions = await this.admin!.describeGroups([group.groupId])
          if (groupDescriptions.groups.length === 0) continue

          const groupDesc = groupDescriptions.groups[0]
          if (groupDesc.state !== 'Stable') continue

          // Get offsets for this group
          const topicOffsets = await this.admin!.fetchOffsets({
            groupId: group.groupId
          })

          // Group by topic
          const topicLagMap = new Map<string, { totalLag: number, partitionCount: number }>()

          for (const { topic, partitions } of topicOffsets) {
            let totalLag = 0
            let partitionCount = 0

            // Get topic metadata to find end offsets
            const topicMetadata = await this.admin!.fetchTopicMetadata({
              topics: [topic]
            })

            if (topicMetadata.topics.length === 0) continue

            const topicPartitions = topicMetadata.topics[0].partitions

            for (const partition of partitions) {
              const topicPartition = topicPartitions.find(p => p.partitionId === partition.partition)
              if (!topicPartition) continue

              // Fetch latest offset for this partition
              const latestOffsets = await this.admin!.fetchTopicOffsets(topic)
              const latestOffset = latestOffsets.find(o => o.partition === partition.partition)

              if (latestOffset && partition.offset !== '-1') {
                const lag = parseInt(latestOffset.high) - parseInt(partition.offset)
                totalLag += lag
                partitionCount++
              }
            }

            if (partitionCount > 0) {
              topicLagMap.set(topic, { totalLag, partitionCount })
            }
          }

          // Convert to result format
          for (const [topic, lagInfo] of topicLagMap) {
            lagResults.push({
              serviceName: group.groupId,
              topic,
              totalLag: lagInfo.totalLag,
              partitionCount: lagInfo.partitionCount,
              lastUpdate: new Date()
            })
          }
        } catch (error) {
          logger.warn(`Failed to get lag for group ${group.groupId}:`, error)
        }
      }

      return lagResults
    } catch (error) {
      logger.error('Failed to get consumer group lag:', error)
      throw error
    }
  }

  async getConsumerGroups(): Promise<string[]> {
    if (!this.admin) {
      await this.connect()
    }

    try {
      const result = await this.admin!.listGroups()
      return result.groups.map((g: { groupId: string }) => g.groupId)
    } catch (error) {
      logger.error('Failed to list consumer groups:', error)
      throw error
    }
  }
}

// Singleton instance
export const kafkaAdmin = new KafkaAdminService()
