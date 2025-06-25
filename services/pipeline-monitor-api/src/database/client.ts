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
}
