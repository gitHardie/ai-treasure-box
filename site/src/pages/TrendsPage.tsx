import { useTools, useSnapshots, useCategories, useStats } from '../hooks/useData'
import LoadingState from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import { useMemo } from 'react'

const emojiMap: Record<string, string> = {
  '代码开发': '💻',
  '学术研究': '🔬',
  '数据分析': '📊',
  '文本生成': '✍️',
  '图像创作': '🎨',
  '音视频': '🎵',
  '教育培训': '📚',
  '办公效率': '⚡',
  '设计创意': '🎭',
  '开发工具': '🛠️',
  '其他': '📦',
}

export default function TrendsPage() {
  const { tools, loading: toolsLoading } = useTools()
  const { snapshots, loading: snapshotLoading } = useSnapshots()
  const { categories: catsData } = useCategories()
  const { stats: statsData } = useStats()

  const computed = useMemo(() => {
    if (tools.length === 0) return null

    const languages: Record<string, number> = {}
    tools.forEach(tool => {
      if (tool.language) {
        languages[tool.language] = (languages[tool.language] || 0) + 1
      }
    })

    const sources: Record<string, number> = {}
    tools.forEach(tool => {
      const src = tool.source_name || tool.source || '未知'
      sources[src] = (sources[src] || 0) + 1
    })

    const topLanguages = Object.entries(languages)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)

    return { topLanguages, sources }
  }, [tools])

  const categoryEntries = useMemo(() => {
    if (!catsData?.categories) return []
    return Object.entries(catsData.categories)
      .sort((a, b) => b[1] - a[1])
  }, [catsData])

  const licenseEntries = useMemo(() => {
    const lc = statsData?.license_counts
    if (!lc || typeof lc !== 'object') return []
    return Object.entries(lc).sort((a, b) => b[1] - a[1])
  }, [statsData])

  const loading = toolsLoading || snapshotLoading

  if (loading) {
    return <LoadingState message={'正在加载趋势数据...'} />
  }

  const latestSnapshot = snapshots.length > 0 ? snapshots[0] : null

  if (!computed && !latestSnapshot && categoryEntries.length === 0) {
    return <EmptyState icon={'📊'} title={'暂无趋势数据'} description={'数据采集中，请稍后再来'} />
  }

  const totalTools = statsData?.total_tools || latestSnapshot?.total_tools || tools.length
  const newThisWeek = statsData?.new_this_week || latestSnapshot?.new_this_week || 0
  const categoryCount = categoryEntries.length
  const sourceCount = Object.keys(computed?.sources || {}).length || (statsData?.source_counts ? Object.keys(statsData.source_counts).length : 0)

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-slate-900 dark:text-white">
        {'📊'} {'数据趋势'}
      </h2>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl p-5 text-white">
          <div className="text-3xl font-bold">{totalTools}</div>
          <div className="text-sm text-indigo-100 mt-1">{'收录工具总数'}</div>
        </div>
        <div className="bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl p-5 text-white">
          <div className="text-3xl font-bold">{categoryCount}</div>
          <div className="text-sm text-green-100 mt-1">{'分类数'}</div>
        </div>
        <div className="bg-gradient-to-br from-amber-500 to-orange-600 rounded-xl p-5 text-white">
          <div className="text-3xl font-bold">{sourceCount}</div>
          <div className="text-sm text-amber-100 mt-1">{'数据源数'}</div>
        </div>
        <div className="bg-gradient-to-br from-pink-500 to-rose-600 rounded-xl p-5 text-white">
          <div className="text-3xl font-bold">{newThisWeek}</div>
          <div className="text-sm text-pink-100 mt-1">{'本周新增'}</div>
        </div>
      </div>

      {categoryEntries.length > 0 && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">{'📁'} {'分类工具分布'}</h3>
          <div className="space-y-3">
            {categoryEntries.map(([cat, count]) => {
              const maxCount = categoryEntries[0][1]
              const percentage = (count / maxCount) * 100
              return (
                <div key={cat} className="flex items-center gap-3">
                  <span className="text-lg shrink-0">{emojiMap[cat] || '📁'}</span>
                  <span className="text-sm text-slate-600 dark:text-slate-400 w-20 truncate shrink-0">
                    {cat}
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

      {licenseEntries.length > 0 && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">{'📜'} {'许可证分布'}</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {licenseEntries.map(([tier, count]) => (
              <div key={tier} className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3 text-center">
                <div className="text-lg font-bold text-slate-900 dark:text-white">{count}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400 mt-1 truncate">{tier}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {computed && computed.topLanguages.length > 0 && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">{'💻'} {'编程语言分布'}</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {computed.topLanguages.map(([lang, count]) => (
              <div key={lang} className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3 text-center">
                <div className="text-lg font-bold text-slate-900 dark:text-white">{count}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">{lang}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {computed && Object.keys(computed.sources).length > 0 && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">{'📡'} {'数据来源分布'}</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {Object.entries(computed.sources).map(([source, count]) => (
              <div key={source} className="flex items-center gap-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3">
                <div className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
                  <span className="text-sm">{'📦'}</span>
                </div>
                <div>
                  <div className="text-sm font-medium text-slate-700 dark:text-slate-300">{source}</div>
                  <div className="text-xs text-slate-500">{count} {'个工具'}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {snapshots.length > 1 && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">{'📈'} {'历史趋势'}</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-slate-200 dark:border-slate-700">
                  <th className="pb-2 text-slate-600 dark:text-slate-400 font-medium">{'日期'}</th>
                  <th className="pb-2 text-slate-600 dark:text-slate-400 font-medium">{'工具总数'}</th>
                  <th className="pb-2 text-slate-600 dark:text-slate-400 font-medium">{'本周新增'}</th>
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
