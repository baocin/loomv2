import { useQuery } from '@tanstack/react-query'

const API_BASE_URL = (import.meta as any).env.VITE_API_URL || 'http://localhost:8082'

export interface PipelineDefinitions {
  visualization: any
  flows: any[]
  summary: {
    totalFlows: number
    byPriority: {
      critical: number
      high: number
      medium: number
      low: number
    }
    totalStages: number
    models: string[]
  }
  timestamp: string
}

export function usePipelineDefinitions() {
  return useQuery<PipelineDefinitions>({
    queryKey: ['pipeline-definitions'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/pipeline-definitions`)
      if (!response.ok) {
        throw new Error('Failed to fetch pipeline definitions')
      }
      return response.json()
    },
    staleTime: 60000, // 1 minute
    refetchInterval: 300000, // 5 minutes
  })
}

export function usePipelineGraph() {
  return useQuery({
    queryKey: ['pipeline-graph'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/pipeline-definitions/graph`)
      if (!response.ok) {
        throw new Error('Failed to fetch pipeline graph')
      }
      return response.json()
    },
    staleTime: 60000,
    refetchInterval: 300000,
  })
}