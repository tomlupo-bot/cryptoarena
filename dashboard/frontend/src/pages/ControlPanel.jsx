import React, { useState } from 'react'
import { useQuery, useMutation } from 'convex/react'
import { api } from '../../convex/_generated/api'

const AVAILABLE_MODELS = [
  { name: "Claude Sonnet 4.5", model: "anthropic/claude-sonnet-4.5", signature: "team-claude", inputPer1m: 3.0, outputPer1m: 15.0, color: "#a855f7" },
  { name: "Gemini 3.1 Pro", model: "google/gemini-3.1-pro-preview", signature: "team-gemini", inputPer1m: 2.0, outputPer1m: 12.0, color: "#3b82f6" },
  { name: "DeepSeek V3.2", model: "deepseek/deepseek-v3.2", signature: "team-deepseek", inputPer1m: 0.25, outputPer1m: 0.40, color: "#10b981" },
  { name: "Gemini 3 Flash", model: "google/gemini-3-flash-preview", signature: "team-flash", inputPer1m: 0.50, outputPer1m: 3.0, color: "#f59e0b" },
  { name: "Qwen 3.5 397B", model: "qwen/qwen3.5-397b-a17b", signature: "team-qwen", inputPer1m: 0.55, outputPer1m: 3.50, color: "#ef4444" },
]

const DATE_PRESETS = [
  { label: "3 days (Oct 1-3)", initDate: "2025-09-30", endDate: "2025-10-03", cost: "~$0.50" },
  { label: "1 week (Oct 1-7)", initDate: "2025-09-30", endDate: "2025-10-07", cost: "~$2" },
  { label: "2 weeks (Oct 1-14)", initDate: "2025-09-30", endDate: "2025-10-14", cost: "~$5" },
]

