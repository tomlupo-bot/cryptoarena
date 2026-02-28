import React, { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useEquityCurves } from '../hooks/useArenaData'

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

export default function EquityCurves() {
  const { data: curves, loading, error } = useEquityCurves()
  const [visibleTeams, setVisibleTeams] = useState(null)

  if (loading) return <div className="text-gray-400">Loading equity curves...</div>
  if (error) return <div className="text-red-400">Error: {error}</div>
  if (!curves) return <div className="text-gray-400">No data yet</div>

  const teams = Object.keys(curves)
  if (visibleTeams === null && teams.length) {
    // Initialize on first render
    setTimeout(() => setVisibleTeams(new Set(teams)), 0)
    return <div className="text-gray-400">Loading...</div>
  }

  // Merge all curves into unified data points
  const allTimestamps = new Set()
  Object.values(curves).forEach(curve => {
    curve?.forEach(pt => allTimestamps.add(pt.timestamp))
  })
  const sortedTimestamps = [...allTimestamps].sort()

  const chartData = sortedTimestamps.map(ts => {
    const point = { timestamp: ts.split('T')[0] }
    teams.forEach(team => {
      const curve = curves[team] || []
      const match = curve.find(p => p.timestamp === ts)
      if (match) point[team] = match.equity
    })
    return point
  })

  const toggleTeam = (team) => {
    setVisibleTeams(prev => {
      const next = new Set(prev)
      next.has(team) ? next.delete(team) : next.add(team)
      return next
    })
  }

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4 text-white">Equity Curves</h2>
      <div className="flex gap-3 mb-4">
        {teams.map((team, i) => (
          <button
            key={team}
            onClick={() => toggleTeam(team)}
            className={`px-3 py-1 rounded text-sm font-medium transition-opacity ${
              visibleTeams?.has(team) ? 'opacity-100' : 'opacity-30'
            }`}
            style={{ color: COLORS[i % COLORS.length], borderColor: COLORS[i % COLORS.length], borderWidth: 1 }}
          >
            {team}
          </button>
        ))}
      </div>
      <div className="bg-gray-900 rounded-lg p-4" style={{ height: 500 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="timestamp" stroke="#9ca3af" tick={{ fontSize: 11 }} />
            <YAxis stroke="#9ca3af" tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: 8 }}
              labelStyle={{ color: '#d1d5db' }}
            />
            <Legend />
            {teams.filter(t => visibleTeams?.has(t)).map((team, i) => (
              <Line key={team} type="monotone" dataKey={team} stroke={COLORS[i % COLORS.length]} strokeWidth={2} dot={false} connectNulls />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
