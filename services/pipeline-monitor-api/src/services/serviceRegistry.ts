import { EventEmitter } from 'events'
import { logger } from '../utils/logger'

export interface ServiceRegistration {
  id: string
  name: string
  version?: string
  type: 'processor' | 'producer' | 'consumer' | 'api'
  status: 'healthy' | 'unhealthy' | 'unknown'
  lastHeartbeat: Date
  endpoints: {
    health?: string
    ready?: string
    metrics?: string
    api?: string
  }
  capabilities: {
    inputTopics?: string[]
    outputTopics?: string[]
    processingType?: string
    description?: string
  }
  metadata: {
    pod?: string
    namespace?: string
    labels?: Record<string, string>
    annotations?: Record<string, string>
  }
  resources?: {
    cpu?: string
    memory?: string
    replicas?: number
  }
}

export class ServiceRegistry extends EventEmitter {
  private services: Map<string, ServiceRegistration> = new Map()
  private heartbeatTimeouts: Map<string, NodeJS.Timeout> = new Map()
  private readonly HEARTBEAT_TIMEOUT = 60000 // 60 seconds

  constructor() {
    super()

    // Cleanup stale services periodically
    setInterval(() => this.cleanupStaleServices(), 30000)
  }

  register(service: ServiceRegistration): void {
    const existingService = this.services.get(service.id)

    // Update service
    this.services.set(service.id, {
      ...service,
      lastHeartbeat: new Date()
    })

    // Reset heartbeat timeout
    this.resetHeartbeatTimeout(service.id)

    // Emit events
    if (!existingService) {
      this.emit('service:registered', service)
      logger.info(`Service registered: ${service.name} (${service.id})`)
    } else {
      this.emit('service:updated', service)
    }
  }

  unregister(serviceId: string): void {
    const service = this.services.get(serviceId)
    if (service) {
      this.services.delete(serviceId)
      this.clearHeartbeatTimeout(serviceId)
      this.emit('service:unregistered', service)
      logger.info(`Service unregistered: ${service.name} (${serviceId})`)
    }
  }

  heartbeat(serviceId: string): void {
    const service = this.services.get(serviceId)
    if (service) {
      service.lastHeartbeat = new Date()
      service.status = 'healthy'
      this.resetHeartbeatTimeout(serviceId)
    }
  }

  getService(serviceId: string): ServiceRegistration | undefined {
    return this.services.get(serviceId)
  }

  getAllServices(): ServiceRegistration[] {
    return Array.from(this.services.values())
  }

  getServicesByType(type: ServiceRegistration['type']): ServiceRegistration[] {
    return Array.from(this.services.values()).filter(s => s.type === type)
  }

  getServicesByInputTopic(topic: string): ServiceRegistration[] {
    return Array.from(this.services.values()).filter(
      s => s.capabilities.inputTopics?.includes(topic)
    )
  }

  getServicesByOutputTopic(topic: string): ServiceRegistration[] {
    return Array.from(this.services.values()).filter(
      s => s.capabilities.outputTopics?.includes(topic)
    )
  }

  getHealthyServices(): ServiceRegistration[] {
    return Array.from(this.services.values()).filter(s => s.status === 'healthy')
  }

  updateServiceStatus(serviceId: string, status: ServiceRegistration['status']): void {
    const service = this.services.get(serviceId)
    if (service) {
      service.status = status
      this.emit('service:status:changed', service)
    }
  }

  updateServiceEndpoints(serviceId: string, endpoints: ServiceRegistration['endpoints']): void {
    const service = this.services.get(serviceId)
    if (service) {
      service.endpoints = { ...service.endpoints, ...endpoints }
      this.emit('service:updated', service)
    }
  }

  updateServiceCapabilities(serviceId: string, capabilities: Partial<ServiceRegistration['capabilities']>): void {
    const service = this.services.get(serviceId)
    if (service) {
      service.capabilities = { ...service.capabilities, ...capabilities }
      this.emit('service:updated', service)
    }
  }

  private resetHeartbeatTimeout(serviceId: string): void {
    this.clearHeartbeatTimeout(serviceId)

    const timeout = setTimeout(() => {
      const service = this.services.get(serviceId)
      if (service) {
        service.status = 'unhealthy'
        this.emit('service:unhealthy', service)
        logger.warn(`Service ${service.name} (${serviceId}) marked unhealthy - no heartbeat`)
      }
    }, this.HEARTBEAT_TIMEOUT)

    this.heartbeatTimeouts.set(serviceId, timeout)
  }

  private clearHeartbeatTimeout(serviceId: string): void {
    const timeout = this.heartbeatTimeouts.get(serviceId)
    if (timeout) {
      clearTimeout(timeout)
      this.heartbeatTimeouts.delete(serviceId)
    }
  }

  private cleanupStaleServices(): void {
    const now = new Date()
    const staleThreshold = 5 * 60 * 1000 // 5 minutes

    for (const [serviceId, service] of this.services) {
      const timeSinceHeartbeat = now.getTime() - service.lastHeartbeat.getTime()
      if (timeSinceHeartbeat > staleThreshold) {
        this.unregister(serviceId)
        logger.info(`Removed stale service: ${service.name} (${serviceId})`)
      }
    }
  }

  // Helper method to build service topology
  buildTopology(): Map<string, Set<string>> {
    const topology = new Map<string, Set<string>>()

    for (const service of this.services.values()) {
      const outputs = service.capabilities.outputTopics || []

      for (const outputTopic of outputs) {
        // Find services that consume this topic
        const consumers = this.getServicesByInputTopic(outputTopic)

        for (const consumer of consumers) {
          if (!topology.has(service.id)) {
            topology.set(service.id, new Set())
          }
          topology.get(service.id)!.add(consumer.id)
        }
      }
    }

    return topology
  }

  // Get service dependencies
  getDependencies(serviceId: string): ServiceRegistration[] {
    const service = this.services.get(serviceId)
    if (!service || !service.capabilities.inputTopics) {
      return []
    }

    const dependencies: ServiceRegistration[] = []

    for (const inputTopic of service.capabilities.inputTopics) {
      const producers = this.getServicesByOutputTopic(inputTopic)
      dependencies.push(...producers)
    }

    return dependencies
  }

  // Get service dependents
  getDependents(serviceId: string): ServiceRegistration[] {
    const service = this.services.get(serviceId)
    if (!service || !service.capabilities.outputTopics) {
      return []
    }

    const dependents: ServiceRegistration[] = []

    for (const outputTopic of service.capabilities.outputTopics) {
      const consumers = this.getServicesByInputTopic(outputTopic)
      dependents.push(...consumers)
    }

    return dependents
  }

  // Export registry state
  toJSON(): Record<string, ServiceRegistration> {
    const result: Record<string, ServiceRegistration> = {}

    for (const [id, service] of this.services) {
      result[id] = { ...service }
    }

    return result
  }
}
