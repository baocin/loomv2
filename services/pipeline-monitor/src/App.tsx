import React, { useState, useCallback } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Node,
  NodeChange,
} from 'reactflow'
import 'reactflow/dist/style.css'

import { nodeTypes } from './components/NodeTypes'
import { DataModal } from './components/DataModal'
import { usePipelineData, useTopicMetrics, useConsumerMetrics, useLatestMessage, useClearCache, useClearAllTopics } from './hooks/usePipelineData'

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

function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [modalData, setModalData] = useState<{ isOpen: boolean; title: string; data: any }>({
    isOpen: false,
    title: '',
    data: null,
  })
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null)

  const { data: pipelineData, isLoading: isPipelineLoading } = usePipelineData()
  const { data: topicMetrics, isLoading: isTopicMetricsLoading } = useTopicMetrics()
  const { data: consumerMetrics, isLoading: isConsumerMetricsLoading } = useConsumerMetrics()
  const { data: latestMessage } = useLatestMessage(selectedTopic || '')
  const clearCacheMutation = useClearCache()
  const clearAllTopicsMutation = useClearAllTopics()

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
    console.log('Node drag stopped, saving position for:', node.id, node.position)

    // Save only this node's position (preserving others)
    setTimeout(() => {
      updateNodePosition(node.id, node.position)
    }, 50)
  }, [])

  // Update nodes with real metrics data and restore positions
  React.useEffect(() => {
    if (!pipelineData || isTopicMetricsLoading || isConsumerMetricsLoading) return

    const savedPositions = loadNodePositions()

    const updatedNodes = pipelineData.nodes.map(node => {
      let updatedData = { ...node.data }

      // Add topic metrics
      if (node.type === 'kafka-topic') {
        const metrics = topicMetrics?.find(m => m.topic === node.id)
        if (metrics) {
          updatedData.metrics = metrics
          updatedData.status = metrics.isActive ? 'active' : 'idle'
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
      }

      // Restore saved position if available, otherwise use default
      const savedPosition = savedPositions[node.id]
      const position = savedPosition ? savedPosition : node.position

      // Debug: Log position restoration
      if (savedPosition) {
        console.log(`Restored position for ${node.id}:`, savedPosition)
      }

      return {
        ...node,
        data: updatedData,
        position,
      }
    })

    setNodes(updatedNodes)
    setEdges(pipelineData.edges)
  }, [pipelineData, topicMetrics, consumerMetrics, setNodes, setEdges])

  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    if (node.type === 'kafka-topic') {
      setSelectedTopic(node.id)
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

      <DataModal
        isOpen={modalData.isOpen}
        onClose={closeModal}
        title={modalData.title}
        data={modalData.data}
      />
    </div>
  )
}

export default App
