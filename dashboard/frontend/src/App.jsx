import React, { useState } from 'react'
import { useQuery } from 'convex/react'
import { api } from '../convex/_generated/api'
import Leaderboard from './pages/Leaderboard'
import EquityCurves from './pages/EquityCurves'
import TokenEconomics from './pages/TokenEconomics'
import Experiments from './pages/Experiments'
import ControlPanel from './pages/ControlPanel'

const TABS = [
  { id: 'control', label: '🎮 Control', component: ControlPanel },
  { id: 'experiments', label: '🧪 Experiments', component: Experiments },
  { id: 'leaderboard', label: '🏆 Leaderboard', component: Leaderboard },
  { id: 'equity', label: '📈 Equity Curves', component: EquityCurves },
  { id: 'economics', label: '💰 Token Economics', component: TokenEconomics },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('control')
  const activeExperiment = useQuery(api.arena.getActiveExperiment)
  const ActiveComponent = TABS.find(t => t.id === activeTab)?.component || Experiments

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">🏟️ CryptoArena</h1>
            <p className="text-sm text-gray-400 mt-1">
              Competitive LLM Crypto Trading Arena
            </p>
          </div>
          {activeExperiment && (
            <div className="text-right">
              <span className={`text-sm px-2 py-1 rounded ${
                activeExperiment.status === 'running' ? 'bg-green-900 text-green-300' :
                activeExperiment.status === 'completed' ? 'bg-blue-900 text-blue-300' :
                'bg-gray-800 text-gray-400'
              }`}>
                {activeExperiment.status === 'running' ? '🔴 LIVE' : activeExperiment.status}
              </span>
              <p className="text-xs text-gray-500 mt-1">{activeExperiment.name}</p>
            </div>
          )}
        </div>
      </header>

      <nav className="border-b border-gray-800 px-6">
        <div className="flex gap-1">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'text-white border-b-2 border-blue-500'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="p-6">
        <ActiveComponent experimentId={activeExperiment?._id} />
      </main>
    </div>
  )
}
