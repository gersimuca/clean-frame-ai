import { createContext, useContext, useState, useCallback, useEffect } from 'react'

const PipelineContext = createContext(null)

const initialStats = {
  total: 0,
  pending: 0,
  accepted: 0,
  rejected: 0,
  error: 0,
  corrupt: 0,
  irrelevant: 0,
  badFraming: 0,
}

export function PipelineProvider({ children }) {
  const [pipelineState, setPipelineState] = useState({
    isRunning: false,
    isStopping: false,
    progress: 0,
    currentStage: null,
    rate: 0,
    etaSeconds: null,
    stats: initialStats,
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
    lastResult: null,
    selectedImage: null,
    filter: 'all',
  })

  const appendLog = useCallback((message, level = 'info') => {
    if (!message) return
    setPipelineState(prev => ({
      ...prev,
      logs: [...prev.logs.slice(-499), {
        time: new Date().toISOString(),
        message,
        level,
      }],
    }))
  }, [])

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch('/api/stats')
      const data = await res.json()
      setPipelineState(prev => ({ ...prev, stats: { ...prev.stats, ...data } }))
    } catch (e) {
      console.error('Failed to fetch stats', e)
    }
  }, [])

  useEffect(() => {
    fetchStats()

    // Server-Sent Events stream of pipeline progress (replaces the old
    // WebSocket, which only ever supported one listener and had no way to
    // sync up a tab that opened mid-run).
    const source = new EventSource('/api/pipeline/stream')

    source.onmessage = (event) => {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'snapshot':
          // Sent immediately on connect so a fresh/refreshed tab reflects
          // the true current state instead of assuming "idle".
          setPipelineState(prev => ({
            ...prev,
            isRunning: data.running,
            progress: data.progress,
            currentStage: data.stage,
            stats: { ...prev.stats, ...data.stats },
          }))
          break

        case 'progress':
          setPipelineState(prev => ({
            ...prev,
            isRunning: true,
            progress: data.progress,
            currentStage: data.stage,
            rate: data.rate ?? prev.rate,
            etaSeconds: data.eta_seconds ?? null,
            stats: { ...prev.stats, ...data.stats },
          }))
          appendLog(data.message, data.level)
          break

        case 'image_result':
          setPipelineState(prev => ({
            ...prev,
            progress: data.progress ?? prev.progress,
            rate: data.rate ?? prev.rate,
            etaSeconds: data.eta_seconds ?? prev.etaSeconds,
            stats: { ...prev.stats, ...data.stats },
            lastResult: data.image ?? prev.lastResult,
          }))
          appendLog(data.message, data.level)
          break

        case 'complete':
          setPipelineState(prev => ({
            ...prev,
            isRunning: false,
            isStopping: false,
            progress: 100,
            rate: 0,
            etaSeconds: null,
            stats: { ...prev.stats, ...data.stats },
          }))
          appendLog(data.message, data.level || 'info')
          break

        case 'error':
          setPipelineState(prev => ({ ...prev, isRunning: false, isStopping: false }))
          appendLog(data.message, 'error')
          break

        default:
          break
      }
    }

    // EventSource reconnects automatically on drop; the snapshot event on
    // reconnect resyncs state, so there's nothing extra to do here.
    source.onerror = () => {}

    return () => source.close()
  }, [appendLog])

  const startPipeline = useCallback(async () => {
    setPipelineState(prev => ({ ...prev, isRunning: true, progress: 0, rate: 0, etaSeconds: null }))

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
      setPipelineState(prev => ({ ...prev, isRunning: false }))
      appendLog(error.message, 'error')
    }
  }, [pipelineState.config, appendLog])

  const stopPipeline = useCallback(async () => {
    setPipelineState(prev => ({ ...prev, isStopping: true }))
    try {
      await fetch('/api/pipeline/stop', { method: 'POST' })
    } catch (error) {
      console.error('Failed to stop pipeline:', error)
      setPipelineState(prev => ({ ...prev, isStopping: false }))
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
    refreshStats: fetchStats,
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
