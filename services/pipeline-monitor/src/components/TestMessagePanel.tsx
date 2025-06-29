import React, { useState } from 'react'
import { Send, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react'
import { useAvailableTopics, useSendTestMessage, useTopicExample, useTestProducerHealth } from '../hooks/useTestProducer'

interface TestMessagePanelProps {
  selectedTopic?: string
  onTopicChange?: (topic: string) => void
}

export const TestMessagePanel: React.FC<TestMessagePanelProps> = ({ selectedTopic, onTopicChange }) => {
  const [messageCount, setMessageCount] = useState(1)
  const [customPayload, setCustomPayload] = useState('')
  const [useCustom, setUseCustom] = useState(false)

  const { data: topics, isLoading: topicsLoading } = useAvailableTopics()
  const { data: example, isLoading: exampleLoading } = useTopicExample(selectedTopic || '')
  const { data: health } = useTestProducerHealth()
  const sendMessage = useSendTestMessage()

  const isHealthy = health?.status === 'healthy'

  const handleSendMessage = async () => {
    if (!selectedTopic) return

    try {
      let message = undefined

      if (useCustom && customPayload.trim()) {
        try {
          message = JSON.parse(customPayload)
        } catch (e) {
          alert('Invalid JSON in custom payload')
          return
        }
      }

      await sendMessage.mutateAsync({
        topic: selectedTopic,
        count: messageCount,
        message,
      })
    } catch (error) {
      console.error('Failed to send test message:', error)
    }
  }

  const loadExamplePayload = () => {
    if (example?.example_payload) {
      setCustomPayload(JSON.stringify(example.example_payload, null, 2))
      setUseCustom(true)
    }
  }

  if (topicsLoading) {
    return (
      <div className="p-4 border rounded-lg bg-gray-50">
        <div className="flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm">Loading test topics...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 border rounded-lg bg-white shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Send Test Message</h3>
        <div className="flex items-center gap-2 text-sm">
          {isHealthy ? (
            <>
              <CheckCircle2 className="w-4 h-4 text-green-500" />
              <span className="text-green-600">Test Producer Online</span>
            </>
          ) : (
            <>
              <AlertCircle className="w-4 h-4 text-red-500" />
              <span className="text-red-600">Test Producer Offline</span>
            </>
          )}
        </div>
      </div>

      {/* Topic Selection */}
      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Topic</label>
        <select
          value={selectedTopic || ''}
          onChange={(e) => onTopicChange?.(e.target.value)}
          className="w-full p-2 border rounded-md text-sm"
          disabled={!isHealthy}
        >
          <option value="">Select a topic...</option>
          {topics?.categories && Object.entries(topics.categories).map(([category, topicList]) => (
            <optgroup key={category} label={category}>
              {topicList.map(topic => (
                <option key={topic} value={topic}>{topic}</option>
              ))}
            </optgroup>
          ))}
        </select>
      </div>

      {/* Message Count */}
      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Number of Messages</label>
        <input
          type="number"
          min="1"
          max="10"
          value={messageCount}
          onChange={(e) => setMessageCount(parseInt(e.target.value) || 1)}
          className="w-full p-2 border rounded-md text-sm"
          disabled={!isHealthy}
        />
      </div>

      {/* Payload Options */}
      {selectedTopic && (
        <div className="mb-4">
          <div className="flex items-center gap-4 mb-2">
            <label className="flex items-center gap-2">
              <input
                type="radio"
                checked={!useCustom}
                onChange={() => setUseCustom(false)}
                disabled={!isHealthy}
              />
              <span className="text-sm">Use example payload</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="radio"
                checked={useCustom}
                onChange={() => setUseCustom(true)}
                disabled={!isHealthy}
              />
              <span className="text-sm">Custom payload</span>
            </label>
          </div>

          {!useCustom && example && (
            <div className="bg-gray-50 p-3 rounded-md">
              <div className="text-xs text-gray-600 mb-2">
                Example payload ({example.payload_size_bytes} bytes)
              </div>
              <pre className="text-xs overflow-auto max-h-32">
                {JSON.stringify(example.example_payload, null, 2)}
              </pre>
              <button
                onClick={loadExamplePayload}
                className="mt-2 text-xs text-blue-600 hover:text-blue-800"
                disabled={!isHealthy}
              >
                Edit this payload
              </button>
            </div>
          )}

          {useCustom && (
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium">Custom JSON Payload</span>
                {!customPayload && example && (
                  <button
                    onClick={loadExamplePayload}
                    className="text-xs text-blue-600 hover:text-blue-800"
                    disabled={!isHealthy}
                  >
                    Load example
                  </button>
                )}
              </div>
              <textarea
                value={customPayload}
                onChange={(e) => setCustomPayload(e.target.value)}
                placeholder="Enter custom JSON payload..."
                className="w-full h-32 p-2 border rounded-md text-xs font-mono"
                disabled={!isHealthy}
              />
            </div>
          )}

          {exampleLoading && (
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Loading example...</span>
            </div>
          )}
        </div>
      )}

      {/* Send Button */}
      <div className="flex items-center gap-4">
        <button
          onClick={handleSendMessage}
          disabled={!selectedTopic || !isHealthy || sendMessage.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-md text-sm font-medium transition-colors"
        >
          {sendMessage.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
          Send {messageCount > 1 ? `${messageCount} Messages` : 'Message'}
        </button>

        {sendMessage.isSuccess && (
          <div className="flex items-center gap-1 text-green-600 text-sm">
            <CheckCircle2 className="w-4 h-4" />
            <span>Sent successfully!</span>
          </div>
        )}

        {sendMessage.isError && (
          <div className="flex items-center gap-1 text-red-600 text-sm">
            <AlertCircle className="w-4 h-4" />
            <span>Failed: {sendMessage.error?.message}</span>
          </div>
        )}
      </div>
    </div>
  )
}
