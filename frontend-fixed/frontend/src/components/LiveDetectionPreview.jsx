import { CheckCircle2, XCircle, ScanSearch } from 'lucide-react'

export default function LiveDetectionPreview({ image }) {
  const hasDetections = Array.isArray(image?.detections) && image.detections.length > 0

  return (
    <div className="glass-panel p-4 flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
          <ScanSearch className="w-4 h-4 text-emerald-600" />
          Live Detection Preview
        </h3>
        {image && (
          <span className={`flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full ${
            image.status === 'accepted' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
          }`}>
            {image.status === 'accepted' ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
            {image.status}
          </span>
        )}
      </div>

      {image ? (
        <>
          <div className="relative bg-gray-100 rounded-lg overflow-hidden aspect-video">
            <img src={image.thumbnailUrl} alt={image.filename} className="w-full h-full object-contain" />
            {hasDetections && (
              <svg
                className="absolute inset-0 w-full h-full"
                viewBox={`0 0 ${image.width || 1000} ${image.height || 1000}`}
                preserveAspectRatio="xMidYMid meet"
              >
                {image.detections.map((det, i) => (
                  <rect
                    key={i}
                    x={det.x1}
                    y={det.y1}
                    width={det.x2 - det.x1}
                    height={det.y2 - det.y1}
                    fill="none"
                    stroke="#10b981"
                    strokeWidth={Math.max(2, (image.width || 1000) / 200)}
                    rx="4"
                  />
                ))}
              </svg>
            )}
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-gray-500 gap-2">
            <span className="truncate">{image.filename}</span>
            {image.reason && <span className="text-red-500 truncate flex-shrink-0">{image.reason}</span>}
          </div>
        </>
      ) : (
        <div className="flex-1 flex items-center justify-center text-gray-400 text-sm aspect-video bg-gray-50 rounded-lg">
          Waiting for the first result…
        </div>
      )}
    </div>
  )
}
