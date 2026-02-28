import { useState, useEffect } from 'react'

// Reads from static JSON deployed via git push
const DATA_URL = '/data/arena.json'

let _cache = null
let _cacheTime = 0
const CACHE_TTL = 10000

export function useArenaData() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function fetchData() {
      try {
        if (_cache && Date.now() - _cacheTime < CACHE_TTL) {
          if (!cancelled) { setData(_cache); setLoading(false) }
          return
        }
        const res = await fetch(DATA_URL)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const json = await res.json()
        _cache = json
        _cacheTime = Date.now()
        if (!cancelled) { setData(json); setLoading(false) }
      } catch (err) {
        if (!cancelled) { setError(err.message); setLoading(false) }
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => { cancelled = true; clearInterval(interval) }
  }, [])

  return { data, loading, error }
}

// Convenience hooks that extract specific views from the static data
export function useLeaderboard() {
  const { data, loading, error } = useArenaData()
  if (!data) return { data: null, loading, error }

  const results = data.results || []
  const leaderboard = results
    .sort((a, b) => (b.current_equity || 0) - (a.current_equity || 0))
    .map((r, i) => ({
      team: r.team,
      model: r.model,
      equity: r.current_equity || 10000,
      return_pct: r.total_return_pct || 0,
      drawdown_pct: r.max_drawdown_pct || 0,
      survival_tier: r.survival_tier || 'unknown',
      cumulative_token_cost: r.cumulative_token_cost || 0,
      status: r.status || 'unknown',
      rank: i + 1,
      medal: ['🥇', '🥈', '🥉'][i] || `#${i + 1}`,
    }))

  return { data: { leaderboard }, loading, error }
}

export function useEquityCurves() {
  const { data, loading, error } = useArenaData()
  if (!data) return { data: null, loading, error }

  const curves = {}
  for (const team of (data.teams || [])) {
    curves[team.name] = team.equity_curve || []
  }
  return { data: curves, loading, error }
}

export function useTokenEconomics() {
  const { data, loading, error } = useArenaData()
  if (!data) return { data: null, loading, error }

  const economics = (data.results || []).map(r => ({
    team: r.team,
    model: r.model,
    token_cost: r.cumulative_token_cost || 0,
    llm_calls: r.total_llm_calls || 0,
    avg_cost: r.avg_cost_per_call || 0,
    cost_pct: r.token_cost_as_pct_of_initial || 0,
  }))
  return { data: economics, loading, error }
}
