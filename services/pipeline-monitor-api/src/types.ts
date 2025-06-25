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

export interface TopicMessage {
  topic: string
  partition: number
  offset: string
  key: string | null
  value: any
  timestamp: Date
  headers?: Record<string, string>
}

export interface DatabaseMetrics {
  totalTables: number
  totalRows: number
  databaseSize: string
  activeConnections: number
  avgQueryTime: number
  slowQueries: number
}

export interface SystemHealth {
  kafka: {
    connected: boolean
    brokers: number
    topics: number
  }
  database: {
    connected: boolean
    metrics: DatabaseMetrics
  }
  consumers: {
    active: number
    total: number
  }
}
