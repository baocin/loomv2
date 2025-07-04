import { DatabaseClient } from '../database/client'
import { logger } from '../utils/logger'

export interface ConsumerConfig {
  serviceName: string
  consumerGroupId: string
  maxPollRecords: number
  sessionTimeoutMs: number
  maxPollIntervalMs: number
  heartbeatIntervalMs: number
  partitionAssignmentStrategy: string
  enableAutoCommit: boolean
  autoCommitIntervalMs: number
  autoOffsetReset: 'earliest' | 'latest' | 'none'
  fetchMinBytes: number
  fetchMaxWaitMs: number
  maxPartitionFetchBytes: number
  requestTimeoutMs: number
  retryBackoffMs: number
  reconnectBackoffMs: number
  reconnectBackoffMaxMs: number
}

export interface KafkaConsumerOptions {
  'group.id': string
  'session.timeout.ms': number
  'max.poll.interval.ms': number
  'heartbeat.interval.ms': number
  'enable.auto.commit': boolean
  'auto.commit.interval.ms': number
  'auto.offset.reset': 'earliest' | 'latest' | 'none'
  'fetch.min.bytes': number
  'fetch.wait.max.ms': number
  'max.partition.fetch.bytes': number
  'request.timeout.ms': number
  'retry.backoff.ms': number
  'reconnect.backoff.ms': number
  'reconnect.backoff.max.ms': number
  'partition.assignment.strategy': string
  'max.poll.records': number
}

export class ConsumerConfigLoader {
  constructor(private databaseClient: DatabaseClient) {}

  /**
   * Load consumer configuration for a specific service from the database
   */
  async loadConfig(serviceName: string): Promise<ConsumerConfig | null> {
    try {
      const query = `
        SELECT 
          service_name,
          consumer_group_id,
          max_poll_records,
          session_timeout_ms,
          max_poll_interval_ms,
          heartbeat_interval_ms,
          partition_assignment_strategy,
          enable_auto_commit,
          auto_commit_interval_ms,
          auto_offset_reset,
          fetch_min_bytes,
          fetch_max_wait_ms,
          max_partition_fetch_bytes,
          request_timeout_ms,
          retry_backoff_ms,
          reconnect_backoff_ms,
          reconnect_backoff_max_ms
        FROM pipeline_consumer_configs
        WHERE service_name = $1
      `
      
      const result = await this.databaseClient.query(query, [serviceName])
      
      if (result.rows.length === 0) {
        logger.warn(`No consumer configuration found for service: ${serviceName}`)
        return null
      }

      const row = result.rows[0]
      return {
        serviceName: row.service_name,
        consumerGroupId: row.consumer_group_id,
        maxPollRecords: row.max_poll_records,
        sessionTimeoutMs: row.session_timeout_ms,
        maxPollIntervalMs: row.max_poll_interval_ms,
        heartbeatIntervalMs: row.heartbeat_interval_ms,
        partitionAssignmentStrategy: row.partition_assignment_strategy,
        enableAutoCommit: row.enable_auto_commit,
        autoCommitIntervalMs: row.auto_commit_interval_ms,
        autoOffsetReset: row.auto_offset_reset,
        fetchMinBytes: row.fetch_min_bytes,
        fetchMaxWaitMs: row.fetch_max_wait_ms,
        maxPartitionFetchBytes: row.max_partition_fetch_bytes,
        requestTimeoutMs: row.request_timeout_ms,
        retryBackoffMs: row.retry_backoff_ms,
        reconnectBackoffMs: row.reconnect_backoff_ms,
        reconnectBackoffMaxMs: row.reconnect_backoff_max_ms
      }
    } catch (error) {
      logger.error(`Failed to load consumer config for ${serviceName}`, error)
      throw error
    }
  }

