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
import dagre from 'dagre'

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
      <div className="relative bg-blue-100 border-2 border-blue-500 rounded-lg p-4 min-w-[200px]">
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
      <div className="relative bg-green-100 border-2 border-green-500 rounded-lg p-4 min-w-[250px]">
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
    <div className="bg-purple-100 border-2 border-purple-500 rounded-lg p-4 min-w-[200px]">
      <div className="font-bold text-sm">{data.label}</div>
      {data.description && (
        <div className="text-xs text-gray-600 mt-1">{data.description}</div>
      )}
    </div>
  ),
  'table': ({ data }: any) => (
    <div className="relative bg-orange-100 border-2 border-orange-500 rounded-lg p-4 min-w-[200px]">
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
    <div className="relative bg-purple-100 border-2 border-purple-500 rounded-lg p-4 min-w-[200px]">
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
    <div className="relative bg-yellow-100 border-2 border-yellow-500 rounded-lg p-4 min-w-[200px]">
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
  )
}

// Layout algorithm
const getLayoutedElements = (nodes: Node[], edges: Edge[]) => {
  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))
  dagreGraph.setGraph({
    rankdir: 'LR',
    ranksep: 200,
    nodesep: 80,
    marginx: 20,
    marginy: 20,
    ranker: 'network-simplex'
  })

  nodes.forEach((node) => {
    let width = 250
    let height = 100

    if (node.type === 'database') {
      width = 150
    } else if (node.type === 'table') {
      width = 220
      height = 80
    } else if (node.type === 'processor') {
      width = 300
      // Calculate height based on content
      const baseHeight = 120 // Increased for button
      const inputLines = (node.data.inputTopics || []).length
      const outputLines = (node.data.outputTopics || []).length
      const topicLines = inputLines + outputLines
      // Add extra height for topic lists
      height = baseHeight + (topicLines > 0 ? 20 + (topicLines * 16) : 0)
    } else if (node.type === 'kafka-topic') {
      width = 250
      height = node.data.hasTable ? 140 : 120 // Extra height for button and table name
    } else if (node.type === 'api') {
      width = 220
      const endpointLines = (node.data.endpoints || []).length
      height = 100 + (endpointLines > 0 ? 20 + (endpointLines * 16) : 0)
    } else if (node.type === 'fetcher') {
      width = 240
      const sourceLines = (node.data.sources || []).length
      height = 100 + (sourceLines > 0 ? 20 + (sourceLines * 16) : 0)
    }

    dagreGraph.setNode(node.id, { width, height })
  })

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target)
  })

  dagre.layout(dagreGraph)

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id)
    const width = nodeWithPosition.width
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - width / 2,
        y: nodeWithPosition.y - nodeWithPosition.height / 2,
      },
    }
  })

  return { nodes: layoutedNodes, edges }
}

