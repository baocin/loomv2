import { Router } from 'express'
import { KafkaMetricsCollector } from '../kafka/metrics'
import { KafkaClient } from '../kafka/client'
import { DatabaseClient } from '../database/client'
import { MemoryCache } from '../utils/cache'
import { logger } from '../utils/logger'
import { config } from '../config'
import { PipelineBuilder } from '../services/pipelineBuilder'
import { K8sDiscovery } from '../services/k8sDiscovery'
import { ServiceRegistry } from '../services/serviceRegistry'
import { HealthMonitor } from '../services/healthMonitor'

export function createKafkaRoutes(
  kafkaClient: KafkaClient,
  metricsCollector: KafkaMetricsCollector,
  databaseClient: DatabaseClient,
  k8sDiscovery?: K8sDiscovery,
  serviceRegistry?: ServiceRegistry,
  healthMonitor?: HealthMonitor
): Router {
  const router = Router()
  const messageCache = new MemoryCache<any>(config.cache.cacheTimeout)
  const pipelineBuilder = new PipelineBuilder(kafkaClient, metricsCollector, databaseClient)

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

  // Get pipeline structure from database
  router.get('/pipeline/database', async (req, res) => {
    try {
      const pipeline = await pipelineBuilder.buildPipeline()
      res.json(pipeline)
    } catch (error) {
      logger.error('Failed to build pipeline from database', error)
      res.status(500).json({ error: 'Failed to build pipeline from database' })
    }
  })

  // Get pipeline topology from database
  router.get('/pipeline/topology', async (req, res) => {
    try {
      const topology = await databaseClient.getPipelineTopology()
      res.json(topology)
    } catch (error) {
      logger.error('Failed to get pipeline topology', error)
      res.status(500).json({ error: 'Failed to get pipeline topology' })
    }
  })

  // Get service dependencies from database
  router.get('/pipeline/dependencies', async (req, res) => {
    try {
      const dependencies = await databaseClient.getServiceDependencies()
      res.json(dependencies)
    } catch (error) {
      logger.error('Failed to get service dependencies', error)
      res.status(500).json({ error: 'Failed to get service dependencies' })
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
          // Recreate topic to immediately clear all data
          await kafkaClient.recreateTopic(topic)
          logger.info(`Successfully recreated topic ${topic}`)
          results.push({
            topic,
            status: 'cleared',
            method: 'recreation'
          })
        } catch (topicError) {
          logger.error(`Failed to recreate topic ${topic}:`, topicError)
          results.push({
            topic,
            status: 'error',
            error: topicError instanceof Error ? topicError.message : String(topicError),
            method: 'recreation'
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

  // Auto-discovery endpoint
  router.get('/discover/all', async (req, res) => {
    try {
      // Get all topics
      const topics = await kafkaClient.getTopics()
      const userTopics = topics.filter(topic =>
        !topic.startsWith('__') && !topic.startsWith('_')
      )

      // Get consumer groups
      const consumerGroups = await kafkaClient.getConsumerGroups()
      const userGroups = consumerGroups.filter(group =>
        !group.groupId.startsWith('__') && !group.groupId.startsWith('_')
      )

      // Get flows
      const flows = await pipelineBuilder.detectFlows()

      // Get K8s services if available
      let k8sServices: any[] = []
      if (k8sDiscovery) {
        try {
          k8sServices = await k8sDiscovery.discoverServices()
        } catch (error) {
          logger.warn('K8s discovery failed', error)
        }
      }

      // Get registered services
      let registeredServices: any[] = []
      if (serviceRegistry) {
        registeredServices = serviceRegistry.getAllServices()
      }

      // Get health statuses
      let healthStatuses: any[] = []
      if (healthMonitor) {
        healthStatuses = healthMonitor.getAllHealthStatuses()
      }

      res.json({
        topics: userTopics,
        consumers: userGroups,
        flows,
        services: {
          kubernetes: k8sServices,
          registered: registeredServices
        },
        health: healthStatuses,
        summary: {
          topicCount: userTopics.length,
          consumerCount: userGroups.length,
          flowCount: flows.length,
          serviceCount: registeredServices.length + k8sServices.length
        }
      })
    } catch (error) {
      logger.error('Failed to perform auto-discovery', error)
      res.status(500).json({ error: 'Failed to perform auto-discovery' })
    }
  })

  // Service health endpoint
  router.get('/services/health', async (req, res) => {
    try {
      if (!healthMonitor) {
        res.status(501).json({ error: 'Health monitoring not available' })
        return
      }

      const pipelineHealth = healthMonitor.getPipelineHealth()
      const healthStatuses = healthMonitor.getAllHealthStatuses()

      res.json({
        pipeline: pipelineHealth,
        services: healthStatuses,
        timestamp: new Date().toISOString()
      })
    } catch (error) {
      logger.error('Failed to get service health', error)
      res.status(500).json({ error: 'Failed to get service health' })
    }
  })

  // Service registry endpoint
  router.get('/services/registry', async (req, res) => {
    try {
      if (!serviceRegistry) {
        res.status(501).json({ error: 'Service registry not available' })
        return
      }

      const services = serviceRegistry.getAllServices()
      const topology = serviceRegistry.buildTopology()

      res.json({
        services,
        topology: Array.from(topology.entries()).map(([from, to]) => ({
          from,
          to: Array.from(to)
        })),
        timestamp: new Date().toISOString()
      })
    } catch (error) {
      logger.error('Failed to get service registry', error)
      res.status(500).json({ error: 'Failed to get service registry' })
    }
  })

  // Service metrics endpoint
  router.get('/services/:serviceId/metrics', async (req, res) => {
    try {
      const { serviceId } = req.params

      if (!healthMonitor) {
        res.status(501).json({ error: 'Health monitoring not available' })
        return
      }

      const metrics = await healthMonitor.getServiceMetrics(serviceId)
      if (!metrics) {
        res.status(404).json({ error: 'Service not found' })
        return
      }

      res.json(metrics)
    } catch (error) {
      logger.error(`Failed to get metrics for service ${req.params.serviceId}`, error)
      res.status(500).json({ error: 'Failed to get service metrics' })
    }
  })

  // Comprehensive pipeline structure endpoint
  router.get('/structure', async (req, res) => {
    try {
      // Get all topics
      const topics = await kafkaClient.getTopics()
      const userTopics = topics.filter(topic =>
        !topic.startsWith('__') && !topic.startsWith('_')
      )

      // Get consumer groups
      const consumerGroups = await kafkaClient.getConsumerGroups()
      const userGroups = consumerGroups.filter(group =>
        !group.groupId.startsWith('__') && !group.groupId.startsWith('_')
      )

      // Get consumer group subscriptions
      const subscriptions = await kafkaClient.getConsumerGroupSubscriptions()

      // Build comprehensive structure
      const structure = {
        producers: pipelineBuilder.identifyProducers(userTopics),
        topics: userTopics.map(topic => ({
          name: topic,
          category: topic.split('.')[0],
          dataType: topic.split('.')[1],
          stage: topic.endsWith('.raw') ? 'raw' :
                 topic.includes('.processed') || topic.includes('.filtered') ? 'processed' :
                 topic.includes('analysis') ? 'analysis' : 'unknown',
          description: pipelineBuilder.getTopicLabel(topic)
        })),
        consumers: userGroups.map(group => {
          const groupId = group.groupId
          const subscribedTopics = subscriptions.get(groupId) || []

          return {
            groupId,
            label: pipelineBuilder.getConsumerLabel(groupId),
            description: pipelineBuilder.getConsumerDescription(groupId),
            subscribedTopics,
            producesTopics: pipelineBuilder.determineOutputTopics(groupId, userTopics),
            status: group.state || 'unknown',
            memberCount: group.members?.length || 0
          }
        }),
        flows: await pipelineBuilder.detectFlows(),
        categories: {
          device: userTopics.filter(t => t.startsWith('device.')).length,
          media: userTopics.filter(t => t.startsWith('media.')).length,
          analysis: userTopics.filter(t => t.startsWith('analysis.')).length,
          external: userTopics.filter(t => t.startsWith('external.')).length,
          task: userTopics.filter(t => t.startsWith('task.')).length,
          digital: userTopics.filter(t => t.startsWith('digital.')).length
        },
        stats: {
          totalTopics: userTopics.length,
          totalConsumers: userGroups.length,
          totalProducers: pipelineBuilder.identifyProducers(userTopics).length,
          activeFlows: (await pipelineBuilder.detectFlows()).filter(f => f.health === 'healthy').length
        }
      }

      res.json(structure)
    } catch (error) {
      logger.error('Failed to get pipeline structure', error)
      res.status(500).json({ error: 'Failed to get pipeline structure' })
    }
  })

  return router
}
