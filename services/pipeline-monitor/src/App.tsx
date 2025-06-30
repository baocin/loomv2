import React, { useState, useCallback, useRef, useEffect } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Node,
  NodeChange,
  ReactFlowProvider,
} from 'reactflow'
import 'reactflow/dist/style.css'
import './App.css'
import { toPng } from 'html-to-image'

import { nodeTypes } from './components/NodeTypes'
import { DataModal } from './components/DataModal'
import { LogViewer } from './components/LogViewer'
import { TestMessagePanel } from './components/TestMessagePanel'
import { StructureViewEnhanced } from './components/StructureViewEnhanced'
import { useTopicMetrics, useConsumerMetrics, useLatestMessage, useClearCache, useClearAllTopics, useAutoDiscovery, useServiceHealth } from './hooks/usePipelineData'
import { usePipelineDefinitions } from './hooks/usePipelineDefinitions'
import { usePipelineGraph } from './hooks/usePipelineGraph'

const STORAGE_KEY = 'loom-pipeline-node-positions'

// Position persistence utilities
const updateNodePosition = (nodeId: string, position: { x: number; y: number }) => {
  try {
    // Get existing positions
    const stored = localStorage.getItem(STORAGE_KEY)
    const existingPositions = stored ? JSON.parse(stored) : {}

    // Update just this node's position
    existingPositions[nodeId] = position

    console.log(`Updating position for ${nodeId}:`, position)
    console.log('All positions after update:', existingPositions)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(existingPositions))
  } catch (error) {
    console.warn('Failed to update node position:', error)
  }
}

const loadNodePositions = (): Record<string, { x: number; y: number }> => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) {
      console.log('No stored positions found in localStorage')
      return {}
    }

    const positions = JSON.parse(stored)
    console.log('Loaded positions from localStorage:', positions)

    // Validate that positions are valid objects with x,y numbers
    const validPositions: Record<string, { x: number; y: number }> = {}
    for (const [nodeId, pos] of Object.entries(positions)) {
      if (pos && typeof pos === 'object' &&
          typeof (pos as any).x === 'number' &&
          typeof (pos as any).y === 'number') {
        validPositions[nodeId] = pos as { x: number; y: number }
      }
    }

    return validPositions
  } catch (error) {
    console.warn('Failed to load node positions from localStorage:', error)
    return {}
  }
}

const clearNodePositions = () => {
  try {
    localStorage.removeItem(STORAGE_KEY)
    console.log('Cleared all stored node positions')
  } catch (error) {
    console.warn('Failed to clear node positions:', error)
  }
}

const exportPositions = () => {
  try {
    const positions = loadNodePositions()
    const dataStr = JSON.stringify(positions, null, 2)
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr)
    
    const exportFileDefaultName = `loom-pipeline-positions-${new Date().toISOString().split('T')[0]}.json`
    
    const linkElement = document.createElement('a')
    linkElement.setAttribute('href', dataUri)
    linkElement.setAttribute('download', exportFileDefaultName)
    linkElement.click()
  } catch (error) {
    console.error('Failed to export positions:', error)
  }
}

const importPositions = (file: File) => {
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const positions = JSON.parse(e.target?.result as string)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(positions))
      window.location.reload() // Reload to apply imported positions
    } catch (error) {
      console.error('Failed to import positions:', error)
      alert('Failed to import positions. Please check the file format.')
    }
  }
  reader.readAsText(file)
}

