import React, { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useApi } from '../hooks/useApi'

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

export default function EquityCurves() {
  const { data: teamsData } = useApi('/teams')
  const [curves, setCurves] = useState({})
  const [visibleTeams, setVisibleTeams] = useState(new Set())

  const teams = teamsData?.teams || []

  useEffect(() => {
    if (!teams.length) return
    setVisibleTeams(new Set(teams))

    teams.forEach(async (team) => {
      try {
        const res = await fetch(`/api/equity/${team}`)
        if (res.ok) {
          const json = await res.json()
          setCurves(prev => ({ ...prev, [team]: json.equity_curve }))
        }
      } catch {}
    })
  }, [teams.join(',')])

  // Merge all curves into unified data points
  const allTimestamps = new Set()
  Object.values(curves).forEach(curve => {
    curve?.forEach(pt => allTimestamps.add(pt.timestamp))
  })
  const sortedTimestamps = [...allTimestamps].sort()

  const chartData = sortedTimestamps.map(ts => {
    const point = { timestamp: ts }
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
      <h2 className="text-xl font-semibold mb-4">Equity Curves</h2>

      {/* Team toggles */}
      <div className="flex gap-3 mb-4">
        {teams.map((team, i) => (
          <button
            key={team}
            onClick={() => toggleTeam(team)}
            className={`px-3 py-1 rounded text-sm font-medium transition-opacity ${
              visibleTeams.has(team) ? 'opacity-100' : 'opacity-30'
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
            {teams.filter(t => visibleTeams.has(t)).map((team, i) => (
              <Line
                key={team}
                type="monotone"
                dataKey={team}
                stroke={COLORS[i % COLORS.length]}
                strokeWidth={2}
                dot={false}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