  /**
   * Convert database config to Kafka consumer options format
   */
  toKafkaOptions(config: ConsumerConfig): KafkaConsumerOptions {
    return {
      'group.id': config.consumerGroupId,
      'session.timeout.ms': config.sessionTimeoutMs,
      'max.poll.interval.ms': config.maxPollIntervalMs,
      'heartbeat.interval.ms': config.heartbeatIntervalMs,
      'enable.auto.commit': config.enableAutoCommit,
      'auto.commit.interval.ms': config.autoCommitIntervalMs,
      'auto.offset.reset': config.autoOffsetReset,
      'fetch.min.bytes': config.fetchMinBytes,
      'fetch.wait.max.ms': config.fetchMaxWaitMs,
      'max.partition.fetch.bytes': config.maxPartitionFetchBytes,
      'request.timeout.ms': config.requestTimeoutMs,
      'retry.backoff.ms': config.retryBackoffMs,
      'reconnect.backoff.ms': config.reconnectBackoffMs,
      'reconnect.backoff.max.ms': config.reconnectBackoffMaxMs,
      'partition.assignment.strategy': config.partitionAssignmentStrategy,
      'max.poll.records': config.maxPollRecords
    }
  }

  /**
   * Get default configuration if no database config exists
   */
  getDefaultConfig(serviceName: string): ConsumerConfig {
    // Conservative defaults
    return {
      serviceName,
      consumerGroupId: `loom-${serviceName}`,
      maxPollRecords: 100,
      sessionTimeoutMs: 60000,
      maxPollIntervalMs: 300000,
      heartbeatIntervalMs: 20000,
      partitionAssignmentStrategy: 'range',
      enableAutoCommit: false,
      autoCommitIntervalMs: 5000,
      autoOffsetReset: 'earliest',
      fetchMinBytes: 1,
      fetchMaxWaitMs: 500,
      maxPartitionFetchBytes: 1048576, // 1MB
      requestTimeoutMs: 305000,
      retryBackoffMs: 100,
      reconnectBackoffMs: 50,
      reconnectBackoffMaxMs: 1000
    }
  }

  /**
   * Load all consumer configurations
   */
  async loadAllConfigs(): Promise<Map<string, ConsumerConfig>> {
    try {
      const query = `
        SELECT * FROM pipeline_consumer_configs
        ORDER BY service_name
      `
      
      const result = await this.databaseClient.query(query)
      const configs = new Map<string, ConsumerConfig>()

      for (const row of result.rows) {
        configs.set(row.service_name, {
          serviceName: row.service_name,
          consumerGroupId: row.consumer_group_id,
          maxPollRecords: row.max_poll_records,
          sessionTimeoutMs: row.session_timeout_ms,
          maxPollIntervalMs: row.max_poll_interval_ms,
          heartbeatIntervalMs: row.heartbeat_interval_ms,
          partitionAssignmentStrategy: row.partition_assignment_strategy,
          enableAutoCommit: row.enable_auto_commit,
          autoCommitIntervalMs: row.auto_commit_interval_ms,
          autoOffsetReset: row.auto_offset_reset,
          fetchMinBytes: row.fetch_min_bytes,
          fetchMaxWaitMs: row.fetch_max_wait_ms,
          maxPartitionFetchBytes: row.max_partition_fetch_bytes,
          requestTimeoutMs: row.request_timeout_ms,
          retryBackoffMs: row.retry_backoff_ms,
          reconnectBackoffMs: row.reconnect_backoff_ms,
          reconnectBackoffMaxMs: row.reconnect_backoff_max_ms
        })
      }

      logger.info(`Loaded ${configs.size} consumer configurations`)
      return configs
    } catch (error) {
      logger.error('Failed to load all consumer configs', error)
      throw error
    }
  }

