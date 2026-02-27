import React from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useApi } from '../hooks/useApi'

export default function TokenEconomics() {
  const { data, loading, error } = useApi('/economics')

  if (loading) return <div className="text-gray-400">Loading economics...</div>
  if (error) return <div className="text-red-400">Error: {error}</div>

  const economics = data?.economics || []

  const chartData = economics.map(e => ({
    team: e.team,
    'Trading PnL': e.trading_pnl,
    'Token Cost': -e.token_cost,
    'Net Return': e.net_return,
  }))

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Token Economics</h2>

      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {economics.map(e => (
          <div key={e.team} className="bg-gray-900 rounded-lg p-4">
            <h3 className="text-lg font-medium text-white mb-2">{e.team}</h3>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Trading PnL</span>
                <span className={e.trading_pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                  {e.trading_pnl >= 0 ? '+' : ''}{e.trading_pnl?.toFixed(2)} USDT
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Token Cost</span>
                <span className="text-yellow-400">-${e.token_cost?.toFixed(4)}</span>
              </div>
              <div className="flex justify-between border-t border-gray-700 pt-1 mt-1">
                <span className="text-gray-300 font-medium">Net Return</span>
                <span className={`font-medium ${e.net_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {e.net_return >= 0 ? '+' : ''}{e.net_return?.toFixed(2)} USDT
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Token % of Capital</span>
                <span className="text-gray-300">{e.token_cost_pct?.toFixed(4)}%</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Stacked bar chart */}
      <div className="bg-gray-900 rounded-lg p-4" style={{ height: 400 }}>
        <h3 className="text-sm font-medium text-gray-400 mb-3">Trading PnL vs Token Costs</h3>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="team" stroke="#9ca3af" />
            <YAxis stroke="#9ca3af" />
            <Tooltip
              contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: 8 }}
            />
            <Legend />
            <Bar dataKey="Trading PnL" fill="#10b981" stackId="a" />
            <Bar dataKey="Token Cost" fill="#ef4444" stackId="a" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
