import { Pool, PoolClient } from 'pg'
import { config } from '../config'
import { DatabaseMetrics } from '../types'
import { logger } from '../utils/logger'

export class DatabaseClient {
  private pool: Pool | null = null

  async connect(): Promise<void> {
    try {
      this.pool = new Pool({
        host: config.database.host,
        port: config.database.port,
        database: config.database.database,
        user: config.database.user,
        password: config.database.password,
        ssl: config.database.ssl,
        max: 10,
        idleTimeoutMillis: 30000,
        connectionTimeoutMillis: 2000,
      })

      // Test connection
      const client = await this.pool.connect()
      await client.query('SELECT NOW()')
      client.release()

      logger.info('Database client connected successfully')
    } catch (error) {
      logger.error('Failed to connect to database', error)
      throw error
    }
  }

  async disconnect(): Promise<void> {
    if (this.pool) {
      await this.pool.end()
      this.pool = null
      logger.info('Database client disconnected')
    }
  }

  async getMetrics(): Promise<DatabaseMetrics> {
    if (!this.pool) throw new Error('Database not connected')

    const client = await this.pool.connect()

    try {
      // Get total tables
      const tablesResult = await client.query(`
        SELECT COUNT(*) as count
        FROM information_schema.tables
        WHERE table_schema = 'public'
      `)
      const totalTables = parseInt(tablesResult.rows[0].count)

      // Get database size
      const sizeResult = await client.query(`
        SELECT pg_size_pretty(pg_database_size(current_database())) as size
      `)
      const databaseSize = sizeResult.rows[0].size

      // Get active connections
      const connectionsResult = await client.query(`
        SELECT COUNT(*) as count
        FROM pg_stat_activity
        WHERE state = 'active'
      `)
      const activeConnections = parseInt(connectionsResult.rows[0].count)

      // Get total rows (approximate)
      const rowsResult = await client.query(`
        SELECT SUM(n_tup_ins + n_tup_upd) as total_rows
        FROM pg_stat_user_tables
      `)
      const totalRows = parseInt(rowsResult.rows[0].total_rows || '0')

      // Get average query time (from pg_stat_statements if available)
      let avgQueryTime = 0
      try {
        const queryTimeResult = await client.query(`
          SELECT COALESCE(AVG(mean_time), 0) as avg_time
          FROM pg_stat_statements
          WHERE calls > 0
        `)
        avgQueryTime = parseFloat(queryTimeResult.rows[0]?.avg_time || '0')
      } catch (error) {
        // pg_stat_statements extension might not be available
        logger.debug('pg_stat_statements not available for query time metrics')
      }

      // Get slow queries count
      let slowQueries = 0
      try {
        const slowQueriesResult = await client.query(`
          SELECT COUNT(*) as count
          FROM pg_stat_statements
          WHERE mean_time > 1000
        `)
        slowQueries = parseInt(slowQueriesResult.rows[0]?.count || '0')
      } catch (error) {
        // pg_stat_statements extension might not be available
        logger.debug('pg_stat_statements not available for slow query metrics')
      }

      return {
        totalTables,
        totalRows,
        databaseSize,
        activeConnections,
        avgQueryTime,
        slowQueries,
      }
    } finally {
      client.release()
    }
  }

  async getTableMetrics(): Promise<any[]> {
    if (!this.pool) throw new Error('Database not connected')

    const client = await this.pool.connect()

    try {
      const result = await client.query(`
        SELECT
          schemaname,
          tablename,
          n_tup_ins as inserts,
          n_tup_upd as updates,
          n_tup_del as deletes,
          n_live_tup as live_tuples,
          n_dead_tup as dead_tuples,
          last_vacuum,
          last_autovacuum,
          last_analyze,
          last_autoanalyze
        FROM pg_stat_user_tables
        ORDER BY n_live_tup DESC
        LIMIT 20
      `)

      return result.rows
    } finally {
      client.release()
    }
  }

  async testConnection(): Promise<boolean> {
    if (!this.pool) return false

    try {
      const client = await this.pool.connect()
      await client.query('SELECT 1')
      client.release()
      return true
    } catch (error) {
      logger.error('Database connection test failed', error)
      return false
    }
  }

  async query(text: string, params?: any[]): Promise<any> {
    if (!this.pool) throw new Error('Database not connected')

    const client = await this.pool.connect()
    try {
      const result = await client.query(text, params)
      return result
    } finally {
      client.release()
    }
  }

  // Pipeline flow methods
  async getPipelineFlows(): Promise<any[]> {
    if (!this.pool) throw new Error('Database not connected')

    const query = `
      SELECT
        pf.flow_name,
        pf.description,
        pf.priority,
        pf.expected_events_per_second,
        pf.average_event_size_bytes,
        pf.peak_multiplier,
        pf.is_active,
        COUNT(DISTINCT ps.id) as stage_count,
        COUNT(DISTINCT pst.topic_name) as topic_count
      FROM pipeline_flows pf
      LEFT JOIN pipeline_stages ps ON pf.flow_name = ps.flow_name
      LEFT JOIN pipeline_stage_topics pst ON ps.id = pst.stage_id
      WHERE pf.is_active = true
      GROUP BY pf.flow_name, pf.description, pf.priority,
               pf.expected_events_per_second, pf.average_event_size_bytes,
               pf.peak_multiplier, pf.is_active
      ORDER BY pf.priority DESC, pf.flow_name
    `

    const result = await this.query(query)
    return result.rows
  }

