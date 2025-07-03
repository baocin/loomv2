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
    metrics?: {
      messageCount?: number
      lag?: number
      rate?: number
      lastActivity?: Date
    }
  }
}

interface PipelineEdge {
  id: string
  source: string
  target: string
  animated?: boolean
  data?: {
    throughput?: number
    lag?: number
  }
}

interface PipelineFlow {
  nodes: PipelineNode[]
  edges: PipelineEdge[]
  summary?: {
    totalFlows: number
    activeFlows: number
    totalTopics: number
    totalProcessors: number
    healthStatus: 'healthy' | 'warning' | 'error'
  }
}

// Legacy interface for compatibility
interface TopicFlow {
  source: string
  processor: string
  destination: string
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

  async buildPipeline(): Promise<PipelineFlow> {
    try {
      // Get pipeline structure from database
      const topology = await this.databaseClient.getPipelineTopology()
      const { flows, stages, topics } = topology

      // Get health metrics from Kafka
      const topicMetrics = await this.metricsCollector.collectTopicMetrics()
      const consumerMetrics = await this.metricsCollector.collectConsumerMetrics()

      // Create maps for quick metric lookups
      const topicMetricsMap = new Map(topicMetrics.map(m => [m.topic, m]))
      const consumerLagByTopic = new Map<string, number>()

      // Calculate total lag per topic
      consumerMetrics.forEach(cm => {
        const currentLag = consumerLagByTopic.get(cm.topic) || 0
        consumerLagByTopic.set(cm.topic, currentLag + cm.lag)
      })

      const nodes: PipelineNode[] = []
      const edges: PipelineEdge[] = []
      const nodePositions = new Map<string, { x: number; y: number }>()

      // Layout configuration
      const layout = {
        columnWidth: 300,
        nodeHeight: 80,
        nodeSpacing: 20,
        startX: 50,
        startY: 50
      }

      // Step 1: Create External Producer nodes (API endpoints and external sources)
      let currentX = layout.startX
      let currentY = layout.startY

      // API endpoints from database
      const apiEndpoints = new Set<string>()
      topics.forEach((topic: any) => {
        if (topic.primary_endpoints) {
          topic.primary_endpoints.forEach((endpoint: string) => apiEndpoints.add(endpoint))
        }
      })

      Array.from(apiEndpoints).forEach((endpoint, idx) => {
        const nodeId = `api-${endpoint}`
        nodes.push({
          id: nodeId,
          type: 'external',
          position: { x: currentX, y: currentY + idx * (layout.nodeHeight + layout.nodeSpacing) },
          data: {
            label: endpoint,
            status: 'active',
            description: 'API Endpoint'
          }
        })
        nodePositions.set(nodeId, { x: currentX, y: currentY + idx * (layout.nodeHeight + layout.nodeSpacing) })
      })

      // External producers for topics without API endpoints
      const orphanedTopics = topics.filter((t: any) =>
        t.topic_name.endsWith('.raw') &&
        (!t.primary_endpoints || t.primary_endpoints.length === 0) &&
        t.producer_count === 0
      )

      const externalProducers = this.groupExternalProducers(orphanedTopics)
      let producerY = currentY + apiEndpoints.size * (layout.nodeHeight + layout.nodeSpacing) + layout.nodeSpacing

      externalProducers.forEach((config, producerId) => {
        const nodeId = `external-${producerId}`
        nodes.push({
          id: nodeId,
          type: 'external',
          position: { x: currentX, y: producerY },
          data: {
            label: config.label,
            status: 'active',
            description: config.description
          }
        })
        nodePositions.set(nodeId, { x: currentX, y: producerY })
        producerY += layout.nodeHeight + layout.nodeSpacing
      })

      // Step 2: Create Topic nodes with health metrics
      currentX += layout.columnWidth

      // Group topics by processing stage
      const topicGroups = this.categorizeTopics(topics)

      Object.entries(topicGroups).forEach(([groupName, groupTopics], groupIdx) => {
        let groupY = layout.startY + groupIdx * 200

        groupTopics.forEach((topic: any, idx: number) => {
          const metrics = topicMetricsMap.get(topic.topic_name)
          const lag = consumerLagByTopic.get(topic.topic_name) || 0

          // Determine health status based on metrics
          const status = this.determineTopicHealth(metrics, lag)

          nodes.push({
            id: topic.topic_name,
            type: 'kafka-topic',
            position: { x: currentX, y: groupY + idx * (layout.nodeHeight + layout.nodeSpacing) },
            data: {
              label: this.getTopicLabel(topic.topic_name),
              status,
              description: topic.description,
              metrics: metrics ? {
                messageCount: metrics.messageCount,
                lag,
                lastActivity: metrics.lastMessageTime
              } : undefined
            }
          })
          nodePositions.set(topic.topic_name, { x: currentX, y: groupY + idx * (layout.nodeHeight + layout.nodeSpacing) })

          // Connect producers to topics
          if (topic.primary_endpoints) {
            topic.primary_endpoints.forEach((endpoint: string) => {
              edges.push({
                id: `e-api-${endpoint}-${topic.topic_name}`,
                source: `api-${endpoint}`,
                target: topic.topic_name,
                animated: status === 'active'
              })
            })
          }

          // Connect external producers
          externalProducers.forEach((config, producerId) => {
            if (config.topics.includes(topic.topic_name)) {
              edges.push({
                id: `e-external-${producerId}-${topic.topic_name}`,
                source: `external-${producerId}`,
                target: topic.topic_name,
                animated: status === 'active'
              })
            }
          })
        })
      })

      // Step 3: Create Processor nodes from pipeline stages
      currentX += layout.columnWidth
      const processors = this.consolidateProcessors(stages)

      let processorY = layout.startY
      processors.forEach(processor => {
        // Calculate processor health based on consumer lag
        let totalLag = 0
        processor.inputTopics.forEach((topic: string) => {
          totalLag += consumerLagByTopic.get(topic) || 0
        })

        const status = totalLag > 10000 ? 'error' : totalLag > 1000 ? 'idle' : 'active'

        nodes.push({
          id: processor.id,
          type: 'processor',
          position: { x: currentX, y: processorY },
          data: {
            label: processor.label,
            status,
            description: processor.description,
            metrics: {
              lag: totalLag
            }
          }
        })
        nodePositions.set(processor.id, { x: currentX, y: processorY })
        processorY += layout.nodeHeight + layout.nodeSpacing * 2

        // Connect topics to processors
        processor.inputTopics.forEach((topic: string) => {
          if (nodePositions.has(topic)) {
            edges.push({
              id: `e-${topic}-${processor.id}`,
              source: topic,
              target: processor.id,
              animated: status === 'active',
              data: {
                lag: consumerLagByTopic.get(topic) || 0
              }
            })
          }
        })

        // Connect processors to output topics
        processor.outputTopics.forEach((topic: string) => {
          // We'll connect these after creating output topic nodes
        })
      })

      // Step 4: Create output/processed topic nodes
      currentX += layout.columnWidth
      const processedTopics = topics.filter((t: any) =>
        !t.topic_name.endsWith('.raw') && nodePositions.has(t.topic_name) === false
      )

      processedTopics.forEach((topic: any, idx: number) => {
        const metrics = topicMetricsMap.get(topic.topic_name)
        const status = this.determineTopicHealth(metrics, 0)

        nodes.push({
          id: topic.topic_name,
          type: 'kafka-topic',
          position: { x: currentX, y: layout.startY + idx * (layout.nodeHeight + layout.nodeSpacing) },
          data: {
            label: this.getTopicLabel(topic.topic_name),
            status,
            description: topic.description,
            metrics: metrics ? {
              messageCount: metrics.messageCount,
              lastActivity: metrics.lastMessageTime
            } : undefined
          }
        })
        nodePositions.set(topic.topic_name, { x: currentX, y: layout.startY + idx * (layout.nodeHeight + layout.nodeSpacing) })
      })

      // Connect processors to their output topics
      processors.forEach(processor => {
        processor.outputTopics.forEach((topic: string) => {
          if (nodePositions.has(topic)) {
            const metrics = topicMetricsMap.get(topic)
            edges.push({
              id: `e-${processor.id}-${topic}`,
              source: processor.id,
              target: topic,
              animated: metrics?.isActive || false
            })
          }
        })
      })

      // Step 5: Add kafka-to-db consumer and database
      const topicsWithTables = topics.filter((t: any) => t.table_name)
      if (topicsWithTables.length > 0) {
        currentX += layout.columnWidth
        const kafkaToDbId = 'kafka-to-db-consumer'

        nodes.push({
          id: kafkaToDbId,
          type: 'processor',
          position: { x: currentX, y: layout.startY + 200 },
          data: {
            label: 'Kafka to DB Consumer',
            status: 'active',
            description: `Persists ${topicsWithTables.length} topics to TimescaleDB`
          }
        })

        // Connect topics to kafka-to-db
        topicsWithTables.forEach((topic: any) => {
          if (nodePositions.has(topic.topic_name)) {
            edges.push({
              id: `e-${topic.topic_name}-${kafkaToDbId}`,
              source: topic.topic_name,
              target: kafkaToDbId,
              animated: true
            })
          }
        })

        // Add database node
        currentX += layout.columnWidth
        nodes.push({
          id: 'timescaledb',
          type: 'database',
          position: { x: currentX, y: layout.startY + 200 },
          data: {
            label: 'TimescaleDB',
            status: 'active',
            description: 'Time-series storage'
          }
        })

        edges.push({
          id: 'e-kafka-to-db-consumer-timescaledb',
          source: kafkaToDbId,
          target: 'timescaledb',
          animated: true
        })
      }

      // Calculate summary statistics
      const activeFlows = flows.filter((f: any) => f.is_active).length
      const totalLag = Array.from(consumerLagByTopic.values()).reduce((sum, lag) => sum + lag, 0)
      const healthStatus = totalLag > 100000 ? 'error' : totalLag > 10000 ? 'warning' : 'healthy'

      return {
        nodes,
        edges,
        summary: {
          totalFlows: flows.length,
          activeFlows,
          totalTopics: topics.length,
          totalProcessors: processors.size,
          healthStatus
        }
      }
    } catch (error) {
      logger.error('Failed to build pipeline', error)
      return { nodes: [], edges: [] }
    }
  }

