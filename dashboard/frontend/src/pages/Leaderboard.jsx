import React from 'react'
import { useQuery } from 'convex/react'
import { api } from '../../convex/_generated/api'

const tierColors = {
  thriving: 'text-green-400',
  stable: 'text-blue-400',
  struggling: 'text-yellow-400',
  critical: 'text-red-400',
  dead: 'text-gray-500',
}

export default function Leaderboard({ experimentId }) {
  const teams = useQuery(
    api.arena.getLeaderboard,
    experimentId ? { experimentId } : "skip"
  )

  if (!experimentId) return <div className="text-gray-400">Select an experiment to view leaderboard</div>
  if (!teams) return <div className="text-gray-400">Loading leaderboard...</div>
  if (teams.length === 0) return <div className="text-gray-400">No team data yet — arena may still be starting</div>

  const medals = ['🥇', '🥈', '🥉']

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4 text-white">Live Standings</h2>
      <div className="bg-gray-900 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="text-left text-gray-400 text-sm border-b border-gray-800">
              <th className="px-4 py-3 w-16">Rank</th>
              <th className="px-4 py-3">Team</th>
              <th className="px-4 py-3">Model</th>
              <th className="px-4 py-3 text-right">Equity</th>
              <th className="px-4 py-3 text-right">Return</th>
              <th className="px-4 py-3 text-right">Token Cost</th>
              <th className="px-4 py-3 text-center">Status</th>
            </tr>
          </thead>
          <tbody>
            {teams.map((team, i) => (
              <tr key={team.team} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                <td className="px-4 py-3 text-lg">{medals[i] || `#${i+1}`}</td>
                <td className="px-4 py-3 font-medium text-white">{team.team}</td>
                <td className="px-4 py-3 text-sm text-gray-400">{team.model.split('/').pop()}</td>
                <td className="px-4 py-3 text-right font-mono">
                  ${team.equity.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </td>
                <td className={`px-4 py-3 text-right font-mono ${team.returnPct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {team.returnPct >= 0 ? '+' : ''}{team.returnPct.toFixed(2)}%
                </td>
                <td className="px-4 py-3 text-right font-mono text-yellow-400">
                  ${team.tokenCost.toFixed(4)}
                </td>
                <td className={`px-4 py-3 text-center font-medium ${tierColors[team.survivalTier] || 'text-gray-400'}`}>
                  {team.status === 'dead' ? '💀' : ''} {team.survivalTier}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
