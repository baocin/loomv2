import { useQuery } from '@tanstack/react-query'
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
        console.warn('Failed to fetch real pipeline data, using mock data:', error)
        return getMockPipelineData()
      }
    },
    refetchInterval: 5000,
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
        console.warn('Failed to fetch real metrics, using mock data:', error)
        return getMockTopicMetrics()
      }
    },
    refetchInterval: 3000,
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
        console.warn('Failed to fetch real consumer metrics, using mock data:', error)
        return getMockConsumerMetrics()
      }
    },
    refetchInterval: 3000,
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
        console.warn(`Failed to fetch latest message for ${topic}, using mock data:`, error)
        return getMockLatestMessage(topic)
      }
    },
    enabled: !!topic,
    refetchInterval: 5000,
  })
}

// Mock data functions
function getMockTopicMetrics(): KafkaTopicMetrics[] {
  const topics = [
    'device.audio.raw',
    'device.sensor.gps.raw',
    'device.sensor.accelerometer.raw',
    'device.health.heartrate.raw',
    'media.audio.vad_filtered',
    'media.text.transcribed.words',
    'media.image.analysis.minicpm_results',
    'analysis.inferred_context.mistral_results'
  ]

  return topics.map((topic) => ({
    topic,
    lastMessageTime: new Date(Date.now() - Math.random() * 300000), // Random within last 5 min
    lastProcessedTime: new Date(Date.now() - Math.random() * 600000), // Random within last 10 min
    messageCount: Math.floor(Math.random() * 10000) + 100,
    partitionCount: Math.floor(Math.random() * 3) + 1,
    consumerLag: Math.floor(Math.random() * 100),
    producerRate: Math.random() * 50 + 5,
    consumerRate: Math.random() * 45 + 3,
    isActive: Math.random() > 0.2, // 80% active
  }))
}

function getMockConsumerMetrics(): ConsumerMetrics[] {
  const consumers = [
    { groupId: 'vad-processor', topic: 'device.audio.raw' },
    { groupId: 'transcription-service', topic: 'media.audio.vad_filtered' },
    { groupId: 'vision-analyzer', topic: 'device.image.camera.raw' },
    { groupId: 'reasoning-service', topic: 'media.text.transcribed.words' },
  ]

  return consumers.map(({ groupId, topic }, index) => ({
    groupId,
    topic,
    partition: 0,
    currentOffset: Math.floor(Math.random() * 1000) + 500,
    logEndOffset: Math.floor(Math.random() * 1000) + 600,
    lag: Math.floor(Math.random() * 50),
    consumerId: `${groupId}-${Math.random().toString(36).substr(2, 9)}`,
    host: `pod-${index + 1}.loom-cluster.local`,
    lastHeartbeat: new Date(Date.now() - Math.random() * 30000), // Within last 30 sec
  }))
}

function getMockLatestMessage(topic: string): any {
  const sampleData = {
    'device.audio.raw': {
      device_id: 'macos-studio',
      timestamp: new Date().toISOString(),
      chunk_data: 'iVBORw0KGgoAAAANSUhEUgAA...', // Base64 audio
      sample_rate: 48000,
      channels: 1,
    },
    'device.sensor.gps.raw': {
      device_id: 'iphone-14',
      timestamp: new Date().toISOString(),
      latitude: 37.7749,
      longitude: -122.4194,
      accuracy: 5.2,
    },
    'media.text.transcribed.words': {
      text: 'Hello, this is a transcribed message from the audio pipeline.',
      confidence: 0.95,
      speaker_id: 'user_1',
      start_time: 0.5,
      end_time: 3.2,
    },
  }

  return sampleData[topic as keyof typeof sampleData] || {
    message: `Sample data for ${topic}`,
    timestamp: new Date().toISOString()
  }
}