function SimplePipelineMonitor() {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [topology, setTopology] = useState<any>(null)

  useEffect(() => {
    fetchPipelineStructure()
  }, [])

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
          id: 'fetcher_email',
          label: 'Email Fetcher',
          description: 'IMAP email ingestion',
          sources: ['Gmail', 'Outlook', 'IMAP servers'],
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
          id: 'fetcher_twitter',
          label: 'Twitter/X Fetcher',
          description: 'Social media scraper',
          sources: ['Twitter/X likes', 'Bookmarks'],
          outputTopics: ['external.twitter.liked.raw', 'task.url.ingest']
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

      // Create edges from API to raw topics with endpoint details
      const apiTopicMappings = [
        { topic: 'device.audio.raw', endpoints: ['/audio/upload', '/audio/stream'] },
        { topic: 'device.sensor.gps.raw', endpoint: '/sensor/gps' },
        { topic: 'device.sensor.accelerometer.raw', endpoint: '/sensor/accelerometer' },
        { topic: 'device.health.heartrate.raw', endpoint: '/sensor/heartrate' },
        { topic: 'device.state.power.raw', endpoint: '/sensor/power' },
        { topic: 'os.events.app_lifecycle.raw', endpoint: '/os-events/app-lifecycle' },
        { topic: 'os.events.system.raw', endpoint: '/os-events/system' },
        { topic: 'device.system.apps.android.raw', endpoints: ['/system/apps/android', '/system/apps/android/usage'] }
      ]

      apiTopicMappings.forEach(mapping => {
        const topicId = topicNameToId.get(mapping.topic)
        if (topicId) {
          const endpoints = mapping.endpoints || [mapping.endpoint]
          const endpointLabel = endpoints.join(', ')
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

          // Check if edge already exists
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
      })

      // Create table nodes for topics that have database tables
      const tableNodeSet = new Set<string>()
      const topicToTable = new Map<string, string>() // Map topic names to table node IDs

      topologyData.topics?.forEach((topic: any) => {
        if (topic.table_name) {
          const tableNodeId = `table_${topic.table_name.replace(/[\._]/g, '_')}`

          if (!tableNodeSet.has(tableNodeId)) {
            tableNodeSet.add(tableNodeId)
            const tableNode: Node = {
              id: tableNodeId,
              type: 'table',
              position: { x: 0, y: 0 },
              data: {
                label: topic.table_name,
                topic: topic.topic_name
              }
            }
            newNodes.push(tableNode)
            nodeMap.set(tableNodeId, tableNode)
          }

          topicToTable.set(topic.topic_name, tableNodeId)
        }
      })

      // Find kafka-to-db consumers and connect them to tables
      topologyData.stages?.forEach((stage: any) => {
        // Check if this is a kafka-to-db consumer (has inputs but no outputs)
        if (stage.service_name.includes('kafka-to-db') ||
            stage.service_name.includes('timescale-writer') ||
            stage.service_name.includes('kafka-to-db-saver') ||
            (stage.input_topics && stage.input_topics.length > 0 &&
             (!stage.output_topics || stage.output_topics.length === 0))) {

          // For each input topic, check if it has a table
          stage.input_topics?.forEach((topicName: string) => {
            const tableId = topicToTable.get(topicName)
            if (tableId) {
              const processorId = `processor_${stage.service_name.replace(/[\.-]/g, '_')}`
              const edgeId = `${processorId}-${tableId}`

              if (!newEdges.find(e => e.id === edgeId)) {
                const processorNode = nodeMap.get(processorId)
                const tableNode = nodeMap.get(tableId)
                const shortServiceName = processorNode?.data?.label?.replace('loom-', '').substring(0, 20) || 'processor'
                const tableName = tableNode?.data?.label || 'table'
                newEdges.push({
                  id: edgeId,
                  source: processorId,
                  target: tableId,
                  label: `${shortServiceName} → ${tableName}`,
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

      // Layout the graph
      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(newNodes, newEdges)
      setNodes(layoutedNodes)
      setEdges(layoutedEdges)
      setLoading(false)
    } catch (err) {
      console.error('Error fetching pipeline structure:', err)
      setError(err instanceof Error ? err.message : 'Failed to load pipeline structure')
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="w-screen h-screen flex items-center justify-center">
        <div className="text-xl">Loading pipeline structure...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="w-screen h-screen flex items-center justify-center">
        <div className="text-xl text-red-600">Error: {error}</div>
      </div>
    )
  }

  return (
    <div className="w-screen h-screen" style={{ width: '100vw', height: '100vh' }}>
      <div className="absolute top-4 left-4 z-10 bg-white p-4 rounded-lg shadow-lg" style={{ maxWidth: '300px' }}>
        <h1 className="text-xl font-bold mb-2">Loom Pipeline Structure</h1>
        <div className="text-sm text-gray-600">
          <div>API Endpoints: 1</div>
          <div>External Fetchers: {nodes.filter(n => n.type === 'fetcher').length}</div>
          <div>Topics: {nodes.filter(n => n.type === 'kafka-topic').length}</div>
          <div>Processors: {nodes.filter(n => n.type === 'processor').length}</div>
          <div>Tables: {nodes.filter(n => n.type === 'table').length}</div>
          <div>Connections: {edges.length}</div>
        </div>

        {/* Color Guide */}
        <div className="mt-4 pt-3 border-t border-gray-200">
          <div className="text-xs font-semibold text-gray-700 mb-2">Color Guide:</div>
          <div className="space-y-1">
            <div className="flex items-center text-xs">
              <div className="w-4 h-4 bg-purple-100 border-2 border-purple-500 rounded mr-2"></div>
              <span>Ingestion API</span>
            </div>
            <div className="flex items-center text-xs">
              <div className="w-4 h-4 bg-yellow-100 border-2 border-yellow-500 rounded mr-2"></div>
              <span>External Fetchers</span>
            </div>
            <div className="flex items-center text-xs">
              <div className="w-4 h-4 bg-blue-100 border-2 border-blue-500 rounded mr-2"></div>
              <span>Kafka Topics</span>
            </div>
            <div className="flex items-center text-xs">
              <div className="w-4 h-4 bg-green-100 border-2 border-green-500 rounded mr-2"></div>
              <span>Processors/Consumers</span>
            </div>
            <div className="flex items-center text-xs">
              <div className="w-4 h-4 bg-orange-100 border-2 border-orange-500 rounded mr-2"></div>
              <span>Database Tables</span>
            </div>
            <div className="flex items-center text-xs mt-2">
              <div className="w-8 h-0.5 bg-purple-500 mr-2"></div>
              <span>API → Topic</span>
            </div>
            <div className="flex items-center text-xs">
              <div className="w-8 h-0.5 bg-yellow-500 mr-2"></div>
              <span>Fetcher → Topic</span>
            </div>
            <div className="flex items-center text-xs">
              <div className="w-8 h-0.5 bg-blue-500 mr-2"></div>
              <span>Topic → Consumer</span>
            </div>
            <div className="flex items-center text-xs">
              <div className="w-8 h-0.5 bg-green-500 mr-2"></div>
              <span>Consumer → Topic</span>
            </div>
            <div className="flex items-center text-xs">
              <div className="w-8 h-0.5 bg-orange-500 mr-2"></div>
              <span>Consumer → Table</span>
            </div>
          </div>
        </div>

        <button
          onClick={fetchPipelineStructure}
          className="mt-3 w-full bg-blue-500 hover:bg-blue-600 text-white text-sm py-2 px-3 rounded-md"
        >
          Refresh
        </button>
        
        <button
          onClick={() => {
            // Create a comprehensive structure object
            const structure = {
              metadata: {
                exportDate: new Date().toISOString(),
                totalNodes: nodes.length,
                totalEdges: edges.length,
                apiEndpoints: 1,
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
                serviceName: n.data.label,
                description: n.data.description,
                consumerGroup: n.data.consumerGroup,
                inputTopics: n.data.inputTopics,
                outputTopics: n.data.outputTopics
              })),
              tables: nodes.filter(n => n.type === 'table').map(n => ({
                id: n.id,
                tableName: n.data.label,
                sourceTopic: n.data.topic
              })),
              connections: edges.map(e => ({
                id: e.id,
                source: e.source,
                target: e.target,
                label: e.label,
                type: e.type
              })),
              rawTopology: topology
            }
            
            // Convert to JSON and download
            const dataStr = JSON.stringify(structure, null, 2)
            const dataBlob = new Blob([dataStr], { type: 'application/json' })
            const url = URL.createObjectURL(dataBlob)
            const link = document.createElement('a')
            link.href = url
            link.download = `loom-pipeline-structure-${new Date().toISOString().split('T')[0]}.json`
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
            URL.revokeObjectURL(url)
          }}
          className="mt-2 w-full bg-green-500 hover:bg-green-600 text-white text-sm py-2 px-3 rounded-md"
        >
          Download Structure as JSON
        </button>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{
          padding: 0.3,
          minZoom: 0.1,
          maxZoom: 1.5
        }}
        defaultEdgeOptions={{
          type: 'smoothstep',
          animated: true
        }}
      >
        <Background variant={BackgroundVariant.Dots} />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  )
}

function AppSimple() {
  return (
    <ReactFlowProvider>
      <SimplePipelineMonitor />
    </ReactFlowProvider>
  )
}

export default AppSimple
