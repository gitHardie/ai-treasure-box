import { useState, useMemo } from 'react'
import type { ToolItem } from '../types'
import { useTools } from '../hooks/useData'
import ToolDetail from '../components/ToolDetail'
import LoadingState from '../components/LoadingState'
import EmptyState from '../components/EmptyState'

function formatStars(stars: number | null | undefined): string {
  if (!stars) return "0"
  if (stars >= 1000) return (stars / 1000).toFixed(1) + 'k'
  return stars.toString()
}

function getDomain(url: string): string {
  try { return new URL(url).hostname } catch { return '' }
}

type TabId = 'global' | 'china'

export default function RankingsPage() {
  const { tools, loading, error } = useTools()
  const [activeTab, setActiveTab] = useState<TabId>('global')
  const [selectedTool, setSelectedTool] = useState<ToolItem | null>(null)
  const [filterCat, setFilterCat] = useState('all')

  const cats = useMemo(() => {
    const all = new Set<string>()
    tools.forEach(t => t.topics?.forEach(topic => all.add(topic)))
    return ['all', ...Array.from(all).slice(0, 12)]
  }, [tools])

  const rankings = useMemo(() => {
    let list = [...tools]
    if (activeTab === 'china') {
      list = list.filter(t => t.is_china_tool)
    }
    if (filterCat !== 'all') {
      list = list.filter(t =>
        t.topics?.some(topic => topic.toLowerCase().includes(filterCat.toLowerCase()))
      )
    }
    // Sort by stars for global, by a "heat" score for china
    if (activeTab === 'global') {
      list.sort((a, b) => (b.stars || 0) - (a.stars || 0))
    } else {
      // Heat score: stars + forks * 3
      list.sort((a, b) => ((b.stars||0) + (b.forks||0) * 3) - ((a.stars||0) + (a.forks||0) * 3))
    }
    return list.map((item, idx) => ({
      ...item,
      rank: idx + 1,
      rank_change: item.rank_change || 0,
    }))
  }, [tools, activeTab, filterCat])

  if (loading) return <LoadingState message="加载排行数据..." />
  if (error) return <EmptyState icon="⚠️" title="加载失败" description={error} />

  const rankColor = (rank: number) => {
    if (rank === 1) return 'from-amber-400 to-yellow-500'
    if (rank === 2) return 'from-slate-300 to-slate-400'
    if (rank === 3) return 'from-orange-400 to-amber-600'
    return 'from-slate-400 to-slate-500'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white mb-2">
          🏆 AI 工具排行榜
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          实时追踪最受欢迎的 AI 开源项目
        </p>
      </div>

      {/* Tabs */}
      <div className="flex items-center justify-center gap-3">
        <button
          onClick={() => setActiveTab('global')}
          className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
            activeTab === 'global'
              ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/25'
              : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700 hover:border-indigo-300'
          }`}
        >
          🌍 全球热门
        </button>
        <button
          onClick={() => setActiveTab('china')}
          className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
            activeTab === 'china'
              ? 'bg-red-500 text-white shadow-lg shadow-red-500/25'
              : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700 hover:border-red-300'
          }`}
        >
          🇨🇳 国内推荐
        </button>
      </div>

      {/* Category filter */}
      <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
        {cats.slice(0, 8).map(cat => (
          <button
            key={cat}
            onClick={() => setFilterCat(cat)}
            className={`px-3 py-1.5 rounded-full text-xs whitespace-nowrap transition-all ${
              filterCat === cat
                ? 'bg-indigo-500 text-white'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
          >
            {cat === 'all' ? '全部' : cat}
          </button>
        ))}
      </div>

      {/* Rankings list */}
      <div className="space-y-3">
        {rankings.slice(0, 30).map((item, idx) => (
          <div
            key={item.name + (item.source || '')}
            onClick={() => setSelectedTool(item)}
            className="flex items-center gap-4 p-4 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 cursor-pointer hover:shadow-lg hover:shadow-indigo-500/5 hover:-translate-y-0.5 transition-all duration-200 group"
            style={{ animationDelay: `${idx * 30}ms` }}
          >
            {/* Rank */}
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 font-bold text-lg ${
              item.rank <= 3
                ? `bg-gradient-to-br ${rankColor(item.rank)} text-white shadow-lg`
                : 'bg-slate-100 dark:bg-slate-800 text-slate-500'
            }`}>
              {item.rank}
            </div>

            {/* Icon */}
            <img
              src={`https://www.google.com/s2/favicons?domain=${getDomain(item.url)}&sz=32`}
              alt=""
              className="w-10 h-10 rounded-xl bg-slate-100 dark:bg-slate-800 shrink-0"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
            />

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-slate-900 dark:text-white truncate group-hover:text-indigo-500 transition-colors">
                  {item.name}
                </h3>
                {item.is_china_tool && (
                  <span className="text-[10px] px-1.5 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded font-medium shrink-0">国内</span>
                )}
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5">
                {item.description}
              </p>
            </div>

            {/* Stars */}
            <div className="text-right shrink-0">
              <div className="flex items-center gap-1 text-amber-500">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
                <span className="font-bold text-sm">{formatStars(item.stars)}</span>
              </div>
              {item.rank_change !== 0 && (
                <div className={`text-xs mt-0.5 font-medium ${
                  item.rank_change > 0 ? 'text-emerald-500' : 'text-red-500'
                }`}>
                  {item.rank_change > 0 ? `↑${Math.abs(item.rank_change)}` : `↓${Math.abs(item.rank_change)}`}
                </div>
              )}
              {item.rank_change === 0 && (
                <div className="text-xs mt-0.5 text-slate-400">→ 持平</div>
              )}
            </div>
          </div>
        ))}
      </div>

      {rankings.length === 0 && (
        <EmptyState
          icon="📭"
          title="暂无排行数据"
          description={activeTab === 'china' ? '当前没有国内工具的排行数据' : '暂无工具数据'}
        />
      )}

      {selectedTool && (
        <ToolDetail tool={selectedTool} onClose={() => setSelectedTool(null)} />
      )}
    </div>
  )
}
