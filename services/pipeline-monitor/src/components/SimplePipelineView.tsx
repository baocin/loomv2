import React from 'react'
import { useQuery } from '@tanstack/react-query'

const API_BASE = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8082'

interface ConsumerLag {
  service_name: string
  topic: string
  total_lag: string
  partition_count: number
  last_update: string
}

export const SimplePipelineView: React.FC = () => {
  // Fetch consumer lag
  const { data: consumerLag, error: lagError } = useQuery({
    queryKey: ['consumer-lag'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/api/consumers/lag`)
      if (!response.ok) throw new Error('Failed to fetch consumer lag')
      return response.json() as Promise<ConsumerLag[]>
    },
    refetchInterval: 5000 // Refresh every 5 seconds
  })

  if (lagError) {
    return <div className="p-4 text-red-600">Error loading consumer lag: {lagError.message}</div>
  }

  if (!consumerLag) {
    return <div className="p-4">Loading consumer lag data...</div>
  }

  // Group by service name
  const lagByService = consumerLag.reduce((acc, item) => {
    if (!acc[item.service_name]) {
      acc[item.service_name] = []
    }
    acc[item.service_name].push(item)
    return acc
  }, {} as Record<string, ConsumerLag[]>)

  return (
    <div className="p-4">
      <h2 className="text-2xl font-bold mb-4">Consumer Lag Status</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Object.entries(lagByService).map(([serviceName, topics]) => {
          const totalLag = topics.reduce((sum, t) => sum + parseInt(t.total_lag), 0)
          const hasLag = totalLag > 0

          return (
            <div
              key={serviceName}
              className={`border rounded-lg p-4 ${
                hasLag ? 'border-yellow-500 bg-yellow-50' : 'border-green-500 bg-green-50'
              }`}
            >
              <h3 className="font-semibold text-lg mb-2">{serviceName}</h3>
              <div className="space-y-2">
                {topics.map((topic) => (
                  <div key={`${serviceName}-${topic.topic}`} className="text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600 truncate mr-2" title={topic.topic}>
                        {topic.topic.split('.').slice(-2).join('.')}
                      </span>
                      <span className={`font-medium ${
                        parseInt(topic.total_lag) > 0 ? 'text-yellow-600' : 'text-green-600'
                      }`}>
                        Lag: {parseInt(topic.total_lag).toLocaleString()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-2 text-xs text-gray-500">
                Total Lag: {totalLag.toLocaleString()} messages
              </div>
              <div className="text-xs text-gray-400">
                Updated: {new Date(topics[0].last_update).toLocaleTimeString()}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
