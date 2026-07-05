import { CheckCircle2, Trash2, X } from 'lucide-react'

export default function BatchActions({ selectedCount, onClear, onSelectAll, allSelected, onAccept, onReject }) {
  return (
    <div className="glass-panel p-4 flex items-center justify-between animate-slide-in">
      <div className="flex items-center gap-4">
        <button onClick={onSelectAll} className="text-sm text-gray-500 hover:text-gray-900 transition-colors">
          {allSelected ? 'Deselect All' : 'Select All'}
        </button>
        <span className="text-sm text-gray-500">{selectedCount} selected</span>
      </div>
      <div className="flex items-center gap-2">
        <button onClick={onAccept} className="btn-primary flex items-center gap-2 text-sm">
          <CheckCircle2 className="w-4 h-4" />
          Accept Selected
        </button>
        <button onClick={onReject} className="btn-secondary flex items-center gap-2 text-sm text-red-600 border-red-200 hover:bg-red-50">
          <Trash2 className="w-4 h-4" />
          Reject Selected
        </button>
        <button onClick={onClear} className="p-2 text-gray-400 hover:text-gray-700 transition-colors">
          <X className="w-5 h-5" />
        </button>
      </div>
    </div>
  )
}