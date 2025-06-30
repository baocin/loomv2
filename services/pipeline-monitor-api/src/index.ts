import express from 'express'
import cors from 'cors'
import { createServer } from 'http'
import { config } from './config'
import { logger } from './utils/logger'
import { KafkaClient } from './kafka/client'
import { KafkaMetricsCollector } from './kafka/metrics'
import { DatabaseClient } from './database/client'
import { MonitorWebSocketServer } from './websocket/server'
import { createKafkaRoutes } from './routes/kafka'
import { createDatabaseRoutes } from './routes/database'
import { createHealthRoutes } from './routes/health'
import pipelineDefinitionsRoutes from './routes/pipeline-definitions'
import { K8sDiscovery } from './services/k8sDiscovery'
import { ServiceRegistry } from './services/serviceRegistry'
import { HealthMonitor } from './services/healthMonitor'

class PipelineMonitorAPI {
  private app: express.Application
  private server: any
  private kafkaClient: KafkaClient
  private databaseClient: DatabaseClient
  private metricsCollector: KafkaMetricsCollector
  private wsServer: MonitorWebSocketServer
  private k8sDiscovery: K8sDiscovery
  private serviceRegistry: ServiceRegistry
  private healthMonitor: HealthMonitor

  constructor() {
    this.app = express()
    this.kafkaClient = new KafkaClient()
    this.databaseClient = new DatabaseClient()
    this.metricsCollector = new KafkaMetricsCollector(this.kafkaClient)
    this.k8sDiscovery = new K8sDiscovery()
    this.serviceRegistry = new ServiceRegistry()
    this.healthMonitor = new HealthMonitor(this.serviceRegistry, this.k8sDiscovery, this.kafkaClient)
    this.wsServer = new MonitorWebSocketServer(this.metricsCollector, this.databaseClient, this.kafkaClient)

    this.setupMiddleware()
    this.setupRoutes()
  }

  private setupMiddleware(): void {
    // CORS
    this.app.use(cors(config.cors))

    // JSON parsing
    this.app.use(express.json({ limit: '10mb' }))
    this.app.use(express.urlencoded({ extended: true, limit: '10mb' }))

    // Request logging
    this.app.use((req, res, next) => {
      logger.info(`${req.method} ${req.path}`, {
        ip: req.ip,
        userAgent: req.get('User-Agent'),
      })
      next()
    })

    // Error handling
    this.app.use((error: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
      logger.error('Unhandled error', error)
      res.status(500).json({
        error: 'Internal server error',
        message: process.env.NODE_ENV === 'development' ? error.message : undefined,
      })
    })
  }

  private setupRoutes(): void {
    // Health routes
    this.app.use('/health', createHealthRoutes(
      this.kafkaClient,
      this.databaseClient,
      this.metricsCollector
    ))

    // API routes
    this.app.use('/api/kafka', createKafkaRoutes(
      this.kafkaClient,
      this.metricsCollector,
      this.k8sDiscovery,
      this.serviceRegistry,
      this.healthMonitor
    ))
    this.app.use('/api/database', createDatabaseRoutes(this.databaseClient))
    this.app.use('/api/pipeline-definitions', pipelineDefinitionsRoutes)

    // Root endpoint
    this.app.get('/', (req, res) => {
      res.json({
        service: 'pipeline-monitor-api',
        version: '1.0.0',
        status: 'running',
        timestamp: new Date().toISOString(),
        websocket: '/ws',
        endpoints: {
          health: '/health',
          kafka: '/api/kafka',
          database: '/api/database',
        },
      })
    })

    // 404 handler
    this.app.use('*', (req, res) => {
      res.status(404).json({
        error: 'Not found',
        path: req.originalUrl,
      })
    })
  }

  async start(): Promise<void> {
    try {
      // Connect to external services
      logger.info('Connecting to Kafka...')
      await this.kafkaClient.connect()

      logger.info('Connecting to database...')
      await this.databaseClient.connect()

      // Create HTTP server
      this.server = createServer(this.app)

      // Initialize WebSocket server
      this.wsServer.initialize(this.server)

      // Start HTTP server
      this.server.listen(config.port, '0.0.0.0', () => {
        logger.info(`Pipeline Monitor API started on port ${config.port}`)
        logger.info(`WebSocket endpoint: ws://localhost:${config.port}/ws`)
      })

      // Graceful shutdown handling
      process.on('SIGTERM', () => this.shutdown())
      process.on('SIGINT', () => this.shutdown())

    } catch (error) {
      logger.error('Failed to start server', error)
      process.exit(1)
    }
  }

  private async shutdown(): Promise<void> {
    logger.info('Shutting down Pipeline Monitor API...')

    try {
      // Shutdown health monitor
      this.healthMonitor.shutdown()

      // Close WebSocket server
      this.wsServer.shutdown()

      // Close HTTP server
      if (this.server) {
        await new Promise<void>((resolve) => {
          this.server.close(() => resolve())
        })
      }

      // Disconnect from external services
      await Promise.all([
        this.kafkaClient.disconnect(),
        this.databaseClient.disconnect(),
      ])

      logger.info('Pipeline Monitor API shut down successfully')
      process.exit(0)
    } catch (error) {
      logger.error('Error during shutdown', error)
      process.exit(1)
    }
  }
}

// Start the server
const api = new PipelineMonitorAPI()
api.start().catch((error) => {
  logger.error('Failed to start API', error)
  process.exit(1)
})
