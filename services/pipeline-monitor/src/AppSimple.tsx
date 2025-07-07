import { useEffect, useState } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  ReactFlowProvider,
  BackgroundVariant,
  MarkerType,
  Handle,
  Position
} from 'reactflow'
import 'reactflow/dist/style.css'
import './App.css'

const API_BASE = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8082'

// Helper function to generate example messages for topics
const getExampleMessage = (topicName: string): string => {
  const examples: { [key: string]: string } = {
    'device.audio.raw': '{"device_id": "phone-123", "timestamp": "2024-01-20T10:30:00Z", "audio_data": "base64_encoded_audio_chunk", "format": "pcm16", "sample_rate": 16000}',
    'device.sensor.gps.raw': '{"device_id": "phone-123", "timestamp": "2024-01-20T10:30:00Z", "latitude": 37.7749, "longitude": -122.4194, "accuracy": 10.5}',
    'device.sensor.accelerometer.raw': '{"device_id": "phone-123", "timestamp": "2024-01-20T10:30:00Z", "x": 0.12, "y": -0.98, "z": 0.05}',
    'device.health.heartrate.raw': '{"device_id": "watch-456", "timestamp": "2024-01-20T10:30:00Z", "bpm": 72, "confidence": 0.95}',
    'media.audio.vad_filtered': '{"device_id": "phone-123", "timestamp": "2024-01-20T10:30:00Z", "audio_data": "base64_speech_audio", "speech_probability": 0.92}',
    'media.text.transcribed.words': '{"device_id": "phone-123", "timestamp": "2024-01-20T10:30:00Z", "word": "hello", "confidence": 0.89, "start_time": 1.2, "end_time": 1.5}',
    'os.events.app_lifecycle.raw': '{"device_id": "phone-123", "timestamp": "2024-01-20T10:30:00Z", "app_id": "com.example.app", "event_type": "foreground", "duration_ms": 45000}',
    'os.events.system.raw': '{"device_id": "phone-123", "timestamp": "2024-01-20T10:30:00Z", "event_type": "screen_on", "category": "screen"}',
    'device.state.power.raw': '{"device_id": "phone-123", "timestamp": "2024-01-20T10:30:00Z", "battery_level": 85, "is_charging": false, "power_source": "battery"}'
  }

  // Try to find exact match first
  if (examples[topicName]) {
    return examples[topicName]
  }

  // Generate generic example based on topic patterns
  if (topicName.includes('.raw')) {
    return `{"device_id": "device-123", "timestamp": "2024-01-20T10:30:00Z", "data": "raw_${topicName.split('.')[1]}_data"}`
  } else if (topicName.includes('.processed') || topicName.includes('.filtered')) {
    return `{"device_id": "device-123", "timestamp": "2024-01-20T10:30:00Z", "processed_data": "${topicName.split('.')[1]}_result", "confidence": 0.85}`
  } else if (topicName.includes('.analysis')) {
    return `{"device_id": "device-123", "timestamp": "2024-01-20T10:30:00Z", "analysis_result": {"type": "${topicName.split('.')[1]}", "score": 0.78}}`
  }

  return `{"message": "Example data for ${topicName}", "timestamp": "2024-01-20T10:30:00Z"}`
}

