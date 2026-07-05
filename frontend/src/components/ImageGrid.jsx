import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Grid,
  List,
  Search,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ImageIcon,
  Skull
} from 'lucide-react'
import ImageCard from './ImageCard'
import BatchActions from './BatchActions'

const STATUS_CONFIG = {
  accepted: { icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50', label: 'Accepted' },
  invalid: { icon: Skull, color: 'text-red-700', bg: 'bg-red-50', label: 'All Invalid / Corrupt' },
  corrupt: { icon: AlertTriangle, color: 'text-red-600', bg: 'bg-red-50', label: 'Corrupt Files' },
  irrelevant: { icon: XCircle, color: 'text-amber-600', bg: 'bg-amber-50', label: 'Irrelevant Content' },
  'bad-framing': { icon: ImageIcon, color: 'text-orange-600', bg: 'bg-orange-50', label: 'Bad Framing' },
}

export default function ImageGrid() {
  const { status } = useParams()
  const navigate = useNavigate()
  const [images, setImages] = useState([])
  const [viewMode, setViewMode] = useState('grid')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedImages, setSelectedImages] = useState(new Set())
  const [loading, setLoading] = useState(true)

  const config = STATUS_CONFIG[status] || STATUS_CONFIG.accepted

  useEffect(() => {
    fetchImages()
  }, [status])

  const fetchImages = async () => {
    setLoading(true)
    try {
      const endpoint = status === 'invalid' ? '/api/images/invalid' : `/api/images?status=${status}&limit=200`
      const response = await fetch(endpoint)
      const data = await response.json()
      setImages(data.images || [])
    } catch (error) {
      console.error('Failed to fetch images:', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleSelection = (id) => {
    setSelectedImages(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const selectAll = () => {
    if (selectedImages.size === images.length) {
      setSelectedImages(new Set())
    } else {
      setSelectedImages(new Set(images.map(img => img.id)))
    }
  }

  const handleBatchAction = async (action) => {
    const ids = Array.from(selectedImages)
    try {
      await Promise.all(ids.map(id => fetch(`/api/images/${id}/${action}`, { method: 'POST' })))
      setSelectedImages(new Set())
      fetchImages()
    } catch (e) {
      console.error('Batch action failed', e)
    }
  }

  const filteredImages = images.filter(img =>
    img.filename?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    img.reason?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${config.bg}`}>
            <config.icon className={`w-6 h-6 ${config.color}`} />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900">{config.label}</h2>
            <p className="text-gray-500 text-sm">{filteredImages.length} images</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input type="text" placeholder="Search by name or reason..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="input-field pl-10 w-72" />
          </div>
          <div className="flex bg-white border border-gray-200 rounded-lg p-1">
            <button onClick={() => setViewMode('grid')} className={`p-2 rounded ${viewMode === 'grid' ? 'bg-gray-100 text-gray-900' : 'text-gray-400 hover:text-gray-700'}`}>
              <Grid className="w-4 h-4" />
            </button>
            <button onClick={() => setViewMode('list')} className={`p-2 rounded ${viewMode === 'list' ? 'bg-gray-100 text-gray-900' : 'text-gray-400 hover:text-gray-700'}`}>
              <List className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {selectedImages.size > 0 && (
        <BatchActions
          selectedCount={selectedImages.size}
          onClear={() => setSelectedImages(new Set())}
          onSelectAll={selectAll}
          allSelected={selectedImages.size === images.length}
          onAccept={() => handleBatchAction('accept')}
          onReject={() => handleBatchAction('reject')}
        />
      )}

      {loading ? (
        <div className="flex items-center justify-center h-96">
          <div className="animate-spin w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full" />
        </div>
      ) : filteredImages.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-96 text-gray-400">
          <config.icon className="w-16 h-16 mb-4 opacity-30" />
          <p className="text-lg">No images found</p>
        </div>
      ) : (
        <div className={viewMode === 'grid' ? 'grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4' : 'space-y-2'}>
          {filteredImages.map((image) => (
            <ImageCard
              key={image.id}
              image={image}
              viewMode={viewMode}
              isSelected={selectedImages.has(image.id)}
              onToggle={() => toggleSelection(image.id)}
              onClick={() => navigate(`/review/${status}/${image.id}`)}
            />
          ))}
        </div>
      )}
    </div>
  )
}