import { useQuery } from '@tanstack/react-query'

const API_BASE_URL = (import.meta as any).env.VITE_API_URL || 'http://localhost:8082'

interface GraphNode {
  id: string
  type: 'kafka-topic' | 'processor' | 'database' | 'external'
  position: { x: number; y: number }
  data: {
    label: string
    status?: 'active' | 'idle' | 'error' | 'unknown'
    description?: string
    priority?: string
    models?: string[]
    metrics?: any
    health?: any
    containerName?: string
  }
}

interface GraphEdge {
  id: string
  source: string
  target: string
  animated?: boolean
}

interface PipelineGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

// Generate positions for nodes in a column-based layout
function generateLayout(nodes: GraphNode[], edges: GraphEdge[]): GraphNode[] {
  // Build adjacency lists for efficient graph traversal
  const incomingEdges = new Map<string, string[]>()
  const outgoingEdges = new Map<string, string[]>()
  
  edges.forEach(edge => {
    if (!incomingEdges.has(edge.target)) {
      incomingEdges.set(edge.target, [])
    }
    incomingEdges.get(edge.target)!.push(edge.source)
    
    if (!outgoingEdges.has(edge.source)) {
      outgoingEdges.set(edge.source, [])
    }
    outgoingEdges.get(edge.source)!.push(edge.target)
  })
  
  // Calculate the column (distance from source) for each node
  const nodeColumns = new Map<string, number>()
  const visited = new Set<string>()
  
  // Find all nodes with no incoming edges (sources)
  const sourceNodes = nodes.filter(node => 
    !incomingEdges.has(node.id) || incomingEdges.get(node.id)!.length === 0
  )
  
  // BFS from all source nodes to assign columns
  const queue: { id: string; column: number }[] = []
  sourceNodes.forEach(node => {
    queue.push({ id: node.id, column: 0 })
    nodeColumns.set(node.id, 0)
  })
  
  while (queue.length > 0) {
    const { id, column } = queue.shift()!
    
    if (visited.has(id)) continue
    visited.add(id)
    
    // Process all outgoing edges
    const targets = outgoingEdges.get(id) || []
    targets.forEach(targetId => {
      const currentColumn = nodeColumns.get(targetId) || -1
      const newColumn = column + 1
      
      // Always use the maximum column to ensure proper ordering
      if (newColumn > currentColumn) {
        nodeColumns.set(targetId, newColumn)
        queue.push({ id: targetId, column: newColumn })
      }
    })
  }
  
  // Handle disconnected nodes (no path from any source)
  nodes.forEach(node => {
    if (!nodeColumns.has(node.id)) {
      // Place at the end
      const maxColumn = Math.max(...Array.from(nodeColumns.values()), -1)
      nodeColumns.set(node.id, maxColumn + 1)
    }
  })
  
  // Group nodes by column and type
  const columnGroups = new Map<number, {
    topics: string[]
    processors: string[]
  }>()
  
  nodes.forEach(node => {
    const column = nodeColumns.get(node.id) || 0
    if (!columnGroups.has(column)) {
      columnGroups.set(column, { topics: [], processors: [] })
    }
    
    const group = columnGroups.get(column)!
    if (node.type === 'processor') {
      group.processors.push(node.id)
    } else {
      group.topics.push(node.id)
    }
  })
  
  // Create a scoring system to align connected nodes
  const getConnectionScore = (nodeId: string, column: number): number => {
    let score = 0
    
    // Look at incoming connections from previous columns
    const incoming = incomingEdges.get(nodeId) || []
    incoming.forEach(sourceId => {
      const sourceColumn = nodeColumns.get(sourceId)
      if (sourceColumn !== undefined && sourceColumn < column) {
        const sourcePos = nodePositions.get(sourceId)
        if (sourcePos) {
          score += sourcePos.y * 10 // Weight by Y position of source
        }
      }
    })
    
    // Look at outgoing connections to next columns
    const outgoing = outgoingEdges.get(nodeId) || []
    outgoing.forEach(targetId => {
      const targetColumn = nodeColumns.get(targetId)
      if (targetColumn !== undefined && targetColumn > column) {
        // We'll process these later, so just add a base score
        score += 1000
      }
    })
    
    return score
  }
  
  // Layout configuration
  const COLUMN_WIDTH = 350
  const VERTICAL_SPACING = 80
  const START_X = 100
  const START_Y = 100
  const MIN_COLUMN_HEIGHT = 800
  
  // Calculate positions
  const nodePositions = new Map<string, { x: number; y: number }>()
  
  // Process each column
  const sortedColumns = Array.from(columnGroups.keys()).sort((a, b) => a - b)
  
  sortedColumns.forEach(column => {
    const group = columnGroups.get(column)!
    const x = START_X + column * COLUMN_WIDTH
    
    // Get all nodes in this column
    const allNodesInColumn = [...group.topics, ...group.processors]
    
    // Sort nodes by their connection scores to align with connected nodes
    const nodesWithScores = allNodesInColumn.map(nodeId => ({
      nodeId,
      isProcessor: group.processors.includes(nodeId),
      score: getConnectionScore(nodeId, column)
    }))
    
    // Sort by score, then by type (topics first), then alphabetically
    nodesWithScores.sort((a, b) => {
      if (Math.abs(a.score - b.score) > 100) {
        return a.score - b.score
      }
      // If scores are similar, group by type
      if (a.isProcessor !== b.isProcessor) {
        return a.isProcessor ? 1 : -1
      }
      // Finally sort alphabetically
      return a.nodeId.localeCompare(b.nodeId)
    })
    
    // Calculate total height needed for this column
    const totalNodes = allNodesInColumn.length
    const totalHeight = Math.max(
      totalNodes * VERTICAL_SPACING,
      MIN_COLUMN_HEIGHT
    )
    
    // Position nodes based on sorted order
    const startY = START_Y + (totalHeight - (totalNodes - 1) * VERTICAL_SPACING) / 2
    
    nodesWithScores.forEach((node, index) => {
      const y = startY + index * VERTICAL_SPACING
      // Add slight horizontal offset for processors
      const xOffset = node.isProcessor ? 30 : 0
      nodePositions.set(node.nodeId, { x: x + xOffset, y })
    })
  })
  
  // Second pass: Adjust positions to minimize edge crossings
  sortedColumns.forEach(column => {
    const group = columnGroups.get(column)!
    const nodesInColumn = [...group.topics, ...group.processors]
    
    // Calculate average Y position of connected nodes
    const targetYPositions = new Map<string, number>()
    
    nodesInColumn.forEach(nodeId => {
      let totalY = 0
      let connectionCount = 0
      
      // Check incoming connections
      const incoming = incomingEdges.get(nodeId) || []
      incoming.forEach(sourceId => {
        const sourcePos = nodePositions.get(sourceId)
        if (sourcePos) {
          totalY += sourcePos.y
          connectionCount++
        }
      })
      
      // Check outgoing connections
      const outgoing = outgoingEdges.get(nodeId) || []
      outgoing.forEach(targetId => {
        const targetPos = nodePositions.get(targetId)
        if (targetPos) {
          totalY += targetPos.y
          connectionCount++
        }
      })
      
      if (connectionCount > 0) {
        targetYPositions.set(nodeId, totalY / connectionCount)
      }
    })
    
    // Sort nodes by their target Y position
    const sortedNodes = nodesInColumn.sort((a, b) => {
      const targetA = targetYPositions.get(a) || nodePositions.get(a)!.y
      const targetB = targetYPositions.get(b) || nodePositions.get(b)!.y
      return targetA - targetB
    })
    
    // Reposition nodes based on new order
    const currentX = START_X + column * COLUMN_WIDTH
    const startY = START_Y + (MIN_COLUMN_HEIGHT - (sortedNodes.length - 1) * VERTICAL_SPACING) / 2
    
    sortedNodes.forEach((nodeId, index) => {
      const isProcessor = group.processors.includes(nodeId)
      const xOffset = isProcessor ? 30 : 0
      nodePositions.set(nodeId, { 
        x: currentX + xOffset, 
        y: startY + index * VERTICAL_SPACING 
      })
    })
  })
  
  // Apply positions to nodes
  return nodes.map(node => ({
    ...node,
    position: nodePositions.get(node.id) || { x: 0, y: 0 }
  }))
}

