import { useState, useEffect, useCallback } from 'react'
import type { ToolItem } from '../types'

const STORAGE_KEY = 'ai-treasure-favorites'

function getStoredIds(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function storeIds(ids: string[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(ids))
}

export function useFavorites() {
  const [favoriteIds, setFavoriteIds] = useState<string[]>(getStoredIds)

  useEffect(() => {
    storeIds(favoriteIds)
  }, [favoriteIds])

  const add = useCallback((id: string) => {
    setFavoriteIds(prev => prev.includes(id) ? prev : [...prev, id])
  }, [])

  const remove = useCallback((id: string) => {
    setFavoriteIds(prev => prev.filter(fid => fid !== id))
  }, [])

  const toggle = useCallback((id: string) => {
    setFavoriteIds(prev => prev.includes(id) ? prev.filter(fid => fid !== id) : [...prev, id])
  }, [])

  const isFavorite = useCallback((id: string) => {
    return favoriteIds.includes(id)
  }, [favoriteIds])

  const getFavoriteTools = useCallback((tools: ToolItem[]): ToolItem[] => {
    return tools.filter(t => favoriteIds.includes(t.name + (t.source || '')))
  }, [favoriteIds])

  const count = favoriteIds.length

  return { favoriteIds, add, remove, toggle, isFavorite, getFavoriteTools, count }
}
