import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import {
  X,
  ChevronLeft,
  ChevronRight,
  RotateCcw,
  CheckCircle2,
  Trash2,
  Download,
  Info,
  AlertTriangle
} from 'lucide-react'
import { fetchImagesForStatus } from '../lib/images'

export default function ReviewModal() {
  const { status, id } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const [image, setImage] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showInfo, setShowInfo] = useState(false)
  const [siblingIds, setSiblingIds] = useState(location.state?.ids || null)

  useEffect(() => {
    fetchImage()
  }, [id])

  // Sibling id list powers prev/next. ImageGrid passes it via router state so
  // there's no extra round-trip in the common case; if it's missing (direct
  // link, refresh, or the state got lost on navigation) we fetch it once so
  // prev/next still work instead of silently doing nothing.
  useEffect(() => {
    if (location.state?.ids) {
      setSiblingIds(location.state.ids)
      return
    }
    let cancelled = false
    fetchImagesForStatus(status)
      .then(data => {
        if (!cancelled) setSiblingIds((data.images || []).map(img => img.id))
      })
      .catch(() => {
        if (!cancelled) setSiblingIds([])
      })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status])

  const fetchImage = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/images/${id}`)
      const data = await response.json()
      setImage(data)
    } catch (error) {
      console.error('Failed to fetch image:', error)
    } finally {
      setLoading(false)
    }
  }

  const currentIndex = siblingIds ? siblingIds.findIndex(sid => String(sid) === String(id)) : -1
  const prevId = currentIndex > 0 ? siblingIds[currentIndex - 1] : null
  const nextId = siblingIds && currentIndex >= 0 && currentIndex < siblingIds.length - 1
    ? siblingIds[currentIndex + 1]
    : null

  const goTo = useCallback((targetId) => {
    if (targetId == null) return
    navigate(`/review/${status}/${targetId}`, { state: { ids: siblingIds } })
  }, [navigate, status, siblingIds])

  useEffect(() => {
    const handleKeydown = (e) => {
      if (e.key === 'ArrowLeft') goTo(prevId)
      else if (e.key === 'ArrowRight') goTo(nextId)
      else if (e.key === 'Escape') navigate(`/review/${status}`)
    }
    window.addEventListener('keydown', handleKeydown)
    return () => window.removeEventListener('keydown', handleKeydown)
  }, [goTo, prevId, nextId, navigate, status])

  const handleAction = async (action) => {
    try {
      await fetch(`/api/images/${id}/${action}`, { method: 'POST' })
      navigate(`/review/${status}`)
    } catch (error) {
      console.error('Action failed:', error)
    }
  }

  const handleDelete = async () => {
    if (!confirm('Permanently delete this image from database?')) return
    try {
      await fetch(`/api/images/${id}`, { method: 'DELETE' })
      navigate(`/review/${status}`)
    } catch (error) {
      console.error('Delete failed:', error)
    }
  }

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50">
        <div className="animate-spin w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  if (!image) return null

  const isInvalid = image.status === 'rejected' || image.status === 'error'
  const hasScore = typeof image.score === 'number'
  const hasDetections = Array.isArray(image.detections) && image.detections.length > 0

  return (
    <div className="fixed inset-0 bg-black/95 z-50 flex animate-fade-in">
      <div className="flex-1 flex items-center justify-center relative">
        <button onClick={() => navigate(`/review/${status}`)} className="absolute top-4 right-4 w-10 h-10 bg-gray-800/80 rounded-full flex items-center justify-center text-white hover:bg-gray-700 transition-colors z-10">
          <X className="w-5 h-5" />
        </button>
        <button
          onClick={() => goTo(prevId)}
          disabled={!prevId}
          className="absolute left-4 top-1/2 -translate-y-1/2 w-12 h-12 bg-gray-800/80 rounded-full flex items-center justify-center text-white hover:bg-gray-700 transition-colors disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-gray-800/80"
        >
          <ChevronLeft className="w-6 h-6" />
        </button>
        <button
          onClick={() => goTo(nextId)}
          disabled={!nextId}
          className="absolute right-4 top-1/2 -translate-y-1/2 w-12 h-12 bg-gray-800/80 rounded-full flex items-center justify-center text-white hover:bg-gray-700 transition-colors disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-gray-800/80"
        >
          <ChevronRight className="w-6 h-6" />
        </button>

        <img src={image.url} alt={image.filename} className="max-w-full max-h-full object-contain" />

        {hasDetections && (
          <svg className="absolute inset-0 pointer-events-none" viewBox={`0 0 ${image.width || 1000} ${image.height || 1000}`} preserveAspectRatio="xMidYMid meet">
            {image.detections.map((det, i) => (
              <rect key={i} x={det.x1} y={det.y1} width={det.x2 - det.x1} height={det.y2 - det.y1} fill="none" stroke="#10b981" strokeWidth="3" rx="4" />
            ))}
          </svg>
        )}
      </div>

      <div className="w-80 bg-white border-l border-gray-200 flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center gap-2 mb-1">
            {isInvalid && <AlertTriangle className="w-5 h-5 text-red-500" />}
            <h3 className="text-lg font-semibold text-gray-900 truncate">{image.filename}</h3>
          </div>
          <p className="text-sm text-gray-500">{image.fileSize} • {image.dimensions}</p>
          <span className={`inline-block mt-2 text-xs px-2 py-1 rounded-full font-medium ${
            image.status === 'accepted' ? 'bg-emerald-100 text-emerald-700' :
            image.status === 'rejected' ? 'bg-red-100 text-red-700' :
            'bg-gray-100 text-gray-700'
          }`}>
            {image.status?.toUpperCase()}
          </span>
        </div>

        <div className="flex-1 overflow-auto p-6 space-y-6">
          {image.reason && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm font-medium text-red-700 mb-1 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                Rejection Reason
              </p>
              <p className="text-sm text-red-800 font-mono">{image.reason}</p>
            </div>
          )}

          {hasScore && (
            <div>
              <p className="text-sm font-medium text-gray-600 mb-2">Quality Score</p>
              <div className="flex items-center gap-3">
                <div className="flex-1 h-3 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${Math.max(0, Math.min(100, image.score * 100))}%` }} />
                </div>
                <span className="text-lg font-mono font-bold text-emerald-600">{image.score.toFixed(3)}</span>
              </div>
            </div>
          )}

          <div>
            <button onClick={() => setShowInfo(!showInfo)} className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 transition-colors">
              <Info className="w-4 h-4" />
              <span>Metadata</span>
            </button>
            {showInfo && (
              <div className="mt-3 space-y-2 text-sm">
                {Object.entries(image.metadata || {}).map(([key, value]) => (
                  <div key={key} className="flex justify-between py-1 border-b border-gray-100">
                    <span className="text-gray-500">{key}</span>
                    <span className="text-gray-700 font-mono">{String(value)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {hasDetections && (
            <div>
              <p className="text-sm font-medium text-gray-600 mb-3">Detected Objects</p>
              <div className="space-y-2">
                {image.detections.map((det, i) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-emerald-500 rounded-full" />
                      <span className="text-sm text-gray-700">{det.label}</span>
                    </div>
                    <span className="text-xs font-mono text-emerald-600">{(det.confidence * 100).toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="p-6 border-t border-gray-200 space-y-3">
          {image.status !== 'accepted' && (
            <button onClick={() => handleAction('accept')} className="w-full btn-primary flex items-center justify-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              Accept Image
            </button>
          )}
          {image.status === 'accepted' && (
            <button onClick={() => handleAction('reject')} className="w-full btn-secondary flex items-center justify-center gap-2 text-red-600 border-red-200 hover:bg-red-50">
              <Trash2 className="w-4 h-4" />
              Move to Rejected
            </button>
          )}
          <button onClick={() => handleAction('reprocess')} className="w-full btn-secondary flex items-center justify-center gap-2">
            <RotateCcw className="w-4 h-4" />
            Reprocess
          </button>
          <a href={image.url} download={image.filename} className="w-full btn-secondary flex items-center justify-center gap-2">
            <Download className="w-4 h-4" />
            Download Original
          </a>
          <button onClick={handleDelete} className="w-full py-2 text-red-500 hover:text-red-700 text-sm font-medium transition-colors">
            Permanently Delete
          </button>
        </div>
      </div>
    </div>
  )
}
