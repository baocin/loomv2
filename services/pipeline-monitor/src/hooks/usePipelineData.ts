import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import type { PipelineFlow, KafkaTopicMetrics, ConsumerMetrics } from '../types'

const API_BASE_URL = (import.meta as any).env.VITE_API_URL || 'http://localhost:8082'

export const usePipelineData = () => {
  return useQuery({
    queryKey: ['pipelineData'],
    queryFn: async (): Promise<PipelineFlow> => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/kafka/pipeline`)
        if (!response.ok) throw new Error('Failed to fetch pipeline data')
        return response.json()
      } catch (error) {
        console.error('Failed to fetch pipeline data:', error)
        throw error
      }
    },
    refetchInterval: 5000, // Reduced from 2s to 5s
    staleTime: 4000, // Consider data fresh for 4s
  })
}

export const useTopicMetrics = () => {
  return useQuery({
    queryKey: ['topicMetrics'],
    queryFn: async (): Promise<KafkaTopicMetrics[]> => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/kafka/topics/metrics`)
        if (!response.ok) throw new Error('Failed to fetch topic metrics')
        return response.json()
      } catch (error) {
        console.error('Failed to fetch topic metrics:', error)
        throw error
      }
    },
    refetchInterval: 10000, // Reduced from 2s to 10s - metrics don't change that fast
    staleTime: 8000, // Consider data fresh for 8s
  })
}

export const useConsumerMetrics = () => {
  return useQuery({
    queryKey: ['consumerMetrics'],
    queryFn: async (): Promise<ConsumerMetrics[]> => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/kafka/consumers/metrics`)
        if (!response.ok) throw new Error('Failed to fetch consumer metrics')
        return response.json()
      } catch (error) {
        console.error('Failed to fetch consumer metrics:', error)
        throw error
      }
    },
    refetchInterval: 10000, // Reduced from 2s to 10s
    staleTime: 8000, // Consider data fresh for 8s
  })
}

export const useLatestMessage = (topic: string) => {
  return useQuery({
    queryKey: ['latestMessage', topic],
    queryFn: async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/kafka/topics/${topic}/latest`)
        if (!response.ok) throw new Error('Failed to fetch latest message')
        return response.json()
      } catch (error) {
        console.error(`Failed to fetch latest message for ${topic}:`, error)
        return null
      }
    },
    enabled: !!topic,
    refetchInterval: 5000, // Reduced from 2s to 5s
    staleTime: 4000, // Consider data fresh for 4s
  })
}

export const useClearCache = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/kafka/cache/clear`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      if (!response.ok) {
        throw new Error('Failed to clear cache')
      }
      return response.json()
    },
    onSuccess: () => {
      // Invalidate all queries to force refetch
      queryClient.invalidateQueries({ queryKey: ['pipelineData'] })
      queryClient.invalidateQueries({ queryKey: ['topicMetrics'] })
      queryClient.invalidateQueries({ queryKey: ['consumerMetrics'] })
      queryClient.invalidateQueries({ queryKey: ['latestMessage'] })
    },
  })
}

export const useClearAllTopics = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/kafka/topics/clear-all`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to clear all topics')
      }
      return response.json()
    },
    onSuccess: () => {
      // Invalidate all queries to force refetch after clearing topics
      queryClient.invalidateQueries({ queryKey: ['pipelineData'] })
      queryClient.invalidateQueries({ queryKey: ['topicMetrics'] })
      queryClient.invalidateQueries({ queryKey: ['consumerMetrics'] })
      queryClient.invalidateQueries({ queryKey: ['latestMessage'] })
    },
  })
}

export const useAutoDiscovery = () => {
  return useQuery({
    queryKey: ['autoDiscovery'],
    queryFn: async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/kafka/discover/all`)
        if (!response.ok) throw new Error('Failed to fetch auto-discovery data')
        return response.json()
      } catch (error) {
        console.error('Failed to fetch auto-discovery data:', error)
        throw error
      }
    },
    refetchInterval: 30000, // Reduced from 5s to 30s - discovery data rarely changes
    staleTime: 25000, // Consider data fresh for 25s
  })
}

export const useServiceHealth = () => {
  return useQuery({
    queryKey: ['serviceHealth'],
    queryFn: async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/kafka/services/health`)
        if (!response.ok) throw new Error('Failed to fetch service health')
        return response.json()
      } catch (error) {
        console.error('Failed to fetch service health:', error)
        throw error
      }
    },
    refetchInterval: 20000, // Increased from 10s to 20s
    staleTime: 15000, // Consider data fresh for 15s
  })
}

export const useServiceRegistry = () => {
  return useQuery({
    queryKey: ['serviceRegistry'],
    queryFn: async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/kafka/services/registry`)
        if (!response.ok) throw new Error('Failed to fetch service registry')
        return response.json()
      } catch (error) {
        console.error('Failed to fetch service registry:', error)
        throw error
      }
    },
    refetchInterval: 60000, // Increased from 30s to 60s - registry rarely changes
    staleTime: 50000, // Consider data fresh for 50s
  })
}

export const usePipelineStructure = () => {
  return useQuery({
    queryKey: ['pipelineStructure'],
    queryFn: async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/kafka/structure`)
        if (!response.ok) throw new Error('Failed to fetch pipeline structure')
        return response.json()
      } catch (error) {
        console.error('Failed to fetch pipeline structure:', error)
        throw error
      }
    },
    refetchInterval: 30000, // Reduced from 5s to 30s - structure rarely changes
    staleTime: 25000, // Consider data fresh for 25s
  })
}
