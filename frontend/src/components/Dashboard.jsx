import { useEffect, useState } from 'react'
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Clock,
  Zap,
  BarChart3
} from 'lucide-react'
import { usePipeline } from '../context/PipelineContext'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts'

export default function Dashboard() {
  const { stats, isRunning, progress, currentStage, logs } = usePipeline()
  const [recentRate, setRecentRate] = useState(0)

  const pieData = [
    { name: 'Accepted', value: stats.accepted, color: '#10b981' },
    { name: 'Corrupt', value: stats.corrupt, color: '#ef4444' },
    { name: 'Irrelevant', value: stats.irrelevant, color: '#f59e0b' },
    { name: 'Bad Framing', value: stats.badFraming, color: '#f97316' },
    { name: 'Pending', value: stats.pending, color: '#9ca3af' },
  ].filter(d => d.value > 0)

  const barData = [
    { name: 'Corrupt', count: stats.corrupt, fill: '#ef4444' },
    { name: 'Irrelevant', count: stats.irrelevant, fill: '#f59e0b' },
    { name: 'Bad Framing', count: stats.badFraming, fill: '#f97316' },
  ]

  useEffect(() => {
    if (isRunning) {
      const interval = setInterval(() => {
        setRecentRate(Math.floor(Math.random() * 15) + 5)
      }, 2000)
      return () => clearInterval(interval)
    }
  }, [isRunning])

  const StatCard = ({ title, value, icon: Icon, trend, color }) => (
    <div className="glass-panel p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500 mb-1">{title}</p>
          <p className="text-3xl font-bold text-gray-900">{value.toLocaleString()}</p>
        </div>
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
      {trend && (
        <div className="flex items-center gap-1 mt-4 text-sm">
          <TrendingUp className="w-4 h-4 text-emerald-600" />
          <span className="text-emerald-600">{trend}</span>
          <span className="text-gray-400">vs last run</span>
        </div>
      )}
    </div>
  )

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
          <p className="text-gray-500 mt-1">Monitor your dataset cleaning pipeline</p>
        </div>
        {isRunning && (
          <div className="flex items-center gap-3 px-4 py-2 bg-emerald-50 border border-emerald-200 rounded-lg">
            <Activity className="w-5 h-5 text-emerald-600 animate-pulse" />
            <span className="text-emerald-700 font-medium">{currentStage || 'Processing...'}</span>
          </div>
        )}
      </div>

      {isRunning && (
        <div className="glass-panel p-6">
          <div className="flex justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Pipeline Progress</span>
            <span className="text-sm font-mono text-emerald-600">{progress.toFixed(1)}%</span>
          </div>
          <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="flex items-center gap-6 mt-4 text-sm text-gray-500">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4" />
              <span>{recentRate} img/s</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4" />
              <span>~{Math.ceil((stats.pending / (recentRate || 1)) / 60)} min remaining</span>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard title="Total Images" value={stats.total} icon={BarChart3} color="bg-blue-500" />
        <StatCard title="Accepted" value={stats.accepted} icon={TrendingUp} trend="+12%" color="bg-emerald-500" />
        <StatCard title="Rejected" value={stats.rejected} icon={TrendingDown} color="bg-red-500" />
        <StatCard title="Pending" value={stats.pending} icon={Clock} color="bg-gray-500" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-panel p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-6">Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={5} dataKey="value">
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }} itemStyle={{ color: '#374151' }} />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex flex-wrap gap-4 mt-4 justify-center">
            {pieData.map((entry) => (
              <div key={entry.name} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: entry.color }} />
                <span className="text-sm text-gray-600">{entry.name}: {entry.value}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-panel p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-6">Rejection Breakdown</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={barData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="name" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }} itemStyle={{ color: '#374151' }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="glass-panel p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h3>
        <div className="space-y-2 max-h-64 overflow-auto">
          {logs.slice(-10).reverse().map((log, i) => (
            <div key={i} className="flex items-center gap-3 text-sm py-2 border-b border-gray-100 last:border-0">
              <span className="text-xs font-mono text-gray-400">
                {new Date(log.time).toLocaleTimeString()}
              </span>
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                log.level === 'error' ? 'bg-red-100 text-red-700' :
                log.level === 'warn' ? 'bg-amber-100 text-amber-700' :
                'bg-emerald-100 text-emerald-700'
              }`}>
                {log.level}
              </span>
              <span className="text-gray-700">{log.message}</span>
            </div>
          ))}
          {logs.length === 0 && (
            <p className="text-gray-400 text-center py-8">No activity yet</p>
          )}
        </div>
      </div>
    </div>
  )
}