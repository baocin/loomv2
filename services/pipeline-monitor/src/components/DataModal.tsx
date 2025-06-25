import React from 'react'
import { X } from 'lucide-react'

interface DataModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  data: any
  onViewLogs?: () => void
  isKafkaTopic?: boolean
}

export const DataModal: React.FC<DataModalProps> = ({ isOpen, onClose, title, data, onViewLogs, isKafkaTopic }) => {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-96 m-4">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-lg font-semibold">{title} - Raw Data</h3>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 overflow-auto max-h-80">
          <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto">
            {JSON.stringify(data, null, 2)}
          </pre>

          {isKafkaTopic && onViewLogs && (
            <div className="mt-4 flex justify-end">
              <button
                onClick={onViewLogs}
                className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-md text-sm font-medium transition-colors"
              >
                View Live Logs
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