  private groupExternalProducers(orphanedTopics: any[]): Map<string, { label: string, description: string, topics: string[] }> {
    const producers = new Map<string, { label: string, description: string, topics: string[] }>()

    // Group mobile device topics
    const mobileTopics = orphanedTopics
      .filter(t => ['device', 'os', 'digital'].includes(t.category))
      .map(t => t.topic_name)

    if (mobileTopics.length > 0) {
      producers.set('mobile-clients', {
        label: 'Mobile Clients',
        description: 'Android/iOS device clients',
        topics: mobileTopics
      })
    }

    // Group external source topics by source
    const externalTopics = orphanedTopics.filter(t => t.category === 'external')
    const bySource = new Map<string, string[]>()

    externalTopics.forEach(t => {
      const source = t.source || t.topic_name.split('.')[1]
      if (!bySource.has(source)) {
        bySource.set(source, [])
      }
      bySource.get(source)!.push(t.topic_name)
    })

    bySource.forEach((topics, source) => {
      const label = source.charAt(0).toUpperCase() + source.slice(1) + ' Fetcher'
      producers.set(`${source}-fetcher`, {
        label,
        description: `Fetches data from ${source}`,
        topics
      })
    })

    return producers
  }

  private categorizeTopics(topics: any[]): Record<string, any[]> {
    const groups: Record<string, any[]> = {
      raw: [],
      processed: [],
      analysis: [],
      other: []
    }

    topics.forEach(topic => {
      if (topic.topic_name.endsWith('.raw')) {
        groups.raw.push(topic)
      } else if (
        topic.topic_name.includes('.filtered') ||
        topic.topic_name.includes('.processed') ||
        topic.topic_name.includes('.enriched') ||
        topic.topic_name.includes('.transcribed') ||
        topic.topic_name.includes('.classified') ||
        topic.topic_name.includes('.detected') ||
        topic.topic_name.includes('.parsed') ||
        topic.topic_name.includes('.embedded')
      ) {
        groups.processed.push(topic)
      } else if (
        topic.topic_name.includes('.analysis') ||
        topic.topic_name.includes('.results') ||
        topic.topic_name.includes('motion.') ||
        topic.topic_name.includes('location.')
      ) {
        groups.analysis.push(topic)
      } else {
        groups.other.push(topic)
      }
    })

    // Remove empty groups
    Object.keys(groups).forEach(key => {
      if (groups[key].length === 0) {
        delete groups[key]
      }
    })

    return groups
  }

