import { WebSocketServer, WebSocket } from 'ws'
import { IncomingMessage } from 'http'
import { KafkaMetricsCollector } from '../kafka/metrics'
import { DatabaseClient } from '../database/client'
import { logger } from '../utils/logger'

export class MonitorWebSocketServer {
  private wss: WebSocketServer | null = null
  private clients: Set<WebSocket> = new Set()
  private metricsCollector: KafkaMetricsCollector
  private databaseClient: DatabaseClient
  private broadcastInterval: NodeJS.Timeout | null = null

  constructor(
    metricsCollector: KafkaMetricsCollector,
    databaseClient: DatabaseClient
  ) {
    this.metricsCollector = metricsCollector
    this.databaseClient = databaseClient
  }

  initialize(server: any): void {
    this.wss = new WebSocketServer({
      server,
      path: '/ws',
      perMessageDeflate: {
        zlibDeflateOptions: {
          level: 6,
        },
      },
    })

    this.wss.on('connection', (ws: WebSocket, request: IncomingMessage) => {
      this.handleConnection(ws, request)
    })

    // Start broadcasting metrics to all connected clients
    this.startBroadcasting()

    logger.info('WebSocket server initialized')
  }

  private handleConnection(ws: WebSocket, request: IncomingMessage): void {
    const clientIp = request.socket.remoteAddress
    logger.info(`WebSocket client connected from ${clientIp}`)

    this.clients.add(ws)

    // Send initial data
    this.sendInitialData(ws)

    ws.on('message', (message: Buffer) => {
      try {
        const data = JSON.parse(message.toString())
        this.handleMessage(ws, data)
      } catch (error) {
        logger.error('Failed to parse WebSocket message', error)
        this.sendError(ws, 'Invalid message format')
      }
    })

    ws.on('close', () => {
      this.clients.delete(ws)
      logger.info(`WebSocket client disconnected from ${clientIp}`)
    })

    ws.on('error', (error) => {
      logger.error('WebSocket client error', error)
      this.clients.delete(ws)
    })

    // Send ping every 30 seconds to keep connection alive
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.ping()
      } else {
        clearInterval(pingInterval)
      }
    }, 30000)
  }

  private async sendInitialData(ws: WebSocket): Promise<void> {
    try {
      const [topicMetrics, consumerMetrics, dbMetrics] = await Promise.all([
        this.metricsCollector.collectTopicMetrics(),
        this.metricsCollector.collectConsumerMetrics(),
        this.databaseClient.getMetrics().catch(() => null),
      ])

      this.sendMessage(ws, {
        type: 'initial_data',
        data: {
          topicMetrics,
          consumerMetrics,
          databaseMetrics: dbMetrics,
          timestamp: new Date().toISOString(),
        },
      })
    } catch (error) {
      logger.error('Failed to send initial data', error)
      this.sendError(ws, 'Failed to fetch initial data')
    }
  }

  private handleMessage(ws: WebSocket, data: any): void {
    switch (data.type) {
      case 'subscribe_topic':
        this.handleTopicSubscription(ws, data.topic)
        break

      case 'unsubscribe_topic':
        this.handleTopicUnsubscription(ws, data.topic)
        break

      case 'request_metrics':
        this.sendCurrentMetrics(ws)
        break

      default:
        this.sendError(ws, `Unknown message type: ${data.type}`)
    }
  }

  private handleTopicSubscription(ws: WebSocket, topic: string): void {
    // Store topic subscription info in client metadata
    if (!ws.metadata) {
      ws.metadata = { subscribedTopics: new Set() }
    }
    ws.metadata.subscribedTopics.add(topic)

    logger.debug(`Client subscribed to topic: ${topic}`)
    this.sendMessage(ws, {
      type: 'subscription_confirmed',
      topic,
    })
  }

  private handleTopicUnsubscription(ws: WebSocket, topic: string): void {
    if (ws.metadata?.subscribedTopics) {
      ws.metadata.subscribedTopics.delete(topic)
    }

    logger.debug(`Client unsubscribed from topic: ${topic}`)
    this.sendMessage(ws, {
      type: 'unsubscription_confirmed',
      topic,
    })
  }

  private async sendCurrentMetrics(ws: WebSocket): Promise<void> {
    try {
      const [topicMetrics, consumerMetrics] = await Promise.all([
        this.metricsCollector.collectTopicMetrics(),
        this.metricsCollector.collectConsumerMetrics(),
      ])

      this.sendMessage(ws, {
        type: 'metrics_update',
        data: {
          topicMetrics,
          consumerMetrics,
          timestamp: new Date().toISOString(),
        },
      })
    } catch (error) {
      logger.error('Failed to send current metrics', error)
      this.sendError(ws, 'Failed to fetch current metrics')
    }
  }

  private startBroadcasting(): void {
    this.broadcastInterval = setInterval(async () => {
      if (this.clients.size === 0) return

      try {
        const [topicMetrics, consumerMetrics] = await Promise.all([
          this.metricsCollector.collectTopicMetrics(),
          this.metricsCollector.collectConsumerMetrics(),
        ])

        this.broadcast({
          type: 'metrics_update',
          data: {
            topicMetrics,
            consumerMetrics,
            timestamp: new Date().toISOString(),
          },
        })
      } catch (error) {
        logger.error('Failed to broadcast metrics', error)
      }
    }, 5000) // Broadcast every 5 seconds
  }

  private broadcast(message: any): void {
    const messageStr = JSON.stringify(message)

    for (const client of this.clients) {
      if (client.readyState === WebSocket.OPEN) {
        try {
          client.send(messageStr)
        } catch (error) {
          logger.error('Failed to send message to client', error)
          this.clients.delete(client)
        }
      } else {
        this.clients.delete(client)
      }
    }
  }

  private sendMessage(ws: WebSocket, message: any): void {
    if (ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify(message))
      } catch (error) {
        logger.error('Failed to send message to client', error)
      }
    }
  }

  private sendError(ws: WebSocket, error: string): void {
    this.sendMessage(ws, {
      type: 'error',
      message: error,
      timestamp: new Date().toISOString(),
    })
  }

  shutdown(): void {
    if (this.broadcastInterval) {
      clearInterval(this.broadcastInterval)
      this.broadcastInterval = null
    }

    for (const client of this.clients) {
      client.close()
    }
    this.clients.clear()

    if (this.wss) {
      this.wss.close()
      this.wss = null
    }

    logger.info('WebSocket server shut down')
  }

  getConnectedClientsCount(): number {
    return this.clients.size
  }
}

// Extend WebSocket interface to include metadata
declare module 'ws' {
  interface WebSocket {
    metadata?: {
      subscribedTopics: Set<string>
    }
  }
}
