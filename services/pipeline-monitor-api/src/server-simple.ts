import express from 'express'
import cors from 'cors'
import { Pool } from 'pg'
import { logger } from './utils/logger'

const app = express()
const port = process.env.PORT || 8080

// Middleware
app.use(cors())
app.use(express.json())

// Database connection
const pool = new Pool({
  host: process.env.LOOM_DATABASE_HOST || 'timescaledb',
  port: parseInt(process.env.LOOM_DATABASE_PORT || '5432'),
  database: process.env.LOOM_DATABASE_NAME || 'loom',
  user: process.env.LOOM_DATABASE_USER || 'loom',
  password: process.env.LOOM_DATABASE_PASSWORD || 'loom',
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000,
})

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok' })
})

// Get pipeline topology - the only endpoint we need
app.get('/api/pipelines/topology', async (req, res) => {
  try {
    // Get all pipeline flows
    const flowsResult = await pool.query(`
      SELECT DISTINCT flow_name, description, priority
      FROM pipeline_flows
      ORDER BY flow_name
    `)

    // Get all pipeline stages with their topics and consumer groups
    const stagesResult = await pool.query(`
      WITH stage_topics AS (
        SELECT
          pst.stage_id,
          array_agg(pst.topic_name) FILTER (WHERE pst.topic_role = 'input') as input_topics,
          array_agg(pst.topic_name) FILTER (WHERE pst.topic_role = 'output') as output_topics,
          array_agg(pst.topic_name) FILTER (WHERE pst.topic_role = 'error') as error_topics
        FROM pipeline_stage_topics pst
        GROUP BY pst.stage_id
      )
      SELECT
        ps.flow_name,
        ps.stage_name,
        ps.service_name,
        ps.stage_order,
        st.input_topics,
        st.output_topics,
        st.error_topics,
        ps.configuration as config,
        pcc.consumer_group_id
      FROM pipeline_stages ps
      LEFT JOIN stage_topics st ON ps.id = st.stage_id
      LEFT JOIN pipeline_consumer_configs pcc ON ps.service_name = pcc.service_name
      ORDER BY ps.flow_name, ps.stage_order
    `)

    // Get all topics - simplified query
    const topicsResult = await pool.query(`
      SELECT
        kt.topic_name,
        ttc.table_name,
        kt.retention_days,
        kt.description
      FROM kafka_topics kt
      LEFT JOIN topic_table_configs ttc ON kt.topic_name = ttc.topic_name
      WHERE kt.is_active = true
      ORDER BY kt.topic_name
    `)

    // Get API endpoint mappings
    const apiMappingsResult = await pool.query(`
      SELECT
        topic_name,
        api_endpoint,
        api_method,
        api_description,
        is_primary
      FROM topic_api_endpoints
      ORDER BY topic_name, api_endpoint
    `)

    res.json({
      flows: flowsResult.rows,
      stages: stagesResult.rows,
      topics: topicsResult.rows,
      apiMappings: apiMappingsResult.rows
    })
  } catch (error) {
    console.error('Failed to get pipeline topology:', error)
    logger.error('Failed to get pipeline topology:', error)
    res.status(500).json({
      error: 'Failed to fetch pipeline topology',
      details: error instanceof Error ? error.message : String(error)
    })
  }
})

// Error handling
app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
  logger.error('Unhandled error:', err)
  res.status(500).json({ error: 'Internal server error' })
})

// Start server
app.listen(port, () => {
  logger.info(`Pipeline monitor API (simplified) listening on port ${port}`)
})

// Graceful shutdown
process.on('SIGTERM', async () => {
  logger.info('SIGTERM received, shutting down gracefully')
  await pool.end()
  process.exit(0)
})
