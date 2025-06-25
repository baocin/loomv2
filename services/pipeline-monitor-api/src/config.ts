import dotenv from 'dotenv'

dotenv.config()

export const config = {
  port: parseInt(process.env.PORT || '8080'),

  kafka: {
    brokers: (process.env.LOOM_KAFKA_BOOTSTRAP_SERVERS || 'localhost:9092').split(','),
    clientId: 'pipeline-monitor-api',
    connectionTimeout: 3000,
    requestTimeout: 30000,
  },

  database: {
    host: process.env.LOOM_DATABASE_HOST || 'localhost',
    port: parseInt(process.env.LOOM_DATABASE_PORT || '5432'),
    database: process.env.LOOM_DATABASE_NAME || 'loom',
    user: process.env.LOOM_DATABASE_USER || 'loom',
    password: process.env.LOOM_DATABASE_PASSWORD || 'loom',
    ssl: process.env.LOOM_DATABASE_SSL === 'true',
  },

  cors: {
    origin: process.env.CORS_ORIGIN || 'http://localhost:3000',
    credentials: true,
  },

  cache: {
    maxTopicMessages: parseInt(process.env.MAX_TOPIC_MESSAGES || '100'),
    cacheTimeout: parseInt(process.env.CACHE_TIMEOUT || '30000'), // 30 seconds
  },

  monitoring: {
    metricsInterval: parseInt(process.env.METRICS_INTERVAL || '5000'), // 5 seconds
    healthCheckInterval: parseInt(process.env.HEALTH_CHECK_INTERVAL || '10000'), // 10 seconds
  },
}
