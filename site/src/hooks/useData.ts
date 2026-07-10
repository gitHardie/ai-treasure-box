import { useState, useEffect, useCallback } from 'react'
import type { ToolItem, NewsItem, ToolData, NewsData, SnapshotData, RankingItem, ToolsJsonData, CategoriesData, StatsData } from '../types'

function getBasePath(): string {
  return import.meta.env.BASE_URL.replace(/\/$/, '')
}

export function useTools() {
  const [tools, setTools] = useState<ToolItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchTools = async () => {
      try {
        setLoading(true)
        const basePath = getBasePath()
        const res = await fetch(basePath + '/data/tools.json')
        if (!res.ok) {
          throw new Error('Failed to fetch tools.json: ' + res.status)
        }
        const data: ToolsJsonData = await res.json()
        setTools(data.tools || [])
        setError(null)
      } catch (e) {
        setError('Failed to load tools data')
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    fetchTools()
  }, [])

  return { tools, loading, error }
}

export function useCategories() {
  const [categories, setCategories] = useState<CategoriesData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const basePath = getBasePath()
    fetch(basePath + '/data/categories.json')
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setCategories(data) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return { categories, loading }
}

export function useStats() {
  const [stats, setStats] = useState<StatsData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const basePath = getBasePath()
    fetch(basePath + '/data/stats.json')
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setStats(data) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return { stats, loading }
}

export function useNews() {
  const [news, setNews] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchNews = async () => {
      try {
        setLoading(true)
        const basePath = getBasePath()
        let allNews: NewsItem[] = []
        try {
          const res = await fetch(basePath + '/data/news/latest.json')
          if (res.ok) {
            const data: NewsData = await res.json()
            allNews = data.items
          }
        } catch (e) { /* skip */ }
        allNews.sort((a, b) => {
          const dateA = new Date(a.published_at || a.collected_at || '0').getTime()
          const dateB = new Date(b.published_at || b.collected_at || '0').getTime()
          return dateB - dateA
        })
        setNews(allNews)
        setError(null)
      } catch (e) {
        setError('Failed to load news')
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    fetchNews()
  }, [])

  return { news, loading, error }
}

export function useSnapshots() {
  const [snapshots, setSnapshots] = useState<SnapshotData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchSnapshots = async () => {
      try {
        setLoading(true)
        const basePath = getBasePath()
        let data: SnapshotData[] = []
        try {
          const res = await fetch(basePath + '/data/snapshots/latest.json')
          if (res.ok) {
            const json = await res.json()
            data = Array.isArray(json) ? json : [json]
          }
        } catch (e) { /* skip */ }
        setSnapshots(data)
        setError(null)
      } catch (e) {
        setError('Failed to load snapshots')
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    fetchSnapshots()
  }, [])

  return { snapshots, loading, error }
}

export function useRankings() {
  const { tools, loading, error } = useTools()
  const [rankings, setRankings] = useState<RankingItem[]>([])

  useEffect(() => {
    if (tools.length === 0) return
    const sorted = [...tools].sort((a, b) => b.stars - a.stars)
    const ranked: RankingItem[] = sorted.map((item, idx) => ({
      ...item,
      rank: idx + 1,
      prev_rank: item.rank_change !== undefined ? idx + 1 - (item.rank_change || 0) : undefined,
      rank_change: item.rank_change || 0,
    }))
    setRankings(ranked)
  }, [tools])

  return { rankings, loading, error }
}

export function useTheme() {
  const [isDark, setIsDark] = useState(() => {
    return document.documentElement.classList.contains('dark')
  })

  const toggle = useCallback(() => {
    setIsDark(prev => {
      const next = !prev
      if (next) {
        document.documentElement.classList.add('dark')
        localStorage.setItem('theme', 'dark')
      } else {
        document.documentElement.classList.remove('dark')
        localStorage.setItem('theme', 'light')
      }
      return next
    })
  }, [])

  return { isDark, toggle }
}
