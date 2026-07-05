import { usePipeline } from '../context/PipelineContext'
import { Trash2, Download } from 'lucide-react'

export default function LogViewer() {
  const { logs, clearLogs } = usePipeline()

  const downloadLogs = () => {
    const blob = new Blob([logs.map(l => `[${l.time}] ${l.level}: ${l.message}`).join('\n')], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `puralens-logs-${new Date().toISOString()}.txt`
    a.click()
  }

  return (
    <div className="glass-panel p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Pipeline Logs</h3>
        <div className="flex gap-2">
          <button onClick={downloadLogs} className="btn-secondary text-sm flex items-center gap-2">
            <Download className="w-4 h-4" />
            Export
          </button>
          <button onClick={clearLogs} className="btn-secondary text-sm flex items-center gap-2">
            <Trash2 className="w-4 h-4" />
            Clear
          </button>
        </div>
      </div>
      <div className="bg-gray-50 rounded-lg p-4 font-mono text-sm h-96 overflow-auto border border-gray-200">
        {logs.map((log, i) => (
          <div key={i} className="py-1 border-b border-gray-200 last:border-0">
            <span className="text-gray-400">[{new Date(log.time).toLocaleTimeString()}]</span>{' '}
            <span className={`${
              log.level === 'error' ? 'text-red-600' :
              log.level === 'warn' ? 'text-amber-600' :
              'text-emerald-600'
            }`}>[{log.level}]</span>{' '}
            <span className="text-gray-700">{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  )
}