import React from 'react'
import { Handle, Position } from 'reactflow'
import { formatDistanceToNow } from 'date-fns'
import { Database, MessageSquare, Cpu, ExternalLink, Circle } from 'lucide-react'
import { clsx } from 'clsx'
import type { PipelineNode } from '../types'

interface NodeProps {
  data: PipelineNode['data']
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'active': return 'bg-green-500'
    case 'idle': return 'bg-yellow-500'
    case 'error': return 'bg-red-500'
    default: return 'bg-gray-500'
  }
}

const getStatusBorder = (status: string) => {
  switch (status) {
    case 'active': return 'border-green-300'
    case 'idle': return 'border-yellow-300'
    case 'error': return 'border-red-300'
    default: return 'border-gray-300'
  }
}

export const KafkaTopicNode: React.FC<NodeProps> = ({ data }) => {
  const metrics = data.metrics as any
  const health = data.health as any

  return (
    <div className={clsx(
      'px-4 py-3 shadow-lg rounded-lg bg-white border-2 relative',
      getStatusBorder(data.status || 'unknown'),
      health?.errorCount > 0 && 'border-red-500',
      (data as any).isPulsing && 'animate-pulse-border'
    )}>
      <Handle type="target" position={Position.Left} />

      <div className="flex items-center gap-2 mb-2">
        <MessageSquare className="w-4 h-4 text-blue-600" />
        <Circle className={clsx('w-2 h-2 rounded-full', getStatusColor(data.status || 'unknown'))} />
        <span className="font-semibold text-sm">{data.label}</span>
      </div>

      {metrics && (
        <div className="text-xs text-gray-600 space-y-1">
          <div>Messages: {metrics.messageCount?.toLocaleString() || 0}</div>
          <div>Lag: {metrics.consumerLag || 0}</div>
          {metrics.lastMessageTime && (
            <div>Last: {formatDistanceToNow(new Date(metrics.lastMessageTime), { addSuffix: true })}</div>
          )}
        </div>
      )}

      {/* Error indicator */}
      {health?.errorCount > 0 && (
        <div className="absolute -top-2 -right-2 bg-red-500 text-white text-xs font-bold rounded-full w-6 h-6 flex items-center justify-center">
          {health.errorCount > 99 ? '99+' : health.errorCount}
        </div>
      )}

      <Handle type="source" position={Position.Right} />
    </div>
  )
}

export const ProcessorNode: React.FC<NodeProps> = ({ data }) => {
  const metrics = data.metrics as any
  const health = data.health as any

  return (
    <div className={clsx(
      'w-32 h-32 shadow-lg rounded-full bg-white border-2 flex flex-col items-center justify-center relative',
      getStatusBorder(data.status || 'unknown'),
      health?.errorCount > 0 && 'border-red-500 border-4'
    )}>
      <Handle type="target" position={Position.Left} />

      <div className="flex flex-col items-center gap-1">
        <Cpu className="w-5 h-5 text-purple-600" />
        <Circle className={clsx('w-2 h-2 rounded-full', getStatusColor(data.status || 'unknown'))} />
        <span className="font-semibold text-xs text-center leading-tight">{data.label}</span>
      </div>

      {data.description && (
        <div className="text-xs text-gray-600 text-center mt-1 leading-tight max-w-full overflow-hidden">
          {data.description.slice(0, 20)}...
        </div>
      )}

      {/* Error indicator */}
      {health?.errorCount > 0 && (
        <div className="absolute -top-2 -right-2 bg-red-500 text-white text-xs font-bold rounded-full w-6 h-6 flex items-center justify-center">
          {health.errorCount > 99 ? '99+' : health.errorCount}
        </div>
      )}

      {/* Error rate indicator */}
      {health?.errorRate > 0 && (
        <div className="absolute -bottom-12 left-1/2 transform -translate-x-1/2 text-xs text-red-600 font-semibold">
          Error Rate: {(health.errorRate * 100).toFixed(1)}%
        </div>
      )}

      {metrics && (
        <div className="absolute -bottom-8 left-1/2 transform -translate-x-1/2 text-xs text-gray-600 text-center whitespace-nowrap">
          {metrics.lastHeartbeat && (
            <div>Active {formatDistanceToNow(new Date(metrics.lastHeartbeat), { addSuffix: true })}</div>
          )}
        </div>
      )}

      <Handle type="source" position={Position.Right} />
    </div>
  )
}

export const DatabaseNode: React.FC<NodeProps> = ({ data }) => {
  const health = data.health as any

  return (
    <div className={clsx(
      'px-4 py-3 shadow-lg rounded-lg bg-white border-2 relative',
      getStatusBorder(data.status || 'unknown'),
      health?.errorCount > 0 && 'border-red-500'
    )}>
      <Handle type="target" position={Position.Left} />

      <div className="flex items-center gap-2 mb-2">
        <Database className="w-4 h-4 text-green-600" />
        <Circle className={clsx('w-2 h-2 rounded-full', getStatusColor(data.status || 'unknown'))} />
        <span className="font-semibold text-sm">{data.label}</span>
      </div>

      {data.description && (
        <div className="text-xs text-gray-600">{data.description}</div>
      )}

      {/* Error indicator */}
      {health?.errorCount > 0 && (
        <div className="absolute -top-2 -right-2 bg-red-500 text-white text-xs font-bold rounded-full w-6 h-6 flex items-center justify-center">
          {health.errorCount > 99 ? '99+' : health.errorCount}
        </div>
      )}
    </div>
  )
}

export const ExternalNode: React.FC<NodeProps> = ({ data }) => {
  const health = data.health as any

  return (
    <div className={clsx(
      'px-4 py-3 shadow-lg rounded-lg bg-white border-2 relative',
      getStatusBorder(data.status || 'unknown'),
      health?.errorCount > 0 && 'border-red-500'
    )}>
      <div className="flex items-center gap-2 mb-2">
        <ExternalLink className="w-4 h-4 text-orange-600" />
        <Circle className={clsx('w-2 h-2 rounded-full', getStatusColor(data.status || 'unknown'))} />
        <span className="font-semibold text-sm">{data.label}</span>
      </div>

      {data.description && (
        <div className="text-xs text-gray-600">{data.description}</div>
      )}

      {/* Error indicator */}
      {health?.errorCount > 0 && (
        <div className="absolute -top-2 -right-2 bg-red-500 text-white text-xs font-bold rounded-full w-6 h-6 flex items-center justify-center">
          {health.errorCount > 99 ? '99+' : health.errorCount}
        </div>
      )}

      <Handle type="source" position={Position.Right} />
    </div>
  )
}

export const nodeTypes = {
  'kafka-topic': KafkaTopicNode,
  'processor': ProcessorNode,
  'database': DatabaseNode,
  'external': ExternalNode,
}
