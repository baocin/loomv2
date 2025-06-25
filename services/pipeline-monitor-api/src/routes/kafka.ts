import { Router } from 'express'
import { KafkaMetricsCollector } from '../kafka/metrics'
import { KafkaClient } from '../kafka/client'
import { MemoryCache } from '../utils/cache'
import { logger } from '../utils/logger'
import { config } from '../config'
import { PipelineBuilder } from '../services/pipelineBuilder'

export function createKafkaRoutes(
  kafkaClient: KafkaClient,
  metricsCollector: KafkaMetricsCollector
): Router {
  const router = Router()
  const messageCache = new MemoryCache<any>(config.cache.cacheTimeout)
  const pipelineBuilder = new PipelineBuilder(kafkaClient, metricsCollector)

  // Get pipeline structure
  router.get('/pipeline', async (req, res) => {
    try {
      const pipeline = await pipelineBuilder.buildPipeline()
      res.json(pipeline)
    } catch (error) {
      logger.error('Failed to build pipeline', error)
      res.status(500).json({ error: 'Failed to build pipeline structure' })
    }
  })

  // Get all topic metrics
  router.get('/topics/metrics', async (req, res) => {
    try {
      const metrics = await metricsCollector.collectTopicMetrics()
      res.json(metrics)
    } catch (error) {
      logger.error('Failed to get topic metrics', error)
      res.status(500).json({ error: 'Failed to fetch topic metrics' })
    }
  })

  // Get consumer metrics
  router.get('/consumers/metrics', async (req, res) => {
    try {
      const metrics = await metricsCollector.collectConsumerMetrics()
      res.json(metrics)
    } catch (error) {
      logger.error('Failed to get consumer metrics', error)
      res.status(500).json({ error: 'Failed to fetch consumer metrics' })
    }
  })

  // Get latest message from a topic
  router.get('/topics/:topic/latest', async (req, res) => {
    const { topic } = req.params

    try {
      // Check cache first
      const cacheKey = `latest_${topic}`
      let message = messageCache.get(cacheKey)

      if (!message) {
        message = await kafkaClient.getLatestMessage(topic)
        if (message) {
          messageCache.set(cacheKey, message)
        }
      }

      if (!message) {
        res.status(404).json({ error: 'No messages found in topic' })
        return
      }

      res.json(message)
    } catch (error) {
      logger.error(`Failed to get latest message from topic ${topic}`, error)
      res.status(500).json({ error: 'Failed to fetch latest message' })
    }
  })

  // Get topic metadata
  router.get('/topics/:topic/metadata', async (req, res) => {
    const { topic } = req.params

    try {
      const metadata = await kafkaClient.getTopicMetadata(topic)

      if (!metadata) {
        res.status(404).json({ error: 'Topic not found' })
        return
      }

      res.json(metadata)
    } catch (error) {
      logger.error(`Failed to get metadata for topic ${topic}`, error)
      res.status(500).json({ error: 'Failed to fetch topic metadata' })
    }
  })

  // List all topics
  router.get('/topics', async (req, res) => {
    try {
      const topics = await kafkaClient.getTopics()

      // Filter out internal topics
      const userTopics = topics.filter(topic =>
        !topic.startsWith('__') && !topic.startsWith('_')
      )

      res.json(userTopics)
    } catch (error) {
      logger.error('Failed to list topics', error)
      res.status(500).json({ error: 'Failed to fetch topics' })
    }
  })

  // Get consumer groups
  router.get('/consumers', async (req, res) => {
    try {
      const groups = await kafkaClient.getConsumerGroups()

      // Filter out internal groups
      const userGroups = groups.filter(group =>
        !group.groupId.startsWith('__') && !group.groupId.startsWith('_')
      )

      res.json(userGroups)
    } catch (error) {
      logger.error('Failed to list consumer groups', error)
      res.status(500).json({ error: 'Failed to fetch consumer groups' })
    }
  })

  // Get consumer group details
  router.get('/consumers/:groupId/offsets', async (req, res) => {
    const { groupId } = req.params
    const { topics } = req.query

    try {
      const topicList = topics ? (topics as string).split(',') : undefined
      const offsets = await kafkaClient.getConsumerGroupOffsets(groupId, topicList)
      res.json(offsets)
    } catch (error) {
      logger.error(`Failed to get offsets for consumer group ${groupId}`, error)
      res.status(500).json({ error: 'Failed to fetch consumer group offsets' })
    }
  })

  // Clear all cached data
  router.post('/cache/clear', async (req, res) => {
    try {
      // Clear message cache
      messageCache.clear()

      // Clear metrics collector caches
      metricsCollector.clearCaches()

      logger.info('Successfully cleared all caches')
      res.json({ message: 'All caches cleared successfully' })
    } catch (error) {
      logger.error('Failed to clear caches', error)
      res.status(500).json({ error: 'Failed to clear caches' })
    }
  })

  // DANGER: Clear all messages from all topics
  router.post('/topics/clear-all', async (req, res) => {
    try {
      logger.warn('DESTRUCTIVE OPERATION: Clearing all Kafka topic messages')

      // Get all topics first
      const topics = await kafkaClient.getTopics()
      const userTopics = topics.filter(topic =>
        !topic.startsWith('__') && !topic.startsWith('_')
      )

      logger.info(`Found ${userTopics.length} user topics to clear`)

      const results = []

      for (const topic of userTopics) {
        try {
          // Get topic metadata to find partitions
          const metadata = await kafkaClient.getTopicMetadata(topic)
          if (metadata && metadata.partitions) {
            // Clear each partition by seeking to end
            for (const partition of metadata.partitions) {
              try {
                await kafkaClient.clearTopicPartition(topic, partition.partitionId)
                logger.info(`Cleared topic ${topic} partition ${partition.partitionId}`)
              } catch (partitionError) {
                logger.error(`Failed to clear ${topic} partition ${partition.partitionId}:`, partitionError)
                results.push({
                  topic,
                  partition: partition.partitionId,
                  status: 'error',
                  error: partitionError instanceof Error ? partitionError.message : String(partitionError)
                })
              }
            }
            results.push({
              topic,
              status: 'cleared',
              partitions: metadata.partitions.length
            })
          } else {
            results.push({
              topic,
              status: 'error',
              error: 'Could not get topic metadata'
            })
          }
        } catch (topicError) {
          logger.error(`Failed to process topic ${topic}:`, topicError)
          results.push({
            topic,
            status: 'error',
            error: topicError instanceof Error ? topicError.message : String(topicError)
          })
        }
      }

      // Clear all caches after clearing topics
      messageCache.clear()
      metricsCollector.clearCaches()

      logger.warn(`Completed clearing ${userTopics.length} topics`)

      res.json({
        message: `Cleared messages from ${userTopics.length} topics`,
        results,
        totalTopics: userTopics.length,
        clearedSuccessfully: results.filter(r => r.status === 'cleared').length,
        errors: results.filter(r => r.status === 'error').length
      })

    } catch (error) {
      logger.error('Failed to clear all topics:', error)
      res.status(500).json({
        error: 'Failed to clear topics',
        details: error instanceof Error ? error.message : String(error)
      })
    }
  })

  return router
}
