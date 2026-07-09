import { useState } from 'react'
import type { ToolItem } from '../types'
import { useTools } from '../hooks/useData'
import { useFavorites } from '../hooks/useFavorites'
import ToolCard from '../components/ToolCard'
import ToolDetail from '../components/ToolDetail'
import EmptyState from '../components/EmptyState'

export default function FavoritesPage() {
  const { tools } = useTools()
  const { getFavoriteTools } = useFavorites()
  const [selectedTool, setSelectedTool] = useState<ToolItem | null>(null)

  const favorites = getFavoriteTools(tools)

  if (favorites.length === 0) {
    return (
      <EmptyState
        icon="💝"
        title="还没有收藏"
        description="去发现页面收藏你喜欢的工具吧"
      />
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">❤️ 我的收藏</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            共收藏 {favorites.length} 个工具
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {favorites.map((tool, idx) => (
          <ToolCard
            key={tool.name + (tool.source || '')}
            tool={tool}
            onClick={setSelectedTool}
            index={idx}
          />
        ))}
      </div>

      {selectedTool && (
        <ToolDetail tool={selectedTool} onClose={() => setSelectedTool(null)} />
      )}
    </div>
  )
}
