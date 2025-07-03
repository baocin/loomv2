import { KafkaClient } from '../kafka/client'
import { KafkaMetricsCollector } from '../kafka/metrics'
import { DatabaseClient } from '../database/client'
import { logger } from '../utils/logger'

interface PipelineNode {
  id: string
  type: 'kafka-topic' | 'processor' | 'database' | 'external'
  position: { x: number; y: number }
  data: {
    label: string
    status: 'active' | 'idle' | 'error' | 'unknown'
    description?: string
  }
}

interface PipelineEdge {
  id: string
  source: string
  target: string
  animated?: boolean
}

interface PipelineFlow {
  nodes: PipelineNode[]
  edges: PipelineEdge[]
}

interface TopicFlow {
  source: string
  processor: string
  destination: string
  health?: 'healthy' | 'warning' | 'error' | 'unknown'
  lag?: number
}

interface ProcessorInfo {
  id: string
  label: string
  description: string
  inputTopics: string[]
  outputTopics: string[]
  health?: 'healthy' | 'warning' | 'error' | 'unknown'
  lag?: number
}

export class PipelineBuilder {
  private kafkaClient: KafkaClient
  private metricsCollector: KafkaMetricsCollector
  private databaseClient: DatabaseClient

  constructor(kafkaClient: KafkaClient, metricsCollector: KafkaMetricsCollector, databaseClient: DatabaseClient) {
    this.kafkaClient = kafkaClient
    this.metricsCollector = metricsCollector
    this.databaseClient = databaseClient
  }

  async detectFlows(): Promise<TopicFlow[]> {
    // This method is deprecated - all flow information comes from database
    // Keeping for backwards compatibility but returns empty array
    return []
  }

