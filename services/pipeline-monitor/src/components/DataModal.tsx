import React from 'react'
import { X, Send } from 'lucide-react'
import { useSendTestMessage } from '../hooks/useTestProducer'

interface DataModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  data: any
  onViewLogs?: () => void
  isKafkaTopic?: boolean
}

export const DataModal: React.FC<DataModalProps> = ({ isOpen, onClose, title, data, onViewLogs, isKafkaTopic }) => {
  const sendTestMessage = useSendTestMessage()

  const handleSendTestMessage = async () => {
    if (!isKafkaTopic) return

    try {
      await sendTestMessage.mutateAsync({
        topic: title,
        count: 1,
      })
    } catch (error) {
      console.error('Failed to send test message:', error)
    }
  }

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-96 m-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-lg font-semibold">{title}</h3>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 overflow-auto max-h-80">
          {/* Show health status if available */}
          {data?.health && (
            <div className="mb-4 p-3 bg-gray-50 rounded">
              <h4 className="font-semibold mb-2">Health Status</h4>
              <div className="space-y-1 text-sm">
                <div className="flex items-center gap-2">
                  <span className="font-medium">Status:</span>
                  <span className={`font-semibold ${
                    data.health.status === 'healthy' ? 'text-green-600' :
                    data.health.status === 'degraded' ? 'text-yellow-600' : 'text-red-600'
                  }`}>
                    {data.health.status.toUpperCase()}
                  </span>
                </div>
                {data.health.uptime && (
                  <div>
                    <span className="font-medium">Uptime:</span> {Math.floor(data.health.uptime / 1000 / 60)} minutes
                  </div>
                )}
                {data.health.responseTime && (
                  <div>
                    <span className="font-medium">Response Time:</span> {data.health.responseTime}ms
                  </div>
                )}
                {data.health.details && (
                  <div className="mt-2">
                    <span className="font-medium">Details:</span>
                    <div className="ml-4 text-xs">
                      {Object.entries(data.health.details).map(([key, value]) => (
                        <div key={key}>
                          {key}: {value ? '✓' : '✗'}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto">
            {JSON.stringify(data, null, 2)}
          </pre>

          {isKafkaTopic && (
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={handleSendTestMessage}
                disabled={sendTestMessage.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 disabled:bg-gray-400 text-white rounded-md text-sm font-medium transition-colors"
              >
                <Send className="w-4 h-4" />
                {sendTestMessage.isPending ? 'Sending...' : 'Send Test Message'}
              </button>
              {onViewLogs && (
                <button
                  onClick={onViewLogs}
                  className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-md text-sm font-medium transition-colors"
                >
                  View Live Logs
                </button>
              )}
            </div>
          )}

          {sendTestMessage.isSuccess && (
            <div className="mt-2 text-sm text-green-600">
              ✓ Test message sent successfully!
            </div>
          )}

          {sendTestMessage.isError && (
            <div className="mt-2 text-sm text-red-600">
              ✗ Failed to send: {sendTestMessage.error?.message}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