  async getPipelineStages(flowName?: string): Promise<any[]> {
    if (!this.pool) throw new Error('Database not connected')

    let query = `
      SELECT
        ps.id,
        ps.flow_name,
        ps.stage_name,
        ps.stage_order,
        ps.service_name,
        ps.service_image,
        ps.replicas,
        ps.configuration,
        ps.processing_timeout_seconds,
        ps.retry_max_attempts,
        ps.retry_backoff_seconds,
        ps.sla_seconds,
        ps.error_rate_threshold,
        ps.is_active,
        array_agg(DISTINCT pst_in.topic_name) FILTER (WHERE pst_in.topic_role = 'input') as input_topics,
        array_agg(DISTINCT pst_out.topic_name) FILTER (WHERE pst_out.topic_role = 'output') as output_topics,
        array_agg(DISTINCT pst_err.topic_name) FILTER (WHERE pst_err.topic_role = 'error') as error_topics
      FROM pipeline_stages ps
      LEFT JOIN pipeline_stage_topics pst_in ON ps.id = pst_in.stage_id AND pst_in.topic_role = 'input'
      LEFT JOIN pipeline_stage_topics pst_out ON ps.id = pst_out.stage_id AND pst_out.topic_role = 'output'
      LEFT JOIN pipeline_stage_topics pst_err ON ps.id = pst_err.stage_id AND pst_err.topic_role = 'error'
    `

    const params: any[] = []
    if (flowName) {
      query += ' WHERE ps.flow_name = $1'
      params.push(flowName)
    }

    query += `
      GROUP BY ps.id, ps.flow_name, ps.stage_name, ps.stage_order,
               ps.service_name, ps.service_image, ps.replicas, ps.configuration,
               ps.processing_timeout_seconds, ps.retry_max_attempts,
               ps.retry_backoff_seconds, ps.sla_seconds, ps.error_rate_threshold,
               ps.is_active
      ORDER BY ps.flow_name, ps.stage_order
    `

    const result = await this.query(query, params)
    return result.rows
  }

  async getTopicMappings(): Promise<any[]> {
    if (!this.pool) throw new Error('Database not connected')

    const query = `
      SELECT
        kt.topic_name,
        kt.category,
        kt.source,
        kt.datatype,
        kt.stage,
        kt.description,
        kt.retention_days,
        kt.is_active,
        ttc.table_name,
        array_agg(DISTINCT tae.api_endpoint) FILTER (WHERE tae.is_primary = true) as primary_endpoints,
        array_agg(DISTINCT tae.api_endpoint) FILTER (WHERE tae.is_primary = false) as secondary_endpoints,
        COUNT(DISTINCT pst_in.stage_id) as consumer_count,
        COUNT(DISTINCT pst_out.stage_id) as producer_count
      FROM kafka_topics kt
      LEFT JOIN topic_table_configs ttc ON kt.topic_name = ttc.topic_name
      LEFT JOIN topic_api_endpoints tae ON kt.topic_name = tae.topic_name
      LEFT JOIN pipeline_stage_topics pst_in ON kt.topic_name = pst_in.topic_name AND pst_in.topic_role = 'input'
      LEFT JOIN pipeline_stage_topics pst_out ON kt.topic_name = pst_out.topic_name AND pst_out.topic_role = 'output'
      WHERE kt.is_active = true
      GROUP BY kt.topic_name, kt.category, kt.source, kt.datatype, kt.stage,
               kt.description, kt.retention_days, kt.is_active, ttc.table_name
      ORDER BY kt.category, kt.source, kt.datatype
    `

    const result = await this.query(query)
    return result.rows
  }

  async getPipelineTopology(): Promise<any> {
    if (!this.pool) throw new Error('Database not connected')

    // Get all active pipelines with their stages
    const flows = await this.getPipelineFlows()
    const stages = await this.getPipelineStages()
    const topics = await this.getTopicMappings()

    // Build a map of topic producers and consumers
    const topicProducers = new Map<string, string[]>()
    const topicConsumers = new Map<string, string[]>()

    stages.forEach(stage => {
      const serviceId = `${stage.flow_name}-${stage.service_name}`

      // Track producers
      if (stage.output_topics) {
        stage.output_topics.forEach((topic: string) => {
          if (!topicProducers.has(topic)) {
            topicProducers.set(topic, [])
          }
          topicProducers.get(topic)!.push(serviceId)
        })
      }

      // Track consumers
      if (stage.input_topics) {
        stage.input_topics.forEach((topic: string) => {
          if (!topicConsumers.has(topic)) {
            topicConsumers.set(topic, [])
          }
          topicConsumers.get(topic)!.push(serviceId)
        })
      }
    })

    return {
      flows,
      stages,
      topics,
      topology: {
        topicProducers: Object.fromEntries(topicProducers),
        topicConsumers: Object.fromEntries(topicConsumers)
      }
    }
  }

  async getServiceDependencies(): Promise<any[]> {
    if (!this.pool) throw new Error('Database not connected')

    const query = `
      WITH service_connections AS (
        SELECT DISTINCT
          ps1.service_name as from_service,
          ps2.service_name as to_service,
          pst1.topic_name as via_topic
        FROM pipeline_stages ps1
        JOIN pipeline_stage_topics pst1 ON ps1.id = pst1.stage_id AND pst1.topic_role = 'output'
        JOIN pipeline_stage_topics pst2 ON pst1.topic_name = pst2.topic_name AND pst2.topic_role = 'input'
        JOIN pipeline_stages ps2 ON pst2.stage_id = ps2.id
        WHERE ps1.service_name != ps2.service_name
          AND ps1.is_active = true
          AND ps2.is_active = true
      )
      SELECT
        from_service,
        to_service,
        array_agg(DISTINCT via_topic) as topics
      FROM service_connections
      GROUP BY from_service, to_service
      ORDER BY from_service, to_service
    `

    const result = await this.query(query)
    return result.rows
  }
}
