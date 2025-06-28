import axios, { AxiosInstance } from 'axios'
import { EventEmitter } from 'events'
import { logger } from '../utils/logger'
import { ServiceRegistry, ServiceRegistration } from './serviceRegistry'
import { K8sDiscovery } from './k8sDiscovery'
import { KafkaClient } from '../kafka/client'

interface HealthStatus {
  serviceId: string
  serviceName: string
  status: 'healthy' | 'unhealthy' | 'degraded' | 'unknown'
  lastCheck: Date
  uptime?: number
  responseTime?: number
  details?: {
    liveness?: boolean
    readiness?: boolean
    kafka?: boolean
    database?: boolean
  }
  error?: string
}

interface ServiceMetrics {
  serviceId: string
  consumerLag?: number
  messagesProcessed?: number
  errorRate?: number
  averageProcessingTime?: number
}

export class HealthMonitor extends EventEmitter {
  private httpClient: AxiosInstance
  private healthStatuses: Map<string, HealthStatus> = new Map()
  private checkIntervals: Map<string, NodeJS.Timeout> = new Map()
  private readonly CHECK_INTERVAL = 30000 // 30 seconds
  private readonly HTTP_TIMEOUT = 5000 // 5 seconds

  constructor(
    private serviceRegistry: ServiceRegistry,
    private k8sDiscovery: K8sDiscovery,
    private kafkaClient: KafkaClient
  ) {
    super()
    
    this.httpClient = axios.create({
      timeout: this.HTTP_TIMEOUT,
      validateStatus: () => true // Don't throw on any status code
    })

    // Start monitoring registered services
    this.serviceRegistry.on('service:registered', (service) => {
      this.startMonitoring(service)
    })

    this.serviceRegistry.on('service:unregistered', (service) => {
      this.stopMonitoring(service.id)
    })

    // Start monitoring existing services
    this.initializeMonitoring()
  }

  private async initializeMonitoring(): Promise<void> {
    const services = this.serviceRegistry.getAllServices()
    for (const service of services) {
      await this.startMonitoring(service)
    }
  }

  async startMonitoring(service: ServiceRegistration): Promise<void> {
    // Initial health check
    await this.checkServiceHealth(service)

    // Set up periodic checks
    const interval = setInterval(async () => {
      await this.checkServiceHealth(service)
    }, this.CHECK_INTERVAL)

    this.checkIntervals.set(service.id, interval)
  }

  stopMonitoring(serviceId: string): void {
    const interval = this.checkIntervals.get(serviceId)
    if (interval) {
      clearInterval(interval)
      this.checkIntervals.delete(serviceId)
    }
    this.healthStatuses.delete(serviceId)
  }

  async checkServiceHealth(service: ServiceRegistration): Promise<HealthStatus> {
    const startTime = Date.now()
    const status: HealthStatus = {
      serviceId: service.id,
      serviceName: service.name,
      status: 'unknown',
      lastCheck: new Date(),
      details: {}
    }

    try {
      // Get service endpoint from K8s if not provided
      let baseUrl = service.endpoints.api
      if (!baseUrl && service.metadata.namespace) {
        baseUrl = await this.k8sDiscovery.getServiceEndpoint(
          service.name,
          service.metadata.namespace
        )
      }

      if (!baseUrl) {
        throw new Error('No service endpoint available')
      }

      // Check liveness
      if (service.endpoints.health) {
        try {
          const response = await this.httpClient.get(`${baseUrl}${service.endpoints.health}`)
          status.details!.liveness = response.status === 200
          status.responseTime = Date.now() - startTime
        } catch (error) {
          status.details!.liveness = false
          logger.warn(`Liveness check failed for ${service.name}`, error)
        }
      }

      // Check readiness
      if (service.endpoints.ready) {
        try {
          const response = await this.httpClient.get(`${baseUrl}${service.endpoints.ready}`)
          status.details!.readiness = response.status === 200
        } catch (error) {
          status.details!.readiness = false
          logger.warn(`Readiness check failed for ${service.name}`, error)
        }
      }

      // Check Kafka consumer health if applicable
      if (service.type === 'consumer' || service.capabilities.inputTopics?.length) {
        status.details!.kafka = await this.checkKafkaConsumerHealth(service)
      }

      // Calculate overall status
      const livenessOk = status.details!.liveness !== false
      const readinessOk = status.details!.readiness !== false
      const kafkaOk = status.details!.kafka !== false

      if (livenessOk && readinessOk && kafkaOk) {
        status.status = 'healthy'
      } else if (livenessOk) {
        status.status = 'degraded'
      } else {
        status.status = 'unhealthy'
      }

      // Calculate uptime
      const previousStatus = this.healthStatuses.get(service.id)
      if (previousStatus && previousStatus.status === 'healthy') {
        status.uptime = (previousStatus.uptime || 0) + this.CHECK_INTERVAL
      } else if (status.status === 'healthy') {
        status.uptime = 0
      }

    } catch (error) {
      status.status = 'unhealthy'
      status.error = error instanceof Error ? error.message : 'Unknown error'
      logger.error(`Health check failed for ${service.name}`, error)
    }

    // Store and emit status
    this.healthStatuses.set(service.id, status)
    this.serviceRegistry.updateServiceStatus(service.id, status.status)
    this.emit('health:updated', status)

    return status
  }

