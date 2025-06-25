import React, { useEffect, useRef, useState } from 'react'
import { useLogStream } from '../hooks/useLogStream'

interface LogViewerProps {
  topic: string | null
  onClose: () => void
}

export const LogViewer: React.FC<LogViewerProps> = ({ topic, onClose }) => {
  const {
    messages,
    isConnected,
    isStreaming,
    error,
    startStream,
    stopStream,
    clearMessages
  } = useLogStream()

  const [autoScroll, setAutoScroll] = useState(true)
  const [filter, setFilter] = useState('')
  const [showJson, setShowJson] = useState(true)
  const logContainerRef = useRef<HTMLDivElement>(null)

  // Start streaming when topic changes
  useEffect(() => {
    if (topic && isConnected) {
      startStream(topic)
    }

    return () => {
      if (isStreaming) {
        stopStream()
      }
    }
  }, [topic, isConnected, startStream, stopStream, isStreaming])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [messages, autoScroll])

  // Filter messages
  const filteredMessages = messages.filter(msg => {
    if (!filter) return true
    const msgStr = JSON.stringify(msg).toLowerCase()
    return msgStr.includes(filter.toLowerCase())
  })

  const formatMessage = (msg: any) => {
    if (!showJson) {
      return msg.value?.text || msg.value?.message || JSON.stringify(msg.value)
    }
    return JSON.stringify(msg.value, null, 2)
  }

  if (!topic) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl h-[80vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold">Log Stream: {topic}</h2>
              <div className="flex items-center gap-4 mt-1 text-sm">
                <span className={`flex items-center gap-1 ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
                  <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
                <span className={`flex items-center gap-1 ${isStreaming ? 'text-blue-600' : 'text-gray-600'}`}>
                  <div className={`w-2 h-2 rounded-full ${isStreaming ? 'bg-blue-500 animate-pulse' : 'bg-gray-500'}`} />
                  {isStreaming ? 'Streaming' : 'Stopped'}
                </span>
                <span className="text-gray-600">
                  {filteredMessages.length} messages
                </span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Controls */}
        <div className="px-6 py-3 border-b border-gray-200 flex items-center gap-4">
          <input
            type="text"
            placeholder="Filter messages..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm">Auto-scroll</span>
          </label>

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={showJson}
              onChange={(e) => setShowJson(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm">JSON format</span>
          </label>

          <button
            onClick={clearMessages}
            className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-md text-sm"
          >
            Clear
          </button>

          {isStreaming ? (
            <button
              onClick={stopStream}
              className="px-3 py-1.5 bg-red-500 hover:bg-red-600 text-white rounded-md text-sm"
            >
              Stop
            </button>
          ) : (
            <button
              onClick={() => topic && startStream(topic)}
              className="px-3 py-1.5 bg-green-500 hover:bg-green-600 text-white rounded-md text-sm"
            >
              Start
            </button>
          )}
        </div>

        {/* Error message */}
        {error && (
          <div className="px-6 py-3 bg-red-50 border-b border-red-200">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {/* Log container */}
        <div
          ref={logContainerRef}
          className="flex-1 overflow-y-auto bg-gray-900 text-gray-100 font-mono text-xs p-4"
        >
          {filteredMessages.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              {isStreaming ? 'Waiting for messages...' : 'No messages to display'}
            </div>
          ) : (
            <div className="space-y-2">
              {filteredMessages.map((msg, idx) => (
                <div key={idx} className="border-b border-gray-800 pb-2">
                  <div className="flex items-start gap-4 text-gray-400 mb-1">
                    <span className="text-blue-400">[{msg.formattedTimestamp}]</span>
                    <span className="text-green-400">Partition: {msg.partition}</span>
                    <span className="text-yellow-400">Offset: {msg.offset}</span>
                    {msg.key && <span className="text-purple-400">Key: {msg.key}</span>}
                  </div>
                  <pre className="text-gray-100 whitespace-pre-wrap break-all">
                    {formatMessage(msg)}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
