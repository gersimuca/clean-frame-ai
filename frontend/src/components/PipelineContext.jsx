import { createContext, useContext, useState, useCallback, useEffect } from 'react'

const PipelineContext = createContext(null)

export function PipelineProvider({ children }) {
  const [pipelineState, setPipelineState] = useState({
    isRunning: false,
    progress: 0,
    currentStage: null,
    stats: {
      total: 0,
      pending: 0,
      accepted: 0,
      rejected: 0,
      error: 0,
      corrupt: 0,
      irrelevant: 0,
      badFraming: 0,
    },
    config: {
      relevanceThreshold: 0.30,
      dogConfidence: 0.65,
      minBoxRatio: 0.03,
      maxBoxRatio: 0.95,
      minImageSize: 50,
      numWorkers: 4,
      device: 'cuda',
      corruptEnabled: true,
      relevanceEnabled: true,
      framingEnabled: true,
    },
    logs: [],
    selectedImage: null,
    filter: 'all',
  })

  const [ws, setWs] = useState(null)

  useEffect(() => {
    fetchStats()
    const socket = new WebSocket('ws://localhost:8000/ws/pipeline')

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data)

      if (data.type === 'progress') {
        setPipelineState(prev => ({
          ...prev,
          progress: data.progress,
          currentStage: data.stage,
          stats: { ...prev.stats, ...data.stats },
        }))
      } else if (data.type === 'complete') {
        setPipelineState(prev => ({
          ...prev,
          isRunning: false,
          progress: 100,
          stats: { ...prev.stats, ...data.stats },
        }))
      } else if (data.message) {
        setPipelineState(prev => ({
          ...prev,
          logs: [...prev.logs.slice(-499), {
            time: new Date().toISOString(),
            message: data.message || data.stage || 'Update',
            level: data.level || 'info'
          }],
        }))
      }
    }

    socket.onclose = () => {
      console.log('WebSocket disconnected')
    }

    setWs(socket)
    return () => socket.close()
  }, [])

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/stats')
      const data = await res.json()
      setPipelineState(prev => ({ ...prev, stats: data }))
    } catch (e) {
      console.error('Failed to fetch stats', e)
    }
  }

  const startPipeline = useCallback(async () => {
    setPipelineState(prev => ({ ...prev, isRunning: true, progress: 0 }))

    try {
      const response = await fetch('/api/pipeline/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(pipelineState.config),
      })

      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || 'Failed to start pipeline')
      }
    } catch (error) {
      setPipelineState(prev => ({
        ...prev,
        isRunning: false,
        logs: [...prev.logs, { time: new Date().toISOString(), message: error.message, level: 'error' }],
      }))
    }
  }, [pipelineState.config])

  const stopPipeline = useCallback(async () => {
    try {
      await fetch('/api/pipeline/stop', { method: 'POST' })
      setPipelineState(prev => ({ ...prev, isRunning: false }))
    } catch (error) {
      console.error('Failed to stop pipeline:', error)
    }
  }, [])

  const updateConfig = useCallback((updates) => {
    setPipelineState(prev => ({
      ...prev,
      config: { ...prev.config, ...updates },
    }))
  }, [])

  const setFilter = useCallback((filter) => {
    setPipelineState(prev => ({ ...prev, filter }))
  }, [])

  const selectImage = useCallback((image) => {
    setPipelineState(prev => ({ ...prev, selectedImage: image }))
  }, [])

  const clearLogs = useCallback(() => {
    setPipelineState(prev => ({ ...prev, logs: [] }))
  }, [])

  const value = {
    ...pipelineState,
    startPipeline,
    stopPipeline,
    updateConfig,
    setFilter,
    selectImage,
    clearLogs,
  }

  return (
    <PipelineContext.Provider value={value}>
      {children}
    </PipelineContext.Provider>
  )
}

export const usePipeline = () => {
  const context = useContext(PipelineContext)
  if (!context) throw new Error('usePipeline must be used within PipelineProvider')
  return context
}