  /**
   * Get recommended configuration based on processing characteristics
   */
  async getRecommendedConfig(
    serviceName: string,
    processingTimeMs: number,
    isCpuIntensive: boolean,
    requiresGpu: boolean,
    isNetworkBound: boolean
  ): Promise<ConsumerConfig> {
    // Try to load existing config first
    const existingConfig = await this.loadConfig(serviceName)
    if (existingConfig) {
      return existingConfig
    }

    // Generate recommended config based on characteristics
    const baseConfig = this.getDefaultConfig(serviceName)

    if (requiresGpu || processingTimeMs > 10000) {
      // Very slow processing - process one at a time
      baseConfig.maxPollRecords = 1
      baseConfig.maxPollIntervalMs = Math.max(600000, processingTimeMs * 3)
      baseConfig.sessionTimeoutMs = Math.min(baseConfig.maxPollIntervalMs / 2, 300000)
    } else if (isCpuIntensive || processingTimeMs > 1000) {
      // CPU intensive - small batches
      baseConfig.maxPollRecords = 10
      baseConfig.maxPollIntervalMs = Math.max(300000, processingTimeMs * 20)
      baseConfig.sessionTimeoutMs = Math.min(baseConfig.maxPollIntervalMs / 3, 120000)
    } else if (isNetworkBound) {
      // Network bound - moderate batches with longer timeouts
      baseConfig.maxPollRecords = 20
      baseConfig.maxPollIntervalMs = 360000
      baseConfig.sessionTimeoutMs = 180000
      baseConfig.fetchMaxWaitMs = 5000 // Wait longer for batches
    } else if (processingTimeMs < 100) {
      // Fast processing - large batches
      baseConfig.maxPollRecords = 500
      baseConfig.maxPollIntervalMs = 60000
      baseConfig.sessionTimeoutMs = 30000
    }

    // Use sticky partitions for stateful processing
    if (isCpuIntensive || requiresGpu) {
      baseConfig.partitionAssignmentStrategy = 'sticky'
    }

    // Adjust heartbeat interval
    baseConfig.heartbeatIntervalMs = Math.floor(baseConfig.sessionTimeoutMs / 3)

    // Ensure request timeout is larger than poll interval
    baseConfig.requestTimeoutMs = baseConfig.maxPollIntervalMs + 5000

    return baseConfig
  }

  /**
   * Validate consumer configuration
   */
  validateConfig(config: ConsumerConfig): string[] {
    const errors: string[] = []

    // Validate timeout relationships
    if (config.sessionTimeoutMs <= config.heartbeatIntervalMs * 2) {
      errors.push('Session timeout must be greater than 2x heartbeat interval')
    }

    if (config.maxPollIntervalMs <= config.sessionTimeoutMs) {
      errors.push('Max poll interval must be greater than session timeout')
    }

    if (config.requestTimeoutMs <= config.maxPollIntervalMs) {
      errors.push('Request timeout must be greater than max poll interval')
    }

    // Validate poll records
    if (config.maxPollRecords <= 0 || config.maxPollRecords > 5000) {
      errors.push('Max poll records must be between 1 and 5000')
    }

    // Validate partition assignment strategy
    const validStrategies = ['range', 'roundrobin', 'sticky', 'cooperative-sticky']
    if (!validStrategies.includes(config.partitionAssignmentStrategy)) {
      errors.push(`Invalid partition assignment strategy: ${config.partitionAssignmentStrategy}`)
    }

    return errors
  }
}

// Export a helper function for standalone usage
export async function loadConsumerConfig(
  databaseClient: DatabaseClient,
  serviceName: string
): Promise<KafkaConsumerOptions> {
  const loader = new ConsumerConfigLoader(databaseClient)
  const config = await loader.loadConfig(serviceName)
  
  if (!config) {
    logger.warn(`Using default config for service: ${serviceName}`)
    const defaultConfig = loader.getDefaultConfig(serviceName)
    return loader.toKafkaOptions(defaultConfig)
  }

  const errors = loader.validateConfig(config)
  if (errors.length > 0) {
    logger.error(`Invalid consumer config for ${serviceName}: ${errors.join(', ')}`)
    throw new Error(`Invalid consumer configuration: ${errors.join(', ')}`)
  }

  return loader.toKafkaOptions(config)
}