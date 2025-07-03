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
    const flows: TopicFlow[] = []

    try {
      // Get consumer group subscriptions
      const subscriptions = await this.kafkaClient.getConsumerGroupSubscriptions()

      // Build processor mappings from environment variables
      const processorMappings: Record<string, { input: string[], output: string[] }> = this.buildProcessorMappingsFromEnv()

      // Fallback to hardcoded mappings if env vars not available
      if (Object.keys(processorMappings).length === 0) {
        logger.warn('No environment variable mappings found, using hardcoded fallbacks')
        Object.assign(processorMappings, this.getHardcodedMappings())
      }

      // Add discovered subscriptions to mappings
      for (const [groupId, topics] of subscriptions) {
        if (!processorMappings[groupId]) {
          processorMappings[groupId] = {
            input: topics,
            output: []
          }
        } else {
          // Update input topics with actual subscriptions
          processorMappings[groupId].input = topics
        }
      }

      // Build flows based on mappings
      for (const [processor, mapping] of Object.entries(processorMappings)) {
        if (mapping.input.length > 0 && mapping.output.length > 0) {
          for (const inputTopic of mapping.input) {
            for (const outputTopic of mapping.output) {
              flows.push({
                source: inputTopic,
                processor: processor,
                destination: outputTopic
              })
            }
          }
        }
      }

      // Add consumer lag information
      for (const flow of flows) {
        try {
          const lag = await this.kafkaClient.getConsumerLag(flow.processor, [flow.source])
          if (lag && lag.length > 0) {
            const totalLag = lag.reduce((sum: number, l: any) => sum + l.lag, 0)
            flow.lag = totalLag
            flow.health = totalLag > 1000 ? 'warning' : totalLag > 10000 ? 'error' : 'healthy'
          }
        } catch (error) {
          logger.warn(`Failed to get lag for ${flow.processor}`, error)
          flow.health = 'unknown'
        }
      }

      return flows
    } catch (error) {
      logger.error('Failed to detect flows', error)
      return flows
    }
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

      // Define external producers for topics without producers in stages
      // These are services that produce data but aren't defined in pipeline stages
      const externalProducerMappings: Record<string, { label: string, description: string, topics: string[] }> = {
        'x-likes-fetcher': {
          label: 'X Likes Fetcher',
          description: 'Fetches liked posts from X/Twitter',
          topics: ['external.twitter.liked.raw']
        },
        'calendar-fetcher': {
          label: 'Calendar Fetcher',
          description: 'Syncs calendar events',
          topics: ['external.calendar.events.raw']
        },
        'email-fetcher': {
          label: 'Email Fetcher',
          description: 'Fetches emails from IMAP',
          topics: ['external.email.events.raw']
        },
        'mobile-client': {
          label: 'Mobile Clients',
          description: 'Android/iOS apps',
          topics: [
            'device.health.heartrate.raw',
            'device.health.steps.raw',
            'device.metadata.raw',
            'device.sensor.barometer.raw',
            'device.sensor.temperature.raw',
            'device.system.apps.android.raw',
            'device.video.screen.raw',
            'digital.clipboard.raw',
            'os.events.app_lifecycle.raw',
            'os.events.system.raw',
            'os.events.notifications.raw'
          ]
        },
        'desktop-client': {
          label: 'Desktop Clients',
          description: 'macOS/Windows apps',
          topics: ['device.system.apps.macos.raw']
        }
      }

      // Add external producers that aren't covered by API endpoints
      Object.entries(externalProducerMappings).forEach(([id, config]) => {
        // Check if any of the topics exist and don't have API endpoints
        const relevantTopics = config.topics.filter(topicName =>
          topics.some((t: any) => t.topic_name === topicName && (!t.primary_endpoints || t.primary_endpoints.length === 0))
        )

        if (relevantTopics.length > 0) {
          externalProducers.set(id, {
            topics: relevantTopics,
            description: config.description
          })
        }
      })

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
        const producerConfig = externalProducerMappings[producerId]
        nodes.push({
          id: nodeId,
          type: 'external',
          position: { x: xPos, y: yPos + nodeIdx * 80 },
          data: {
            label: producerConfig.label,
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
    // Try to build from database first
    try {
      const dbPipeline = await this.buildPipelineFromDatabase()
      if (dbPipeline.nodes.length > 0) {
        return dbPipeline
      }
    } catch (error) {
      logger.warn('Failed to build pipeline from database, falling back to discovery', error)
    }

    // Fallback to original discovery method
    try {
      const topics = await this.kafkaClient.getTopics()
      const consumerGroups = await this.kafkaClient.getConsumerGroups()
      const flows = await this.detectFlows()

      // Filter out internal topics and monitoring topics
      const userTopics = topics.filter(t =>
        !t.startsWith('__') &&
        !t.startsWith('_') &&
        !t.includes('monitoring') &&
        !t.includes('metrics') &&
        !t.includes('health') &&
        !t.includes('heartbeat') &&
        !t.includes('status') &&
        !t.startsWith('Internal.Scheduled.Jobs') &&
        !t.toLowerCase().includes('internal.scheduled.jobs')
      )

      const nodes: PipelineNode[] = []
      const edges: PipelineEdge[] = []
      const nodePositions = new Map<string, { x: number; y: number }>()

      // Categorize topics by their purpose
      const categories = this.categorizeTopics(userTopics)

      // Create producer nodes (replaces old external sources)
      let xPos = 0
      let yPos = 100

      const producers = this.identifyProducers(userTopics)

      producers.forEach((producer, idx) => {
        const nodeId = `producer-${producer.id}`
        nodes.push({
          id: nodeId,
          type: 'external',
          position: { x: xPos, y: yPos + idx * 100 },
          data: {
            label: producer.label,
            status: 'active',
            description: producer.description
          }
        })
        nodePositions.set(nodeId, { x: xPos, y: yPos + idx * 100 })
      })

      // Create topic nodes
      xPos = 300
      const topicsByStage = this.groupTopicsByStage(userTopics)

      // Raw data topics
      topicsByStage.raw.forEach((topic, idx) => {
        const nodeId = topic
        nodes.push({
          id: nodeId,
          type: 'kafka-topic',
          position: { x: xPos, y: 50 + idx * 80 },
          data: {
            label: this.getTopicLabel(topic),
            status: 'active'
          }
        })
        nodePositions.set(nodeId, { x: xPos, y: 50 + idx * 80 })

        // Connect producers to topics
        const matchingProducer = producers.find(p => this.matchesProducerPattern(p, topic))
        if (matchingProducer) {
          const sourceId = `producer-${matchingProducer.id}`
          edges.push({
            id: `e-${sourceId}-${nodeId}`,
            source: sourceId,
            target: nodeId,
            animated: true
          })
        }
      })

      // Processing nodes (based on consumer groups)
      xPos = 600
      const processors = this.identifyProcessors(consumerGroups, userTopics)
      processors.forEach((processor, idx) => {
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

        // Connect raw topics to processors
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

      // Processed/filtered topics
      xPos = 900
      topicsByStage.processed.forEach((topic, idx) => {
        const nodeId = topic
        nodes.push({
          id: nodeId,
          type: 'kafka-topic',
          position: { x: xPos, y: 50 + idx * 80 },
          data: {
            label: this.getTopicLabel(topic),
            status: 'active'
          }
        })
        nodePositions.set(nodeId, { x: xPos, y: 50 + idx * 80 })

        // Connect processors to processed topics
        const processor = processors.find(p => p.outputTopics.includes(topic))
        if (processor) {
          edges.push({
            id: `e-${processor.id}-${nodeId}`,
            source: processor.id,
            target: nodeId,
            animated: true
          })
        }
      })

      // Analysis/final topics
      xPos = 1200
      topicsByStage.analysis.forEach((topic, idx) => {
        const nodeId = topic
        nodes.push({
          id: nodeId,
          type: 'kafka-topic',
          position: { x: xPos, y: 100 + idx * 100 },
          data: {
            label: this.getTopicLabel(topic),
            status: 'active'
          }
        })
        nodePositions.set(nodeId, { x: xPos, y: 100 + idx * 100 })
      })

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

      // Connect topics to database
      // Include processed, analysis, and specific raw topics that are stored directly
      const finalTopics = topicsByStage.processed.concat(topicsByStage.analysis)

      // Add specific raw topics that should be stored directly in database
      const directStorageRawTopics = topicsByStage.raw.filter(topic =>
        topic.includes('external.twitter.liked.raw') ||
        topic.includes('external.calendar.events.raw') ||
        topic.includes('external.email.events.raw') ||
        topic.includes('device.sensor.gps.raw') ||
        topic.includes('device.health.heartrate.raw') ||
        topic.includes('device.state.power.raw') ||
        topic.includes('device.system.apps') ||
        topic.includes('os.events') ||
        topic.includes('digital.')
      )

      const allDatabaseTopics = finalTopics.concat(directStorageRawTopics)

      allDatabaseTopics.forEach(topic => {
        edges.push({
          id: `e-${topic}-timescaledb`,
          source: topic,
          target: 'timescaledb',
          animated: false
        })
      })

      return { nodes, edges }
    } catch (error) {
      logger.error('Failed to build pipeline', error)
      return { nodes: [], edges: [] }
    }
  }

  private categorizeTopics(topics: string[]): {
    device: string[],
    media: string[],
    analysis: string[],
    external: string[],
    task: string[],
    digital: string[],
    internal: string[]
  } {
    return {
      device: topics.filter(t => t.startsWith('device.')),
      media: topics.filter(t => t.startsWith('media.')),
      analysis: topics.filter(t => t.startsWith('analysis.')),
      external: topics.filter(t => t.startsWith('external.')),
      task: topics.filter(t => t.startsWith('task.')),
      digital: topics.filter(t => t.startsWith('digital.')),
      internal: topics.filter(t => t.startsWith('internal.'))
    }
  }

  private groupTopicsByStage(topics: string[]): { raw: string[], processed: string[], analysis: string[] } {
    return {
      raw: topics.filter(t => t.endsWith('.raw') || t.includes('.raw.')),
      processed: topics.filter(t =>
        t.includes('.vad_filtered') ||
        t.includes('.transcribed') ||
        t.includes('.processed') ||
        t.includes('.vision_annotations') ||
        t.includes('.word_timestamps')
      ),
      analysis: topics.filter(t =>
        t.startsWith('analysis.') ||
        t.includes('.analysis.') ||
        t.includes('.results')
      )
    }
  }

  private getExternalSources(categories: {
    device: string[],
    media: string[],
    analysis: string[],
    external: string[],
    task: string[],
    digital: string[],
    internal: string[]
  }) {
    const sources: { id: string, type: string, label: string, description: string }[] = []

    if (categories.device.some(t => t.includes('audio'))) {
      sources.push({
        id: 'audio',
        type: 'audio',
        label: 'Audio Devices',
        description: 'Microphones, recordings'
      })
    }

    if (categories.device.some(t => t.includes('sensor'))) {
      sources.push({
        id: 'sensors',
        type: 'sensor',
        label: 'Device Sensors',
        description: 'GPS, accelerometer, etc.'
      })
    }

    if (categories.device.some(t => t.includes('image') || t.includes('video'))) {
      sources.push({
        id: 'visual',
        type: 'visual',
        label: 'Cameras/Screen',
        description: 'Images, videos, screenshots'
      })
    }

    if (categories.external.length > 0) {
      sources.push({
        id: 'external',
        type: 'external',
        label: 'External Sources',
        description: 'Web, social media, email'
      })
    }

    return sources
  }

  private getTopicSourceType(topic: string): string {
    if (topic.includes('audio')) return 'audio'
    if (topic.includes('sensor')) return 'sensor'
    if (topic.includes('image') || topic.includes('video')) return 'visual'
    if (topic.startsWith('external.')) return 'external'
    return 'unknown'
  }

  private identifyProcessors(consumerGroups: any[], topics: string[]): {
    id: string,
    label: string,
    description: string,
    inputTopics: string[],
    outputTopics: string[]
  }[] {
    const processors: {
      id: string,
      label: string,
      description: string,
      inputTopics: string[],
      outputTopics: string[]
    }[] = []

    // Create a processor for each consumer group
    consumerGroups.forEach(group => {
      const groupId = group.groupId || group.name
      if (!groupId || groupId.startsWith('__') || groupId.startsWith('_')) {
        return // Skip internal groups
      }

      // Skip monitor-related consumer groups
      if (groupId.toLowerCase().includes('monitor') ||
          groupId.toLowerCase().includes('internal.scheduled.jobs') ||
          groupId.toLowerCase().includes('scheduled-jobs')) {
        return
      }

      // Determine input topics based on group name patterns
      const inputTopics = this.determineInputTopics(groupId, topics)
      const outputTopics = this.determineOutputTopics(groupId, topics)

      processors.push({
        id: `consumer-${groupId}`,
        label: this.getConsumerLabel(groupId),
        description: this.getConsumerDescription(groupId),
        inputTopics,
        outputTopics
      })
    })

    // Add known processors that might not have consumer groups yet
    this.addKnownProcessors(processors, topics)

    return processors
  }

  private determineInputTopics(groupId: string, topics: string[]): string[] {
    // Map consumer group names to their likely input topics
    const inputMappings: Record<string, string[]> = {
      'silero-vad-consumer': ['device.audio.raw'],
      'kyutai-stt-consumer': ['device.audio.raw'],  // Changed from VAD-filtered to raw audio
      'minicpm-vision-consumer': ['device.image.camera.raw', 'device.video.screen.raw'],
      'kafka-to-db-consumer': topics.filter(t =>
        t.includes('.raw') || t.includes('.processed') || t.includes('.analysis')
      )
    }

    // Check for exact matches first
    if (inputMappings[groupId]) {
      return inputMappings[groupId].filter(topic => topics.includes(topic))
    }

    // Pattern-based matching
    if (groupId.includes('vad')) {
      return topics.filter(t => t.includes('audio') && t.includes('raw'))
    }
    if (groupId.includes('transcr') || groupId.includes('speech') || groupId.includes('asr') || groupId.includes('stt') || groupId.includes('kyutai')) {
      return topics.filter(t => t.includes('audio') && t.includes('raw'))  // Kyutai STT now processes raw audio
    }
    if (groupId.includes('vision') || groupId.includes('image')) {
      return topics.filter(t => (t.includes('image') || t.includes('video')) && t.includes('raw'))
    }
    if (groupId.includes('db') || groupId.includes('database') || groupId.includes('storage')) {
      return topics.filter(t => !t.includes('raw')) // Processed data to database
    }

    // Default: try to infer from group name
    return topics.filter(t => t.includes(groupId.split('-')[0]))
  }

  determineOutputTopics(groupId: string, topics: string[]): string[] {
    // Map consumer groups to their output topics
    const outputMappings: Record<string, string[]> = {
      'silero-vad-consumer': ['media.audio.vad_filtered'],
      'kyutai-stt-consumer': ['media.text.transcribed.words'],
      'minicpm-vision-consumer': ['media.image.analysis.minicpm_results'],
      'kafka-to-db-consumer': [] // Database consumer doesn't produce topics
    }

    if (outputMappings[groupId]) {
      return outputMappings[groupId].filter(topic => topics.includes(topic))
    }

    // Pattern-based output detection
    if (groupId.includes('vad')) {
      return topics.filter(t => t.includes('vad_filtered'))
    }
    if (groupId.includes('transcr') || groupId.includes('speech') || groupId.includes('asr') || groupId.includes('stt') || groupId.includes('kyutai')) {
      return topics.filter(t => t.includes('transcribed'))
    }
    if (groupId.includes('vision') || groupId.includes('image')) {
      return topics.filter(t => t.includes('vision') || t.includes('analysis'))
    }

    return [] // Many consumers just store to database
  }

  getConsumerLabel(groupId: string): string {
    const labelMappings: Record<string, string> = {
      // Audio Pipeline
      'silero-vad-consumer': 'VAD Processor',
      'kyutai-stt-consumer': 'Kyutai STT',  // Updated name

      // Vision Pipeline
      'minicpm-vision-consumer': 'Vision Analyzer',
      'face-emotion-consumer': 'Face Emotion',
      'moondream-ocr-consumer': 'OCR Processor',

      // Text Pipeline
      'text-embedder-consumer': 'Text Embedder',
      'nomic-embed-consumer': 'Nomic Embedder',

      // Reasoning Pipeline
      'mistral-reasoning-consumer': 'Mistral Reasoning',
      'onefilellm-consumer': 'OneFile LLM',

      // External Data
      'x-url-processor-consumer': 'Twitter Processor',
      'hackernews-url-processor-consumer': 'HackerNews Processor',
      'twitter-ocr-processor-consumer': 'Twitter OCR',

      // Fetchers
      'x-likes-fetcher': 'Twitter Fetcher',
      'hackernews-fetcher': 'HackerNews Fetcher',
      'email-fetcher': 'Email Fetcher',
      'calendar-fetcher': 'Calendar Fetcher',

      // Database
      'kafka-to-db-consumer': 'Database Writer'
    }

    if (labelMappings[groupId]) {
      return labelMappings[groupId]
    }

    // Generate label from group ID
    return groupId
      .replace(/-consumer$/, '')
      .replace(/-/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase())
  }

  getConsumerDescription(groupId: string): string {
    const descriptionMappings: Record<string, string> = {
      // Audio Pipeline
      'silero-vad-consumer': 'Voice Activity Detection',
      'kyutai-stt-consumer': 'Speech-to-Text (Kyutai 2.6B)',  // Updated description

      // Vision Pipeline
      'minicpm-vision-consumer': 'Image analysis & captioning',
      'face-emotion-consumer': 'Facial emotion detection',
      'moondream-ocr-consumer': 'OCR text extraction',

      // Text Pipeline
      'text-embedder-consumer': 'Text vectorization',
      'nomic-embed-consumer': 'Multimodal embeddings',

      // Reasoning Pipeline
      'mistral-reasoning-consumer': 'Context understanding',
      'onefilellm-consumer': 'Document summarization',

      // External Data
      'x-url-processor-consumer': 'Twitter content archiving',
      'hackernews-url-processor-consumer': 'HackerNews archiving',
      'twitter-ocr-processor-consumer': 'Twitter screenshot OCR',

      // Fetchers
      'x-likes-fetcher': 'Twitter likes collection',
      'hackernews-fetcher': 'HackerNews monitoring',
      'email-fetcher': 'Email synchronization',
      'calendar-fetcher': 'Calendar event sync',

      // Database
      'kafka-to-db-consumer': 'Data persistence'
    }

    return descriptionMappings[groupId] || 'Data processing service'
  }

  private addKnownProcessors(processors: any[], topics: string[]): void {
    // Add processors for known services that might not have active consumer groups
    const knownServices = [
      // Audio Pipeline
      { groupId: 'silero-vad-consumer', required: ['device.audio.raw'] },
      { groupId: 'kyutai-stt-consumer', required: ['device.audio.raw'] },  // Now requires raw audio

      // Vision Pipeline
      { groupId: 'minicpm-vision-consumer', required: ['device.image.camera.raw'] },
      { groupId: 'face-emotion-consumer', required: ['media.image.vision_annotations'] },
      { groupId: 'moondream-ocr-consumer', required: ['device.image.camera.raw'] },

      // Text Pipeline
      { groupId: 'text-embedder-consumer', required: ['external.email.events.raw'] },

      // Reasoning Pipeline
      { groupId: 'mistral-reasoning-consumer', required: ['media.text.word_timestamps'] },

      // External Data
      { groupId: 'x-url-processor-consumer', required: ['task.url.ingest'] },
      { groupId: 'hackernews-url-processor-consumer', required: ['task.url.ingest'] },
      { groupId: 'twitter-ocr-processor-consumer', required: ['external.twitter.liked.raw'] },

      // Database
      { groupId: 'kafka-to-db-consumer', required: ['device.audio.raw'] }
    ]

    knownServices.forEach(service => {
      const hasRequiredTopics = service.required.some(topic => topics.includes(topic))
      const alreadyExists = processors.some(p => p.id === `consumer-${service.groupId}`)

      if (hasRequiredTopics && !alreadyExists) {
        processors.push({
          id: `consumer-${service.groupId}`,
          label: this.getConsumerLabel(service.groupId),
          description: this.getConsumerDescription(service.groupId),
          inputTopics: this.determineInputTopics(service.groupId, topics),
          outputTopics: this.determineOutputTopics(service.groupId, topics)
        })
      }
    })
  }

  identifyProducers(topics: string[]): {
    id: string,
    type: string,
    label: string,
    description: string,
    outputTopics: string[]
  }[] {
    const producers: {
      id: string,
      type: string,
      label: string,
      description: string,
      outputTopics: string[]
    }[] = []

    // Identify ingestion API producer
    if (topics.some(t => t.includes('device.') && t.includes('.raw'))) {
      producers.push({
        id: 'ingestion-api',
        type: 'api',
        label: 'Ingestion API',
        description: 'Real-time data ingestion service',
        outputTopics: topics.filter(t => t.includes('device.') && t.includes('.raw'))
      })
    }

    // Identify task URL ingest producer
    if (topics.some(t => t.startsWith('task.url.ingest'))) {
      producers.push({
        id: 'url-ingest-scheduler',
        type: 'scheduler',
        label: 'URL Scheduler',
        description: 'Schedules URLs for processing',
        outputTopics: topics.filter(t => t.startsWith('task.url.ingest'))
      })
    }

    // Identify scheduled data fetchers
    if (topics.some(t => t.startsWith('external.hackernews'))) {
      producers.push({
        id: 'hackernews-fetcher',
        type: 'external',
        label: 'HackerNews Fetcher',
        description: 'Scheduled news aggregation',
        outputTopics: topics.filter(t => t.includes('hackernews'))
      })
    }

    if (topics.some(t => t.startsWith('external.twitter'))) {
      producers.push({
        id: 'x-likes-fetcher',
        type: 'external',
        label: 'X Likes Fetcher',
        description: 'Twitter/X likes data collection',
        outputTopics: topics.filter(t => t.includes('twitter'))
      })
    }

    if (topics.some(t => t.startsWith('external.calendar'))) {
      producers.push({
        id: 'calendar-fetcher',
        type: 'external',
        label: 'Calendar Fetcher',
        description: 'Calendar events sync',
        outputTopics: topics.filter(t => t.includes('calendar'))
      })
    }

    if (topics.some(t => t.startsWith('external.email'))) {
      producers.push({
        id: 'email-fetcher',
        type: 'external',
        label: 'Email Fetcher',
        description: 'Email monitoring service',
        outputTopics: topics.filter(t => t.includes('email'))
      })
    }


    if (topics.some(t => t.startsWith('external.web'))) {
      producers.push({
        id: 'web-analytics',
        type: 'external',
        label: 'Web Analytics',
        description: 'Website visit tracking',
        outputTopics: topics.filter(t => t.includes('web'))
      })
    }

    // Identify client producers (macOS, Android)
    if (topics.some(t => t.includes('device.system.apps.macos'))) {
      producers.push({
        id: 'macos-client',
        type: 'device',
        label: 'macOS Client',
        description: 'macOS system monitoring',
        outputTopics: topics.filter(t => t.includes('macos'))
      })
    }

    if (topics.some(t => t.includes('device.system.apps.android'))) {
      producers.push({
        id: 'android-client',
        type: 'device',
        label: 'Android Client',
        description: 'Android system monitoring',
        outputTopics: topics.filter(t => t.includes('android'))
      })
    }

    // Identify task/URL processors
    if (topics.some(t => t.startsWith('task.'))) {
      producers.push({
        id: 'task-scheduler',
        type: 'internal',
        label: 'Task Scheduler',
        description: 'Background task coordination',
        outputTopics: topics.filter(t => t.startsWith('task.'))
      })
    }

    return producers
  }

  private matchesProducerPattern(producer: any, topic: string): boolean {
    // Direct output topic matching
    if (producer.outputTopics && producer.outputTopics.includes(topic)) {
      return true
    }

    // Specific producer-to-topic mappings based on the actual topics we see
    const mappings: Record<string, string[]> = {
      'ingestion-api': [
        'device.audio.raw',
        'device.sensor.accelerometer.raw',
        'device.sensor.gps.raw',
        'device.image.camera.raw',
        'device.video.screen.raw',
        'device.health.heartrate.raw',
        'device.state.power.raw',
        'device.metadata.raw',
        'device.text.notes.raw',
        'device.system.apps.macos.raw',
        'device.system.apps.android.raw',
        'digital.notes.raw',
        'digital.clipboard.raw'
      ],
      'url-ingest-scheduler': ['task.url.ingest'],
      'hackernews-fetcher': ['external.hackernews.activity.raw'],
      'x-likes-fetcher': ['external.twitter.liked.raw'],
      'calendar-fetcher': ['external.calendar.events.raw'],
      'email-fetcher': ['external.email.events.raw'],
      'web-analytics': ['external.web.visits.raw'],
      'macos-client': ['device.system.apps.macos.raw'],
      'android-client': ['device.system.apps.android.raw']
    }

    // Check if this producer should produce this topic
    const producerTopics = mappings[producer.id]
    if (producerTopics && producerTopics.includes(topic)) {
      return true
    }

    // Fallback pattern matching
    if (producer.type === 'api' && topic.startsWith('device.') && topic.includes('.raw')) {
      return true
    }
    if (producer.type === 'external' && topic.startsWith('external.')) {
      const topicParts = topic.split('.')
      let producerName = producer.id.replace('-fetcher', '').replace('-analytics', '')

      // Handle special cases
      if (producer.id === 'x-likes-fetcher') {
        producerName = 'twitter' // x-likes-fetcher produces twitter topics
      }

      return topicParts.includes(producerName)
    }
    if (producer.type === 'device' && topic.includes('device.system')) {
      const clientType = producer.id.replace('-client', '')
      return topic.includes(clientType)
    }
    if (producer.type === 'internal' && topic.startsWith('task.')) {
      return true
    }

    return false
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

  private buildProcessorMappingsFromEnv(): Record<string, { input: string[], output: string[] }> {
    const mappings: Record<string, { input: string[], output: string[] }> = {}

    try {
      // Audio Processing Pipeline
      if (process.env.LOOM_KAFKA_INPUT_TOPIC_VAD && process.env.LOOM_KAFKA_OUTPUT_TOPIC_VAD) {
        mappings['silero-vad-consumer'] = {
          input: [process.env.LOOM_KAFKA_INPUT_TOPIC_VAD],
          output: [process.env.LOOM_KAFKA_OUTPUT_TOPIC_VAD]
        }
      }

      // Kyutai STT - reads raw audio directly
      if (process.env.LOOM_KAFKA_INPUT_TOPIC_VAD && process.env.LOOM_KAFKA_OUTPUT_TOPIC_PARAKEET) {
        mappings['kyutai-stt-consumer'] = {
          input: [process.env.LOOM_KAFKA_INPUT_TOPIC_VAD], // device.audio.raw
          output: [process.env.LOOM_KAFKA_OUTPUT_TOPIC_PARAKEET] // media.text.transcribed.words
        }
      }

      // MiniCPM Vision
      if (process.env.LOOM_KAFKA_INPUT_TOPICS_MINICPM && process.env.LOOM_KAFKA_OUTPUT_TOPIC_MINICPM) {
        try {
          const inputTopics = JSON.parse(process.env.LOOM_KAFKA_INPUT_TOPICS_MINICPM)
          mappings['minicpm-vision-consumer'] = {
            input: inputTopics,
            output: [process.env.LOOM_KAFKA_OUTPUT_TOPIC_MINICPM]
          }
        } catch (e) {
          logger.warn('Failed to parse LOOM_KAFKA_INPUT_TOPICS_MINICPM as JSON')
        }
      }

      // Face Emotion Recognition
      if (process.env.LOOM_KAFKA_INPUT_TOPIC_FACE && process.env.LOOM_KAFKA_OUTPUT_TOPIC_FACE) {
        mappings['face-emotion-consumer'] = {
          input: [process.env.LOOM_KAFKA_INPUT_TOPIC_FACE],
          output: [process.env.LOOM_KAFKA_OUTPUT_TOPIC_FACE]
        }
      }

      // BUD-E Audio Emotion
      if (process.env.LOOM_KAFKA_INPUT_TOPIC_BUDE && process.env.LOOM_KAFKA_OUTPUT_TOPIC_BUDE) {
        mappings['bud-e-emotion-consumer'] = {
          input: [process.env.LOOM_KAFKA_INPUT_TOPIC_BUDE],
          output: [process.env.LOOM_KAFKA_OUTPUT_TOPIC_BUDE]
        }
      }

      // External Data Services
      if (process.env.LOOM_KAFKA_OUTPUT_TOPIC_X) {
        mappings['x-likes-fetcher'] = {
          input: [],
          output: [process.env.LOOM_KAFKA_OUTPUT_TOPIC_X]
        }
      }

      if (process.env.LOOM_KAFKA_OUTPUT_TOPIC_EMAIL) {
        mappings['email-fetcher'] = {
          input: [],
          output: [process.env.LOOM_KAFKA_OUTPUT_TOPIC_EMAIL]
        }
      }

      if (process.env.LOOM_KAFKA_OUTPUT_TOPIC_CALENDAR) {
        mappings['calendar-fetcher'] = {
          input: [],
          output: [process.env.LOOM_KAFKA_OUTPUT_TOPIC_CALENDAR]
        }
      }

      if (process.env.LOOM_KAFKA_OUTPUT_TOPIC_HACKERNEWS) {
        mappings['hackernews-fetcher'] = {
          input: [],
          output: [process.env.LOOM_KAFKA_OUTPUT_TOPIC_HACKERNEWS]
        }
      }

      // URL Processors
      if (process.env.LOOM_KAFKA_INPUT_TOPIC_X_PROCESSOR && process.env.LOOM_KAFKA_OUTPUT_TOPIC_X_PROCESSOR) {
        mappings['x-url-processor'] = {
          input: [process.env.LOOM_KAFKA_INPUT_TOPIC_X_PROCESSOR],
          output: [process.env.LOOM_KAFKA_OUTPUT_TOPIC_X_PROCESSOR]
        }
      }

      if (process.env.LOOM_KAFKA_INPUT_TOPIC_HACKERNEWS_PROCESSOR && process.env.LOOM_KAFKA_OUTPUT_TOPIC_HACKERNEWS_PROCESSOR) {
        mappings['hackernews-url-processor'] = {
          input: [process.env.LOOM_KAFKA_INPUT_TOPIC_HACKERNEWS_PROCESSOR],
          output: [process.env.LOOM_KAFKA_OUTPUT_TOPIC_HACKERNEWS_PROCESSOR]
        }
      }

      // Database Consumer
      if (process.env.LOOM_KAFKA_CONSUMER_TOPICS) {
        try {
          const consumerTopics = JSON.parse(process.env.LOOM_KAFKA_CONSUMER_TOPICS)
          mappings['kafka-to-db-consumer'] = {
            input: consumerTopics,
            output: [] // Database consumer doesn't produce topics
          }
        } catch (e) {
          logger.warn('Failed to parse LOOM_KAFKA_CONSUMER_TOPICS as JSON')
        }
      }

      logger.info(`Built ${Object.keys(mappings).length} processor mappings from environment variables`)
      return mappings

    } catch (error) {
      logger.error('Error building processor mappings from environment:', error)
      return {}
    }
  }

  private getHardcodedMappings(): Record<string, { input: string[], output: string[] }> {
    return {
      // Audio Processing Pipeline
      'silero-vad-consumer': {
        input: ['device.audio.raw'],
        output: ['media.audio.vad_filtered']
      },
      'kyutai-stt-consumer': {
        input: ['device.audio.raw'],
        output: ['media.text.transcribed.words']
      },

      // Vision Processing Pipeline
      'minicpm-vision-consumer': {
        input: ['device.image.camera.raw', 'device.video.screen.raw'],
        output: ['media.image.analysis.minicpm_results']
      },
      'face-emotion-consumer': {
        input: ['media.image.analysis.minicpm_results'],
        output: ['analysis.image.emotion_results']
      },

      // External Data Services
      'x-likes-fetcher': {
        input: [],
        output: ['external.twitter.liked.raw']
      },
      'email-fetcher': {
        input: [],
        output: ['external.email.events.raw']
      },
      'calendar-fetcher': {
        input: [],
        output: ['external.calendar.events.raw']
      },
      'hackernews-fetcher': {
        input: [],
        output: ['external.hackernews.favorites.raw']
      },

      // URL Processors
      'x-url-processor': {
        input: ['task.url.ingest'],
        output: ['task.url.processed.twitter_archived']
      },
      'hackernews-url-processor': {
        input: ['external.hackernews.favorites.raw'],
        output: ['task.url.processed.hackernews_archived']
      },

      // Database Consumer
      'kafka-to-db-consumer': {
        input: [
          'device.audio.raw',
          'device.sensor.gps.raw',
          'device.sensor.accelerometer.raw',
          'media.text.transcribed.words',
          'analysis.audio.emotion_results',
          'analysis.image.emotion_results',
          'external.email.events.raw',
          'external.calendar.events.raw',
          'external.twitter.liked.raw',
          'external.hackernews.favorites.raw'
        ],
        output: []
      }
    }
  }
}
