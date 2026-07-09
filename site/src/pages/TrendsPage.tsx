import { useTools, useSnapshots } from '../hooks/useData'
import LoadingState from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import { useMemo } from 'react'

export default function TrendsPage() {
  const { tools, loading: toolsLoading } = useTools()
  const { snapshots, loading: snapshotLoading } = useSnapshots()

  // Compute stats from tools data
  const stats = useMemo(() => {
    if (tools.length === 0) return null

    // Category distribution by topics
    const categories: Record<string, number> = {}
    tools.forEach(tool => {
      tool.topics?.forEach(topic => {
        categories[topic] = (categories[topic] || 0) + 1
      })
    })

    // Language distribution
    const languages: Record<string, number> = {}
    tools.forEach(tool => {
      if (tool.language) {
        languages[tool.language] = (languages[tool.language] || 0) + 1
      }
    })

    // Source distribution
    const sources: Record<string, number> = {}
    tools.forEach(tool => {
      const src = tool.source_name || tool.source || '未知'
      sources[src] = (sources[src] || 0) + 1
    })

    // Top categories
    const topCategories = Object.entries(categories)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)

    // Top languages
    const topLanguages = Object.entries(languages)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)

    return {
      totalTools: tools.length,
      topCategories,
      topLanguages,
      sources,
    }
  }, [tools])

  const loading = toolsLoading || snapshotLoading

  if (loading) {
    return <LoadingState message="正在加载趋势数据..." />
  }

  // Use snapshot data if available, otherwise use computed stats
  const latestSnapshot = snapshots.length > 0 ? snapshots[0] : null

  if (!stats && !latestSnapshot) {
    return <EmptyState icon="📊" title="暂无趋势数据" description="数据采集中，请稍后再来" />
  }

  const totalTools = latestSnapshot?.total_tools || stats?.totalTools || 0
  const newThisWeek = latestSnapshot?.new_this_week || 0

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-slate-900 dark:text-white">
        📊 数据趋势
      </h2>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl p-5 text-white">
          <div className="text-3xl font-bold">{totalTools}</div>
          <div className="text-sm text-indigo-100 mt-1">收录工具总数</div>
        </div>
        <div className="bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl p-5 text-white">
          <div className="text-3xl font-bold">{newThisWeek}</div>
          <div className="text-sm text-green-100 mt-1">本周新增</div>
        </div>
        <div className="bg-gradient-to-br from-amber-500 to-orange-600 rounded-xl p-5 text-white">
          <div className="text-3xl font-bold">{stats?.topCategories.length || 0}</div>
          <div className="text-sm text-amber-100 mt-1">热门标签数</div>
        </div>
        <div className="bg-gradient-to-br from-pink-500 to-rose-600 rounded-xl p-5 text-white">
          <div className="text-3xl font-bold">{Object.keys(stats?.sources || {}).length}</div>
          <div className="text-sm text-pink-100 mt-1">数据来源</div>
        </div>
      </div>

      {/* Category distribution */}
      {stats && stats.topCategories.length > 0 && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">🏷️ 热门标签分布</h3>
          <div className="space-y-3">
            {stats.topCategories.map(([tag, count]) => {
              const maxCount = stats.topCategories[0][1]
              const percentage = (count / maxCount) * 100
              return (
                <div key={tag} className="flex items-center gap-3">
                  <span className="text-sm text-slate-600 dark:text-slate-400 w-24 truncate shrink-0">
                    {tag}
                  </span>
                  <div className="flex-1 h-6 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-500"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300 w-10 text-right">
                    {count}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Language distribution */}
      {stats && stats.topLanguages.length > 0 && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">💻 编程语言分布</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {stats.topLanguages.map(([lang, count]) => (
              <div key={lang} className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3 text-center">
                <div className="text-lg font-bold text-slate-900 dark:text-white">{count}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">{lang}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Source distribution */}
      {stats && Object.keys(stats.sources).length > 0 && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">📡 数据来源分布</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {Object.entries(stats.sources).map(([source, count]) => (
              <div key={source} className="flex items-center gap-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3">
                <div className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
                  <span className="text-sm">📦</span>
                </div>
                <div>
                  <div className="text-sm font-medium text-slate-700 dark:text-slate-300">{source}</div>
                  <div className="text-xs text-slate-500">{count} 个工具</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Snapshot history */}
      {snapshots.length > 1 && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">📈 历史趋势</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-slate-200 dark:border-slate-700">
                  <th className="pb-2 text-slate-600 dark:text-slate-400 font-medium">日期</th>
                  <th className="pb-2 text-slate-600 dark:text-slate-400 font-medium">工具总数</th>
                  <th className="pb-2 text-slate-600 dark:text-slate-400 font-medium">本周新增</th>
                </tr>
              </thead>
              <tbody>
                {snapshots.slice(0, 10).map((snap, idx) => (
                  <tr key={idx} className="border-b border-slate-100 dark:border-slate-800">
                    <td className="py-2 text-slate-700 dark:text-slate-300">{snap.date}</td>
                    <td className="py-2 text-slate-700 dark:text-slate-300">{snap.total_tools}</td>
                    <td className="py-2 text-green-500">+{snap.new_this_week}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