  async buildPipelineFromDatabase(): Promise<PipelineFlow> {
    try {
      const topology = await this.databaseClient.getPipelineTopology()
      const { flows, stages, topics } = topology

      const nodes: PipelineNode[] = []
      const edges: PipelineEdge[] = []
      const nodePositions = new Map<string, { x: number; y: number }>()

      // Create nodes for API endpoints and external producers
      let xPos = 0
      let yPos = 50
      const apiEndpoints = new Set<string>()
      const externalProducers = new Map<string, { topics: string[], description: string }>()

      // Collect API endpoints
      topics.forEach((topic: any) => {
        if (topic.primary_endpoints) {
          topic.primary_endpoints.forEach((endpoint: string) => {
            apiEndpoints.add(endpoint)
          })
        }
      })

      // Find topics that have no producers (neither API endpoints nor pipeline stages)
      const topicsWithNoProducers = topics.filter((topic: any) => {
        const hasApiEndpoint = topic.primary_endpoints && topic.primary_endpoints.length > 0
        const hasStageProducer = topic.producer_count > 0
        return !hasApiEndpoint && !hasStageProducer && topic.topic_name.endsWith('.raw')
      })

      // Group orphaned topics by category to create logical external producers
      if (topicsWithNoProducers.length > 0) {
        const mobileTopics = topicsWithNoProducers.filter((t: any) =>
          t.category === 'device' || t.category === 'os' || t.category === 'digital'
        ).map((t: any) => t.topic_name)

        const externalTopics = topicsWithNoProducers.filter((t: any) =>
          t.category === 'external'
        ).map((t: any) => t.topic_name)

        if (mobileTopics.length > 0) {
          externalProducers.set('mobile-clients', {
            topics: mobileTopics,
            description: 'Mobile device clients'
          })
        }

        if (externalTopics.length > 0) {
          // Group by source for external topics
          const bySource = externalTopics.reduce((acc: any, topic: string) => {
            const source = topic.split('.')[1] // e.g., 'twitter', 'calendar', 'email'
            if (!acc[source]) acc[source] = []
            acc[source].push(topic)
            return acc
          }, {})

          Object.entries(bySource).forEach(([source, sourceTopics]: [string, any]) => {
            externalProducers.set(`${source}-fetcher`, {
              topics: sourceTopics,
              description: `${source.charAt(0).toUpperCase() + source.slice(1)} data fetcher`
            })
          })
        }
      }

      // Create API endpoint nodes
      let nodeIdx = 0
      Array.from(apiEndpoints).forEach((endpoint) => {
        const nodeId = `api-${endpoint}`
        nodes.push({
          id: nodeId,
          type: 'external',
          position: { x: xPos, y: yPos + nodeIdx * 80 },
          data: {
            label: endpoint,
            status: 'active',
            description: 'API Endpoint'
          }
        })
        nodePositions.set(nodeId, { x: xPos, y: yPos + nodeIdx * 80 })
        nodeIdx++
      })

      // Create external producer nodes
      Array.from(externalProducers.entries()).forEach(([producerId, config]) => {
        const nodeId = `external-${producerId}`
        nodes.push({
          id: nodeId,
          type: 'external',
          position: { x: xPos, y: yPos + nodeIdx * 80 },
          data: {
            label: producerId.split('-').map(word =>
              word.charAt(0).toUpperCase() + word.slice(1)
            ).join(' '),
            status: 'active',
            description: config.description
          }
        })
        nodePositions.set(nodeId, { x: xPos, y: yPos + nodeIdx * 80 })
        nodeIdx++
      })

      // Create topic nodes grouped by stage
      xPos = 300
      const rawTopics = topics.filter((t: any) => t.topic_name.endsWith('.raw'))
      const processedTopics = topics.filter((t: any) =>
        t.topic_name.includes('.filtered') ||
        t.topic_name.includes('.processed') ||
        t.topic_name.includes('.transcribed') ||
        t.topic_name.includes('.classified') ||
        t.topic_name.includes('.enriched') ||
        t.topic_name.includes('.geocoded') ||
        t.topic_name.includes('.detected') ||
        t.topic_name.includes('.embedded') ||
        t.topic_name.includes('.parsed') ||
        t.topic_name.includes('.archived') ||
        t.topic_name.includes('.fetched') ||
        t.topic_name.includes('.events')
      )
      const analysisTopics = topics.filter((t: any) =>
        t.topic_name.includes('.analysis') ||
        t.topic_name.includes('.results') ||
        t.topic_name.includes('motion.') ||
        t.topic_name.includes('location.')
      )

      // Also get error topics and task topics
      const errorTopics = topics.filter((t: any) => t.topic_name.includes('processing.errors'))
      const taskTopics = topics.filter((t: any) => t.topic_name.startsWith('task.'))

      // Raw topics
      rawTopics.forEach((topic: any, idx: number) => {
        const nodeId = topic.topic_name
        nodes.push({
          id: nodeId,
          type: 'kafka-topic',
          position: { x: xPos, y: 50 + idx * 80 },
          data: {
            label: this.getTopicLabel(topic.topic_name),
            status: 'active',
            description: topic.description
          }
        })
        nodePositions.set(nodeId, { x: xPos, y: 50 + idx * 80 })

        // Connect API endpoints to topics
        if (topic.primary_endpoints) {
          topic.primary_endpoints.forEach((endpoint: string) => {
            const sourceId = `api-${endpoint}`
            edges.push({
              id: `e-${sourceId}-${nodeId}`,
              source: sourceId,
              target: nodeId,
              animated: true
            })
          })
        }

        // Connect external producers to topics
        externalProducers.forEach((config, producerId) => {
          if (config.topics.includes(topic.topic_name)) {
            const sourceId = `external-${producerId}`
            edges.push({
              id: `e-${sourceId}-${nodeId}`,
              source: sourceId,
              target: nodeId,
              animated: true
            })
          }
        })
      })

      // Processing nodes (from pipeline stages)
      xPos = 600
      const processors = new Map<string, ProcessorInfo>()

      stages.forEach((stage: any) => {
        const processorId = `${stage.flow_name}-${stage.service_name}`

        if (!processors.has(processorId)) {
          processors.set(processorId, {
            id: processorId,
            label: stage.service_name,
            description: stage.flow_name,
            inputTopics: [],
            outputTopics: []
          })
        }

        const processor = processors.get(processorId)!
        if (stage.input_topics) {
          processor.inputTopics.push(...stage.input_topics)
        }
        if (stage.output_topics) {
          processor.outputTopics.push(...stage.output_topics)
        }
      })


      Array.from(processors.values()).forEach((processor, idx) => {
        const nodeId = processor.id
        nodes.push({
          id: nodeId,
          type: 'processor',
          position: { x: xPos, y: 100 + idx * 120 },
          data: {
            label: processor.label,
            status: 'active',
            description: processor.description
          }
        })
        nodePositions.set(nodeId, { x: xPos, y: 100 + idx * 120 })

        // Connect input topics to processors
        processor.inputTopics.forEach(topic => {
          if (nodePositions.has(topic)) {
            edges.push({
              id: `e-${topic}-${nodeId}`,
              source: topic,
              target: nodeId,
              animated: true
            })
          }
        })
      })

      // Processed topics
      xPos = 900
      processedTopics.forEach((topic: any, idx: number) => {
        const nodeId = topic.topic_name
        nodes.push({
          id: nodeId,
          type: 'kafka-topic',
          position: { x: xPos, y: 50 + idx * 80 },
          data: {
            label: this.getTopicLabel(topic.topic_name),
            status: 'active',
            description: topic.description
          }
        })
        nodePositions.set(nodeId, { x: xPos, y: 50 + idx * 80 })

        // Connect processors to output topics
        processors.forEach(processor => {
          if (processor.outputTopics.includes(topic.topic_name)) {
            edges.push({
              id: `e-${processor.id}-${nodeId}`,
              source: processor.id,
              target: nodeId,
              animated: true
            })
          }
        })
      })

      // Analysis topics
      xPos = 1200
      analysisTopics.forEach((topic: any, idx: number) => {
        const nodeId = topic.topic_name
        nodes.push({
          id: nodeId,
          type: 'kafka-topic',
          position: { x: xPos, y: 100 + idx * 100 },
          data: {
            label: this.getTopicLabel(topic.topic_name),
            status: 'active',
            description: topic.description
          }
        })
        nodePositions.set(nodeId, { x: xPos, y: 100 + idx * 100 })
      })

      // Kafka-to-DB Consumer node (special processor that writes to database)
      const kafkaToDbConsumerId = 'kafka-to-db-consumer'
      const topicsWithTables = topics.filter((t: any) => t.table_name)

      if (topicsWithTables.length > 0) {
        // Position the kafka-to-db consumer between the last topics and database
        const kafkaToDbXPos = 1350
        nodes.push({
          id: kafkaToDbConsumerId,
          type: 'processor',
          position: { x: kafkaToDbXPos, y: 200 },
          data: {
            label: 'Kafka to DB Consumer',
            status: 'active',
            description: `Persists data from ${topicsWithTables.length} topics to TimescaleDB`
          }
        })
        nodePositions.set(kafkaToDbConsumerId, { x: kafkaToDbXPos, y: 200 })

        // Connect all topics with table mappings to kafka-to-db consumer
        topicsWithTables.forEach((topic: any) => {
          if (nodePositions.has(topic.topic_name)) {
            edges.push({
              id: `e-${topic.topic_name}-${kafkaToDbConsumerId}`,
              source: topic.topic_name,
              target: kafkaToDbConsumerId,
              animated: true
            })
          }
        })
      }

      // Database node
      nodes.push({
        id: 'timescaledb',
        type: 'database',
        position: { x: 1500, y: 200 },
        data: {
          label: 'TimescaleDB',
          status: 'active',
          description: 'Time-series storage'
        }
      })

      // Connect kafka-to-db consumer to database
      if (topicsWithTables.length > 0) {
        edges.push({
          id: `e-${kafkaToDbConsumerId}-timescaledb`,
          source: kafkaToDbConsumerId,
          target: 'timescaledb',
          animated: false
        })
      }

      return { nodes, edges }
    } catch (error) {
      logger.error('Failed to build pipeline from database', error)
      return { nodes: [], edges: [] }
    }
  }

  async buildPipeline(): Promise<PipelineFlow> {
    // Always use database-driven pipeline
    return this.buildPipelineFromDatabase()
  }

  // Removed buildPipelineFromDiscovery - all pipeline info comes from database

  // Removed categorizeTopics and groupTopicsByStage - all categorization comes from database

  // Removed getExternalSources and getTopicSourceType - all source info comes from database

  // Removed processor identification methods - all processor info comes from database

  // Removed consumer labeling methods - all labels and descriptions come from database

  // Removed producer identification methods - all producer info comes from database

  getTopicLabel(topic: string): string {
    const parts = topic.split('.')
    if (parts.length < 3) return topic

    // Extract meaningful parts
    const category = parts[0]
    const type = parts[1]
    const detail = parts.slice(2).join(' ')

    // Create readable label
    const typeLabel = type.charAt(0).toUpperCase() + type.slice(1)
    const detailLabel = detail.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())

    return `${typeLabel} ${detailLabel}`.trim()
  }

  // Remove all hardcoded mappings - everything comes from database
}
