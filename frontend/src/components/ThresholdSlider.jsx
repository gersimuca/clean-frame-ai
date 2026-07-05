import { useState, useEffect } from 'react'

export default function ThresholdSlider({ label, value, onChange, min, max, step, description }) {
  const [localValue, setLocalValue] = useState(value)

  useEffect(() => {
    setLocalValue(value)
  }, [value])

  const handleChange = (e) => {
    const v = parseFloat(e.target.value)
    setLocalValue(v)
    onChange(v)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <label className="text-sm font-medium text-gray-700">{label}</label>
        <span className="text-sm font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
          {localValue.toFixed(step < 0.01 ? 3 : 2)}
        </span>
      </div>
      <input type="range" min={min} max={max} step={step} value={localValue} onChange={handleChange} className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-emerald-600" />
      <p className="text-xs text-gray-500 mt-1">{description}</p>
    </div>
  )
}