import React, { useState } from 'react'
import { usePipelineDefinitions } from '../hooks/usePipelineDefinitions'

export const StructureViewEnhanced: React.FC = () => {
  const { data: definitions, isLoading, error } = usePipelineDefinitions()
  const [selectedFlow, setSelectedFlow] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center h-full">
        <div className="text-gray-500">Loading pipeline definitions...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="text-red-500">Error loading pipeline definitions</div>
      </div>
    )
  }

  const priorityColors = {
    critical: 'border-red-500 bg-red-50',
    high: 'border-orange-500 bg-orange-50',
    medium: 'border-green-500 bg-green-50',
    low: 'border-blue-500 bg-blue-50',
  }

  const priorityBadgeColors = {
    critical: 'bg-red-500 text-white',
    high: 'bg-orange-500 text-white',
    medium: 'bg-green-500 text-white',
    low: 'bg-blue-500 text-white',
  }

  const selectedFlowData = selectedFlow ? 
    definitions?.flows.find(f => f.name === selectedFlow) : null

  return (
    <div className="flex h-full">
      {/* Left Panel - Flow List/Grid */}
      <div className="w-1/2 p-4 border-r overflow-y-auto">
        <div className="mb-4">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">Data Processing Flows</h3>
            <div className="flex gap-2">
              <button
                onClick={() => setViewMode('grid')}
                className={`px-3 py-1 rounded ${viewMode === 'grid' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
              >
                Grid
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`px-3 py-1 rounded ${viewMode === 'list' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
              >
                List
              </button>
            </div>
          </div>

          {/* Summary Stats */}
          <div className="grid grid-cols-4 gap-2 mb-4">
            <div className="bg-gray-100 p-3 rounded text-center">
              <div className="text-2xl font-bold">{definitions?.summary.totalFlows || 0}</div>
              <div className="text-xs text-gray-600">Total Flows</div>
            </div>
            <div className="bg-red-100 p-3 rounded text-center">
              <div className="text-2xl font-bold text-red-600">
                {definitions?.summary.byPriority.critical || 0}
              </div>
              <div className="text-xs text-gray-600">Critical</div>
            </div>
            <div className="bg-orange-100 p-3 rounded text-center">
              <div className="text-2xl font-bold text-orange-600">
                {definitions?.summary.byPriority.high || 0}
              </div>
              <div className="text-xs text-gray-600">High</div>
            </div>
            <div className="bg-green-100 p-3 rounded text-center">
              <div className="text-2xl font-bold text-green-600">
                {definitions?.summary.byPriority.medium || 0}
              </div>
              <div className="text-xs text-gray-600">Medium</div>
            </div>
          </div>
        </div>

        {/* Flow Items */}
        <div className={viewMode === 'grid' ? 'grid grid-cols-2 gap-3' : 'space-y-2'}>
          {definitions?.flows
            .sort((a, b) => {
              const priorityOrder = ['critical', 'high', 'medium', 'low']
              return priorityOrder.indexOf(a.priority) - priorityOrder.indexOf(b.priority)
            })
            .map(flow => (
              <div
                key={flow.name}
                onClick={() => setSelectedFlow(flow.name)}
                className={`
                  border-2 rounded-lg p-4 cursor-pointer transition-all
                  ${priorityColors[flow.priority as keyof typeof priorityColors] || 'border-gray-300'}
                  ${selectedFlow === flow.name ? 'ring-2 ring-blue-500' : ''}
                  hover:shadow-md
                `}
              >
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-semibold text-sm">{flow.name.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}</h4>
                  <span className={`text-xs px-2 py-1 rounded ${priorityBadgeColors[flow.priority as keyof typeof priorityBadgeColors]}`}>
                    {flow.priority}
                  </span>
                </div>
                
                <div className="text-xs text-gray-600 space-y-1">
                  <div>Stages: {flow.stages?.length || 0}</div>
                  {flow.data_volume && (
                    <div>Rate: {flow.data_volume.expected_events_per_second} events/s</div>
                  )}
                </div>
              </div>
            ))}
        </div>
      </div>

      {/* Right Panel - Flow Details */}
      <div className="w-1/2 p-4 overflow-y-auto">
        {selectedFlowData ? (
          <div>
            <h3 className="text-lg font-semibold mb-4">
              {selectedFlowData.name.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
            </h3>
            
            <div className="space-y-4">
              {/* Description */}
              <div>
                <h4 className="font-semibold text-sm text-gray-700 mb-1">Description</h4>
                <p className="text-sm text-gray-600">{selectedFlowData.description}</p>
              </div>

              {/* Data Volume */}
              {selectedFlowData.data_volume && (
                <div>
                  <h4 className="font-semibold text-sm text-gray-700 mb-1">Data Volume</h4>
                  <div className="text-sm text-gray-600">
                    <div>Expected: {selectedFlowData.data_volume.expected_events_per_second} events/sec</div>
                    <div>Size: {selectedFlowData.data_volume.average_event_size_bytes} bytes/event</div>
                    <div>Peak Multiplier: {selectedFlowData.data_volume.peak_multiplier}x</div>
                  </div>
                </div>
              )}

              {/* Processing Stages */}
              <div>
                <h4 className="font-semibold text-sm text-gray-700 mb-2">Processing Stages</h4>
                <div className="space-y-3">
                  {selectedFlowData.stages?.map((stage: any, idx: number) => (
                    <div key={idx} className="border rounded-lg p-3 bg-gray-50">
                      <div className="flex justify-between items-start mb-2">
                        <h5 className="font-medium text-sm">{stage.name}</h5>
                        <span className="text-xs bg-gray-200 px-2 py-1 rounded">
                          {stage.service?.name || 'Unknown Service'}
                        </span>
                      </div>
                      
                      <div className="text-xs text-gray-600 space-y-1">
                        {/* Input/Output Topics */}
                        <div>
                          <span className="font-medium">Inputs:</span> {stage.input_topics?.join(', ') || 'None'}
                        </div>
                        <div>
                          <span className="font-medium">Outputs:</span> {stage.output_topics?.join(', ') || 'None'}
                        </div>
                        
                        {/* Processing Config */}
                        {stage.processing && (
                          <div>
                            <span className="font-medium">Batch Size:</span> {stage.processing.batch_size || 'N/A'}
                            {stage.processing.timeout_seconds && (
                              <span>, Timeout: {stage.processing.timeout_seconds}s</span>
                            )}
                          </div>
                        )}
                        
                        {/* Database Access */}
                        {stage.database_access && (
                          <div>
                            <span className="font-medium">DB Access:</span> {stage.database_access.tables?.join(', ') || 'None'}
                          </div>
                        )}
                        
                        {/* SLA */}
                        {stage.monitoring?.sla_seconds && (
                          <div>
                            <span className="font-medium">SLA:</span> {stage.monitoring.sla_seconds}s
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Models Used */}
              {(() => {
                const models = selectedFlowData.stages?.flatMap((s: any) => 
                  s.configuration?.models || []
                ).filter((m: string, i: number, a: string[]) => a.indexOf(m) === i)
                
                return models?.length > 0 ? (
                  <div>
                    <h4 className="font-semibold text-sm text-gray-700 mb-1">AI Models</h4>
                    <div className="flex flex-wrap gap-2">
                      {models.map((model: string) => (
                        <span key={model} className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">
                          {model}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null
              })()}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400">
            <div className="text-center">
              <svg className="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              <p>Select a flow to view details</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}