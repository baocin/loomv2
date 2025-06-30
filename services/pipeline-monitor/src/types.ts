export interface KafkaTopicMetrics {
  topic: string
  lastMessageTime?: Date
  lastProcessedTime?: Date
  messageCount: number
  partitionCount: number
  consumerLag: number
  producerRate: number
  consumerRate: number
  isActive: boolean
}

export interface ConsumerMetrics {
  groupId: string
  topic: string
  partition: number
  currentOffset: number
  logEndOffset: number
  lag: number
  consumerId: string
  host: string
  lastHeartbeat: Date
}

export interface PipelineNode {
  id: string
  type: 'kafka-topic' | 'processor' | 'database' | 'external'
  position: { x: number; y: number }
  data: {
    label: string
    metrics?: KafkaTopicMetrics | ConsumerMetrics | any
    lastSampleData?: any
    status?: 'active' | 'idle' | 'error' | 'unknown'
    description?: string
    health?: any
    containerName?: string
    priority?: string
    models?: string[]
  }
}

export interface PipelineEdge {
  id: string
  source: string
  target: string
  label?: string
  animated?: boolean
  style?: {
    stroke?: string
    strokeWidth?: number
  }
}

export interface PipelineFlow {
  nodes: PipelineNode[]
  edges: PipelineEdge[]
}
