import { Router } from 'express'
import { exec } from 'child_process'
import { promisify } from 'util'
import { DatabaseClient } from '../database/client'
import { logger } from '../utils/logger'
import { kafkaAdmin } from '../services/kafkaAdmin'

const execAsync = promisify(exec)

export function createConsumerRoutes(databaseClient: DatabaseClient): Router {
  const router = Router()

  // Get all consumer groups
  router.get('/groups', async (req, res) => {
    try {
      const groups = await kafkaAdmin.getConsumerGroups()
      res.json(groups)
    } catch (error) {
      logger.error('Failed to list consumer groups', error)
      res.status(500).json({ error: 'Failed to list consumer groups' })
    }
  })

  // Get consumer metrics
  router.get('/metrics', async (req, res) => {
    try {
      const { service, timeRange = '1 hour' } = req.query
      const metrics = await databaseClient.getConsumerMetrics(
        service as string | undefined,
        timeRange as string
      )
      res.json(metrics)
    } catch (error) {
      logger.error('Failed to get consumer metrics', error)
      res.status(500).json({ error: 'Failed to fetch consumer metrics' })
    }
  })

  // Get consumer lag - now fetches directly from Kafka
  router.get('/lag', async (req, res) => {
    try {
      const { service } = req.query

      // Fetch lag directly from Kafka admin
      const kafkaLag = await kafkaAdmin.getConsumerGroupLag(service as string | undefined)

      // Transform to match expected format
      const formattedLag = kafkaLag.map(lag => ({
        service_name: lag.serviceName,
        topic: lag.topic,
        total_lag: lag.totalLag.toString(),
        partition_count: lag.partitionCount,
        last_update: lag.lastUpdate.toISOString()
      }))

      res.json(formattedLag)
    } catch (error) {
      logger.error('Failed to get consumer lag from Kafka', error)

      // Fallback to database if Kafka admin fails
      try {
        const dbLag = await databaseClient.getConsumerLag(req.query.service as string | undefined)
        res.json(dbLag)
      } catch (dbError) {
        logger.error('Failed to get consumer lag from database', dbError)
        res.status(500).json({ error: 'Failed to fetch consumer lag' })
      }
    }
  })

  // Get message flow metrics
  router.get('/flow', async (req, res) => {
    try {
      const { timeRange = '1 hour' } = req.query
      const flow = await databaseClient.getMessageFlow(timeRange as string)
      res.json(flow)
    } catch (error) {
      logger.error('Failed to get message flow', error)
      res.status(500).json({ error: 'Failed to fetch message flow' })
    }
  })

  // Get consumer logs
  router.get('/:serviceName/logs', async (req, res) => {
    try {
      const { serviceName } = req.params
      const { lines = '500' } = req.query

      // Map service name to container name
      const containerName = `loomv2-${serviceName}-1`

      try {
        // Execute docker logs command
        const { stdout, stderr } = await execAsync(
          `docker logs ${containerName} --tail ${lines} 2>&1`
        )

        // Split logs into lines and return
        const logLines = stdout.split('\n').filter(line => line.trim())

        res.json({
          service: serviceName,
          container: containerName,
          lines: logLines.length,
          logs: logLines
        })
      } catch (dockerError: any) {
        // If container not found, try k8s pod
        try {
          const { stdout } = await execAsync(
            `kubectl logs -n loom-dev deployment/${serviceName} --tail=${lines}`
          )

          const logLines = stdout.split('\n').filter(line => line.trim())

          res.json({
            service: serviceName,
            deployment: serviceName,
            lines: logLines.length,
            logs: logLines
          })
        } catch (k8sError) {
          logger.error(`Failed to get logs for ${serviceName}`, { dockerError, k8sError })
          res.status(404).json({
            error: 'Service logs not found',
            service: serviceName,
            triedContainers: [containerName, `deployment/${serviceName}`]
          })
        }
      }
    } catch (error) {
      logger.error(`Failed to get logs for ${req.params.serviceName}`, error)
      res.status(500).json({ error: 'Failed to fetch consumer logs' })
    }
  })

  // Get consumer status with detailed metrics
  router.get('/:serviceName/status', async (req, res) => {
    try {
      const { serviceName } = req.params

      // Get various metrics for this consumer
      const [metrics, lag, stages] = await Promise.all([
        databaseClient.getConsumerMetrics(serviceName, '1 hour'),
        databaseClient.getConsumerLag(serviceName),
        databaseClient.getPipelineStages()
      ])

      // Find stages for this service
      const serviceStages = stages.filter(s => s.service_name === serviceName)

      // Calculate aggregate metrics
      const totalMessagesProcessed = metrics.reduce((sum, m) =>
        sum + parseInt(m.total_messages_processed || '0'), 0
      )

      const avgProcessingTime = metrics.length > 0
        ? metrics.reduce((sum, m) => sum + parseFloat(m.avg_processing_time_ms || '0'), 0) / metrics.length
        : 0

      const totalLag = lag.reduce((sum, l) => sum + parseInt(l.total_lag || '0'), 0)

      res.json({
        service: serviceName,
        status: totalLag > 1000 ? 'lagging' : 'healthy',
        metrics: {
          totalMessagesProcessed,
          avgProcessingTime,
          totalLag,
          lastUpdate: metrics[0]?.last_update || null
        },
        stages: serviceStages.map(s => ({
          flow: s.flow_name,
          stage: s.stage_name,
          inputs: s.input_topics || [],
          outputs: s.output_topics || [],
          config: {
            replicas: s.replicas,
            timeout: s.processing_timeout_seconds,
            sla: s.sla_seconds
          }
        })),
        lag: lag.map(l => ({
          topic: l.topic,
          lag: parseInt(l.total_lag || '0'),
          partitions: parseInt(l.partition_count || '0')
        }))
      })
    } catch (error) {
      logger.error(`Failed to get status for ${req.params.serviceName}`, error)
      res.status(500).json({ error: 'Failed to fetch consumer status' })
    }
  })

  return router
}
