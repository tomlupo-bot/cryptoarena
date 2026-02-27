import { useState, useEffect } from 'react'

const API_BASE = '/api'

export function useApi(endpoint, refreshInterval = 5000) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function fetchData() {
      try {
        const res = await fetch(`${API_BASE}${endpoint}`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const json = await res.json()
        if (!cancelled) {
          setData(json)
          setLoading(false)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message)
          setLoading(false)
        }
      }
    }

    fetchData()
    const interval = setInterval(fetchData, refreshInterval)

    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [endpoint, refreshInterval])

  return { data, loading, error }
}
