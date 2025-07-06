import { Pool } from 'pg';
import { Kafka, Consumer, ConsumerConfig, KafkaConfig } from 'kafkajs';
import { logger } from '../utils/logger';

interface ConsumerConfiguration {
  serviceName: string;
  maxPollRecords: number;
  fetchMaxWaitMs: number;
  sessionTimeoutMs: number;
  maxPollIntervalMs: number;
  enableAutoCommit: boolean;
  autoOffsetReset: 'latest' | 'earliest';
  fetchMinBytes: number;
  fetchMaxBytes: number;
  maxPartitionFetchBytes: number;
  retryBackoffMs: number;
  requestTimeoutMs: number;
  connectionsMaxIdleMs: number;
  isolationLevel: number;
  description?: string;
}

interface ProcessingRecommendation {
  serviceName: string;
  currentConfig: string;
  recommendedConfig: string;
  reason: string;
  priority: string;
}

export class KafkaConsumerConfigLoader {
  private pool: Pool;
  private kafka: Kafka;
  private configCache: Map<string, ConsumerConfiguration> = new Map();
  private cacheExpiry = 5 * 60 * 1000; // 5 minutes
  private lastCacheUpdate = 0;

  constructor(pool: Pool, kafkaConfig: KafkaConfig) {
    this.pool = pool;
    this.kafka = new Kafka(kafkaConfig);
  }

  /**
   * Load consumer configuration for a specific service
   */
  async loadConfig(serviceName: string): Promise<ConsumerConfiguration | null> {
    // Check cache first
    if (this.configCache.has(serviceName) &&
        Date.now() - this.lastCacheUpdate < this.cacheExpiry) {
      return this.configCache.get(serviceName)!;
    }

    try {
      const query = `
        SELECT
          service_name,
          max_poll_records,
          fetch_max_wait_ms,
          session_timeout_ms,
          max_poll_interval_ms,
          enable_auto_commit,
          auto_offset_reset,
          fetch_min_bytes,
          fetch_max_bytes,
          max_partition_fetch_bytes,
          retry_backoff_ms,
          request_timeout_ms,
          connections_max_idle_ms,
          isolation_level,
          description
        FROM pipeline_consumer_configs
        WHERE service_name = $1
      `;

      const result = await this.pool.query(query, [serviceName]);

      if (result.rows.length === 0) {
        logger.warn(`No consumer config found for service: ${serviceName}`);
        return null;
      }

      const config = this.mapRowToConfig(result.rows[0]);
      this.configCache.set(serviceName, config);
      this.lastCacheUpdate = Date.now();

      return config;
    } catch (error) {
      logger.error('Error loading consumer config:', error);
      throw error;
    }
  }

  /**
   * Create a configured Kafka consumer for a service
   */
  async createConsumer(
    serviceName: string,
    topics: string[],
    groupId?: string
  ): Promise<Consumer | null> {
    const config = await this.loadConfig(serviceName);
    if (!config) {
      logger.warn(`Creating consumer with defaults for ${serviceName}`);
      return this.createDefaultConsumer(serviceName, topics, groupId);
    }

    const consumerConfig: ConsumerConfig = {
      groupId: groupId || `${serviceName}-consumer-group`,
      sessionTimeout: config.sessionTimeoutMs,
      heartbeatInterval: Math.floor(config.sessionTimeoutMs / 3),
      maxWaitTimeInMs: config.fetchMaxWaitMs,
      retry: {
        retries: 5,
        initialRetryTime: config.retryBackoffMs,
      },
    };

    const consumer = this.kafka.consumer(consumerConfig);

    // Subscribe with specific options
    await consumer.subscribe({
      topics,
      fromBeginning: config.autoOffsetReset === 'earliest',
    });

    logger.info(`Created optimized consumer for ${serviceName}`, {
      topics,
      maxPollRecords: config.maxPollRecords,
      sessionTimeout: config.sessionTimeoutMs,
    });

    return consumer;
  }

  /**
   * Create a default consumer if no config exists
   */
  private createDefaultConsumer(
    serviceName: string,
    topics: string[],
    groupId?: string
  ): Consumer {
    const consumer = this.kafka.consumer({
      groupId: groupId || `${serviceName}-consumer-group`,
      sessionTimeout: 30000,
      heartbeatInterval: 10000,
    });

    consumer.subscribe({ topics, fromBeginning: false });
    return consumer;
  }

