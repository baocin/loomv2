import { Router } from 'express'
import { DatabaseClient } from '../database/client'
import { logger } from '../utils/logger'

export function createPipelineRoutes(databaseClient: DatabaseClient): Router {
  const router = Router()

  // Get all pipeline flows
  router.get('/flows', async (req, res) => {
    try {
      const flows = await databaseClient.getPipelineFlows()
      res.json(flows)
    } catch (error) {
      logger.error('Failed to get pipeline flows', error)
      res.status(500).json({ error: 'Failed to fetch pipeline flows' })
    }
  })

  // Get pipeline stages (optionally filtered by flow)
  router.get('/stages', async (req, res) => {
    try {
      const { flow } = req.query
      const stages = await databaseClient.getPipelineStages(flow as string)
      res.json(stages)
    } catch (error) {
      logger.error('Failed to get pipeline stages', error)
      res.status(500).json({ error: 'Failed to fetch pipeline stages' })
    }
  })

  // Get topic mappings with their metadata
  router.get('/topics', async (req, res) => {
    try {
      const topics = await databaseClient.getTopicMappings()
      res.json(topics)
    } catch (error) {
      logger.error('Failed to get topic mappings', error)
      res.status(500).json({ error: 'Failed to fetch topic mappings' })
    }
  })

  // Get complete pipeline topology
  router.get('/topology', async (req, res) => {
    try {
      const topology = await databaseClient.getPipelineTopology()
      res.json(topology)
    } catch (error) {
      logger.error('Failed to get pipeline topology', error)
      res.status(500).json({ error: 'Failed to fetch pipeline topology' })
    }
  })

  // Get service dependencies
  router.get('/dependencies', async (req, res) => {
    try {
      const dependencies = await databaseClient.getServiceDependencies()
      res.json(dependencies)
    } catch (error) {
      logger.error('Failed to get service dependencies', error)
      res.status(500).json({ error: 'Failed to fetch service dependencies' })
    }
  })

  // Get flow details with all stages
  router.get('/flows/:flowName', async (req, res) => {
    try {
      const { flowName } = req.params
      const stages = await databaseClient.getPipelineStages(flowName)

      if (stages.length === 0) {
        res.status(404).json({ error: 'Flow not found' })
        return
      }

      // Get flow metadata
      const flows = await databaseClient.getPipelineFlows()
      const flow = flows.find(f => f.flow_name === flowName)

      res.json({
        flow,
        stages,
        stageCount: stages.length,
        inputTopics: [...new Set(stages.flatMap(s => s.input_topics || []))],
        outputTopics: [...new Set(stages.flatMap(s => s.output_topics || []))],
        errorTopics: [...new Set(stages.flatMap(s => s.error_topics || []))]
      })
    } catch (error) {
      logger.error(`Failed to get flow details for ${req.params.flowName}`, error)
      res.status(500).json({ error: 'Failed to fetch flow details' })
    }
  })

  // Get service-specific pipelines
  router.get('/services/:serviceName', async (req, res) => {
    try {
      const { serviceName } = req.params
      const stages = await databaseClient.getPipelineStages()

      const serviceStages = stages.filter(s => s.service_name === serviceName)

      if (serviceStages.length === 0) {
        res.status(404).json({ error: 'Service not found in any pipeline' })
        return
      }

      res.json({
        service: serviceName,
        stages: serviceStages,
        flows: [...new Set(serviceStages.map(s => s.flow_name))],
        inputTopics: [...new Set(serviceStages.flatMap(s => s.input_topics || []))],
        outputTopics: [...new Set(serviceStages.flatMap(s => s.output_topics || []))]
      })
    } catch (error) {
      logger.error(`Failed to get pipelines for service ${req.params.serviceName}`, error)
      res.status(500).json({ error: 'Failed to fetch service pipelines' })
    }
  })

  // Get topic lineage (what produces and consumes a topic)
  router.get('/topics/:topicName/lineage', async (req, res) => {
    try {
      const { topicName } = req.params
      const stages = await databaseClient.getPipelineStages()
      const topics = await databaseClient.getTopicMappings()

      const topic = topics.find(t => t.topic_name === topicName)
      if (!topic) {
        res.status(404).json({ error: 'Topic not found' })
        return
      }

      const producers = stages.filter(s =>
        s.output_topics && s.output_topics.includes(topicName)
      )

      const consumers = stages.filter(s =>
        s.input_topics && s.input_topics.includes(topicName)
      )

      res.json({
        topic,
        producers: producers.map(s => ({
          flow: s.flow_name,
          stage: s.stage_name,
          service: s.service_name
        })),
        consumers: consumers.map(s => ({
          flow: s.flow_name,
          stage: s.stage_name,
          service: s.service_name
        })),
        apiEndpoints: topic.primary_endpoints || [],
        storageTable: topic.table_name
      })
    } catch (error) {
      logger.error(`Failed to get lineage for topic ${req.params.topicName}`, error)
      res.status(500).json({ error: 'Failed to fetch topic lineage' })
    }
  })

  return router
}
