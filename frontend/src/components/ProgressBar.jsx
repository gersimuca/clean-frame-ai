export default function ProgressBar({ progress = 0, stage, rate, eta }) {
  const safeProgress = Number.isFinite(progress) ? progress : 0
  return (
    <div className="glass-panel p-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 bg-emerald-500 rounded-full animate-pulse" />
          <span className="font-medium text-gray-900">{stage || 'Processing...'}</span>
        </div>
        <span className="text-2xl font-mono font-bold text-emerald-600">{safeProgress.toFixed(1)}%</span>
      </div>
      <div className="w-full h-4 bg-gray-200 rounded-full overflow-hidden">
        <div className="h-full bg-gradient-to-r from-emerald-600 via-emerald-500 to-emerald-400 rounded-full transition-all duration-500 relative" style={{ width: `${safeProgress}%` }}>
          <div className="absolute inset-0 bg-white/20 animate-pulse" />
        </div>
      </div>
      <div className="flex items-center justify-between mt-3 text-sm text-gray-500">
        <span>{rate} images/sec</span>
        <span>ETA: {eta}</span>
      </div>
    </div>
  )
}