  /**
   * Get processing recommendations for services
   */
  async getProcessingRecommendations(): Promise<ProcessingRecommendation[]> {
    try {
      const query = `
        WITH consumer_stats AS (
          SELECT
            h.service_name,
            AVG(h.lag) as avg_lag,
            MAX(h.lag) as max_lag,
            COUNT(*) as measurement_count
          FROM consumer_lag_history h
          WHERE h.timestamp > NOW() - INTERVAL '1 hour'
          GROUP BY h.service_name
        ),
        processing_stats AS (
          SELECT
            m.service_name,
            AVG(m.messages_per_second) as avg_throughput,
            AVG(m.processing_time_ms) as avg_processing_time
          FROM consumer_processing_metrics m
          WHERE m.timestamp > NOW() - INTERVAL '1 hour'
          GROUP BY m.service_name
        )
        SELECT
          c.service_name,
          c.max_poll_records,
          c.session_timeout_ms,
          cs.avg_lag,
          cs.max_lag,
          ps.avg_throughput,
          ps.avg_processing_time,
          CASE
            WHEN cs.avg_lag > 1000 AND c.max_poll_records < 100
              THEN 'Increase max_poll_records to reduce lag'
            WHEN ps.avg_processing_time > c.session_timeout_ms * 0.8
              THEN 'Increase session timeout to prevent rebalances'
            WHEN cs.avg_lag < 10 AND c.max_poll_records > 100
              THEN 'Decrease max_poll_records to reduce latency'
            ELSE 'Configuration optimal'
          END as recommendation,
          CASE
            WHEN cs.avg_lag > 1000 THEN 'high'
            WHEN ps.avg_processing_time > c.session_timeout_ms * 0.8 THEN 'high'
            WHEN cs.avg_lag > 100 THEN 'medium'
            ELSE 'low'
          END as priority
        FROM pipeline_consumer_configs c
        LEFT JOIN consumer_stats cs ON c.service_name = cs.service_name
        LEFT JOIN processing_stats ps ON c.service_name = ps.service_name
        WHERE cs.service_name IS NOT NULL
          AND (cs.avg_lag > 100 OR ps.avg_processing_time > c.session_timeout_ms * 0.5)
        ORDER BY
          CASE
            WHEN cs.avg_lag > 1000 THEN 1
            WHEN ps.avg_processing_time > c.session_timeout_ms * 0.8 THEN 2
            ELSE 3
          END
      `;

      const result = await this.pool.query(query);
      return result.rows.map(row => this.mapRowToRecommendation(row));
    } catch (error) {
      logger.error('Error getting processing recommendations:', error);
      return [];
    }
  }

  /**
   * Record consumer lag metrics
   */
  async recordConsumerLag(
    serviceName: string,
    topic: string,
    partition: number,
    lag: number,
    offset: number
  ): Promise<void> {
    try {
      const query = `
        INSERT INTO consumer_lag_history
        (service_name, topic, partition, lag, consumer_offset)
        VALUES ($1, $2, $3, $4, $5)
      `;

      await this.pool.query(query, [serviceName, topic, partition, lag, offset]);
    } catch (error) {
      logger.error('Error recording consumer lag:', error);
    }
  }

  /**
   * Record processing metrics
   */
  async recordProcessingMetrics(
    serviceName: string,
    messagesProcessed: number,
    processingTimeMs: number,
    memoryUsageMb: number
  ): Promise<void> {
    try {
      const messagesPerSecond = (messagesProcessed / processingTimeMs) * 1000;

      const query = `
        INSERT INTO consumer_processing_metrics
        (service_name, messages_processed, processing_time_ms, messages_per_second, memory_usage_mb)
        VALUES ($1, $2, $3, $4, $5)
      `;

      await this.pool.query(query, [
        serviceName,
        messagesProcessed,
        processingTimeMs,
        messagesPerSecond,
        memoryUsageMb
      ]);
    } catch (error) {
      logger.error('Error recording processing metrics:', error);
    }
  }

  /**
   * Helper to poll messages respecting max_poll_records
   */
  async pollWithLimit(
    consumer: Consumer,
    serviceName: string,
    handler: (messages: any[]) => Promise<void>
  ): Promise<void> {
    const config = await this.loadConfig(serviceName);
    const maxBatchSize = config?.maxPollRecords || 100;

    await consumer.run({
      autoCommit: config?.enableAutoCommit ?? true,
      eachBatch: async ({ batch, commitOffsetsIfNecessary }) => {
        const messages = batch.messages.slice(0, maxBatchSize);

        const startTime = Date.now();
        await handler(messages);
        const processingTime = Date.now() - startTime;

        // Record metrics
        await this.recordProcessingMetrics(
          serviceName,
          messages.length,
          processingTime,
          process.memoryUsage().heapUsed / 1024 / 1024
        );

        // Commit if auto-commit is disabled
        if (!config?.enableAutoCommit) {
          await commitOffsetsIfNecessary();
        }
      },
    });
  }

  private mapRowToConfig(row: any): ConsumerConfiguration {
    return {
      serviceName: row.service_name,
      maxPollRecords: row.max_poll_records,
      fetchMaxWaitMs: row.fetch_max_wait_ms,
      sessionTimeoutMs: row.session_timeout_ms,
      maxPollIntervalMs: row.max_poll_interval_ms,
      enableAutoCommit: row.enable_auto_commit,
      autoOffsetReset: row.auto_offset_reset,
      fetchMinBytes: row.fetch_min_bytes,
      fetchMaxBytes: row.fetch_max_bytes,
      maxPartitionFetchBytes: row.max_partition_fetch_bytes,
      retryBackoffMs: row.retry_backoff_ms,
      requestTimeoutMs: row.request_timeout_ms,
      connectionsMaxIdleMs: row.connections_max_idle_ms,
      isolationLevel: row.isolation_level,
      description: row.description,
    };
  }

  private mapRowToRecommendation(row: any): ProcessingRecommendation {
    return {
      serviceName: row.service_name,
      currentConfig: `max_poll_records: ${row.max_poll_records}, session_timeout: ${row.session_timeout_ms}`,
      recommendedConfig: row.recommendation,
      reason: `Avg lag: ${Math.round(row.avg_lag)}, Avg processing time: ${Math.round(row.avg_processing_time)}ms`,
      priority: row.priority,
    };
  }
}

// Helper function to create a properly configured consumer
export async function createOptimizedConsumer(
  pool: Pool,
  kafkaConfig: KafkaConfig,
  serviceName: string,
  topics: string[],
  groupId?: string
): Promise<Consumer | null> {
  const loader = new KafkaConsumerConfigLoader(pool, kafkaConfig);
  return loader.createConsumer(serviceName, topics, groupId);
}
