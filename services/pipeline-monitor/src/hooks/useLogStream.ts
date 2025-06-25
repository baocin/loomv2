import { useState, useEffect, useRef, useCallback } from 'react'

const WS_URL = (import.meta as any).env.VITE_WS_URL || 'ws://localhost:8082/ws'

export interface LogMessage {
  topic: string
  partition: number
  offset: string
  key: string | null
  value: any
  timestamp: Date
  formattedTimestamp: string
  headers?: any
}

export interface UseLogStreamOptions {
  maxMessages?: number
  autoConnect?: boolean
  fromBeginning?: boolean
}

export const useLogStream = (options: UseLogStreamOptions = {}) => {
  const { maxMessages = 1000, autoConnect = true, fromBeginning = false } = options

  const [messages, setMessages] = useState<LogMessage[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [currentTopic, setCurrentTopic] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const currentTopicRef = useRef<string | null>(null)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    try {
      const ws = new WebSocket(WS_URL)

      ws.onopen = () => {
        console.log('WebSocket connected for log streaming')
        setIsConnected(true)
        setError(null)
        reconnectAttemptsRef.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          switch (data.type) {
            case 'log_message':
              setMessages(prev => {
                const newMessages = [...prev, data.message]
                // Keep only the last maxMessages
                return newMessages.slice(-maxMessages)
              })
              break

            case 'stream_started':
              setIsStreaming(true)
              setCurrentTopic(data.topic)
              currentTopicRef.current = data.topic
              console.log(`Started streaming logs from ${data.topic}`)
              break

            case 'stream_stopped':
              setIsStreaming(false)
              if (currentTopicRef.current === data.topic) {
                currentTopicRef.current = null
              }
              console.log(`Stopped streaming logs from ${data.topic}`)
              break

            case 'error':
              setError(data.message)
              console.error('WebSocket error:', data.message)
              break
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      ws.onerror = (event) => {
        console.error('WebSocket error:', event)
        setError('WebSocket connection error')
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setIsConnected(false)
        setIsStreaming(false)
        wsRef.current = null

        // Attempt to reconnect with exponential backoff
        if (reconnectAttemptsRef.current < 5) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 10000)
          reconnectAttemptsRef.current++

          console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})`)
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, delay)
        }
      }

      wsRef.current = ws
    } catch (err) {
      console.error('Failed to create WebSocket connection:', err)
      setError('Failed to connect to log stream')
    }
  }, [maxMessages])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    setIsConnected(false)
    setIsStreaming(false)
  }, [])

  const startStream = useCallback((topic: string, fromStart = fromBeginning) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('WebSocket not connected')
      return
    }

    // Clear existing messages when starting a new stream
    setMessages([])
    setError(null)
    currentTopicRef.current = topic

    wsRef.current.send(JSON.stringify({
      type: 'stream_logs',
      topic,
      fromBeginning: fromStart
    }))
  }, [fromBeginning])

  const stopStream = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return
    }

    // Use ref to get current topic to avoid dependency issues
    const topic = currentTopicRef.current
    if (topic) {
      wsRef.current.send(JSON.stringify({
        type: 'stop_stream',
        topic: topic
      }))
    }
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  // Auto-connect on mount if enabled
  useEffect(() => {
    if (autoConnect) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [autoConnect, connect, disconnect])

  return {
    messages,
    isConnected,
    isStreaming,
    currentTopic,
    error,
    connect,
    disconnect,
    startStream,
    stopStream,
    clearMessages
  }
}