  private consolidateProcessors(stages: any[]): Map<string, any> {
    const processors = new Map<string, any>()

    stages.forEach(stage => {
      const processorId = `${stage.flow_name}-${stage.service_name}`

      if (!processors.has(processorId)) {
        processors.set(processorId, {
          id: processorId,
          label: stage.service_name,
          description: stage.flow_name,
          inputTopics: new Set<string>(),
          outputTopics: new Set<string>(),
          configuration: stage.configuration,
          replicas: stage.replicas
        })
      }

      const processor = processors.get(processorId)!

      // Add topics to sets to avoid duplicates
      if (stage.input_topics) {
        stage.input_topics.forEach((t: string) => processor.inputTopics.add(t))
      }
      if (stage.output_topics) {
        stage.output_topics.forEach((t: string) => processor.outputTopics.add(t))
      }
    })

    // Convert sets back to arrays
    processors.forEach(processor => {
      processor.inputTopics = Array.from(processor.inputTopics)
      processor.outputTopics = Array.from(processor.outputTopics)
    })

    return processors
  }

  private determineTopicHealth(metrics: any, lag: number): 'active' | 'idle' | 'error' | 'unknown' {
    if (!metrics) return 'unknown'

    // Error if significant lag
    if (lag > 10000) return 'error'

    // Check if topic has recent activity
    if (metrics.lastMessageTime) {
      const ageMs = Date.now() - new Date(metrics.lastMessageTime).getTime()
      if (ageMs < 60000) return 'active' // Active if message in last minute
      if (ageMs < 300000) return 'idle'   // Idle if message in last 5 minutes
    }

    // If no messages at all
    if (metrics.messageCount === 0) return 'idle'

    return metrics.isActive ? 'active' : 'idle'
  }

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

  // Compatibility methods for existing routes
  identifyProducers(topics: string[]): string[] {
    // This is now handled by the database topology
    return []
  }

  getConsumerLabel(consumerId: string): string {
    return consumerId.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  getConsumerDescription(consumerId: string): string {
    return `Consumer group: ${consumerId}`
  }

  determineOutputTopics(consumerId: string, topics: string[]): string[] {
    // This information now comes from the database
    return []
  }

  async detectFlows(): Promise<any[]> {
    // Deprecated - flows come from database
    return []
  }
}
