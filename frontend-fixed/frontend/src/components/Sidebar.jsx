import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  PlayCircle,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Image as ImageIcon,
  Database,
  Upload
} from 'lucide-react'
import { usePipeline } from '../context/PipelineContext'

export default function Sidebar() {
  const { stats, isRunning } = usePipeline()

  const navItems = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/upload', icon: Upload, label: 'Upload Photos' },
    { to: '/pipeline', icon: PlayCircle, label: 'Pipeline' },
    { to: '/review/accepted', icon: CheckCircle2, label: 'Accepted', count: stats.accepted, color: 'text-emerald-600' },
    { to: '/review/invalid', icon: AlertTriangle, label: 'All Invalid', count: stats.rejected + stats.error, color: 'text-red-600' },
    { to: '/review/corrupt', icon: AlertTriangle, label: 'Corrupt', count: stats.corrupt, color: 'text-red-500' },
    { to: '/review/irrelevant', icon: XCircle, label: 'Irrelevant', count: stats.irrelevant, color: 'text-amber-600' },
    { to: '/review/bad-framing', icon: ImageIcon, label: 'Bad Framing', count: stats.badFraming, color: 'text-orange-600' },
  ]

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-emerald-600 rounded-xl flex items-center justify-center">
            <Database className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-lg text-gray-900">PuraLens</h1>
            <p className="text-xs text-gray-500">Dataset Cleaner</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                isActive
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`
            }
          >
            <item.icon className={`w-5 h-5 ${item.color || ''}`} />
            <span className="flex-1">{item.label}</span>
            {item.count > 0 && (
              <span className={`text-xs font-mono px-2 py-0.5 rounded-full bg-gray-100 ${item.color || 'text-gray-500'}`}>
                {item.count.toLocaleString()}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-gray-200">
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 mb-2">
            <div className={`w-2 h-2 rounded-full ${isRunning ? 'bg-emerald-500 animate-pulse' : 'bg-gray-400'}`} />
            <span className="text-sm font-medium text-gray-700">
              {isRunning ? 'Processing...' : 'Idle'}
            </span>
          </div>
          <div className="text-xs text-gray-500">
            {stats.total > 0 ? `${stats.accepted} / ${stats.total} accepted` : 'No images loaded'}
          </div>
        </div>
      </div>
    </aside>
  )
}