import { useState } from 'react'
import {
  Play,
  Square,
  Settings2,
  Cpu,
  HardDrive,
  AlertCircle,
  Database
} from 'lucide-react'
import { usePipeline } from '../context/PipelineContext'
import ThresholdSlider from './ThresholdSlider'
import LogViewer from './LogViewer'

export default function PipelineControls() {
  const { config, updateConfig, startPipeline, stopPipeline, isRunning, isStopping, stats } = usePipeline()
  const [showAdvanced, setShowAdvanced] = useState(false)

  const handleStart = () => {
    startPipeline()
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Pipeline Configuration</h2>
          <p className="text-gray-500 mt-1">Configure cleaning parameters before running</p>
        </div>
        <div className="flex gap-3">
          {isRunning ? (
            <button onClick={stopPipeline} disabled={isStopping} className="btn-secondary flex items-center gap-2 text-red-600 border-red-200 hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed">
              <Square className="w-4 h-4" />
              {isStopping ? 'Stopping…' : 'Stop Pipeline'}
            </button>
          ) : (
            <button onClick={handleStart} className="btn-primary flex items-center gap-2">
              <Play className="w-4 h-4" />
              Start Pipeline
            </button>
          )}
        </div>
      </div>

      <div className="glass-panel p-4 bg-blue-50 border-blue-200">
        <div className="flex items-center gap-3">
          <Database className="w-5 h-5 text-blue-600" />
          <div>
            <p className="text-sm font-medium text-blue-800">Images stored in database</p>
            <p className="text-xs text-blue-600">Upload photos via the Upload page. The pipeline processes images directly from SQLite — no local directories needed.</p>
          </div>
        </div>
      </div>

      <div className="glass-panel p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Settings2 className="w-5 h-5 text-emerald-600" />
          Processing Stages
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { key: 'corruptEnabled', label: 'Corrupt Detection', desc: 'Remove broken/truncated files' },
            { key: 'relevanceEnabled', label: 'Relevance Filter', desc: 'CLIP-based content verification' },
            { key: 'framingEnabled', label: 'Framing Filter', desc: 'Object detection for proper framing' },
          ].map((stage) => (
            <label key={stage.key} className={`flex items-start gap-3 p-4 rounded-lg border cursor-pointer transition-all ${
              config[stage.key] ? 'bg-emerald-50 border-emerald-200' : 'bg-gray-50 border-gray-200 hover:border-gray-300'
            }`}>
              <input type="checkbox" checked={config[stage.key]} onChange={(e) => updateConfig({ [stage.key]: e.target.checked })} className="mt-1 w-4 h-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500" />
              <div>
                <p className="font-medium text-gray-800">{stage.label}</p>
                <p className="text-sm text-gray-500 mt-1">{stage.desc}</p>
              </div>
            </label>
          ))}
        </div>
      </div>

      <div className="glass-panel p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-6">Quality Thresholds</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <ThresholdSlider label="Relevance Threshold" value={config.relevanceThreshold} onChange={(v) => updateConfig({ relevanceThreshold: v })} min={0} max={1} step={0.01} description="Higher = stricter dog content matching" />
          <ThresholdSlider label="Dog Confidence" value={config.dogConfidence} onChange={(v) => updateConfig({ dogConfidence: v })} min={0} max={1} step={0.01} description="Minimum detection confidence for dog objects" />
          <ThresholdSlider label="Min Box Ratio" value={config.minBoxRatio} onChange={(v) => updateConfig({ minBoxRatio: v })} min={0.001} max={0.5} step={0.001} description="Minimum dog size as fraction of image" />
          <ThresholdSlider label="Max Box Ratio" value={config.maxBoxRatio} onChange={(v) => updateConfig({ maxBoxRatio: v })} min={0.1} max={1} step={0.01} description="Maximum dog size (prevents false positives)" />
        </div>
      </div>

      <div className="glass-panel p-6">
        <button onClick={() => setShowAdvanced(!showAdvanced)} className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors">
          <Settings2 className="w-5 h-5" />
          <span className="font-medium">Advanced Settings</span>
        </button>
        {showAdvanced && (
          <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-gray-200">
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-2 flex items-center gap-2"><Cpu className="w-4 h-4" />Device</label>
              <select value={config.device} onChange={(e) => updateConfig({ device: e.target.value })} className="input-field">
                <option value="cuda">CUDA (GPU)</option>
                <option value="cpu">CPU</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-2 flex items-center gap-2"><HardDrive className="w-4 h-4" />Workers</label>
              <input type="number" value={config.numWorkers} onChange={(e) => updateConfig({ numWorkers: parseInt(e.target.value) })} min={1} max={16} className="input-field" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-2 flex items-center gap-2"><AlertCircle className="w-4 h-4" />Min Image Size (px)</label>
              <input type="number" value={config.minImageSize} onChange={(e) => updateConfig({ minImageSize: parseInt(e.target.value) })} min={1} className="input-field" />
            </div>
          </div>
        )}
      </div>

      {stats.total > 0 && (
        <div className="glass-panel p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Dataset Preview</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold text-gray-900">{stats.total.toLocaleString()}</p>
              <p className="text-sm text-gray-500">Total Images</p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold text-emerald-600">{((stats.accepted / stats.total) * 100).toFixed(1)}%</p>
              <p className="text-sm text-gray-500">Acceptance Rate</p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold text-red-500">{((stats.rejected / stats.total) * 100).toFixed(1)}%</p>
              <p className="text-sm text-gray-500">Rejection Rate</p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold text-amber-600">{((stats.pending / stats.total) * 100).toFixed(1)}%</p>
              <p className="text-sm text-gray-500">Remaining</p>
            </div>
          </div>
        </div>
      )}

      <LogViewer />
    </div>
  )
}