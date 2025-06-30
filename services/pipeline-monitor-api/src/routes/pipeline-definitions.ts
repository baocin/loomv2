import { Router } from 'express'
import fs from 'fs/promises'
import path from 'path'
import yaml from 'js-yaml'

const router = Router()

// Cache for pipeline definitions
let pipelineCache: any = null
let cacheTimestamp = 0
const CACHE_DURATION = 60000 // 1 minute

// Load pipeline definitions from flow YAML files
async function loadPipelineDefinitions() {
  const now = Date.now()
  
  // Return cached data if still valid
  if (pipelineCache && (now - cacheTimestamp) < CACHE_DURATION) {
    return pipelineCache
  }

  try {
    const flowsDir = process.env.NODE_ENV === 'development' 
      ? path.join('/docs', 'flows')  // Use mounted volume in container
      : path.join(process.cwd(), '..', '..', 'docs', 'flows')
    const visualizationFile = path.join(flowsDir, 'pipeline-visualization.yaml')
    
    // Load the visualization config
    const vizConfig = yaml.load(await fs.readFile(visualizationFile, 'utf8')) as any
    
    // Load individual flow definitions
    const flowFiles = await fs.readdir(flowsDir)
    const flows: any[] = []
    
    for (const file of flowFiles) {
      if (file.endsWith('.yaml') && !file.startsWith('_') && file !== 'pipeline-visualization.yaml') {
        const filePath = path.join(flowsDir, file)
        const content = await fs.readFile(filePath, 'utf8')
        const flowData = yaml.load(content) as any
        
        if (flowData && flowData.name) {
          flows.push({
            id: flowData.name,
            ...flowData,
            fileName: file
          })
        }
      }
    }
    
    // Build the complete pipeline data structure
    pipelineCache = {
      visualization: vizConfig,
      flows: flows,
      summary: {
        totalFlows: flows.length,
        byPriority: {
          critical: flows.filter(f => f.priority === 'critical').length,
          high: flows.filter(f => f.priority === 'high').length,
          medium: flows.filter(f => f.priority === 'medium').length,
          low: flows.filter(f => f.priority === 'low').length,
        },
        totalStages: flows.reduce((sum, flow) => sum + (flow.stages?.length || 0), 0),
        models: Array.from(new Set(flows.flatMap(f => 
          f.stages?.flatMap((s: any) => 
            s.configuration?.models || []
          ) || []
        ))),
      },
      timestamp: new Date().toISOString()
    }
    
    cacheTimestamp = now
    return pipelineCache
  } catch (error) {
    console.error('Error loading pipeline definitions:', error)
    // Return a fallback structure
    return {
      visualization: {},
      flows: [],
      summary: {
        totalFlows: 0,
        byPriority: { critical: 0, high: 0, medium: 0, low: 0 },
        totalStages: 0,
        models: []
      },
      error: error instanceof Error ? error.message : 'Unknown error',
      timestamp: new Date().toISOString()
    }
  }
}

// GET /pipeline-definitions - Get all pipeline definitions and visualization config
router.get('/', async (req, res) => {
  try {
    const definitions = await loadPipelineDefinitions()
    res.json(definitions)
  } catch (error) {
    console.error('Error fetching pipeline definitions:', error)
    res.status(500).json({ 
      error: 'Failed to load pipeline definitions',
      message: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

// GET /pipeline-definitions/flows/:flowName - Get a specific flow definition
router.get('/flows/:flowName', async (req, res) => {
  try {
    const definitions = await loadPipelineDefinitions()
    const flow = definitions.flows.find((f: any) => f.name === req.params.flowName)
    
    if (!flow) {
      return res.status(404).json({ error: 'Flow not found' })
    }
    
    res.json(flow)
  } catch (error) {
    console.error('Error fetching flow definition:', error)
    res.status(500).json({ 
      error: 'Failed to load flow definition',
      message: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

// GET /pipeline-definitions/graph - Get simplified graph data for visualization
router.get('/graph', async (req, res) => {
  try {
    const definitions = await loadPipelineDefinitions()
    const pipeline_summary = definitions.visualization?.pipeline_summary || {}
    
    if (!pipeline_summary) {
      return res.json({ nodes: [], edges: [] })
    }
    
    // Create nodes and edges from pipeline summary
    const nodes: any[] = []
    const edges: any[] = []
    const processedTopics = new Set<string>()
    
    Object.entries(pipeline_summary).forEach(([flowId, flowData]: [string, any]) => {
      // Add flow node
      nodes.push({
        id: flowId,
        type: 'processor',
        data: {
          label: flowData.name || flowId,
          priority: flowData.priority,
          stages: flowData.stages,
          models: flowData.models,
          metrics: {
            inputRate: flowData.input_rate,
            latencyTarget: flowData.latency_target
          }
        }
      })
      
      // Add topic nodes and edges
      flowData.connections?.inputs?.forEach((topic: string) => {
        if (!processedTopics.has(topic)) {
          nodes.push({
            id: topic,
            type: 'kafka-topic',
            data: { label: topic }
          })
          processedTopics.add(topic)
        }
        edges.push({
          id: `${topic}-${flowId}`,
          source: topic,
          target: flowId
        })
      })
      
      flowData.connections?.outputs?.forEach((topic: string) => {
        if (!processedTopics.has(topic)) {
          nodes.push({
            id: topic,
            type: 'kafka-topic',  
            data: { label: topic }
          })
          processedTopics.add(topic)
        }
        edges.push({
          id: `${flowId}-${topic}`,
          source: flowId,
          target: topic
        })
      })
    })
    
    res.json({ nodes, edges })
  } catch (error) {
    console.error('Error generating graph data:', error)
    res.status(500).json({ 
      error: 'Failed to generate graph data',
      message: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

export default router