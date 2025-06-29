import { KafkaClient } from '../kafka/client'
import { KafkaMetricsCollector } from '../kafka/metrics'
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

  constructor(kafkaClient: KafkaClient, metricsCollector: KafkaMetricsCollector) {
    this.kafkaClient = kafkaClient
    this.metricsCollector = metricsCollector
  }

  async detectFlows(): Promise<TopicFlow[]> {
    const flows: TopicFlow[] = []

    try {
      // Get consumer group subscriptions
      const subscriptions = await this.kafkaClient.getConsumerGroupSubscriptions()

      // Comprehensive processor mappings for all workflows
      const processorMappings: Record<string, { input: string[], output: string[] }> = {
        // Audio Processing Pipeline
        'silero-vad-consumer': {
          input: ['device.audio.raw'],
          output: ['media.audio.vad_filtered']
        },
        'parakeet-tdt-consumer': {
          input: ['media.audio.vad_filtered'],
          output: ['media.text.transcribed.words', 'media.text.word_timestamps']
        },
        'bud-e-emotion-consumer': {
          input: ['media.audio.vad_filtered'],
          output: ['analysis.audio.emotion_scores']
        },

        // Vision Processing Pipeline
        'minicpm-vision-consumer': {
          input: ['device.image.camera.raw', 'device.video.screen.raw'],
          output: ['media.image.vision_annotations']
        },
        'face-emotion-consumer': {
          input: ['media.image.vision_annotations'],
          output: ['analysis.image.face_emotions']
        },
        'moondream-ocr-consumer': {
          input: ['device.image.camera.raw', 'task.url.screenshot'],
          output: ['media.image.analysis.moondream_results']
        },

        // Text Processing Pipeline
        'text-embedder-consumer': {
          input: [
            'external.email.events.raw',
            'external.twitter.liked.raw',
            'media.text.transcribed.words',
            'task.url.processed.content'
          ],
          output: [
            'analysis.text.embedded.emails',
            'analysis.text.embedded.twitter',
            'analysis.text.embedded.general'
          ]
        },
        'nomic-embed-consumer': {
          input: [
            'device.text.notes.raw',
            'media.text.transcribed.words',
            'task.url.processed.content',
            'task.github.processed.content',
            'task.document.processed.content'
          ],
          output: ['analysis.embeddings.nomic']
        },

        // High-Level Reasoning Pipeline
        'mistral-reasoning-consumer': {
          input: [
            'media.text.word_timestamps',
            'task.url.processed.content',
            'analysis.audio.emotion_scores',
            'analysis.image.face_emotions'
          ],
          output: ['analysis.context.reasoning_chains']
        },
        'onefilellm-consumer': {
          input: ['device.text.notes.raw', 'media.text.transcribed.words'],
          output: ['analysis.text.summaries']
        },

        // External Data Processing
        'x-url-processor-consumer': {
          input: ['task.url.ingest'],
          output: ['task.url.processed.twitter_archived']
        },
        'hackernews-url-processor-consumer': {
          input: ['task.url.ingest'],
          output: ['task.url.processed.hackernews_archived']
        },
        'twitter-ocr-processor-consumer': {
          input: ['external.twitter.liked.raw'],
          output: ['task.url.screenshot', 'media.text.ocr_extracted']
        },

        // Data Fetchers (Scheduled Services)
        'x-likes-fetcher': {
          input: [],
          output: ['external.twitter.liked.raw']
        },
        'hackernews-fetcher': {
          input: [],
          output: ['external.hackernews.activity.raw']
        },
        'email-fetcher': {
          input: [],
          output: ['external.email.events.raw']
        },
        'calendar-fetcher': {
          input: [],
          output: ['external.calendar.events.raw']
        },

        // Database Consumer (consumes everything for storage)
        'kafka-to-db-consumer': {
          input: [
            // Raw device data
            'device.audio.raw',
            'device.image.camera.raw',
            'device.video.screen.raw',
            'device.sensor.gps.raw',
            'device.sensor.accelerometer.raw',
            'device.health.heartrate.raw',
            'device.state.power.raw',
            'device.system.apps.macos.raw',
            'device.system.apps.android.raw',
            // Processed media
            'media.audio.vad_filtered',
            'media.text.transcribed.words',
            'media.image.vision_annotations',
            // Analysis results
            'analysis.audio.emotion_scores',
            'analysis.image.face_emotions',
            'analysis.context.reasoning_chains',
            'analysis.text.embedded.emails',
            'analysis.text.embedded.twitter',
            // External data
            'external.twitter.liked.raw',
            'external.hackernews.activity.raw',
            'external.email.events.raw',
            'external.calendar.events.raw',
            // Task results
            'task.url.processed.twitter_archived',
            'task.url.processed.hackernews_archived'
          ],
          output: [] // Database consumer doesn't produce topics
        }
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

  async buildPipeline(): Promise<PipelineFlow> {
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
      'parakeet-tdt-consumer': ['media.audio.vad_filtered'],
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
    if (groupId.includes('transcr') || groupId.includes('speech') || groupId.includes('asr')) {
      return topics.filter(t => t.includes('vad_filtered'))
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
      'parakeet-tdt-consumer': ['media.text.transcribed.words'],
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
    if (groupId.includes('transcr') || groupId.includes('speech') || groupId.includes('asr')) {
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
      'parakeet-tdt-consumer': 'Speech-to-Text',
      'bud-e-emotion-consumer': 'Audio Emotion',

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
      'parakeet-tdt-consumer': 'Audio transcription',
      'bud-e-emotion-consumer': 'Audio emotion analysis',

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
      { groupId: 'parakeet-tdt-consumer', required: ['media.audio.vad_filtered'] },
      { groupId: 'bud-e-emotion-consumer', required: ['media.audio.vad_filtered'] },

      // Vision Pipeline
      { groupId: 'minicpm-vision-consumer', required: ['device.image.camera.raw'] },
      { groupId: 'face-emotion-consumer', required: ['media.image.vision_annotations'] },
      { groupId: 'moondream-ocr-consumer', required: ['device.image.camera.raw'] },

      // Text Pipeline
      { groupId: 'text-embedder-consumer', required: ['external.email.events.raw'] },
      { groupId: 'nomic-embed-consumer', required: ['device.text.notes.raw'] },

      // Reasoning Pipeline
      { groupId: 'mistral-reasoning-consumer', required: ['media.text.word_timestamps'] },
      { groupId: 'onefilellm-consumer', required: ['device.text.notes.raw'] },

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

    if (topics.some(t => t.startsWith('external.reddit'))) {
      producers.push({
        id: 'reddit-fetcher',
        type: 'external',
        label: 'Reddit Fetcher',
        description: 'Reddit activity tracking',
        outputTopics: topics.filter(t => t.includes('reddit'))
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
      'reddit-fetcher': ['external.reddit.activity.raw'],
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
}
