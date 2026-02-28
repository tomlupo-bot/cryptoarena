import React, { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useQuery } from 'convex/react'
import { api } from '../../convex/_generated/api'

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

export default function EquityCurves({ experimentId }) {
  const allSnapshots = useQuery(
    api.arena.getEquityCurves,
    experimentId ? { experimentId } : "skip"
  )
  const [visibleTeams, setVisibleTeams] = useState(null)

  if (!experimentId) return <div className="text-gray-400">Select an experiment to view equity curves</div>
  if (!allSnapshots) return <div className="text-gray-400">Loading...</div>
  if (allSnapshots.length === 0) return <div className="text-gray-400">No equity data yet</div>

  // Group by team
  const byTeam = {}
  for (const s of allSnapshots) {
    if (!byTeam[s.team]) byTeam[s.team] = []
    byTeam[s.team].push(s)
  }
  const teams = Object.keys(byTeam)

  if (visibleTeams === null && teams.length) {
    setTimeout(() => setVisibleTeams(new Set(teams)), 0)
    return <div className="text-gray-400">Loading...</div>
  }

  // Merge into chart data
  const allTimestamps = [...new Set(allSnapshots.map(s => s.timestamp))].sort()
  const chartData = allTimestamps.map(ts => {
    const point = { timestamp: ts.split('T')[0] }
    teams.forEach(team => {
      const match = byTeam[team]?.find(s => s.timestamp === ts)
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
          <button key={team} onClick={() => toggleTeam(team)}
            className={`px-3 py-1 rounded text-sm font-medium transition-opacity ${visibleTeams?.has(team) ? 'opacity-100' : 'opacity-30'}`}
            style={{ color: COLORS[i % COLORS.length], borderColor: COLORS[i % COLORS.length], borderWidth: 1 }}>
            {team}
          </button>
        ))}
      </div>
      <div className="bg-gray-900 rounded-lg p-4" style={{ height: 500 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="timestamp" stroke="#9ca3af" tick={{ fontSize: 11 }} />
            <YAxis stroke="#9ca3af" tick={{ fontSize: 11 }} domain={['auto', 'auto']} />
            <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: 8 }} />
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