// Simple node types
const nodeTypes = {
  'kafka-topic': ({ data }: any) => {
    const [showExample, setShowExample] = useState(false)

    return (
      <div 
        className={`relative bg-blue-100 border-2 border-blue-500 rounded-lg p-4 min-w-[200px] m-2 ${
          data.isFiltered ? 'opacity-30' : ''
        } ${data.isMatched ? 'ring-4 ring-yellow-400 bg-yellow-50' : ''}`}
      >
        <Handle
          type="target"
          position={Position.Left}
          style={{ background: '#3b82f6' }}
        />
        <div className="font-bold text-sm">{data.label}</div>
        {data.description && (
          <div className="text-xs text-gray-600 mt-1">{data.description}</div>
        )}
        {data.hasTable && (
          <div className="text-xs text-purple-600 mt-2">
            <div className="flex items-center">
              <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path d="M3 12v3c0 1.657 3.134 3 7 3s7-1.343 7-3v-3c0 1.657-3.134 3-7 3s-7-1.343-7-3z" />
                <path d="M3 7v3c0 1.657 3.134 3 7 3s7-1.343 7-3V7c0 1.657-3.134 3-7 3S3 8.657 3 7z" />
                <path d="M17 5c0 1.657-3.134 3-7 3S3 6.657 3 5s3.134-3 7-3 7 1.343 7 3z" />
              </svg>
              Stored in DB
            </div>
            {data.tableName && (
              <div className="text-xs text-gray-500 mt-1">Table: {data.tableName}</div>
            )}
          </div>
        )}
        <button
          onClick={() => setShowExample(!showExample)}
          className="text-xs bg-blue-500 text-white px-2 py-1 rounded mt-2 hover:bg-blue-600"
        >
          {showExample ? 'Hide' : 'View'} Example Message
        </button>
        {showExample && (
          <div className="text-xs bg-white p-2 rounded mt-2 font-mono overflow-auto max-w-[300px]">
            {data.exampleMessage || getExampleMessage(data.label)}
          </div>
        )}
        <Handle
          type="source"
          position={Position.Right}
          style={{ background: '#3b82f6' }}
        />
      </div>
    )
  },
  'processor': ({ data }: any) => {
    const [showLog, setShowLog] = useState(false)

    return (
      <div 
        className={`relative bg-green-100 border-2 border-green-500 rounded-lg p-4 min-w-[250px] m-2 ${
          data.isFiltered ? 'opacity-30' : ''
        } ${data.isMatched ? 'ring-4 ring-yellow-400 bg-yellow-50' : ''}`}
      >
        <Handle
          type="target"
          position={Position.Left}
          style={{ background: '#10b981' }}
        />
        <div className="font-bold text-sm">{data.label}</div>
        {data.description && (
          <div className="text-xs text-gray-600 mt-1">{data.description}</div>
        )}
        {data.consumerGroup && (
          <div className="text-xs text-gray-500 mt-2 font-mono">
            Consumer: {data.consumerGroup}
          </div>
        )}
        {data.inputTopics && data.inputTopics.length > 0 && (
          <div className="text-xs text-gray-600 mt-2">
            <div className="font-semibold">Input topics:</div>
            <div className="ml-2 mt-1">
              {data.inputTopics.map((topic: string, idx: number) => (
                <div key={idx} className="text-gray-500">• {topic}</div>
              ))}
            </div>
          </div>
        )}
        {data.outputTopics && data.outputTopics.length > 0 && (
          <div className="text-xs text-gray-600 mt-2">
            <div className="font-semibold">Output topics:</div>
            <div className="ml-2 mt-1">
              {data.outputTopics.map((topic: string, idx: number) => (
                <div key={idx} className="text-gray-500">• {topic}</div>
              ))}
            </div>
          </div>
        )}
        <button
          onClick={() => setShowLog(!showLog)}
          className="text-xs bg-green-500 text-white px-2 py-1 rounded mt-2 hover:bg-green-600"
        >
          {showLog ? 'Hide' : 'View'} Last Log
        </button>
        {showLog && (
          <div className="text-xs bg-white p-2 rounded mt-2 font-mono overflow-auto max-w-[400px]">
            <div className="text-gray-500">[2024-01-20 10:30:15] INFO</div>
            <div className="mt-1">Processing batch of {data.inputTopics?.length || 1} messages from {data.inputTopics?.[0] || 'input topic'}</div>
            <div className="text-green-600 mt-1">✓ Successfully processed and sent to {data.outputTopics?.[0] || 'output topic'}</div>
          </div>
        )}
        <Handle
          type="source"
          position={Position.Right}
          style={{ background: '#10b981' }}
        />
      </div>
    )
  },
  'database': ({ data }: any) => (
    <div 
      className={`bg-purple-100 border-2 border-purple-500 rounded-lg p-4 min-w-[200px] m-2 ${
        data.isFiltered ? 'opacity-30' : ''
      } ${data.isMatched ? 'ring-4 ring-yellow-400 bg-yellow-50' : ''}`}
    >
      <div className="font-bold text-sm">{data.label}</div>
      {data.description && (
        <div className="text-xs text-gray-600 mt-1">{data.description}</div>
      )}
    </div>
  ),
  'table': ({ data }: any) => (
    <div 
      className={`relative bg-orange-100 border-2 border-orange-500 rounded-lg p-4 min-w-[200px] m-2 ${
        data.isFiltered ? 'opacity-30' : ''
      } ${data.isMatched ? 'ring-4 ring-yellow-400 bg-yellow-50' : ''}`}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: '#f97316' }}
      />
      <div className="font-bold text-sm flex items-center">
        <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
          <path d="M3 12v3c0 1.657 3.134 3 7 3s7-1.343 7-3v-3c0 1.657-3.134 3-7 3s-7-1.343-7-3z" />
          <path d="M3 7v3c0 1.657 3.134 3 7 3s7-1.343 7-3V7c0 1.657-3.134 3-7 3S3 8.657 3 7z" />
          <path d="M17 5c0 1.657-3.134 3-7 3S3 6.657 3 5s3.134-3 7-3 7 1.343 7 3z" />
        </svg>
        {data.label}
      </div>
      {data.topic && (
        <div className="text-xs text-gray-600 mt-1">From: {data.topic}</div>
      )}
    </div>
  ),
  'api': ({ data }: any) => (
    <div 
      className={`relative bg-purple-100 border-2 border-purple-500 rounded-lg p-4 min-w-[200px] m-2 ${
        data.isFiltered ? 'opacity-30' : ''
      } ${data.isMatched ? 'ring-4 ring-yellow-400 bg-yellow-50' : ''}`}
    >
      <div className="font-bold text-sm flex items-center">
        <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M2 5a2 2 0 012-2h12a2 2 0 012 2v10a2 2 0 01-2 2H4a2 2 0 01-2-2V5zm3.293 1.293a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 01-1.414-1.414L7.586 10 5.293 7.707a1 1 0 010-1.414zM11 12a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
        </svg>
        {data.label}
      </div>
      {data.description && (
        <div className="text-xs text-gray-600 mt-1">{data.description}</div>
      )}
      {data.endpoints && data.endpoints.length > 0 && (
        <div className="text-xs text-gray-600 mt-2">
          <div className="font-semibold">Endpoints:</div>
          <div className="ml-2 mt-1">
            {data.endpoints.map((endpoint: string, idx: number) => (
              <div key={idx} className="text-gray-500">• {endpoint}</div>
            ))}
          </div>
        </div>
      )}
      <Handle
        type="source"
        position={Position.Right}
        style={{ background: '#9333ea' }}
      />
    </div>
  ),
  'fetcher': ({ data }: any) => (
    <div 
      className={`relative bg-yellow-100 border-2 border-yellow-500 rounded-lg p-4 min-w-[200px] m-2 ${
        data.isFiltered ? 'opacity-30' : ''
      } ${data.isMatched ? 'ring-4 ring-yellow-400 bg-yellow-50' : ''}`}
    >
      <div className="font-bold text-sm flex items-center">
        <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
        </svg>
        {data.label}
      </div>
      {data.description && (
        <div className="text-xs text-gray-600 mt-1">{data.description}</div>
      )}
      {data.sources && data.sources.length > 0 && (
        <div className="text-xs text-gray-600 mt-2">
          <div className="font-semibold">Data sources:</div>
          <div className="ml-2 mt-1">
            {data.sources.map((source: string, idx: number) => (
              <div key={idx} className="text-gray-500">• {source}</div>
            ))}
          </div>
        </div>
      )}
      <Handle
        type="source"
        position={Position.Right}
        style={{ background: '#eab308' }}
      />
    </div>
  ),
  'column-header': ({ data }: any) => (
    <div className="bg-gray-800 text-white px-6 py-3 rounded-lg shadow-lg m-2">
      <div className="font-bold text-lg text-center">{data.label}</div>
    </div>
  )
}

