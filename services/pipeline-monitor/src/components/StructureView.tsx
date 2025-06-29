import React from 'react'
import { usePipelineStructure } from '../hooks/usePipelineData'

export const StructureView: React.FC = () => {
  const { data: structure, isLoading, error } = usePipelineStructure()

  if (isLoading) {
    return (
      <div className="p-4">
        <div className="animate-pulse">Loading pipeline structure...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 text-red-600">
        Error loading structure: {error.message}
      </div>
    )
  }

  if (!structure) {
    return (
      <div className="p-4 text-gray-500">
        No structure data available
      </div>
    )
  }

  return (
    <div className="p-4 max-h-[80vh] overflow-y-auto">
      <h2 className="text-2xl font-bold mb-4">Pipeline Structure</h2>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-blue-50 p-3 rounded-lg">
          <div className="text-sm text-gray-600">Total Topics</div>
          <div className="text-2xl font-bold text-blue-600">{structure.stats?.totalTopics || 0}</div>
        </div>
        <div className="bg-green-50 p-3 rounded-lg">
          <div className="text-sm text-gray-600">Consumers</div>
          <div className="text-2xl font-bold text-green-600">{structure.stats?.totalConsumers || 0}</div>
        </div>
        <div className="bg-purple-50 p-3 rounded-lg">
          <div className="text-sm text-gray-600">Producers</div>
          <div className="text-2xl font-bold text-purple-600">{structure.stats?.totalProducers || 0}</div>
        </div>
        <div className="bg-yellow-50 p-3 rounded-lg">
          <div className="text-sm text-gray-600">Active Flows</div>
          <div className="text-2xl font-bold text-yellow-600">{structure.stats?.activeFlows || 0}</div>
        </div>
      </div>

      {/* Topic Categories */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-3">Topic Categories</h3>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
          {Object.entries(structure.categories || {}).map(([category, count]) => (
            <div key={category} className="bg-gray-100 p-2 rounded text-center">
              <div className="text-xs text-gray-600">{category}</div>
              <div className="font-bold">{count}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Producers */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-3">Producers</h3>
        <div className="space-y-2">
          {structure.producers?.map((producer: any) => (
            <div key={producer.id} className="bg-white border rounded-lg p-3">
              <div className="flex justify-between items-start">
                <div>
                  <div className="font-medium">{producer.label}</div>
                  <div className="text-sm text-gray-600">{producer.description}</div>
                </div>
                <div className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                  {producer.type}
                </div>
              </div>
              {producer.outputTopics && producer.outputTopics.length > 0 && (
                <div className="mt-2 text-xs text-gray-600">
                  Produces: {producer.outputTopics.length} topic{producer.outputTopics.length > 1 ? 's' : ''}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Consumers */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-3">Consumers</h3>
        <div className="space-y-2">
          {structure.consumers?.map((consumer: any) => (
            <div key={consumer.groupId} className="bg-white border rounded-lg p-3">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="font-medium">{consumer.label}</div>
                  <div className="text-sm text-gray-600">{consumer.description}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    Group ID: {consumer.groupId}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <div className={`text-xs px-2 py-1 rounded ${
                    consumer.status === 'Stable' ? 'bg-green-100 text-green-700' :
                    consumer.status === 'Unknown' ? 'bg-gray-100 text-gray-700' :
                    'bg-yellow-100 text-yellow-700'
                  }`}>
                    {consumer.status}
                  </div>
                  {consumer.memberCount > 0 && (
                    <div className="text-xs text-gray-500">
                      {consumer.memberCount} member{consumer.memberCount > 1 ? 's' : ''}
                    </div>
                  )}
                </div>
              </div>

              <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-gray-600">Subscribes to:</span>
                  <div className="text-gray-800">{consumer.subscribedTopics?.length || 0} topics</div>
                </div>
                <div>
                  <span className="text-gray-600">Produces:</span>
                  <div className="text-gray-800">{consumer.producesTopics?.length || 0} topics</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Topics by Stage */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-3">Topics</h3>
        <div className="space-y-4">
          {['raw', 'processed', 'analysis', 'unknown'].map(stage => {
            const topicsInStage = structure.topics?.filter((t: any) => t.stage === stage) || []
            if (topicsInStage.length === 0) return null

            return (
              <div key={stage}>
                <h4 className="text-sm font-medium text-gray-700 mb-2 capitalize">{stage} Topics ({topicsInStage.length})</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {topicsInStage.map((topic: any) => (
                    <div key={topic.name} className="bg-gray-50 p-2 rounded text-sm">
                      <div className="font-medium text-gray-800">{topic.name}</div>
                      <div className="text-xs text-gray-600">{topic.description}</div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Active Flows */}
      {structure.flows && structure.flows.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-3">Active Data Flows</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2">Source Topic</th>
                  <th className="text-left py-2">Processor</th>
                  <th className="text-left py-2">Destination Topic</th>
                  <th className="text-center py-2">Health</th>
                  <th className="text-right py-2">Lag</th>
                </tr>
              </thead>
              <tbody>
                {structure.flows.map((flow: any, idx: number) => (
                  <tr key={idx} className="border-b hover:bg-gray-50">
                    <td className="py-2 text-xs">{flow.source}</td>
                    <td className="py-2 text-xs font-medium">{flow.processor}</td>
                    <td className="py-2 text-xs">{flow.destination}</td>
                    <td className="py-2 text-center">
                      <span className={`inline-block w-2 h-2 rounded-full ${
                        flow.health === 'healthy' ? 'bg-green-500' :
                        flow.health === 'warning' ? 'bg-yellow-500' :
                        flow.health === 'error' ? 'bg-red-500' :
                        'bg-gray-400'
                      }`} />
                    </td>
                    <td className="py-2 text-right text-xs">
                      {flow.lag !== undefined ? flow.lag.toLocaleString() : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
