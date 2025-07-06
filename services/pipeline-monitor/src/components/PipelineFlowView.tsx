import React, { useEffect, useState, useMemo } from 'react'
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  MarkerType
} from 'reactflow'
import 'reactflow/dist/style.css'
import { nodeTypes } from './NodeTypes'
import { ConsumerLogViewer } from './ConsumerLogViewer'
import { useQuery } from '@tanstack/react-query'
import dagre from 'dagre'

const API_BASE = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8082'

// Layout algorithm
const getLayoutedElements = (nodes: Node[], edges: Edge[]) => {
  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))
  dagreGraph.setGraph({ rankdir: 'LR', ranksep: 150, nodesep: 50 })

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 200, height: 100 })
  })

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target)
  })

  dagre.layout(dagreGraph)

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id)
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - 100,
        y: nodeWithPosition.y - 50,
      },
    }
  })

  return { nodes: layoutedNodes, edges }
}

export const PipelineFlowView: React.FC = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [selectedConsumer, setSelectedConsumer] = useState<string | null>(null)

  // Fetch pipeline topology
  const { data: topology } = useQuery({
    queryKey: ['pipeline-topology'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/api/pipelines/topology`)
      if (!response.ok) throw new Error('Failed to fetch topology')
      return response.json()
    },
    refetchInterval: 30000 // Refresh every 30 seconds
  })

  // Fetch consumer metrics
  const { data: consumerMetrics } = useQuery({
    queryKey: ['consumer-metrics'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/api/consumers/metrics`)
      if (!response.ok) throw new Error('Failed to fetch consumer metrics')
      return response.json()
    },
    refetchInterval: 10000 // Refresh every 10 seconds
  })

  // Fetch consumer lag
  const { data: consumerLag, error: lagError } = useQuery({
    queryKey: ['consumer-lag'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/api/consumers/lag`)
      if (!response.ok) throw new Error('Failed to fetch consumer lag')
      const data = await response.json()
      console.log('Consumer lag data:', data)
      return data
    },
    refetchInterval: 5000 // Refresh every 5 seconds
  })

  if (lagError) {
    console.error('Error fetching consumer lag:', lagError)
  }

  // Fetch message flow
  const { data: messageFlow } = useQuery({
    queryKey: ['message-flow'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/api/consumers/flow`)
      if (!response.ok) throw new Error('Failed to fetch message flow')
      return response.json()
    },
    refetchInterval: 10000 // Refresh every 10 seconds
  })

  // Build nodes and edges from topology data
  useEffect(() => {
    if (!topology) return

    const newNodes: Node[] = []
    const newEdges: Edge[] = []
    const nodeMap = new Map<string, Node>()

    // Create topic nodes
    topology.topics?.forEach((topic: any) => {
      const nodeId = `topic-${topic.topic_name}`
      const node: Node = {
        id: nodeId,
        type: 'kafka-topic',
        position: { x: 0, y: 0 },
        data: {
          label: topic.topic_name,
          description: topic.description,
          status: 'active',
          metrics: {
            messageCount: 0, // Could be fetched from Kafka
            consumerLag: consumerLag?.find((l: any) => l.topic === topic.topic_name)?.total_lag || 0
          }
        }
      }
      newNodes.push(node)
      nodeMap.set(nodeId, node)
    })

    // Create consumer nodes
    topology.stages?.forEach((stage: any) => {
      const nodeId = `consumer-${stage.service_name}`

      // Skip if we already have this consumer
      if (nodeMap.has(nodeId)) return

      // Find metrics for this consumer
      const metrics = consumerMetrics?.find((m: any) => m.service_name === stage.service_name)
      const lagData = consumerLag?.filter((l: any) => l.service_name === stage.service_name)
      console.log(`Lag data for ${stage.service_name}:`, lagData)
      const lag = lagData?.reduce((sum: number, l: any) => sum + parseInt(l.total_lag || '0'), 0) || 0

      // Find flow metrics
      const flowMetrics = messageFlow?.filter((f: any) => f.service_name === stage.service_name)
      const inputMessages = flowMetrics?.reduce((sum: number, f: any) => sum + (f.input_messages || 0), 0) || 0
      const outputMessages = flowMetrics?.reduce((sum: number, f: any) => sum + (f.output_messages || 0), 0) || 0
      const passThrough = inputMessages > 0 ? (outputMessages / inputMessages) * 100 : 0

      const node: Node = {
        id: nodeId,
        type: 'consumer',
        position: { x: 0, y: 0 },
        data: {
          label: stage.service_name,
          serviceName: stage.service_name,
          description: stage.stage_name,
          status: lag > 10000 ? 'error' : lag > 1000 ? 'idle' : 'active',
          metrics: {
            lag,
            avgProcessingTime: parseFloat(metrics?.avg_processing_time_ms || '0'),
            messagesPerSecond: parseFloat(metrics?.avg_messages_per_second || '0')
          },
          flow: {
            inputMessages,
            outputMessages,
            passThrough
          },
          onViewLogs: setSelectedConsumer
        }
      }
      newNodes.push(node)
      nodeMap.set(nodeId, node)

      // Create edges from input topics to consumer
      stage.input_topics?.forEach((topicName: string) => {
        const sourceId = `topic-${topicName}`
        if (nodeMap.has(sourceId)) {
          newEdges.push({
            id: `${sourceId}-${nodeId}`,
            source: sourceId,
            target: nodeId,
            type: 'smoothstep',
            animated: true,
            markerEnd: {
              type: MarkerType.ArrowClosed,
              width: 20,
              height: 20,
              color: '#64748b'
            },
            style: {
              stroke: '#64748b',
              strokeWidth: 2
            }
          })
        }
      })

      // Create edges from consumer to output topics
      stage.output_topics?.forEach((topicName: string) => {
        const targetId = `topic-${topicName}`
        if (nodeMap.has(targetId)) {
          newEdges.push({
            id: `${nodeId}-${targetId}`,
            source: nodeId,
            target: targetId,
            type: 'smoothstep',
            animated: true,
            markerEnd: {
              type: MarkerType.ArrowClosed,
              width: 20,
              height: 20,
              color: '#64748b'
            },
            style: {
              stroke: '#64748b',
              strokeWidth: 2
            }
          })
        }
      })
    })

    // Add database nodes
    const dbNode: Node = {
      id: 'database',
      type: 'database',
      position: { x: 800, y: 300 },
      data: {
        label: 'TimescaleDB',
        description: 'Time-series storage',
        status: 'active'
      }
    }
    newNodes.push(dbNode)

    // Connect some topics to database
    topology.topics?.forEach((topic: any) => {
      if (topic.table_name) {
        newEdges.push({
          id: `topic-${topic.topic_name}-database`,
          source: `topic-${topic.topic_name}`,
          target: 'database',
          type: 'smoothstep',
          animated: false,
          style: {
            stroke: '#10b981',
            strokeWidth: 2,
            strokeDasharray: '5 5'
          }
        })
      }
    })

    // Layout the graph
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(newNodes, newEdges)
    setNodes(layoutedNodes)
    setEdges(layoutedEdges)
  }, [topology, consumerMetrics, consumerLag, messageFlow, setNodes, setEdges])

  const customNodeTypes = useMemo(() => ({
    ...nodeTypes,
    consumer: (props: any) => {
      const ConsumerNodeComponent = nodeTypes.consumer as any
      return <ConsumerNodeComponent {...props} onViewLogs={setSelectedConsumer} />
    }
  }), [])

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={customNodeTypes}
        fitView
        attributionPosition="bottom-left"
      >
        <Background variant={BackgroundVariant.Dots} />
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            switch (node.data?.status) {
              case 'active': return '#10b981'
              case 'idle': return '#f59e0b'
              case 'error': return '#ef4444'
              default: return '#6b7280'
            }
          }}
        />
      </ReactFlow>

      {selectedConsumer && (
        <ConsumerLogViewer
          serviceName={selectedConsumer}
          onClose={() => setSelectedConsumer(null)}
        />
      )}
    </div>
  )
}