// Simplified layout algorithm with better organization
const getLayoutedElements = (nodes: Node[], edges: Edge[]) => {
  // Group nodes by type
  const nodeGroups: { [key: string]: Node[] } = {
    api: [],
    fetcher: [],
    rawTopic: [],
    processor: [],
    processedTopic: [],
    kafkaToDb: [],
    table: [],
    header: [],
    error: []
  }

  // Categorize nodes
  nodes.forEach(node => {
    if (node.type === 'column-header') {
      nodeGroups.header.push(node)
    } else if (node.type === 'api') {
      nodeGroups.api.push(node)
    } else if (node.type === 'fetcher') {
      nodeGroups.fetcher.push(node)
    } else if (node.type === 'kafka-topic') {
      if (node.data.label.includes('error')) {
        nodeGroups.error.push(node)
      } else if (node.data.label.includes('.raw')) {
        nodeGroups.rawTopic.push(node)
      } else {
        nodeGroups.processedTopic.push(node)
      }
    } else if (node.type === 'processor') {
      if (node.data.label.includes('kafka-to-db') ||
          node.data.label.includes('timescale-writer') ||
          node.data.label.includes('generic-kafka-to-db')) {
        nodeGroups.kafkaToDb.push(node)
      } else {
        nodeGroups.processor.push(node)
      }
    } else if (node.type === 'table') {
      nodeGroups.table.push(node)
    }
  })

  // Column X positions with more spacing (about a node width = ~250px between columns)
  const columns = {
    api: 50,
    fetcher: 400,  // Separate column for fetchers
    rawTopic: 750,
    processor: 1350,
    processedTopic: 1950,
    kafkaToDb: 2550,
    table: 3150,
    error: 1950  // Same as processedTopic
  }

  // Heights for different node types
  const nodeHeights = {
    api: 150,
    fetcher: 150,
    topic: 150,
    processor: 250,
    table: 100,
    header: 50
  }

  // Vertical spacing
  const verticalSpacing = 60
  const sectionSpacing = 100

  // Position headers
  nodeGroups.header.forEach(node => {
    if (node.position) {
      node.position.y = 0
    }
  })

  // Create a connection graph for better positioning
  const connectionGraph: { [nodeId: string]: { sources: string[], targets: string[] } } = {}

  nodes.forEach(node => {
    connectionGraph[node.id] = { sources: [], targets: [] }
  })

  edges.forEach(edge => {
    if (connectionGraph[edge.source]) {
      connectionGraph[edge.source].targets.push(edge.target)
    }
    if (connectionGraph[edge.target]) {
      connectionGraph[edge.target].sources.push(edge.source)
    }
  })

  // Position nodes in a more organized way
  let currentY = 80

  // API nodes in their own column
  nodeGroups.api.forEach((node, index) => {
    node.position = { x: columns.api, y: currentY + index * (nodeHeights.api + verticalSpacing) }
  })

  // Fetcher nodes in their own column
  nodeGroups.fetcher.forEach((node, index) => {
    node.position = { x: columns.fetcher, y: currentY + index * (nodeHeights.fetcher + verticalSpacing) }
  })

  // Raw topics - position based on their sources
  const positionedNodes = new Set<string>()
  const positionNodeGroup = (group: Node[], columnX: number, defaultHeight: number) => {
    const sortedNodes = [...group].sort((a, b) => {
      // Sort by number of connections for better layout
      const aConnections = (connectionGraph[a.id]?.sources.length || 0) + (connectionGraph[a.id]?.targets.length || 0)
      const bConnections = (connectionGraph[b.id]?.sources.length || 0) + (connectionGraph[b.id]?.targets.length || 0)
      return bConnections - aConnections
    })

    const columnNodes: { node: Node, preferredY: number }[] = []

    sortedNodes.forEach(node => {
      let preferredY = currentY

      // Try to align with source nodes
      const sources = connectionGraph[node.id]?.sources || []
      const positionedSources = sources.filter(id => positionedNodes.has(id))

      if (positionedSources.length > 0) {
        const sourcePositions = positionedSources
          .map(id => nodes.find(n => n.id === id))
          .filter(n => n && n.position)
          .map(n => n!.position!.y)

        if (sourcePositions.length > 0) {
          preferredY = sourcePositions.reduce((sum, y) => sum + y, 0) / sourcePositions.length
        }
      }

      columnNodes.push({ node, preferredY })
    })

    // Sort by preferred Y position
    columnNodes.sort((a, b) => a.preferredY - b.preferredY)

    // Position nodes avoiding overlaps
    let lastY = 80
    columnNodes.forEach(({ node, preferredY }) => {
      const minY = Math.max(preferredY, lastY)
      node.position = { x: columnX, y: minY }
      lastY = minY + defaultHeight + verticalSpacing
      positionedNodes.add(node.id)
    })

    return lastY
  }

  // Position each column in order
  positionNodeGroup(nodeGroups.rawTopic, columns.rawTopic, nodeHeights.topic)
  positionNodeGroup(nodeGroups.processor, columns.processor, nodeHeights.processor)
  positionNodeGroup(nodeGroups.processedTopic, columns.processedTopic, nodeHeights.topic)
  positionNodeGroup(nodeGroups.kafkaToDb, columns.kafkaToDb, nodeHeights.processor)
  positionNodeGroup(nodeGroups.table, columns.table, nodeHeights.table)

  // Position error topics at the bottom
  if (nodeGroups.error.length > 0) {
    const maxY = Math.max(...nodes.filter(n => n.position && n.type !== 'column-header').map(n => n.position!.y))
    nodeGroups.error.forEach((node, index) => {
      node.position = { x: columns.error, y: maxY + sectionSpacing + index * (nodeHeights.topic + verticalSpacing) }
    })
  }

  return { nodes, edges }
}

