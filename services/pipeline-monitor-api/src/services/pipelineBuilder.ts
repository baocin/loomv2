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

export class PipelineBuilder {
  private kafkaClient: KafkaClient
  private metricsCollector: KafkaMetricsCollector

  constructor(kafkaClient: KafkaClient, metricsCollector: KafkaMetricsCollector) {
    this.kafkaClient = kafkaClient
    this.metricsCollector = metricsCollector
  }

  async buildPipeline(): Promise<PipelineFlow> {
    try {
      const topics = await this.kafkaClient.getTopics()
      const consumerGroups = await this.kafkaClient.getConsumerGroups()

      // Filter out internal topics
      const userTopics = topics.filter(t => !t.startsWith('__') && !t.startsWith('_'))

      const nodes: PipelineNode[] = []
      const edges: PipelineEdge[] = []
      const nodePositions = new Map<string, { x: number; y: number }>()

      // Categorize topics by their purpose
      const categories = this.categorizeTopics(userTopics)

      // Create external source nodes
      let xPos = 0
      let yPos = 100

      const externalSources = this.getExternalSources(categories)
      externalSources.forEach((source, idx) => {
        const nodeId = `external-${source.id}`
        nodes.push({
          id: nodeId,
          type: 'external',
          position: { x: xPos, y: yPos + idx * 100 },
          data: {
            label: source.label,
            status: 'active',
            description: source.description
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

        // Connect external sources to raw topics
        const sourceType = this.getTopicSourceType(topic)
        const sourceNode = externalSources.find(s => s.type === sourceType)
        if (sourceNode) {
          edges.push({
            id: `e-${sourceNode.id}-${nodeId}`,
            source: `external-${sourceNode.id}`,
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

    // Identify VAD processor
    if (topics.includes('device.audio.raw') && topics.includes('media.audio.vad_filtered')) {
      processors.push({
        id: 'vad-processor',
        label: 'VAD Processor',
        description: 'Voice Activity Detection',
        inputTopics: ['device.audio.raw'],
        outputTopics: ['media.audio.vad_filtered']
      })
    }

    // Identify transcription service
    if (topics.includes('media.audio.vad_filtered') &&
        topics.some(t => t.includes('transcribed'))) {
      processors.push({
        id: 'transcription-service',
        label: 'Speech-to-Text',
        description: 'Audio transcription',
        inputTopics: ['media.audio.vad_filtered'],
        outputTopics: topics.filter(t => t.includes('transcribed'))
      })
    }

    // Identify vision processor
    if (topics.some(t => t.includes('image') && t.includes('raw')) &&
        topics.some(t => t.includes('vision'))) {
      processors.push({
        id: 'vision-processor',
        label: 'Vision Analyzer',
        description: 'Image analysis & OCR',
        inputTopics: topics.filter(t => t.includes('image') && t.includes('raw')),
        outputTopics: topics.filter(t => t.includes('vision'))
      })
    }

    return processors
  }

  private getTopicLabel(topic: string): string {
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