  private async checkKafkaConsumerHealth(service: ServiceRegistration): Promise<boolean> {
    if (!service.capabilities.inputTopics?.length) {
      return true
    }

    try {
      // Check consumer group lag
      const consumerGroupId = service.metadata?.labels?.['app'] + '-consumer'
      const lag = await this.kafkaClient.getConsumerLag(
        consumerGroupId,
        service.capabilities.inputTopics
      )

      if (lag && lag.length > 0) {
        const totalLag = lag.reduce((sum, l) => sum + l.lag, 0)
        
        // Consider unhealthy if lag is too high
        if (totalLag > 10000) {
          logger.warn(`High lag detected for ${service.name}: ${totalLag}`)
          return false
        }
      }

      return true
    } catch (error) {
      logger.error(`Failed to check Kafka health for ${service.name}`, error)
      return false
    }
  }

  async getServiceMetrics(serviceId: string): Promise<ServiceMetrics | null> {
    const service = this.serviceRegistry.getService(serviceId)
    if (!service) {
      return null
    }

    const metrics: ServiceMetrics = {
      serviceId: serviceId
    }

    try {
      // Get consumer lag if applicable
      if (service.capabilities.inputTopics?.length) {
        const consumerGroupId = service.metadata?.labels?.['app'] + '-consumer'
        const lag = await this.kafkaClient.getConsumerLag(
          consumerGroupId,
          service.capabilities.inputTopics
        )

        if (lag && lag.length > 0) {
          metrics.consumerLag = lag.reduce((sum, l) => sum + l.lag, 0)
        }
      }

      // Get other metrics from service endpoint if available
      if (service.endpoints.metrics) {
        try {
          const baseUrl = service.endpoints.api || 
            await this.k8sDiscovery.getServiceEndpoint(service.name, service.metadata.namespace!)
          
          if (baseUrl) {
            const response = await this.httpClient.get(`${baseUrl}${service.endpoints.metrics}`)
            if (response.status === 200 && response.data) {
              Object.assign(metrics, response.data)
            }
          }
        } catch (error) {
          logger.warn(`Failed to get metrics for ${service.name}`, error)
        }
      }

      return metrics
    } catch (error) {
      logger.error(`Failed to get service metrics for ${service.name}`, error)
      return metrics
    }
  }

  getHealthStatus(serviceId: string): HealthStatus | undefined {
    return this.healthStatuses.get(serviceId)
  }

  getAllHealthStatuses(): HealthStatus[] {
    return Array.from(this.healthStatuses.values())
  }

  getHealthyServices(): HealthStatus[] {
    return Array.from(this.healthStatuses.values()).filter(s => s.status === 'healthy')
  }

  getUnhealthyServices(): HealthStatus[] {
    return Array.from(this.healthStatuses.values()).filter(
      s => s.status === 'unhealthy' || s.status === 'degraded'
    )
  }

  // Calculate service dependencies health
  async getDependencyHealth(serviceId: string): Promise<{
    healthy: number
    unhealthy: number
    unknown: number
    score: number
  }> {
    const dependencies = this.serviceRegistry.getDependencies(serviceId)
    
    let healthy = 0
    let unhealthy = 0
    let unknown = 0

    for (const dep of dependencies) {
      const health = this.healthStatuses.get(dep.id)
      if (!health) {
        unknown++
      } else if (health.status === 'healthy') {
        healthy++
      } else {
        unhealthy++
      }
    }

    const total = dependencies.length
    const score = total > 0 ? (healthy / total) * 100 : 100

    return { healthy, unhealthy, unknown, score }
  }

  // Aggregate health for entire pipeline
  getPipelineHealth(): {
    totalServices: number
    healthy: number
    unhealthy: number
    degraded: number
    unknown: number
    overallHealth: 'healthy' | 'degraded' | 'critical'
  } {
    const statuses = this.getAllHealthStatuses()
    
    const summary = {
      totalServices: statuses.length,
      healthy: statuses.filter(s => s.status === 'healthy').length,
      unhealthy: statuses.filter(s => s.status === 'unhealthy').length,
      degraded: statuses.filter(s => s.status === 'degraded').length,
      unknown: statuses.filter(s => s.status === 'unknown').length,
      overallHealth: 'healthy' as 'healthy' | 'degraded' | 'critical'
    }

    // Calculate overall health
    const healthPercentage = summary.totalServices > 0
      ? (summary.healthy / summary.totalServices) * 100
      : 0

    if (healthPercentage >= 90) {
      summary.overallHealth = 'healthy'
    } else if (healthPercentage >= 70) {
      summary.overallHealth = 'degraded'
    } else {
      summary.overallHealth = 'critical'
    }

    return summary
  }

  // Clean up resources
  shutdown(): void {
    for (const interval of this.checkIntervals.values()) {
      clearInterval(interval)
    }
    this.checkIntervals.clear()
    this.healthStatuses.clear()
    this.removeAllListeners()
  }
}