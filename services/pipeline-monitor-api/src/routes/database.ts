import { Router } from 'express'
import { DatabaseClient } from '../database/client'
import { logger } from '../utils/logger'

export function createDatabaseRoutes(databaseClient: DatabaseClient): Router {
  const router = Router()

  // Get database metrics
  router.get('/metrics', async (req, res) => {
    try {
      const metrics = await databaseClient.getMetrics()
      res.json(metrics)
    } catch (error) {
      logger.error('Failed to get database metrics', error)
      res.status(500).json({ error: 'Failed to fetch database metrics' })
    }
  })

  // Get table metrics
  router.get('/tables', async (req, res) => {
    try {
      const tables = await databaseClient.getTableMetrics()
      res.json(tables)
    } catch (error) {
      logger.error('Failed to get table metrics', error)
      res.status(500).json({ error: 'Failed to fetch table metrics' })
    }
  })

  // Test database connection
  router.get('/health', async (req, res) => {
    try {
      const isConnected = await databaseClient.testConnection()
      res.json({ connected: isConnected })
    } catch (error) {
      logger.error('Database health check failed', error)
      res.status(500).json({ connected: false, error: 'Health check failed' })
    }
  })

  return router
}