function PipelineMonitor() {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [modalData, setModalData] = useState<{ isOpen: boolean; title: string; data: any }>({
    isOpen: false,
    title: '',
    data: null,
  })
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null)
  const [logViewerTopic, setLogViewerTopic] = useState<string | null>(null)
  const [showTestPanel, setShowTestPanel] = useState(false)
  const [testPanelTopic, setTestPanelTopic] = useState<string>('')
  const [showStructureView, setShowStructureView] = useState(false)
  const [useManualPositions, setUseManualPositions] = useState(true)
  const [pulsingTopics, setPulsingTopics] = useState<Set<string>>(new Set())
  const [lastMessageCounts, setLastMessageCounts] = useState<Map<string, number>>(new Map())
  
  const reactFlowWrapper = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data: pipelineGraph, isLoading: isPipelineLoading } = usePipelineGraph()
  const { data: topicMetrics, isLoading: isTopicMetricsLoading } = useTopicMetrics()
  const { data: consumerMetrics, isLoading: isConsumerMetricsLoading } = useConsumerMetrics()
  const { data: latestMessage } = useLatestMessage(selectedTopic || '')
  const clearCacheMutation = useClearCache()
  const clearAllTopicsMutation = useClearAllTopics()
  const { data: autoDiscoveryData } = useAutoDiscovery()
  const { data: serviceHealthData } = useServiceHealth()
  const { data: pipelineDefinitions } = usePipelineDefinitions()
  
  // Screenshot function
  const takeScreenshot = useCallback(() => {
    if (reactFlowWrapper.current === null) {
      return
    }

    toPng(reactFlowWrapper.current, {
      cacheBust: true,
      backgroundColor: '#ffffff',
      width: reactFlowWrapper.current.scrollWidth,
      height: reactFlowWrapper.current.scrollHeight,
      style: {
        width: reactFlowWrapper.current.scrollWidth + 'px',
        height: reactFlowWrapper.current.scrollHeight + 'px',
      }
    })
      .then((dataUrl) => {
        const link = document.createElement('a')
        link.download = `loom-pipeline-${new Date().toISOString().split('T')[0]}.png`
        link.href = dataUrl
        link.click()
      })
      .catch((err) => {
        console.error('Failed to take screenshot:', err)
      })
  }, [])

  // Custom nodes change handler (keep basic functionality)
  const handleNodesChange = useCallback((changes: NodeChange[]) => {
    onNodesChange(changes)

    // Debug: Log all changes for debugging
    const positionChanges = changes.filter(change => change.type === 'position')
    if (positionChanges.length > 0) {
      console.log('Position changes detected:', positionChanges)
    }
  }, [onNodesChange])

  // Handle drag stop event to save positions
  const handleNodeDragStop = useCallback((_event: React.MouseEvent, node: Node, _nodes: Node[]) => {
    if (useManualPositions) {
      console.log('Node drag stopped, saving position for:', node.id, node.position)

      // Save only this node's position (preserving others)
      setTimeout(() => {
        updateNodePosition(node.id, node.position)
      }, 50)
    } else {
      console.log('Node drag stopped, but in algorithm mode - not saving position')
    }
  }, [useManualPositions])

  // Track message count changes for pulse effect
  useEffect(() => {
    if (!topicMetrics) return

    const newPulsing = new Set<string>()
    const newCounts = new Map<string, number>()

    topicMetrics.forEach(metric => {
      const prevCount = lastMessageCounts.get(metric.topic) || 0
      const currentCount = metric.messageCount || 0
      newCounts.set(metric.topic, currentCount)

      // If message count increased, add to pulsing set
      if (currentCount > prevCount && prevCount > 0) {
        newPulsing.add(metric.topic)
        
        // Remove pulse after 2 seconds
        setTimeout(() => {
          setPulsingTopics(prev => {
            const next = new Set(prev)
            next.delete(metric.topic)
            return next
          })
        }, 2000)
      }
    })

    setLastMessageCounts(newCounts)
    setPulsingTopics(prev => new Set([...prev, ...newPulsing]))
  }, [topicMetrics])

  // Update nodes with real metrics data and restore positions
  React.useEffect(() => {
    if (!pipelineGraph || isTopicMetricsLoading || isConsumerMetricsLoading) return

    const savedPositions = useManualPositions ? loadNodePositions() : {}

    const updatedNodes = pipelineGraph.nodes.map(node => {
      let updatedData = { ...node.data }

      // Add topic metrics
      if (node.type === 'kafka-topic') {
        const metrics = topicMetrics?.find(m => m.topic === node.id)
        if (metrics) {
          updatedData.metrics = metrics
          updatedData.status = metrics.isActive ? 'active' : 'idle'
          // Add pulsing class if topic is pulsing
          ;(updatedData as any).isPulsing = pulsingTopics.has(node.id)
        }
      }

      // Add consumer metrics
      if (node.type === 'processor') {
        const metrics = consumerMetrics?.find(m =>
          m.groupId.includes(node.id.replace('-', '')) ||
          node.data.label.toLowerCase().includes(m.groupId.split('-')[0])
        )
        if (metrics) {
          updatedData.metrics = metrics
          updatedData.status = new Date().getTime() - new Date(metrics.lastHeartbeat).getTime() < 30000 ? 'active' : 'idle'
        }

        // Add health status from auto-discovery
        if (serviceHealthData?.services) {
          const health = serviceHealthData.services.find((s: any) =>
            s.serviceId.includes(node.id) ||
            s.serviceName.toLowerCase().includes(node.data.label.toLowerCase())
          )
          if (health) {
            updatedData = {
              ...updatedData,
              health,
              status: health.status === 'healthy' ? 'active' :
                     health.status === 'degraded' ? 'idle' : 'error'
            }
          }
        }
      }

      // Use saved position if manual mode and available, otherwise use algorithm position
      const savedPosition = savedPositions[node.id]
      const position = savedPosition && useManualPositions ? savedPosition : node.position

      // Debug: Log position restoration
      if (savedPosition && useManualPositions) {
        console.log(`Restored manual position for ${node.id}:`, savedPosition)
      }

      return {
        ...node,
        data: updatedData,
        position,
      }
    })

    setNodes(updatedNodes)
    setEdges(pipelineGraph.edges)
  }, [pipelineGraph, topicMetrics, consumerMetrics, setNodes, setEdges, useManualPositions, pulsingTopics, serviceHealthData])

  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    if (node.type === 'kafka-topic') {
      setSelectedTopic(node.id)
      setTestPanelTopic(node.id) // Auto-select in test panel
      setModalData({
        isOpen: true,
        title: node.id,
        data: node.data.metrics || { message: 'No metrics available' },
      })
    } else if (node.type === 'processor') {
      setModalData({
        isOpen: true,
        title: node.data.label,
        data: node.data.metrics || { message: 'No consumer metrics available' },
      })
    }
  }, [])

  const handleViewLogs = useCallback(() => {
    if (selectedTopic) {
      setModalData({ isOpen: false, title: '', data: null })
      setLogViewerTopic(selectedTopic)
    }
  }, [selectedTopic])

  const closeModal = useCallback(() => {
    setModalData({ isOpen: false, title: '', data: null })
    setSelectedTopic(null)
  }, [])

  const handleClearCache = useCallback(() => {
    if (window.confirm('Are you sure you want to clear all cached data? This will reset all metrics and force a refresh.')) {
      clearCacheMutation.mutate()
    }
  }, [clearCacheMutation])

  const handleClearAllTopics = useCallback(() => {
    // First confirmation
    const firstConfirm = window.confirm(
      '⚠️ DANGER: This will permanently delete ALL messages from ALL Kafka topics!\n\n' +
      'This action cannot be undone. Are you absolutely sure?'
    )

    if (!firstConfirm) return

    // Second confirmation with typing requirement
    const confirmText = window.prompt(
      '🚨 FINAL WARNING: Type "DELETE ALL MESSAGES" to confirm this destructive operation:\n\n' +
      'This will clear all data from every Kafka topic in your cluster.'
    )

    if (confirmText !== 'DELETE ALL MESSAGES') {
      alert('Operation cancelled. Confirmation text did not match.')
      return
    }

    // Third confirmation with topic count
    const topicCount = topicMetrics?.length || 0
    const finalConfirm = window.confirm(
      `🔥 FINAL CONFIRMATION:\n\n` +
      `You are about to delete ALL messages from ${topicCount} topics.\n` +
      `This will permanently destroy all your Kafka data.\n\n` +
      `Click OK to proceed with this irreversible action.`
    )

    if (finalConfirm) {
      clearAllTopicsMutation.mutate()
    }
  }, [clearAllTopicsMutation, topicMetrics])

  // Show latest message in modal when available
  React.useEffect(() => {
    if (latestMessage && modalData.isOpen && selectedTopic) {
      setModalData(prev => ({
        ...prev,
        data: {
          ...prev.data,
          latestMessage,
        }
      }))
    }
  }, [latestMessage, modalData.isOpen, selectedTopic])

  if (isPipelineLoading) {
    return (
      <div className="w-screen h-screen flex items-center justify-center">
        <div className="text-xl">Loading pipeline data...</div>
      </div>
    )
  }

  return (
    <div className="w-screen h-screen">
      <div className="absolute top-4 left-4 z-10 bg-white p-4 rounded-lg shadow-lg">
        <h1 className="text-xl font-bold mb-2">Loom Pipeline Monitor</h1>
        <div className="text-sm text-gray-600 space-y-1">
          <div>Topics: {topicMetrics?.length || 0}</div>
          <div>Active Consumers: {consumerMetrics?.filter(c =>
            new Date().getTime() - new Date(c.lastHeartbeat).getTime() < 30000
          ).length || 0}</div>
          
          {/* Pipeline Definitions Summary */}
          {pipelineDefinitions && (
            <div className="mt-2 pt-2 border-t border-gray-200">
              <div className="font-semibold mb-1">Pipeline Flows</div>
              <div className="text-xs space-y-1">
                <div>Total: {pipelineDefinitions.summary.totalFlows}</div>
                <div className="grid grid-cols-2 gap-1 mt-1">
                  <span className="text-red-600">Critical: {pipelineDefinitions.summary.byPriority.critical}</span>
                  <span className="text-orange-600">High: {pipelineDefinitions.summary.byPriority.high}</span>
                  <span className="text-green-600">Medium: {pipelineDefinitions.summary.byPriority.medium}</span>
                  <span className="text-blue-600">Low: {pipelineDefinitions.summary.byPriority.low}</span>
                </div>
              </div>
            </div>
          )}

          {/* Service Health Summary */}
          {serviceHealthData && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <div className="font-semibold mb-1">Service Health</div>
              <div className="text-xs space-y-1">
                <div>Total Services: {serviceHealthData.pipeline?.totalServices || 0}</div>
                <div className="flex items-center gap-2">
                  <span className="text-green-600">Healthy: {serviceHealthData.pipeline?.healthy || 0}</span>
                  <span className="text-red-600">Unhealthy: {serviceHealthData.pipeline?.unhealthy || 0}</span>
                </div>
                {serviceHealthData.pipeline?.overallHealth && (
                  <div className={`font-semibold ${
                    serviceHealthData.pipeline.overallHealth === 'healthy' ? 'text-green-600' :
                    serviceHealthData.pipeline.overallHealth === 'degraded' ? 'text-yellow-600' : 'text-red-600'
                  }`}>
                    Pipeline: {serviceHealthData.pipeline.overallHealth.toUpperCase()}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Auto-Discovery Summary */}
          {autoDiscoveryData && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <div className="font-semibold mb-1">Auto-Discovery</div>
              <div className="text-xs space-y-1">
                <div>Discovered Flows: {autoDiscoveryData.flows?.length || 0}</div>
                <div>K8s Services: {autoDiscoveryData.services?.kubernetes?.length || 0}</div>
              </div>
            </div>
          )}

          <div className="flex items-center gap-2 mt-2">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              <span>Active</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
              <span>Idle</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-red-500 rounded-full"></div>
              <span>Error</span>
            </div>
          </div>
          <div className="text-xs text-gray-500 mt-2">
            Click on nodes to view raw data
          </div>
          <button
            onClick={() => {
              setUseManualPositions(!useManualPositions)
              if (useManualPositions) {
                // Switching to algorithm layout
                clearNodePositions()
              }
            }}
            className="mt-3 w-full bg-purple-500 hover:bg-purple-600 text-white text-sm py-2 px-3 rounded-md transition-colors duration-200 flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
            </svg>
            {useManualPositions ? 'Use Algorithm Layout' : 'Use Manual Layout'}
          </button>
          <div className="text-xs text-gray-500 mt-1 text-center">
            {useManualPositions ? 'Drag nodes to reposition' : 'Auto-aligned by data flow'}
          </div>
          
          {/* Screenshot and Export/Import buttons */}
          <div className="mt-3 grid grid-cols-2 gap-2">
            <button
              onClick={takeScreenshot}
              className="bg-indigo-500 hover:bg-indigo-600 text-white text-sm py-2 px-3 rounded-md transition-colors duration-200 flex items-center justify-center gap-1"
              title="Take Screenshot"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              Screenshot
            </button>
            <button
              onClick={exportPositions}
              disabled={!useManualPositions}
              className="bg-green-500 hover:bg-green-600 disabled:bg-green-300 text-white text-sm py-2 px-3 rounded-md transition-colors duration-200 flex items-center justify-center gap-1"
              title="Export Positions"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Export
            </button>
          </div>
          
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={!useManualPositions}
            className="mt-2 w-full bg-gray-500 hover:bg-gray-600 disabled:bg-gray-300 text-white text-sm py-2 px-3 rounded-md transition-colors duration-200 flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            Import Positions
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            style={{ display: 'none' }}
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) {
                importPositions(file)
              }
            }}
          />
          
          <button
            onClick={() => setShowStructureView(!showStructureView)}
            className="mt-3 w-full bg-blue-500 hover:bg-blue-600 text-white text-sm py-2 px-3 rounded-md transition-colors duration-200 flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            {showStructureView ? 'Hide' : 'Show'} Structure View
          </button>
          <button
            onClick={() => setShowTestPanel(!showTestPanel)}
            className="mt-2 w-full bg-green-500 hover:bg-green-600 text-white text-sm py-2 px-3 rounded-md transition-colors duration-200 flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            {showTestPanel ? 'Hide' : 'Show'} Test Panel
          </button>
          <button
            onClick={handleClearCache}
            disabled={clearCacheMutation.isPending}
            className="mt-3 w-full bg-red-500 hover:bg-red-600 disabled:bg-red-300 text-white text-sm py-2 px-3 rounded-md transition-colors duration-200 flex items-center justify-center gap-2"
          >
            {clearCacheMutation.isPending ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                Clearing...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Clear All Data
              </>
            )}
          </button>
          {clearCacheMutation.isError && (
            <div className="mt-2 text-xs text-red-600">
              Error: {clearCacheMutation.error?.message || 'Failed to clear cache'}
            </div>
          )}
          {clearCacheMutation.isSuccess && (
            <div className="mt-2 text-xs text-green-600">
              Cache cleared successfully!
            </div>
          )}

          {/* DANGER ZONE */}
          <div className="mt-4 pt-4 border-t border-red-200">
            <div className="text-xs font-bold text-red-600 mb-2">⚠️ DANGER ZONE</div>
            <button
              onClick={handleClearAllTopics}
              disabled={clearAllTopicsMutation.isPending}
              className="w-full bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white text-sm py-2 px-3 rounded-md transition-colors duration-200 flex items-center justify-center gap-2 border-2 border-red-800"
            >
              {clearAllTopicsMutation.isPending ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Clearing All Topics...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  DELETE ALL MESSAGES
                </>
              )}
            </button>
            <div className="text-xs text-red-500 mt-1 text-center">
              Permanently clears ALL Kafka topics
            </div>
            {clearAllTopicsMutation.isError && (
              <div className="mt-2 text-xs text-red-600">
                Error: {clearAllTopicsMutation.error?.message || 'Failed to clear topics'}
              </div>
            )}
            {clearAllTopicsMutation.isSuccess && (
              <div className="mt-2 text-xs text-green-600">
                Successfully cleared all topics!
                {clearAllTopicsMutation.data?.clearedSuccessfully && (
                  <span> ({clearAllTopicsMutation.data.clearedSuccessfully} topics cleared)</span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Test Message Panel */}
      {showTestPanel && (
        <div className="absolute top-4 right-4 z-10 w-80">
          <TestMessagePanel
            selectedTopic={testPanelTopic}
            onTopicChange={setTestPanelTopic}
          />
        </div>
      )}

      <div ref={reactFlowWrapper} style={{ width: '100%', height: '100%' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={handleNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          onNodeDragStop={handleNodeDragStop}
          nodeTypes={nodeTypes}
          fitView
          attributionPosition="bottom-left"
          multiSelectionKeyCode="Shift"
          selectionKeyCode="Shift"
          deleteKeyCode="Delete"
          selectNodesOnDrag={false}
        >
        <Controls />
        <MiniMap
          nodeStrokeColor={(n) => {
            if (n.data?.status === 'active') return '#10b981'
            if (n.data?.status === 'idle') return '#f59e0b'
            if (n.data?.status === 'error') return '#ef4444'
            return '#6b7280'
          }}
          nodeColor={(n) => {
            if (n.data?.status === 'active') return '#d1fae5'
            if (n.data?.status === 'idle') return '#fef3c7'
            if (n.data?.status === 'error') return '#fee2e2'
            return '#f3f4f6'
          }}
          nodeBorderRadius={8}
        />
        <Background color="#aaa" gap={16} />
        </ReactFlow>
      </div>

      <DataModal
        isOpen={modalData.isOpen}
        onClose={closeModal}
        title={modalData.title}
        data={modalData.data}
        onViewLogs={handleViewLogs}
        isKafkaTopic={!!selectedTopic}
      />

      <LogViewer
        topic={logViewerTopic}
        onClose={() => setLogViewerTopic(null)}
      />

      {/* Structure View Modal */}
      {showStructureView && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="text-xl font-semibold">Pipeline Structure</h2>
              <button
                onClick={() => setShowStructureView(false)}
                className="text-gray-500 hover:text-gray-700 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <StructureViewEnhanced />
          </div>
        </div>
      )}
    </div>
  )
}

function App() {
  return (
    <ReactFlowProvider>
      <PipelineMonitor />
    </ReactFlowProvider>
  )
}

export default App
