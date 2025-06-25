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

  return (
    <div className={clsx(
      'px-4 py-3 shadow-lg rounded-lg bg-white border-2',
      getStatusBorder(data.status)
    )}>
      <Handle type="target" position={Position.Left} />

      <div className="flex items-center gap-2 mb-2">
        <MessageSquare className="w-4 h-4 text-blue-600" />
        <Circle className={clsx('w-2 h-2 rounded-full', getStatusColor(data.status))} />
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

      <Handle type="source" position={Position.Right} />
    </div>
  )
}

export const ProcessorNode: React.FC<NodeProps> = ({ data }) => {
  const metrics = data.metrics as any

  return (
    <div className={clsx(
      'px-4 py-3 shadow-lg rounded-lg bg-white border-2',
      getStatusBorder(data.status)
    )}>
      <Handle type="target" position={Position.Left} />

      <div className="flex items-center gap-2 mb-2">
        <Cpu className="w-4 h-4 text-purple-600" />
        <Circle className={clsx('w-2 h-2 rounded-full', getStatusColor(data.status))} />
        <span className="font-semibold text-sm">{data.label}</span>
      </div>

      {data.description && (
        <div className="text-xs text-gray-600 mb-2">{data.description}</div>
      )}

      {metrics && (
        <div className="text-xs text-gray-600 space-y-1">
          {metrics.lastHeartbeat && (
            <div>Heartbeat: {formatDistanceToNow(new Date(metrics.lastHeartbeat), { addSuffix: true })}</div>
          )}
          {metrics.consumerId && (
            <div>Consumer: {metrics.consumerId.slice(0, 8)}...</div>
          )}
        </div>
      )}

      <Handle type="source" position={Position.Right} />
    </div>
  )
}

export const DatabaseNode: React.FC<NodeProps> = ({ data }) => {
  return (
    <div className={clsx(
      'px-4 py-3 shadow-lg rounded-lg bg-white border-2',
      getStatusBorder(data.status)
    )}>
      <Handle type="target" position={Position.Left} />

      <div className="flex items-center gap-2 mb-2">
        <Database className="w-4 h-4 text-green-600" />
        <Circle className={clsx('w-2 h-2 rounded-full', getStatusColor(data.status))} />
        <span className="font-semibold text-sm">{data.label}</span>
      </div>

      {data.description && (
        <div className="text-xs text-gray-600">{data.description}</div>
      )}
    </div>
  )
}

export const ExternalNode: React.FC<NodeProps> = ({ data }) => {
  return (
    <div className={clsx(
      'px-4 py-3 shadow-lg rounded-lg bg-white border-2',
      getStatusBorder(data.status)
    )}>
      <div className="flex items-center gap-2 mb-2">
        <ExternalLink className="w-4 h-4 text-orange-600" />
        <Circle className={clsx('w-2 h-2 rounded-full', getStatusColor(data.status))} />
        <span className="font-semibold text-sm">{data.label}</span>
      </div>

      {data.description && (
        <div className="text-xs text-gray-600">{data.description}</div>
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
