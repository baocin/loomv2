import { Router } from 'express'
import { KafkaClient } from '../kafka/client'
import { DatabaseClient } from '../database/client'
import { KafkaMetricsCollector } from '../kafka/metrics'
import { SystemHealth } from '../types'
import { logger } from '../utils/logger'

export function createHealthRoutes(
  kafkaClient: KafkaClient,
  databaseClient: DatabaseClient,
  metricsCollector: KafkaMetricsCollector
): Router {
  const router = Router()

  // Overall system health
  router.get('/', async (req, res) => {
    try {
      const health: SystemHealth = {
        kafka: {
          connected: false,
          brokers: 0,
          topics: 0,
        },
        database: {
          connected: false,
          metrics: {
            totalTables: 0,
            totalRows: 0,
            databaseSize: '0 bytes',
            activeConnections: 0,
            avgQueryTime: 0,
            slowQueries: 0,
          },
        },
        consumers: {
          active: 0,
          total: 0,
        },
      }

      // Check Kafka health
      try {
        const topics = await kafkaClient.getTopics()
        const groups = await kafkaClient.getConsumerGroups()

        health.kafka.connected = true
        health.kafka.topics = topics.filter(t => !t.startsWith('__') && !t.startsWith('_')).length
        health.kafka.brokers = 1 // Would need cluster info for accurate count

        health.consumers.total = groups.filter(g =>
          !g.groupId.startsWith('__') && !g.groupId.startsWith('_')
        ).length

        // Get active consumers
        const consumerMetrics = await metricsCollector.collectConsumerMetrics()
        health.consumers.active = consumerMetrics.filter(c =>
          new Date().getTime() - new Date(c.lastHeartbeat).getTime() < 60000
        ).length

      } catch (error) {
        logger.warn('Kafka health check failed', error)
      }

      // Check database health
      try {
        const isConnected = await databaseClient.testConnection()
        health.database.connected = isConnected

        if (isConnected) {
          health.database.metrics = await databaseClient.getMetrics()
        }
      } catch (error) {
        logger.warn('Database health check failed', error)
      }

      // Determine overall status
      const isHealthy = health.kafka.connected && health.database.connected
      const statusCode = isHealthy ? 200 : 503

      res.status(statusCode).json({
        status: isHealthy ? 'healthy' : 'unhealthy',
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        ...health,
      })

    } catch (error) {
      logger.error('Health check failed', error)
      res.status(500).json({
        status: 'error',
        timestamp: new Date().toISOString(),
        error: 'Health check failed',
      })
    }
  })

  // Readiness probe
  router.get('/ready', async (req, res) => {
    try {
      const kafkaConnected = await kafkaClient.getTopics().then(() => true).catch(() => false)
      const dbConnected = await databaseClient.testConnection()

      const isReady = kafkaConnected && dbConnected

      res.status(isReady ? 200 : 503).json({
        ready: isReady,
        checks: {
          kafka: kafkaConnected,
          database: dbConnected,
        },
        timestamp: new Date().toISOString(),
      })
    } catch (error) {
      logger.error('Readiness check failed', error)
      res.status(503).json({
        ready: false,
        error: 'Readiness check failed',
        timestamp: new Date().toISOString(),
      })
    }
  })

  // Liveness probe
  router.get('/live', (req, res) => {
    res.json({
      alive: true,
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
    })
  })

  return router
}
