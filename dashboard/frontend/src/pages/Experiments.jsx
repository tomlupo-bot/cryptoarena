import React from 'react'
import { useQuery } from 'convex/react'
import { api } from '../../convex/_generated/api'

const STATUS_STYLES = {
  pending: 'bg-yellow-900/50 text-yellow-300',
  running: 'bg-green-900/50 text-green-300',
  completed: 'bg-blue-900/50 text-blue-300',
  failed: 'bg-red-900/50 text-red-300',
  stopped: 'bg-gray-800 text-gray-400',
}

const STATUS_ICONS = {
  pending: '⏳',
  running: '🔴',
  completed: '✅',
  failed: '❌',
  stopped: '⏹️',
}

export default function Experiments() {
  const experiments = useQuery(api.arena.getExperiments) || []

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold">Experiments</h2>
        <p className="text-sm text-gray-500">
          Start new experiments via Discord: type <code className="bg-gray-800 px-1 rounded">arena start</code>
        </p>
      </div>

      {experiments.length === 0 ? (
        <div className="bg-gray-900 rounded-lg p-12 text-center">
          <p className="text-4xl mb-4">🏟️</p>
          <p className="text-gray-400 mb-2">No experiments yet</p>
          <p className="text-sm text-gray-600">
            Start your first arena run from Discord
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {experiments.map((exp) => (
            <div key={exp._id} className="bg-gray-900 rounded-lg p-4 hover:bg-gray-800/50 transition-colors">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-white">{exp.name}</h3>
                  <p className="text-sm text-gray-400 mt-1">
                    📅 {exp.dateRange.initDate} → {exp.dateRange.endDate}
                    {' · '}
                    🤖 {exp.teams.length} teams: {exp.teams.join(', ')}
                  </p>
                </div>
                <div className="text-right">
                  <span className={`text-sm px-2 py-1 rounded ${STATUS_STYLES[exp.status]}`}>
                    {STATUS_ICONS[exp.status]} {exp.status}
                  </span>
                  {exp.totalTokenCost !== undefined && (
                    <p className="text-xs text-yellow-400 mt-1">
                      💰 ${exp.totalTokenCost.toFixed(4)}
                    </p>
                  )}
                </div>
              </div>
              {exp.startedAt && (
                <p className="text-xs text-gray-600 mt-2">
                  Started: {new Date(exp.startedAt).toLocaleString()}
                  {exp.completedAt && ` · Completed: ${new Date(exp.completedAt).toLocaleString()}`}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