export function usePipelineGraph() {
  return useQuery({
    queryKey: ['pipeline-graph'],
    queryFn: async (): Promise<PipelineGraph> => {
      // Get pipeline definitions from YAML
      const definitionsResponse = await fetch(`${API_BASE_URL}/api/pipeline-definitions`)
      if (!definitionsResponse.ok) {
        throw new Error('Failed to fetch pipeline definitions')
      }
      const definitions = await definitionsResponse.json()
      
      // Get current Kafka structure for metrics
      const kafkaResponse = await fetch(`${API_BASE_URL}/api/kafka/pipeline`)
      const kafkaData = kafkaResponse.ok ? await kafkaResponse.json() : null
      
      // Build graph from pipeline definitions
      const nodes: GraphNode[] = []
      const edges: GraphEdge[] = []
      const processedTopics = new Set<string>()
      
      // Extract pipeline flows from visualization config
      const pipelineSummary = definitions.visualization?.pipeline_summary || {}
      
      // First pass: Create all processor nodes
      Object.entries(pipelineSummary).forEach(([flowId, flowData]: [string, any]) => {
        // Add processor node for the flow
        nodes.push({
          id: flowId,
          type: 'processor',
          position: { x: 0, y: 0 }, // Will be calculated later
          data: {
            label: flowData.service_name || flowData.name || flowId.split('_').map((w: string) => 
              w.charAt(0).toUpperCase() + w.slice(1)
            ).join(' '),
            containerName: flowData.container_name,
            priority: flowData.priority,
            description: `${flowData.stages} stages`,
            models: flowData.models,
            metrics: {
              inputRate: flowData.input_rate,
              latencyTarget: flowData.latency_target
            }
          }
        })
      })
      
      // Second pass: Create topic nodes and all edges
      Object.entries(pipelineSummary).forEach(([flowId, flowData]: [string, any]) => {
        // Add input topic nodes and edges
        flowData.connections?.inputs?.forEach((topic: string) => {
          if (!processedTopics.has(topic)) {
            nodes.push({
              id: topic,
              type: 'kafka-topic',
              position: { x: 0, y: 0 },
              data: { 
                label: topic,
                status: 'unknown'
              }
            })
            processedTopics.add(topic)
          }
          edges.push({
            id: `${topic}-${flowId}`,
            source: topic,
            target: flowId,
            animated: true
          })
        })
        
        // Add output topic nodes and edges
        flowData.connections?.outputs?.forEach((topic: string) => {
          if (!processedTopics.has(topic)) {
            nodes.push({
              id: topic,
              type: 'kafka-topic',
              position: { x: 0, y: 0 },
              data: { 
                label: topic,
                status: 'unknown'
              }
            })
            processedTopics.add(topic)
          }
          edges.push({
            id: `${flowId}-${topic}`,
            source: flowId,
            target: topic,
            animated: true
          })
        })
      })
      
      // Third pass: Add any missing topics from Kafka that aren't in the pipeline definitions
      if (kafkaData && kafkaData.nodes) {
        kafkaData.nodes.forEach((kafkaNode: any) => {
          if (kafkaNode.type === 'kafka-topic' && !processedTopics.has(kafkaNode.id)) {
            nodes.push({
              id: kafkaNode.id,
              type: 'kafka-topic',
              position: { x: 0, y: 0 },
              data: {
                label: kafkaNode.id,
                status: 'unknown'
              }
            })
            processedTopics.add(kafkaNode.id)
          }
        })
      }
      
      // Add individual flow details
      definitions.flows?.forEach((flow: any) => {
        // Check if we already have this processor
        const existingNode = nodes.find(n => n.id === flow.name)
        if (existingNode) {
          // Enhance with additional flow data
          existingNode.data = {
            ...existingNode.data,
            description: flow.description || existingNode.data.description
          }
        }
      })
      
      // Merge with Kafka metrics if available
      if (kafkaData) {
        // Update topic statuses from Kafka data
        kafkaData.nodes?.forEach((kafkaNode: any) => {
          const node = nodes.find(n => n.id === kafkaNode.id)
          if (node && kafkaNode.data.metrics) {
            node.data.status = kafkaNode.data.status || 'unknown'
            node.data.metrics = {
              ...node.data.metrics,
              ...kafkaNode.data.metrics
            }
          }
        })
      }
      
      // Apply layout algorithm
      const layoutNodes = generateLayout(nodes, edges)
      
      return {
        nodes: layoutNodes,
        edges
      }
    },
    refetchInterval: 30000, // Refresh every 30 seconds
    staleTime: 10000,
  })
}