import { usePipeline } from '../context/PipelineContext'
import { Activity, CheckCircle2, XCircle, Clock } from 'lucide-react'

export default function StatsPanel() {
  const { stats, isRunning } = usePipeline()

  const items = [
    { label: 'Total', value: stats.total, icon: Activity, color: 'text-blue-500' },
    { label: 'Accepted', value: stats.accepted, icon: CheckCircle2, color: 'text-emerald-600' },
    { label: 'Rejected', value: stats.rejected, icon: XCircle, color: 'text-red-500' },
    { label: 'Pending', value: stats.pending, icon: Clock, color: 'text-amber-600' },
  ]

  return (
    <div className="bg-white border-b border-gray-200 px-6 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-8">
          {items.map((item) => (
            <div key={item.label} className="flex items-center gap-2">
              <item.icon className={`w-4 h-4 ${item.color}`} />
              <span className="text-sm text-gray-500">{item.label}:</span>
              <span className="text-sm font-mono font-bold text-gray-900">{item.value.toLocaleString()}</span>
            </div>
          ))}
        </div>
        {isRunning && (
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
            <span className="text-sm text-emerald-600">Pipeline Active</span>
          </div>
        )}
      </div>
    </div>
  )
}