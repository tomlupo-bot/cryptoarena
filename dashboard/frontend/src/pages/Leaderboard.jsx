import React from 'react'
import { useLeaderboard } from '../hooks/useArenaData'

const tierColors = {
  thriving: 'text-green-400',
  stable: 'text-blue-400',
  struggling: 'text-yellow-400',
  critical: 'text-red-400',
  dead: 'text-gray-500',
}

export default function Leaderboard() {
  const { data, loading, error } = useLeaderboard()

  if (loading) return <div className="text-gray-400">Loading leaderboard...</div>
  if (error) return <div className="text-red-400">Error: {error}</div>

  const standings = data?.leaderboard || []

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Live Standings</h2>
      <div className="bg-gray-900 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="text-left text-gray-400 text-sm border-b border-gray-800">
              <th className="px-4 py-3 w-16">Rank</th>
              <th className="px-4 py-3">Team</th>
              <th className="px-4 py-3 text-right">Equity (USDT)</th>
              <th className="px-4 py-3 text-right">Drawdown</th>
              <th className="px-4 py-3 text-right">Token Cost</th>
              <th className="px-4 py-3 text-center">Status</th>
            </tr>
          </thead>
          <tbody>
            {standings.map((team, i) => (
              <tr key={team.team} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                <td className="px-4 py-3 text-lg">
                  {team.medal || team.rank}
                </td>
                <td className="px-4 py-3 font-medium text-white">
                  {team.team}
                </td>
                <td className="px-4 py-3 text-right font-mono">
                  {(team.equity || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </td>
                <td className="px-4 py-3 text-right font-mono text-red-400">
                  {team.drawdown_pct ? `-${team.drawdown_pct.toFixed(2)}%` : '-'}
                </td>
                <td className="px-4 py-3 text-right font-mono text-yellow-400">
                  ${(team.cumulative_token_cost || 0).toFixed(4)}
                </td>
                <td className={`px-4 py-3 text-center font-medium ${tierColors[team.survival_tier] || 'text-gray-400'}`}>
                  {team.survival_tier || 'unknown'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
