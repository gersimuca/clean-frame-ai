import { Check, Maximize2, AlertTriangle } from 'lucide-react'

export default function ImageCard({ image, viewMode, isSelected, onToggle, onClick }) {
  const isInvalid = image.status === 'rejected' || image.status === 'error'

  if (viewMode === 'list') {
    return (
      <div
        className={`flex items-center gap-4 p-3 rounded-lg border transition-all cursor-pointer ${
          isSelected ? 'bg-emerald-50 border-emerald-200' : isInvalid ? 'bg-red-50 border-red-200' : 'bg-white border-gray-200 hover:border-gray-300'
        }`}
      >
        <button onClick={(e) => { e.stopPropagation(); onToggle() }} className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${isSelected ? 'bg-emerald-600 border-emerald-600' : 'border-gray-300'}`}>
          {isSelected && <Check className="w-3 h-3 text-white" />}
        </button>
        <div className="w-16 h-16 bg-gray-100 rounded-lg overflow-hidden flex-shrink-0 relative">
          <img src={image.thumbnailUrl || image.url} alt={image.filename} className="w-full h-full object-cover" loading="lazy" />
          {isInvalid && (
            <div className="absolute inset-0 bg-red-500/20 flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-red-600" />
            </div>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-800 truncate">{image.filename}</p>
          <p className="text-xs text-gray-500 mt-1">{image.dimensions} • {image.fileSize}</p>
          {image.reason && (
            <p className="text-xs text-red-600 mt-1 truncate">{image.reason}</p>
          )}
        </div>
        <div className="text-right">
          {image.score !== undefined && (
            <span className={`text-xs font-mono px-2 py-1 rounded ${
              image.score > 0.7 ? 'bg-emerald-100 text-emerald-700' :
              image.score > 0.4 ? 'bg-amber-100 text-amber-700' :
              'bg-red-100 text-red-700'
            }`}>
              {image.score.toFixed(3)}
            </span>
          )}
          <p className={`text-xs mt-1 font-medium ${isInvalid ? 'text-red-600' : 'text-gray-400'}`}>
            {image.status}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div
      className={`group relative rounded-xl overflow-hidden border transition-all cursor-pointer ${
        isSelected ? 'ring-2 ring-emerald-500 ring-offset-2 ring-offset-white' : 
        isInvalid ? 'ring-2 ring-red-400 ring-offset-2 ring-offset-white' :
        'border-gray-200 hover:border-gray-300'
      }`}
      onClick={onClick}
    >
      <div className="aspect-square bg-gray-100 relative">
        <img src={image.thumbnailUrl || image.url} alt={image.filename} className="w-full h-full object-cover transition-transform group-hover:scale-105" loading="lazy" />
        {isInvalid && (
          <div className="absolute inset-0 bg-red-500/10 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
            <div className="bg-red-600 text-white px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              {image.reason || 'Invalid'}
            </div>
          </div>
        )}
      </div>
      <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
        <div className="absolute bottom-0 left-0 right-0 p-3">
          <p className="text-sm font-medium text-white truncate">{image.filename}</p>
          {image.score !== undefined && <p className="text-xs text-emerald-300 mt-1">Score: {image.score.toFixed(3)}</p>}
          {image.reason && <p className="text-xs text-red-300 mt-1 truncate">{image.reason}</p>}
        </div>
        <button onClick={(e) => { e.stopPropagation(); onToggle() }} className={`absolute top-3 right-3 w-8 h-8 rounded-full flex items-center justify-center transition-colors ${isSelected ? 'bg-emerald-600 text-white' : 'bg-black/50 text-white hover:bg-black/70'}`}>
          {isSelected ? <Check className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
        </button>
      </div>
      {isSelected && (
        <div className="absolute top-3 left-3 w-6 h-6 bg-emerald-600 rounded-full flex items-center justify-center">
          <Check className="w-4 h-4 text-white" />
        </div>
      )}
      {isInvalid && !isSelected && (
        <div className="absolute top-3 left-3 w-6 h-6 bg-red-500 rounded-full flex items-center justify-center">
          <AlertTriangle className="w-4 h-4 text-white" />
        </div>
      )}
    </div>
  )
}