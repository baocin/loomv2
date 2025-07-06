import React, { useEffect, useState, useRef } from 'react'
import { Terminal, X, Download, Search } from 'lucide-react'

interface ConsumerLogViewerProps {
  serviceName: string
  onClose: () => void
}

export const ConsumerLogViewer: React.FC<ConsumerLogViewerProps> = ({ serviceName, onClose }) => {
  const [logs, setLogs] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState('')
  const [autoScroll, setAutoScroll] = useState(true)
  const [lineCount, setLineCount] = useState(500)
  const logContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchLogs()
  }, [serviceName, lineCount])

  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [logs, autoScroll])

  const fetchLogs = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch(`/api/consumers/${serviceName}/logs?lines=${lineCount}`)
      if (!response.ok) {
        throw new Error(`Failed to fetch logs: ${response.statusText}`)
      }

      const data = await response.json()
      setLogs(data.logs || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch logs')
    } finally {
      setLoading(false)
    }
  }

  const filteredLogs = logs.filter(log => {
    if (!filter) return true
    return log.toLowerCase().includes(filter.toLowerCase())
  })

  const downloadLogs = () => {
    const content = filteredLogs.join('\n')
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${serviceName}-logs-${new Date().toISOString()}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const getLogLevel = (log: string): string => {
    if (log.includes('ERROR') || log.includes('error')) return 'text-red-400'
    if (log.includes('WARN') || log.includes('warning')) return 'text-yellow-400'
    if (log.includes('INFO') || log.includes('info')) return 'text-blue-400'
    if (log.includes('DEBUG') || log.includes('debug')) return 'text-gray-400'
    return 'text-gray-300'
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-gray-900 rounded-lg shadow-2xl w-full max-w-7xl h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-700 bg-gray-800">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Terminal className="w-5 h-5 text-green-400" />
              <h2 className="text-xl font-semibold text-white">Consumer Logs: {serviceName}</h2>
              <span className="text-sm text-gray-400">
                ({filteredLogs.length} / {logs.length} lines)
              </span>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Controls */}
        <div className="px-6 py-3 border-b border-gray-700 bg-gray-800 flex items-center gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Filter logs..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="w-full pl-10 pr-3 py-2 bg-gray-700 text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <select
            value={lineCount}
            onChange={(e) => setLineCount(Number(e.target.value))}
            className="px-3 py-2 bg-gray-700 text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value={100}>Last 100 lines</option>
            <option value={500}>Last 500 lines</option>
            <option value={1000}>Last 1000 lines</option>
            <option value={5000}>Last 5000 lines</option>
          </select>

          <label className="flex items-center gap-2 text-sm text-gray-300">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="rounded text-blue-500 focus:ring-blue-500"
            />
            Auto-scroll
          </label>

          <button
            onClick={fetchLogs}
            className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm transition-colors"
          >
            Refresh
          </button>

          <button
            onClick={downloadLogs}
            className="px-3 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-md text-sm transition-colors flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Download
          </button>
        </div>

        {/* Error message */}
        {error && (
          <div className="px-6 py-3 bg-red-900/50 border-b border-red-700">
            <p className="text-sm text-red-300">{error}</p>
          </div>
        )}

        {/* Log container */}
        <div
          ref={logContainerRef}
          className="flex-1 overflow-y-auto bg-black font-mono text-xs p-4"
        >
          {loading ? (
            <div className="text-center text-gray-500 py-8">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-500"></div>
              <p className="mt-2">Loading logs...</p>
            </div>
          ) : filteredLogs.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              {filter ? 'No logs match your filter' : 'No logs available'}
            </div>
          ) : (
            <div className="space-y-0.5">
              {filteredLogs.map((log, idx) => (
                <div key={idx} className={`${getLogLevel(log)} break-all hover:bg-gray-900/50 px-2 py-0.5 rounded`}>
                  {log}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-gray-700 bg-gray-800 text-xs text-gray-400">
          <div className="flex items-center justify-between">
            <div>
              Tip: Use Ctrl+F to search within logs
            </div>
            <div>
              Last refreshed: {new Date().toLocaleTimeString()}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
