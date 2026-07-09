import { useState } from 'react'
import type { ToolItem } from '../types'
import { useRankings } from '../hooks/useData'
import ToolDetail from '../components/ToolDetail'
import LoadingState from '../components/LoadingState'
import EmptyState from '../components/EmptyState'

function formatStars(stars: number): string {
  if (stars >= 1000) {
    return (stars / 1000).toFixed(1) + 'k'
  }
  return stars.toString()
}

export default function RankingsPage() {
  const { rankings, loading, error } = useRankings()
  const [selectedTool, setSelectedTool] = useState<ToolItem | null>(null)

  if (loading) {
    return <LoadingState message="正在加载排行数据..." />
  }

  if (error) {
    return <EmptyState icon="⚠️" title="加载失败" description={error} />
  }

  if (rankings.length === 0) {
    return <EmptyState icon="🏆" title="暂无排行数据" description="数据采集中，请稍后再来" />
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          🏆 工具排行榜
        </h2>
        <span className="text-sm text-slate-500 dark:text-slate-400">
          按 Stars 数排名
        </span>
      </div>

      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
        {rankings.map((item, idx) => (
          <div
            key={item.name + idx}
            className="flex items-center gap-4 p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer transition-colors border-b border-slate-100 dark:border-slate-800 last:border-b-0"
            onClick={() => setSelectedTool(item)}
          >
            {/* Rank */}
            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm shrink-0 ${
              item.rank === 1 ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' :
              item.rank === 2 ? 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300' :
              item.rank === 3 ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300' :
              'bg-slate-50 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
            }`}>
              {item.rank <= 3 ? ['🥇', '🥈', '🥉'][item.rank - 1] : item.rank}
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="font-medium text-slate-900 dark:text-white truncate">
                  {item.name}
                </h3>
                {item.language && (
                  <span className="text-xs text-slate-500 dark:text-slate-500 shrink-0">
                    {item.language}
                  </span>
                )}
              </div>
              <p className="text-sm text-slate-500 dark:text-slate-400 truncate mt-0.5">
                {item.description}
              </p>
            </div>

            {/* Stars */}
            <div className="text-right shrink-0">
              <div className="flex items-center gap-1 text-amber-500">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
                <span className="font-medium">{formatStars(item.stars)}</span>
              </div>
              {item.rank_change !== 0 && (
                <div className={`text-xs mt-1 ${
                  item.rank_change > 0 ? 'text-green-500' : 'text-red-500'
                }`}>
                  {item.rank_change > 0 ? '↑' : '↓'} {Math.abs(item.rank_change)}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {selectedTool && (
        <ToolDetail tool={selectedTool} onClose={() => setSelectedTool(null)} />
      )}
    </div>
  )
}
