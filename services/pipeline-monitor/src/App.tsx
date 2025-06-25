import React, { useState, useCallback } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Node,
} from 'reactflow'
import 'reactflow/dist/style.css'

import { nodeTypes } from './components/NodeTypes'
import { DataModal } from './components/DataModal'
import { usePipelineData, useTopicMetrics, useConsumerMetrics, useLatestMessage } from './hooks/usePipelineData'

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

  // Update nodes with real metrics data
  React.useEffect(() => {
    if (!pipelineData || isTopicMetricsLoading || isConsumerMetricsLoading) return

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
          updatedData.status = new Date().getTime() - new Date(metrics.lastHeartbeat).getTime() < 60000 ? 'active' : 'idle'
        }
      }

      return {
        ...node,
        data: updatedData,
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
            new Date().getTime() - new Date(c.lastHeartbeat).getTime() < 60000
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
        </div>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
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
