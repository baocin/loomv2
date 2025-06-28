import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

const TEST_PRODUCER_URL = (import.meta as any).env.VITE_TEST_PRODUCER_URL || 'http://localhost:8008'

interface TestMessageRequest {
  topic: string
  count?: number
  message?: any
  key?: string
}

interface TestMessageResponse {
  success: boolean
  topic: string
  count: number
  timestamp: string
  details?: string
}

interface TopicExample {
  topic: string
  example_payload: any
  payload_size_bytes: number
}

interface TopicsResponse {
  total_topics: number
  categories: Record<string, string[]>
  all_topics: string[]
}

export const useAvailableTopics = () => {
  return useQuery({
    queryKey: ['testProducer', 'topics'],
    queryFn: async (): Promise<TopicsResponse> => {
      const response = await fetch(`${TEST_PRODUCER_URL}/topics`)
      if (!response.ok) throw new Error('Failed to fetch available topics')
      return response.json()
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export const useTopicExample = (topic: string) => {
  return useQuery({
    queryKey: ['testProducer', 'example', topic],
    queryFn: async (): Promise<TopicExample | null> => {
      if (!topic) return null
      const response = await fetch(`${TEST_PRODUCER_URL}/topics/${encodeURIComponent(topic)}`)
      if (!response.ok) throw new Error(`Failed to fetch example for topic ${topic}`)
      return response.json()
    },
    enabled: !!topic,
    staleTime: 10 * 60 * 1000, // 10 minutes
  })
}

export const useSendTestMessage = () => {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (request: TestMessageRequest): Promise<TestMessageResponse> => {
      const response = await fetch(`${TEST_PRODUCER_URL}/send`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to send test message')
      }
      
      return response.json()
    },
    onSuccess: (data) => {
      // Invalidate topic metrics to show new messages
      queryClient.invalidateQueries({ queryKey: ['topicMetrics'] })
      queryClient.invalidateQueries({ queryKey: ['latestMessage', data.topic] })
      queryClient.invalidateQueries({ queryKey: ['pipelineData'] })
    },
  })
}

export const useSendBulkTestMessages = () => {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async ({ topics, countPerTopic = 1 }: { topics: string[]; countPerTopic?: number }) => {
      const response = await fetch(`${TEST_PRODUCER_URL}/send/bulk`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          topics,
          count_per_topic: countPerTopic,
        }),
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to send bulk test messages')
      }
      
      return response.json()
    },
    onSuccess: () => {
      // Invalidate all metrics to show new messages
      queryClient.invalidateQueries({ queryKey: ['topicMetrics'] })
      queryClient.invalidateQueries({ queryKey: ['latestMessage'] })
      queryClient.invalidateQueries({ queryKey: ['pipelineData'] })
    },
  })
}

export const useTestProducerHealth = () => {
  return useQuery({
    queryKey: ['testProducer', 'health'],
    queryFn: async () => {
      try {
        const response = await fetch(`${TEST_PRODUCER_URL}/health`)
        if (!response.ok) throw new Error('Test producer not responding')
        return response.json()
      } catch (error) {
        throw new Error('Test producer unavailable')
      }
    },
    refetchInterval: 30000, // 30 seconds
    retry: 1,
  })
}