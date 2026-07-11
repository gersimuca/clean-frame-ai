import { useState, useRef } from 'react'
import { Upload, Link, Trash2, ImagePlus } from 'lucide-react'

export default function UploadPage() {
  const [files, setFiles] = useState([])
  const [uploading, setUploading] = useState(false)
  const [results, setResults] = useState(null)
  const [urlInput, setUrlInput] = useState('')
  const fileInputRef = useRef(null)

  const handleFileSelect = (e) => {
    const selected = Array.from(e.target.files)
    setFiles(prev => [...prev, ...selected])
  }

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleUpload = async () => {
    if (files.length === 0) return

    setUploading(true)
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      })
      const data = await res.json()
      setResults(data)
      setFiles([])
    } catch (e) {
      alert('Upload failed: ' + e.message)
    } finally {
      setUploading(false)
    }
  }

  const handleUrlUpload = async () => {
    if (!urlInput.trim()) return

    setUploading(true)
    const formData = new FormData()
    formData.append('url', urlInput)

    try {
      const res = await fetch('/api/upload/url', {
        method: 'POST',
        body: formData,
      })
      const data = await res.json()
      setResults({ uploaded: [data], total: 1 })
      setUrlInput('')
    } catch (e) {
      alert('URL upload failed: ' + e.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Upload Photos</h2>
        <p className="text-gray-500 mt-1">Upload real dog photos to clean and analyze</p>
      </div>

      <div
        className="glass-panel p-8 border-2 border-dashed border-gray-300 hover:border-emerald-400 transition-colors cursor-pointer text-center"
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault()
          const dropped = Array.from(e.dataTransfer.files)
          setFiles(prev => [...prev, ...dropped])
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*"
          className="hidden"
          onChange={handleFileSelect}
        />
        <ImagePlus className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-700 font-medium">Click or drag photos here</p>
        <p className="text-sm text-gray-400 mt-1">JPG, PNG, WebP supported</p>
      </div>

      {files.length > 0 && (
        <div className="glass-panel p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Selected ({files.length})</h3>
          <div className="space-y-2 max-h-48 overflow-auto">
            {files.map((file, i) => (
              <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                <span className="text-sm text-gray-700 truncate">{file.name}</span>
                <button onClick={() => removeFile(i)} className="text-red-500 hover:text-red-700">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="btn-primary w-full mt-4 flex items-center justify-center gap-2"
          >
            <Upload className="w-4 h-4" />
            {uploading ? 'Uploading...' : `Upload ${files.length} Photos`}
          </button>
        </div>
      )}

      <div className="glass-panel p-6">
        <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
          <Link className="w-4 h-4" />
          Or paste image URL
        </h3>
        <div className="flex gap-2">
          <input
            type="text"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            placeholder="https://example.com/dog.jpg"
            className="input-field"
          />
          <button onClick={handleUrlUpload} disabled={uploading} className="btn-primary">
            Fetch
          </button>
        </div>
      </div>

      {results && (
        <div className="glass-panel p-6 bg-emerald-50 border-emerald-200">
          <h3 className="text-emerald-800 font-medium mb-2">Upload Complete</h3>
          <p className="text-emerald-700">{results.total} images stored in database</p>
          <div className="mt-3 flex gap-2 flex-wrap">
            {results.uploaded?.map((img) => (
              <span key={img.id} className="text-xs bg-white px-2 py-1 rounded border border-emerald-200 text-emerald-700">
                #{img.id}: {img.filename}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}