export default function ControlPanel() {
  const activeExperiment = useQuery(api.arena.getActiveExperiment)
  const requestStart = useMutation(api.arena.requestStart)
  const requestStop = useMutation(api.arena.requestStop)

  const [name, setName] = useState("")
  const [datePreset, setDatePreset] = useState(0)
  const [selectedTeams, setSelectedTeams] = useState(new Set(AVAILABLE_MODELS.map(m => m.signature)))
  const [initialCash, setInitialCash] = useState(10000)
  const [maxDrawdown, setMaxDrawdown] = useState(50)
  const [interval, setInterval_] = useState(60)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const toggleTeam = (sig) => {
    setSelectedTeams(prev => {
      const next = new Set(prev)
      next.has(sig) ? next.delete(sig) : next.add(sig)
      return next
    })
  }

  const handleStart = async () => {
    setError(null)
    setSubmitting(true)
    try {
      const preset = DATE_PRESETS[datePreset]
      const teams = AVAILABLE_MODELS
        .filter(m => selectedTeams.has(m.signature))
        .map(m => ({
          name: m.name,
          model: m.model,
          signature: m.signature,
          tokenPricing: { inputPer1m: m.inputPer1m, outputPer1m: m.outputPer1m },
        }))
      if (teams.length === 0) { setError("Select at least one team"); setSubmitting(false); return }

      await requestStart({
        name: name || `Arena ${preset.label}`,
        dateRange: { initDate: preset.initDate, endDate: preset.endDate },
        teams,
        initialCash,
        tradingIntervalMinutes: interval,
        maxDrawdownPct: maxDrawdown,
      })
    } catch (e) {
      setError(e.message)
    }
    setSubmitting(false)
  }

  const handleStop = async () => {
    if (!activeExperiment) return
    try {
      await requestStop({ id: activeExperiment._id })
    } catch (e) {
      setError(e.message)
    }
  }

  const isRunning = activeExperiment?.status === "running"
  const isPending = activeExperiment?.status === "pending"

  return (
    <div className="max-w-3xl">
      <h2 className="text-xl font-semibold mb-6 text-white">🎮 Control Panel</h2>

      {/* Status banner */}
      {(isRunning || isPending) && (
        <div className={`rounded-lg p-4 mb-6 flex items-center justify-between ${
          isRunning ? 'bg-green-900/30 border border-green-800' : 'bg-yellow-900/30 border border-yellow-800'
        }`}>
          <div>
            <span className={`text-sm font-medium ${isRunning ? 'text-green-300' : 'text-yellow-300'}`}>
              {isRunning ? '🔴 LIVE' : '⏳ PENDING'} — {activeExperiment.name}
            </span>
            <p className="text-xs text-gray-400 mt-1">
              {activeExperiment.teams.join(', ')} · {activeExperiment.dateRange.initDate} → {activeExperiment.dateRange.endDate}
            </p>
          </div>
          <button onClick={handleStop}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors">
            ⏹️ Stop
          </button>
        </div>
      )}

      {error && (
        <div className="bg-red-900/30 border border-red-800 rounded-lg p-3 mb-4 text-red-300 text-sm">
          ❌ {error}
        </div>
      )}

      {/* New Experiment Form */}
      <div className="bg-gray-900 rounded-lg p-6 space-y-6">
        <div>
          <label className="block text-sm text-gray-400 mb-2">Experiment Name</label>
          <input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="e.g. 5-Team Showdown"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
          />
        </div>

        {/* Date Range */}
        <div>
          <label className="block text-sm text-gray-400 mb-2">📅 Date Range</label>
          <div className="grid grid-cols-3 gap-3">
            {DATE_PRESETS.map((p, i) => (
              <button key={i} onClick={() => setDatePreset(i)}
                className={`p-3 rounded-lg border text-left transition-colors ${
                  datePreset === i
                    ? 'border-blue-500 bg-blue-900/20 text-white'
                    : 'border-gray-700 bg-gray-800 text-gray-400 hover:border-gray-600'
                }`}>
                <p className="font-medium text-sm">{p.label}</p>
                <p className="text-xs mt-1 text-gray-500">Est. cost: {p.cost}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Teams */}
        <div>
          <label className="block text-sm text-gray-400 mb-2">🤖 Teams</label>
          <div className="space-y-2">
            {AVAILABLE_MODELS.map(m => (
              <button key={m.signature} onClick={() => toggleTeam(m.signature)}
                className={`w-full flex items-center justify-between p-3 rounded-lg border transition-colors ${
                  selectedTeams.has(m.signature)
                    ? 'border-gray-600 bg-gray-800'
                    : 'border-gray-800 bg-gray-900/50 opacity-40'
                }`}>
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: m.color }} />
                  <div className="text-left">
                    <p className="text-sm font-medium text-white">{m.signature}</p>
                    <p className="text-xs text-gray-500">{m.name}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xs text-yellow-400">${m.outputPer1m}/M out</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Advanced Settings */}
        <details className="group">
          <summary className="text-sm text-gray-400 cursor-pointer hover:text-gray-300">
            ⚙️ Advanced Settings
          </summary>
          <div className="mt-4 grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Initial Capital ($)</label>
              <input type="number" value={initialCash} onChange={e => setInitialCash(Number(e.target.value))}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Max Drawdown (%)</label>
              <input type="number" value={maxDrawdown} onChange={e => setMaxDrawdown(Number(e.target.value))}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Trading Interval (min)</label>
              <input type="number" value={interval} onChange={e => setInterval_(Number(e.target.value))}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm" />
            </div>
          </div>
        </details>

        {/* Start Button */}
        <button onClick={handleStart} disabled={submitting || isRunning || isPending}
          className={`w-full py-3 rounded-lg font-medium text-lg transition-colors ${
            submitting || isRunning || isPending
              ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
              : 'bg-green-600 hover:bg-green-700 text-white'
          }`}>
          {submitting ? '⏳ Creating...' : isRunning ? '🔴 Arena Running' : isPending ? '⏳ Waiting for VPS...' : '▶️ Start Arena'}
        </button>
      </div>
    </div>
  )
}