function SimplePipelineMonitor() {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [topology, setTopology] = useState<any>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [filteredNodes, setFilteredNodes] = useState<Set<string>>(new Set())

  // Load saved positions from localStorage
  const loadSavedPositions = (): { [nodeId: string]: { x: number, y: number } } => {
    try {
      const saved = localStorage.getItem('loom-pipeline-node-positions')
      return saved ? JSON.parse(saved) : {}
    } catch (e) {
      console.error('Failed to load saved positions:', e)
      return {}
    }
  }

  // Save positions to localStorage
  const savePositions = (nodesToSave: Node[]) => {
    try {
      const positions: { [nodeId: string]: { x: number, y: number } } = {}
      nodesToSave.forEach(node => {
        if (node.position) {
          positions[node.id] = { x: node.position.x, y: node.position.y }
        }
      })
      localStorage.setItem('loom-pipeline-node-positions', JSON.stringify(positions))
    } catch (e) {
      console.error('Failed to save positions:', e)
    }
  }

  // Handle node changes (including drags)
  const handleNodesChange = (changes: any) => {
    onNodesChange(changes)

    // If any node was dragged, save the new positions
    const hasPositionChange = changes.some((change: any) =>
      change.type === 'position' && change.dragging === false
    )

    if (hasPositionChange) {
      // Get the current nodes state after the change
      setNodes(currentNodes => {
        savePositions(currentNodes)
        return currentNodes
      })
    }
  }

  useEffect(() => {
    fetchPipelineStructure()
  }, [])

  // Search and filter logic
  useEffect(() => {
    if (!searchTerm.trim()) {
      setFilteredNodes(new Set())
      return
    }

    const searchLower = searchTerm.toLowerCase()
    const matchedNodes = new Set<string>()
    const connectedNodes = new Set<string>()

    // Find directly matched nodes
    nodes.forEach(node => {
      if (node.type === 'column-header') return
      
      const label = node.data.label?.toLowerCase() || ''
      const description = node.data.description?.toLowerCase() || ''
      const consumerGroup = node.data.consumerGroup?.toLowerCase() || ''
      const inputTopics = node.data.inputTopics?.join(' ').toLowerCase() || ''
      const outputTopics = node.data.outputTopics?.join(' ').toLowerCase() || ''
      
      if (label.includes(searchLower) || 
          description.includes(searchLower) ||
          consumerGroup.includes(searchLower) ||
          inputTopics.includes(searchLower) ||
          outputTopics.includes(searchLower)) {
        matchedNodes.add(node.id)
      }
    })

    // Find connected nodes (nodes that have edges to/from matched nodes)
    edges.forEach(edge => {
      if (matchedNodes.has(edge.source) || matchedNodes.has(edge.target)) {
        connectedNodes.add(edge.source)
        connectedNodes.add(edge.target)
      }
    })

    // Combine matched and connected nodes
    const allVisibleNodes = new Set([...matchedNodes, ...connectedNodes])
    setFilteredNodes(allVisibleNodes)
  }, [searchTerm, nodes, edges])

  // Update node styling when search changes
  useEffect(() => {
    if (!nodes.length) return
    
    const updatedNodes = nodes.map(node => {
      if (node.type === 'column-header') return node
      
      const isMatched = searchTerm.trim() && filteredNodes.has(node.id) && (() => {
        const searchLower = searchTerm.toLowerCase()
        const label = node.data.label?.toLowerCase() || ''
        const description = node.data.description?.toLowerCase() || ''
        const consumerGroup = node.data.consumerGroup?.toLowerCase() || ''
        const inputTopics = node.data.inputTopics?.join(' ').toLowerCase() || ''
        const outputTopics = node.data.outputTopics?.join(' ').toLowerCase() || ''
        
        return label.includes(searchLower) || 
               description.includes(searchLower) ||
               consumerGroup.includes(searchLower) ||
               inputTopics.includes(searchLower) ||
               outputTopics.includes(searchLower)
      })()
      
      const isFiltered = searchTerm.trim() && !filteredNodes.has(node.id)
      
      return {
        ...node,
        data: {
          ...node.data,
          isMatched,
          isFiltered
        }
      }
    })
    
    setNodes(updatedNodes)
    
    // Also update edge styling
    const updatedEdges = edges.map(edge => {
      const sourceFiltered = searchTerm.trim() && !filteredNodes.has(edge.source)
      const targetFiltered = searchTerm.trim() && !filteredNodes.has(edge.target)
      const isFiltered = sourceFiltered || targetFiltered
      
      if (isFiltered) {
        return {
          ...edge,
          style: {
            ...edge.style,
            opacity: 0.3
          },
          labelStyle: {
            ...edge.labelStyle,
            opacity: 0.3
          }
        }
      } else {
        return {
          ...edge,
          style: {
            ...edge.style,
            opacity: 1
          },
          labelStyle: {
            ...edge.labelStyle,
            opacity: 1
          }
        }
      }
    })
    
    setEdges(updatedEdges)
  }, [filteredNodes, searchTerm])

  const fetchPipelineStructure = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch(`${API_BASE}/api/pipelines/topology`)
      if (!response.ok) {
        throw new Error('Failed to fetch pipeline topology')
      }

      const topologyData = await response.json()
      setTopology(topologyData)

      const newNodes: Node[] = []
      const newEdges: Edge[] = []
      const nodeMap = new Map<string, Node>()
      const topicNameToId = new Map<string, string>() // Map topic names to node IDs

      // Add column headers
      const columnHeaders = [
        { id: 'header_api', label: 'API Endpoints', x: 50 },
        { id: 'header_fetchers', label: 'Data Fetchers', x: 400 },
        { id: 'header_raw_topics', label: 'Raw Topics', x: 750 },
        { id: 'header_processors', label: 'Processors', x: 1350 },
        { id: 'header_processed', label: 'Processed Topics', x: 1950 },
        { id: 'header_db_writers', label: 'DB Writers', x: 2550 },
        { id: 'header_tables', label: 'Database Tables', x: 3150 }
      ]

      columnHeaders.forEach(header => {
        const node: Node = {
          id: header.id,
          type: 'column-header',
          position: { x: header.x, y: 0 },
          data: { label: header.label },
          selectable: false,
          draggable: false
        }
        newNodes.push(node)
        nodeMap.set(header.id, node)
      })

      // Add ingestion API as a special node
      const apiNodeId = 'api_ingestion'
      const apiNode: Node = {
        id: apiNodeId,
        type: 'api',
        position: { x: 0, y: 0 },
        data: {
          label: 'Ingestion API',
          description: 'FastAPI REST/WebSocket endpoints',
          endpoints: ['/audio/upload', '/sensor/*', '/os-events/*', '/system/*']
        }
      }
      newNodes.push(apiNode)
      nodeMap.set(apiNodeId, apiNode)

      // First, identify which topics are actually written to DB
      const topicsWrittenToDB = new Set<string>()
      topologyData.stages?.forEach((stage: any) => {
        // Check if this is a DB writer service
        if (stage.service_name.includes('kafka-to-db') ||
            stage.service_name.includes('timescale-writer') ||
            stage.service_name.includes('kafka-to-db-saver') ||
            (stage.input_topics && stage.input_topics.length > 0 &&
             (!stage.output_topics || stage.output_topics.length === 0))) {
          // Mark all input topics as written to DB
          stage.input_topics?.forEach((topicName: string) => {
            topicsWrittenToDB.add(topicName)
          })
        }
      })

      // Create fetcher nodes for external data sources
      const fetcherConfigs = [
        {
          id: 'fetcher_gmail',
          label: 'Gmail Fetcher',
          description: 'Gmail email ingestion',
          sources: ['Gmail API'],
          outputTopics: ['external.email.raw']
        },
        {
          id: 'fetcher_fastmail',
          label: 'Fastmail Fetcher',
          description: 'Fastmail email ingestion',
          sources: ['Fastmail IMAP'],
          outputTopics: ['external.email.raw']
        },
        {
          id: 'fetcher_calendar',
          label: 'Calendar Fetcher',
          description: 'CalDAV calendar sync',
          sources: ['Google Calendar', 'iCloud', 'CalDAV'],
          outputTopics: ['external.calendar.events.raw']
        },
        {
          id: 'fetcher_x_likes',
          label: 'X/Twitter Likes Fetcher',
          description: 'Social media scraper',
          sources: ['X.com likes'],
          outputTopics: ['external.twitter.liked.raw', 'task.url.ingest']
        },
        {
          id: 'fetcher_hackernews',
          label: 'HackerNews Fetcher',
          description: 'HN saved items',
          sources: ['HackerNews API'],
          outputTopics: ['external.hackernews.liked', 'task.url.ingest']
        }
      ]

      fetcherConfigs.forEach(config => {
        const node: Node = {
          id: config.id,
          type: 'fetcher',
          position: { x: 0, y: 0 },
          data: {
            label: config.label,
            description: config.description,
            sources: config.sources,
            outputTopics: config.outputTopics
          }
        }
        newNodes.push(node)
        nodeMap.set(config.id, node)
      })

      // Create topic nodes
      topologyData.topics?.forEach((topic: any) => {
        const nodeId = `topic_${topic.topic_name.replace(/\./g, '_')}`
        const isStoredInDB = topicsWrittenToDB.has(topic.topic_name) && topic.table_name
        const node: Node = {
          id: nodeId,
          type: 'kafka-topic',
          position: { x: 0, y: 0 },
          data: {
            label: topic.topic_name,
            description: topic.description,
            hasTable: isStoredInDB,
            tableName: topic.table_name
          }
        }
        newNodes.push(node)
        nodeMap.set(nodeId, node)
        topicNameToId.set(topic.topic_name, nodeId) // Store mapping for lookup
      })

      // Create edges from API to raw topics using database mappings
      if (topologyData.apiMappings) {
        // Group API mappings by topic
        const topicEndpoints = new Map<string, string[]>()

        topologyData.apiMappings.forEach((mapping: any) => {
          if (!topicEndpoints.has(mapping.topic_name)) {
            topicEndpoints.set(mapping.topic_name, [])
          }
          topicEndpoints.get(mapping.topic_name)!.push(mapping.api_endpoint)
        })

        // Create edges for each topic with API endpoints
        topicEndpoints.forEach((endpoints, topicName) => {
          const topicId = topicNameToId.get(topicName)
          if (topicId) {
            // Remove duplicates and sort endpoints
            const uniqueEndpoints = [...new Set(endpoints)].sort()
            const endpointLabel = uniqueEndpoints.join(', ')

            newEdges.push({
              id: `${apiNodeId}-${topicId}`,
              source: apiNodeId,
              target: topicId,
              label: endpointLabel,
              type: 'smoothstep',
              animated: true,
              style: {
                stroke: '#9333ea',
                strokeWidth: 2
              },
              labelStyle: {
                fontSize: 10,
                fontWeight: 600
              },
              labelBgPadding: [8, 4],
              labelBgBorderRadius: 4,
              labelBgStyle: {
                fill: '#ffffff',
                fillOpacity: 0.9
              },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                color: '#9333ea'
              }
            })
          }
        })
      }

      // Create edges from fetchers to their output topics
      fetcherConfigs.forEach(fetcher => {
        fetcher.outputTopics.forEach(topicName => {
          const topicId = topicNameToId.get(topicName)
          if (topicId) {
            const shortFetcherName = fetcher.label.replace(' Fetcher', '')
            const shortTopicName = topicName.split('.').slice(-2).join('.')
            newEdges.push({
              id: `${fetcher.id}-${topicId}`,
              source: fetcher.id,
              target: topicId,
              label: `${shortFetcherName} → ${shortTopicName}`,
              type: 'smoothstep',
              animated: false,
              style: {
                stroke: '#eab308',
                strokeWidth: 2
              },
              labelStyle: {
                fontSize: 10,
                fontWeight: 500
              },
              labelBgPadding: [8, 4],
              labelBgBorderRadius: 4,
              labelBgStyle: {
                fill: '#ffffff',
                fillOpacity: 0.9
              },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                color: '#eab308'
              }
            })
          }
        })
      })

      // Create processor nodes
      topologyData.stages?.forEach((stage: any) => {
        const nodeId = `processor_${stage.service_name.replace(/[\.-]/g, '_')}`

        if (!nodeMap.has(nodeId)) {
          const node: Node = {
            id: nodeId,
            type: 'processor',
            position: { x: 0, y: 0 },
            data: {
              label: stage.service_name,
              description: stage.stage_name,
              consumerGroup: stage.consumer_group_id,
              inputTopics: stage.input_topics || [],
              outputTopics: stage.output_topics || []
            }
          }
          newNodes.push(node)
          nodeMap.set(nodeId, node)
        }

        // Create edges from input topics to processor
        stage.input_topics?.forEach((topicName: string) => {
          const sourceId = topicNameToId.get(topicName) || `topic_${topicName.replace(/\./g, '_')}`
          const edgeId = `${sourceId}-${nodeId}`

          // Check if edge already exists
          if (nodeMap.has(sourceId) && !newEdges.find(e => e.id === edgeId)) {
            const shortTopicName = topicName.split('.').slice(-2).join('.')
            const shortServiceName = stage.service_name.replace('loom-', '').substring(0, 20)
            newEdges.push({
              id: edgeId,
              source: sourceId,
              target: nodeId,
              label: `${shortTopicName} → ${shortServiceName}`,
              type: 'smoothstep',
              animated: true,
              style: {
                stroke: '#3b82f6',
                strokeWidth: 2
              },
              labelStyle: {
                fontSize: 10,
                fontWeight: 500
              },
              labelBgPadding: [8, 4],
              labelBgBorderRadius: 4,
              labelBgStyle: {
                fill: '#ffffff',
                fillOpacity: 0.9
              },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                color: '#3b82f6'
              }
            })
          }
        })

        // Create edges from processor to output topics
        stage.output_topics?.forEach((topicName: string) => {
          const targetId = topicNameToId.get(topicName) || `topic_${topicName.replace(/\./g, '_')}`
          const edgeId = `${nodeId}-${targetId}`

          if (nodeMap.has(targetId) && !newEdges.find(e => e.id === edgeId)) {
            const shortServiceName = stage.service_name.replace('loom-', '').substring(0, 20)
            const shortTopicName = topicName.split('.').slice(-2).join('.')
            newEdges.push({
              id: edgeId,
              source: nodeId,
              target: targetId,
              label: `${shortServiceName} → ${shortTopicName}`,
              type: 'smoothstep',
              animated: true,
              style: {
                stroke: '#10b981',
                strokeWidth: 2
              },
              labelStyle: {
                fontSize: 10,
                fontWeight: 500
              },
              labelBgPadding: [8, 4],
              labelBgBorderRadius: 4,
              labelBgStyle: {
                fill: '#ffffff',
                fillOpacity: 0.9
              },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                color: '#10b981'
              }
            })
          }
        })

        // Handle processors that write to DB (tables)
        if (stage.service_name.includes('kafka-to-db') ||
            stage.service_name.includes('timescale-writer') ||
            (stage.input_topics && stage.input_topics.length > 0 &&
             (!stage.output_topics || stage.output_topics.length === 0))) {

          // Create table nodes for each input topic
          stage.input_topics?.forEach((topicName: string) => {
            const tableName = topologyData.topics?.find((t: any) => t.topic_name === topicName)?.table_name
            if (tableName) {
              const tableNodeId = `table_${tableName}`

              if (!nodeMap.has(tableNodeId)) {
                const tableNode: Node = {
                  id: tableNodeId,
                  type: 'table',
                  position: { x: 0, y: 0 },
                  data: {
                    label: tableName,
                    topic: topicName
                  }
                }
                newNodes.push(tableNode)
                nodeMap.set(tableNodeId, tableNode)
              }

              // Create edge from processor to table
              const edgeId = `${nodeId}-${tableNodeId}`
              if (!newEdges.find(e => e.id === edgeId)) {
                newEdges.push({
                  id: edgeId,
                  source: nodeId,
                  target: tableNodeId,
                  label: `Write to ${tableName}`,
                  type: 'smoothstep',
                  animated: false,
                  style: {
                    stroke: '#f97316',
                    strokeWidth: 2
                  },
                  labelStyle: {
                    fontSize: 10,
                    fontWeight: 500
                  },
                  labelBgPadding: [8, 4],
                  labelBgBorderRadius: 4,
                  labelBgStyle: {
                    fill: '#ffffff',
                    fillOpacity: 0.9
                  },
                  markerEnd: {
                    type: MarkerType.ArrowClosed,
                    color: '#f97316'
                  }
                })
              }
            }
          })
        }
      })

      // Layout the elements
      const layouted = getLayoutedElements(newNodes, newEdges)

      // Apply saved positions if they exist
      const savedPositions = loadSavedPositions()
      const nodesWithSavedPositions = layouted.nodes.map(node => {
        if (savedPositions[node.id]) {
          return {
            ...node,
            position: savedPositions[node.id]
          }
        }
        return node
      })

      // Apply search filtering to nodes
      const nodesWithFiltering = nodesWithSavedPositions.map(node => {
        if (node.type === 'column-header') return node
        
        const isMatched = searchTerm.trim() && filteredNodes.has(node.id) && (() => {
          const searchLower = searchTerm.toLowerCase()
          const label = node.data.label?.toLowerCase() || ''
          const description = node.data.description?.toLowerCase() || ''
          const consumerGroup = node.data.consumerGroup?.toLowerCase() || ''
          const inputTopics = node.data.inputTopics?.join(' ').toLowerCase() || ''
          const outputTopics = node.data.outputTopics?.join(' ').toLowerCase() || ''
          
          return label.includes(searchLower) || 
                 description.includes(searchLower) ||
                 consumerGroup.includes(searchLower) ||
                 inputTopics.includes(searchLower) ||
                 outputTopics.includes(searchLower)
        })()
        
        const isFiltered = searchTerm.trim() && !filteredNodes.has(node.id)
        
        return {
          ...node,
          data: {
            ...node.data,
            isMatched,
            isFiltered
          }
        }
      })
      
      setNodes(nodesWithFiltering)
      setEdges(layouted.edges)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      console.error('Error fetching pipeline structure:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = () => {
    fetchPipelineStructure()
  }

  const handleDownloadStructure = () => {
    const structure = {
      metadata: {
        exportDate: new Date().toISOString(),
        totalNodes: nodes.length,
        totalEdges: edges.length,
        apiEndpoints: nodes.filter(n => n.type === 'api').length,
        fetchers: nodes.filter(n => n.type === 'fetcher').length,
        topics: nodes.filter(n => n.type === 'kafka-topic').length,
        processors: nodes.filter(n => n.type === 'processor').length,
        tables: nodes.filter(n => n.type === 'table').length
      },
      apiEndpoints: nodes.filter(n => n.type === 'api').map(n => ({
        id: n.id,
        label: n.data.label,
        description: n.data.description,
        endpoints: n.data.endpoints
      })),
      fetchers: nodes.filter(n => n.type === 'fetcher').map(n => ({
        id: n.id,
        label: n.data.label,
        description: n.data.description,
        sources: n.data.sources,
        outputTopics: n.data.outputTopics
      })),
      topics: nodes.filter(n => n.type === 'kafka-topic').map(n => ({
        id: n.id,
        name: n.data.label,
        description: n.data.description,
        hasTable: n.data.hasTable,
        tableName: n.data.tableName
      })),
      processors: nodes.filter(n => n.type === 'processor').map(n => ({
        id: n.id,
        name: n.data.label,
        description: n.data.description,
        consumerGroup: n.data.consumerGroup,
        inputTopics: n.data.inputTopics,
        outputTopics: n.data.outputTopics
      })),
      tables: nodes.filter(n => n.type === 'table').map(n => ({
        id: n.id,
        name: n.data.label,
        sourceTopic: n.data.topic
      })),
      connections: edges.map(e => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
        sourceNode: nodes.find(n => n.id === e.source)?.data.label,
        targetNode: nodes.find(n => n.id === e.target)?.data.label
      })),
      topology: topology,
      nodes: nodes,
      edges: edges
    }

    const dataStr = JSON.stringify(structure, null, 2)
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr)

    const exportFileDefaultName = `loom-pipeline-structure-${new Date().toISOString().split('T')[0]}.json`

    const linkElement = document.createElement('a')
    linkElement.setAttribute('href', dataUri)
    linkElement.setAttribute('download', exportFileDefaultName)
    linkElement.click()
  }

  const handleExportPositions = () => {
    const positions: { [nodeId: string]: { x: number, y: number } } = {}
    nodes.forEach(node => {
      if (node.position) {
        positions[node.id] = { x: node.position.x, y: node.position.y }
      }
    })

    const exportData = {
      metadata: {
        exportDate: new Date().toISOString(),
        version: '1.0',
        nodeCount: Object.keys(positions).length
      },
      positions: positions
    }

    const dataStr = JSON.stringify(exportData, null, 2)
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr)

    const exportFileDefaultName = `loom-pipeline-positions-${new Date().toISOString().split('T')[0]}.json`

    const linkElement = document.createElement('a')
    linkElement.setAttribute('href', dataUri)
    linkElement.setAttribute('download', exportFileDefaultName)
    linkElement.click()
  }

  const handleImportPositions = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'application/json'

    input.onchange = async (event: any) => {
      const file = event.target.files[0]
      if (!file) return

      try {
        const text = await file.text()
        const data = JSON.parse(text)

        if (data.positions && typeof data.positions === 'object') {
          // Apply the imported positions to current nodes
          const updatedNodes = nodes.map(node => {
            if (data.positions[node.id]) {
              return {
                ...node,
                position: data.positions[node.id]
              }
            }
            return node
          })

          setNodes(updatedNodes)
          savePositions(updatedNodes)

          alert(`Successfully imported positions for ${Object.keys(data.positions).length} nodes`)
        } else {
          alert('Invalid positions file format')
        }
      } catch (error) {
        console.error('Failed to import positions:', error)
        alert('Failed to import positions file')
      }
    }

    input.click()
  }

  const handleResetPositions = () => {
    if (confirm('Are you sure you want to reset all node positions to default layout?')) {
      localStorage.removeItem('loom-pipeline-node-positions')
      fetchPipelineStructure() // Re-fetch and re-layout
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading pipeline structure...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <div className="text-center bg-white p-8 rounded-lg shadow-lg">
          <div className="text-red-600 mb-4">
            <svg className="h-16 w-16 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold mb-2">Error Loading Pipeline</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={handleRefresh}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen bg-gray-100">
      <div className="absolute top-4 left-4 z-10 bg-white p-4 rounded-lg shadow-lg max-w-sm">
        <h1 className="text-xl font-bold mb-2">Loom Pipeline Structure</h1>
        
        {/* Search Input */}
        <div className="mb-4">
          <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-1">
            Search Nodes
          </label>
          <div className="relative">
            <input
              id="search"
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by name, topic, or description..."
              className="w-full px-3 py-2 pr-8 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
          {searchTerm && (
            <div className="text-xs text-gray-500 mt-1">
              {filteredNodes.size > 0 ? `Showing ${filteredNodes.size} related nodes` : 'No matches found'}
            </div>
          )}
        </div>
        
        <div className="text-sm text-gray-600 mb-4 space-y-1">
          <div>Nodes: {nodes.filter(n => n.type !== 'column-header').length}</div>
          <div>Connections: {edges.length}</div>
        </div>
        <div className="space-y-2">
          <button
            onClick={handleRefresh}
            className="w-full bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition"
          >
            Refresh Structure
          </button>
          <button
            onClick={handleDownloadStructure}
            className="w-full bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition"
          >
            Download Structure as JSON
          </button>

          <div className="border-t pt-2 mt-2">
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">Layout Positions</div>
            <button
              onClick={handleExportPositions}
              className="w-full bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 transition mb-2"
            >
              Export Positions
            </button>
            <button
              onClick={handleImportPositions}
              className="w-full bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 transition mb-2"
            >
              Import Positions
            </button>
            <button
              onClick={handleResetPositions}
              className="w-full bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700 transition"
            >
              Reset to Default Layout
            </button>
          </div>
        </div>
      </div>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.01}
        maxZoom={2}
        defaultViewport={{ x: 0, y: 0, zoom: 0.5 }}
      >
        <Background variant={BackgroundVariant.Dots} />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  )
}

export default function App() {
  return (
    <ReactFlowProvider>
      <SimplePipelineMonitor />
    </ReactFlowProvider>
  )
}
