import React, { useState } from 'react'
import Leaderboard from './pages/Leaderboard'
import EquityCurves from './pages/EquityCurves'
import TokenEconomics from './pages/TokenEconomics'

const TABS = [
  { id: 'leaderboard', label: '🏆 Leaderboard', component: Leaderboard },
  { id: 'equity', label: '📈 Equity Curves', component: EquityCurves },
  { id: 'economics', label: '💰 Token Economics', component: TokenEconomics },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('leaderboard')
  const ActiveComponent = TABS.find(t => t.id === activeTab)?.component || Leaderboard

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4">
        <h1 className="text-2xl font-bold text-white">
          🏟️ CryptoArena Dashboard
        </h1>
        <p className="text-sm text-gray-400 mt-1">
          Competitive LLM Crypto Trading Arena
        </p>
      </header>

      {/* Tabs */}
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

      {/* Content */}
      <main className="p-6">
        <ActiveComponent />
      </main>
    </div>
  )
}
