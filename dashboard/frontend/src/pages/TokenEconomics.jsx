import React from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useQuery } from 'convex/react'
import { api } from '../../convex/_generated/api'

export default function TokenEconomics({ experimentId }) {
  const teams = useQuery(
    api.arena.getLeaderboard,
    experimentId ? { experimentId } : "skip"
  )

  if (!experimentId) return <div className="text-gray-400">Select an experiment to view economics</div>
  if (!teams) return <div className="text-gray-400">Loading...</div>
  if (teams.length === 0) return <div className="text-gray-400">No data yet</div>

  const chartData = teams.map(t => ({
    name: t.team,
    tokenCost: t.tokenCost,
    llmCalls: t.llmCalls,
    costPerCall: t.llmCalls > 0 ? t.tokenCost / t.llmCalls : 0,
    returnPct: t.returnPct,
    netReturn: t.returnPct - (t.tokenCost / 100), // token cost as % of initial $10K
  }))

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4 text-white">Token Economics</h2>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {teams.map(t => (
          <div key={t.team} className="bg-gray-900 rounded-lg p-4">
            <p className="text-sm text-gray-400">{t.team}</p>
            <p className="text-lg font-mono text-yellow-400">${t.tokenCost.toFixed(4)}</p>
            <p className="text-xs text-gray-500">{t.llmCalls} calls</p>
          </div>
        ))}
      </div>

      {/* Bar chart */}
      <div className="bg-gray-900 rounded-lg p-4" style={{ height: 400 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="name" stroke="#9ca3af" tick={{ fontSize: 11 }} />
            <YAxis stroke="#9ca3af" tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: 8 }} />
            <Legend />
            <Bar dataKey="tokenCost" name="Token Cost ($)" fill="#f59e0b" />
            <Bar dataKey="llmCalls" name="LLM Calls" fill="#3b82f6" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