function getMockPipelineData(): PipelineFlow {
  const nodes = [
    // External data sources
    {
      id: 'external-audio',
      type: 'external' as const,
      position: { x: 0, y: 100 },
      data: {
        status: 'active' as const,
        label: 'Audio Devices',
        description: 'Microphones, recordings'
      }
    },
    {
      id: 'external-sensors',
      type: 'external' as const,
      position: { x: 0, y: 200 },
      data: {
        status: 'active' as const,
        label: 'Device Sensors',
        description: 'GPS, accelerometer, etc.'
      }
    },
    {
      id: 'external-images',
      type: 'external' as const,
      position: { x: 0, y: 300 },
      data: {
        status: 'active' as const,
        label: 'Cameras',
        description: 'Screenshots, photos'
      }
    },

    // Raw data topics
    {
      id: 'device.audio.raw',
      type: 'kafka-topic' as const,
      position: { x: 300, y: 100 },
      data: { status: 'active' as const, label: 'Raw Audio' }
    },
    {
      id: 'device.sensor.gps.raw',
      type: 'kafka-topic' as const,
      position: { x: 300, y: 200 },
      data: { status: 'active' as const, label: 'Raw GPS' }
    },
    {
      id: 'device.image.camera.raw',
      type: 'kafka-topic' as const,
      position: { x: 300, y: 300 },
      data: { status: 'active' as const, label: 'Raw Images' }
    },

    // Processing services
    {
      id: 'vad-processor',
      type: 'processor' as const,
      position: { x: 600, y: 100 },
      data: {
        status: 'active' as const,
        label: 'VAD Processor',
        description: 'Voice Activity Detection'
      }
    },
    {
      id: 'vision-analyzer',
      type: 'processor' as const,
      position: { x: 600, y: 300 },
      data: {
        status: 'active' as const,
        label: 'Vision Analyzer',
        description: 'MiniCPM Vision Model'
      }
    },

    // Processed data topics
    {
      id: 'media.audio.vad_filtered',
      type: 'kafka-topic' as const,
      position: { x: 900, y: 100 },
      data: { status: 'active' as const, label: 'Filtered Audio' }
    },
    {
      id: 'media.image.analysis.minicpm_results',
      type: 'kafka-topic' as const,
      position: { x: 900, y: 300 },
      data: { status: 'active' as const, label: 'Image Analysis' }
    },

    // Transcription service
    {
      id: 'transcription-service',
      type: 'processor' as const,
      position: { x: 1200, y: 100 },
      data: {
        status: 'active' as const,
        label: 'Speech-to-Text',
        description: 'Parakeet-TDT ASR'
      }
    },

    // Final processed topics
    {
      id: 'media.text.transcribed.words',
      type: 'kafka-topic' as const,
      position: { x: 1500, y: 100 },
      data: { status: 'active' as const, label: 'Transcribed Text' }
    },

    // Reasoning service
    {
      id: 'reasoning-service',
      type: 'processor' as const,
      position: { x: 1800, y: 200 },
      data: {
        status: 'active' as const,
        label: 'Reasoning Engine',
        description: 'Mistral Context Analysis'
      }
    },

    // Final output
    {
      id: 'analysis.inferred_context.mistral_results',
      type: 'kafka-topic' as const,
      position: { x: 2100, y: 200 },
      data: { status: 'active' as const, label: 'Context Results' }
    },

    // Database
    {
      id: 'timescaledb',
      type: 'database' as const,
      position: { x: 2400, y: 200 },
      data: {
        status: 'active' as const,
        label: 'TimescaleDB',
        description: 'Time-series storage'
      }
    },
  ]

  const edges = [
    // External to raw topics
    { id: 'e1', source: 'external-audio', target: 'device.audio.raw', animated: true },
    { id: 'e2', source: 'external-sensors', target: 'device.sensor.gps.raw', animated: true },
    { id: 'e3', source: 'external-images', target: 'device.image.camera.raw', animated: true },

    // Raw topics to processors
    { id: 'e4', source: 'device.audio.raw', target: 'vad-processor', animated: true },
    { id: 'e5', source: 'device.image.camera.raw', target: 'vision-analyzer', animated: true },

    // Processors to processed topics
    { id: 'e6', source: 'vad-processor', target: 'media.audio.vad_filtered', animated: true },
    { id: 'e7', source: 'vision-analyzer', target: 'media.image.analysis.minicpm_results', animated: true },

    // Filtered audio to transcription
    { id: 'e8', source: 'media.audio.vad_filtered', target: 'transcription-service', animated: true },
    { id: 'e9', source: 'transcription-service', target: 'media.text.transcribed.words', animated: true },

    // Multiple inputs to reasoning
    { id: 'e10', source: 'media.text.transcribed.words', target: 'reasoning-service', animated: true },
    { id: 'e11', source: 'media.image.analysis.minicpm_results', target: 'reasoning-service', animated: true },

    // Reasoning to final output
    { id: 'e12', source: 'reasoning-service', target: 'analysis.inferred_context.mistral_results', animated: true },

    // Final output to database
    { id: 'e13', source: 'analysis.inferred_context.mistral_results', target: 'timescaledb', animated: true },
    { id: 'e14', source: 'device.sensor.gps.raw', target: 'timescaledb', animated: true },
  ]

  return { nodes, edges }
}
