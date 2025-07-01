import React from 'react'
import { useReactFlow } from 'reactflow'

export function ZoomControls() {
  const { zoomIn, zoomOut, fitView, getZoom } = useReactFlow()
  const [zoomLevel, setZoomLevel] = React.useState(100)

  React.useEffect(() => {
    const updateZoomLevel = () => {
      const currentZoom = getZoom()
      setZoomLevel(Math.round(currentZoom * 100))
    }

    // Update zoom level on mount
    updateZoomLevel()

    // Listen for zoom changes
    const handleWheel = () => updateZoomLevel()
    window.addEventListener('wheel', handleWheel)
    
    return () => window.removeEventListener('wheel', handleWheel)
  }, [getZoom])

  const handleZoomIn = () => {
    zoomIn()
    setTimeout(() => setZoomLevel(Math.round(getZoom() * 100)), 100)
  }

  const handleZoomOut = () => {
    zoomOut()
    setTimeout(() => setZoomLevel(Math.round(getZoom() * 100)), 100)
  }

  const handleFitView = () => {
    fitView({ padding: 0.2, duration: 800 })
    setTimeout(() => setZoomLevel(Math.round(getZoom() * 100)), 900)
  }

  const setZoomTo = (level: number) => {
    const { setViewport, getViewport } = useReactFlow()
    const viewport = getViewport()
    setViewport({ ...viewport, zoom: level / 100 })
    setZoomLevel(level)
  }

  return (
    <div className="absolute bottom-4 left-4 z-10 bg-white rounded-lg shadow-lg p-2 flex items-center gap-2">
      <button
        onClick={handleZoomOut}
        className="p-2 hover:bg-gray-100 rounded transition-colors"
        title="Zoom Out"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
        </svg>
      </button>
      
      <div className="flex items-center gap-1 px-2">
        <span className="text-sm font-medium min-w-[50px] text-center">{zoomLevel}%</span>
      </div>
      
      <button
        onClick={handleZoomIn}
        className="p-2 hover:bg-gray-100 rounded transition-colors"
        title="Zoom In"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
        </svg>
      </button>

      <div className="border-l mx-1 h-6"></div>

      <button
        onClick={handleFitView}
        className="p-2 hover:bg-gray-100 rounded transition-colors"
        title="Fit to View"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
        </svg>
      </button>

      <div className="border-l mx-1 h-6"></div>

      {/* Quick zoom presets */}
      <button
        onClick={() => setZoomTo(5)}
        className="px-2 py-1 text-xs hover:bg-gray-100 rounded transition-colors"
        title="5% - Maximum zoom out"
      >
        5%
      </button>
      <button
        onClick={() => setZoomTo(25)}
        className="px-2 py-1 text-xs hover:bg-gray-100 rounded transition-colors"
        title="25% - Overview"
      >
        25%
      </button>
      <button
        onClick={() => setZoomTo(50)}
        className="px-2 py-1 text-xs hover:bg-gray-100 rounded transition-colors"
        title="50% - Half size"
      >
        50%
      </button>
      <button
        onClick={() => setZoomTo(100)}
        className="px-2 py-1 text-xs hover:bg-gray-100 rounded transition-colors"
        title="100% - Default"
      >
        100%
      </button>
      <button
        onClick={() => setZoomTo(150)}
        className="px-2 py-1 text-xs hover:bg-gray-100 rounded transition-colors"
        title="150% - Detailed view"
      >
        150%
      </button>
    </div>
  )
}