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

  // Test pipeline flows query specifically
  router.get('/test-flows', async (req, res) => {
    try {
      logger.info('Testing getPipelineFlows directly...')
      const flows = await databaseClient.getPipelineFlows()
      logger.info(`Successfully got ${flows.length} flows`)
      res.json({ flows: flows.slice(0, 3) }) // Return first 3 for testing
    } catch (error) {
      logger.error('Failed to test pipeline flows', {
        error: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined
      })
      res.status(500).json({ error: 'Failed to test pipeline flows' })
    }
  })

  // Test topology method specifically
  router.get('/test-topology', async (req, res) => {
    try {
      logger.info('Testing getPipelineTopology directly...')
      const topology = await databaseClient.getPipelineTopology()
      logger.info('Successfully got topology')
      res.json({
        flowCount: topology.flows?.length || 0,
        stageCount: topology.stages?.length || 0,
        topicCount: topology.topics?.length || 0
      })
    } catch (error) {
      logger.error('Failed to test topology', {
        error: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined
      })
      res.status(500).json({ error: 'Failed to test topology' })
    }
  })

  return router
}
