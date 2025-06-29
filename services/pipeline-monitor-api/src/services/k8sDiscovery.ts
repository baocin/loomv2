import * as k8s from '@kubernetes/client-node'
import { logger } from '../utils/logger'

interface ServiceInfo {
  name: string
  namespace: string
  labels: Record<string, string>
  annotations: Record<string, string>
  selector: Record<string, string>
  ports: Array<{
    name?: string
    port: number
    targetPort?: number | string
    protocol?: string
  }>
  healthEndpoints?: {
    liveness?: string
    readiness?: string
  }
  replicas?: {
    desired: number
    ready: number
    available: number
  }
  inputTopics?: string[]
  outputTopics?: string[]
}

interface PodInfo {
  name: string
  namespace: string
  labels: Record<string, string>
  status: string
  ready: boolean
  containers: Array<{
    name: string
    ready: boolean
    restartCount: number
  }>
  resources?: {
    cpu?: string
    memory?: string
  }
}

export class K8sDiscovery {
  private kc: k8s.KubeConfig
  private k8sApi: k8s.CoreV1Api
  private k8sAppsApi: k8s.AppsV1Api

  constructor() {
    this.kc = new k8s.KubeConfig()

    // Try in-cluster config first, fallback to default config
    try {
      this.kc.loadFromCluster()
    } catch (error) {
      try {
        this.kc.loadFromDefault()
      } catch (defaultError) {
        logger.warn('Could not load Kubernetes config, K8s discovery disabled', defaultError)
      }
    }

    this.k8sApi = this.kc.makeApiClient(k8s.CoreV1Api)
    this.k8sAppsApi = this.kc.makeApiClient(k8s.AppsV1Api)
  }

  async discoverServices(namespace = 'loom-dev'): Promise<ServiceInfo[]> {
    const services: ServiceInfo[] = []

    try {
      // Get all services in namespace
      const servicesResponse = await this.k8sApi.listNamespacedService(namespace)

      for (const service of servicesResponse.body.items) {
        const serviceInfo: ServiceInfo = {
          name: service.metadata?.name || '',
          namespace: service.metadata?.namespace || namespace,
          labels: service.metadata?.labels || {},
          annotations: service.metadata?.annotations || {},
          selector: service.spec?.selector || {},
          ports: (service.spec?.ports || []).map(port => ({
            name: port.name,
            port: port.port,
            targetPort: port.targetPort,
            protocol: port.protocol
          }))
        }

        // Extract Loom-specific annotations
        if (serviceInfo.annotations['loom.pipeline/input-topics']) {
          serviceInfo.inputTopics = serviceInfo.annotations['loom.pipeline/input-topics'].split(',')
        }
        if (serviceInfo.annotations['loom.pipeline/output-topics']) {
          serviceInfo.outputTopics = serviceInfo.annotations['loom.pipeline/output-topics'].split(',')
        }

        // Try to find associated deployment for health endpoints
        try {
          const deployment = await this.findDeploymentForService(serviceInfo.selector, namespace)
          if (deployment) {
            serviceInfo.healthEndpoints = this.extractHealthEndpoints(deployment)
            serviceInfo.replicas = {
              desired: deployment.spec?.replicas || 0,
              ready: deployment.status?.readyReplicas || 0,
              available: deployment.status?.availableReplicas || 0
            }
          }
        } catch (error) {
          logger.warn(`Failed to find deployment for service ${serviceInfo.name}`, error)
        }

        services.push(serviceInfo)
      }

      return services
    } catch (error) {
      logger.error('Failed to discover K8s services', error)
      return services
    }
  }

  async discoverPods(namespace = 'loom-dev', labelSelector?: string): Promise<PodInfo[]> {
    const pods: PodInfo[] = []

    try {
      const podsResponse = await this.k8sApi.listNamespacedPod(
        namespace,
        undefined,
        undefined,
        undefined,
        undefined,
        labelSelector
      )

      for (const pod of podsResponse.body.items) {
        const podInfo: PodInfo = {
          name: pod.metadata?.name || '',
          namespace: pod.metadata?.namespace || namespace,
          labels: pod.metadata?.labels || {},
          status: pod.status?.phase || 'Unknown',
          ready: this.isPodReady(pod),
          containers: (pod.status?.containerStatuses || []).map(cs => ({
            name: cs.name,
            ready: cs.ready,
            restartCount: cs.restartCount
          }))
        }

        // Extract resource usage if available
        if (pod.spec?.containers && pod.spec.containers.length > 0) {
          const container = pod.spec.containers[0]
          if (container.resources?.requests) {
            podInfo.resources = {
              cpu: container.resources.requests.cpu,
              memory: container.resources.requests.memory
            }
          }
        }

        pods.push(podInfo)
      }

      return pods
    } catch (error) {
      logger.error('Failed to discover K8s pods', error)
      return pods
    }
  }

  async getServiceEndpoint(serviceName: string, namespace = 'loom-dev', port?: number): Promise<string | null> {
    try {
      const service = await this.k8sApi.readNamespacedService(serviceName, namespace)

      // Build service URL
      const servicePort = port || service.body.spec?.ports?.[0]?.port
      if (!servicePort) {
        return null
      }

      // Use cluster-internal DNS name
      return `http://${serviceName}.${namespace}.svc.cluster.local:${servicePort}`
    } catch (error) {
      logger.error(`Failed to get endpoint for service ${serviceName}`, error)
      return null
    }
  }

  private async findDeploymentForService(selector: Record<string, string>, namespace: string): Promise<k8s.V1Deployment | null> {
    if (!selector || Object.keys(selector).length === 0) {
      return null
    }

    try {
      const deployments = await this.k8sAppsApi.listNamespacedDeployment(namespace)

      // Find deployment with matching selector
      for (const deployment of deployments.body.items) {
        const deploymentSelector = deployment.spec?.selector?.matchLabels || {}

        // Check if all selector labels match
        const matches = Object.entries(selector).every(
          ([key, value]) => deploymentSelector[key] === value
        )

        if (matches) {
          return deployment
        }
      }

      return null
    } catch (error) {
      logger.error('Failed to find deployment', error)
      return null
    }
  }

  private extractHealthEndpoints(deployment: k8s.V1Deployment): { liveness?: string; readiness?: string } {
    const endpoints: { liveness?: string; readiness?: string } = {}

    const containers = deployment.spec?.template?.spec?.containers || []
    if (containers.length === 0) {
      return endpoints
    }

    const container = containers[0] // Use first container

    // Extract liveness probe
    if (container.livenessProbe?.httpGet) {
      const probe = container.livenessProbe.httpGet
      endpoints.liveness = probe.path || '/healthz'
    }

    // Extract readiness probe
    if (container.readinessProbe?.httpGet) {
      const probe = container.readinessProbe.httpGet
      endpoints.readiness = probe.path || '/readyz'
    }

    return endpoints
  }

  private isPodReady(pod: k8s.V1Pod): boolean {
    const conditions = pod.status?.conditions || []
    const readyCondition = conditions.find(c => c.type === 'Ready')
    return readyCondition?.status === 'True'
  }

  async getServiceLabels(namespace = 'loom-dev'): Promise<Map<string, Set<string>>> {
    const labelMap = new Map<string, Set<string>>()

    try {
      const services = await this.discoverServices(namespace)

      for (const service of services) {
        for (const [key, value] of Object.entries(service.labels)) {
          if (!labelMap.has(key)) {
            labelMap.set(key, new Set())
          }
          labelMap.get(key)!.add(value)
        }
      }

      return labelMap
    } catch (error) {
      logger.error('Failed to get service labels', error)
      return labelMap
    }
  }
}
