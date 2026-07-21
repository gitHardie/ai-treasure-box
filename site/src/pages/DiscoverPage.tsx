import { useState, useMemo, useEffect } from 'react'
import type { ToolItem } from '../types'
import { useTools, useCategories, useStats } from '../hooks/useData'
import ToolCard from '../components/ToolCard'
import ToolDetail from '../components/ToolDetail'
import CategorySidebar from '../components/CategorySidebar'
import LoadingState from '../components/LoadingState'
import EmptyState from '../components/EmptyState'



export default function DiscoverPage() {
  const { tools, loading, error } = useTools()
  const { categories: catsData } = useCategories()
  const [search, setSearch] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [chinaOnly, setChinaOnly] = useState(false)
  const [selectedScenario, setSelectedScenario] = useState('all')
  const [selectedTool, setSelectedTool] = useState<ToolItem | null>(null)
  const { stats: statsData } = useStats()

  // Deduplicate tools by name+source (fix duplicate key issue)
  const uniqueTools = useMemo(() => {
    const seen = new Set<string>()
    return tools.filter(t => {
      const key = (t.tool_id || t.name + (t.source || ''))
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
  }, [tools])

  // Exclude papers and news - these are not usable tools
  const realTools = useMemo(() => {
    return uniqueTools.filter(t => t.type !== 'paper' && t.type !== 'news')
  }, [uniqueTools])

  // Compute category counts from real tools only
  const realCategoryCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const t of realTools) {
      const c = t.category || '其他'
      counts[c] = (counts[c] || 0) + 1
    }
    return counts
  }, [realTools])

  // Count per hot category
  // Build category list from Master DB
  const hotCategoryCounts = useMemo(() => {
    const emojiMap: Record<string, string> = {
      '代码开发': '💻', '学术研究': '🔬', '数据分析': '📊',
      '文本生成': '✍️', '图像创作': '🎨', '音视频': '🎵',
      '教育培训': '📚', '办公效率': '⚡', '设计创意': '🎭',
      '开发工具': '🛠️', 'AI Agent': '🤖', '金融科技': '💰', '安全合规': '🛡️', '生活服务': '🏠', '其他': '📦',
    }
    return Object.entries(realCategoryCounts)
      .filter(([, count]) => count > 0)
      .sort((a, b) => b[1] - a[1])
      .map(([label, count]) => ({
        label,
        emoji: emojiMap[label] || '📁',
        count,
      }))
  }, [realCategoryCounts])

  // Collect all scenario tags from tools
  const allScenarios = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const t of realTools) {
      t.tags?.scenario?.forEach(s => {
        if (s) counts[s] = (counts[s] || 0) + 1
      })
    }
    return Object.entries(counts)
      .filter(([, c]) => c >= 2)
      .sort((a, b) => b[1] - a[1])
      .map(([label, count]) => ({ label, count }))
  }, [realTools])

  // SINGLE useMemo for all filtering - eliminates intermediate caching issues
  const filteredTools = useMemo(() => {
    let result = realTools

    // Step 1: Filter by category
    if (selectedCategory !== 'all') {
      result = result.filter(t => t.category === selectedCategory)
    }

    // Step 2: Filter by scenario
    if (selectedScenario !== 'all') {
      result = result.filter(t => t.tags?.scenario?.includes(selectedScenario))
    }

    // Step 3: Filter by china only
    if (chinaOnly) {
      result = result.filter(t => t.is_china_tool)
    }

    // Step 4: Filter by search
    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(tool =>
        tool.name.toLowerCase().includes(q) ||
        tool.description?.toLowerCase().includes(q) ||
        tool.topics?.some(t => t.toLowerCase().includes(q)) ||
        tool.tags?.function?.some(t => t.toLowerCase().includes(q)) ||
        tool.category?.toLowerCase().includes(q) ||
        tool.full_name?.toLowerCase().includes(q)
      )
    }

    return result
  }, [realTools, selectedCategory, chinaOnly, search])

  // Scroll to grid when category changes
  useEffect(() => {
    if (selectedCategory !== 'all') {
      // Small delay to let the DOM update
      setTimeout(() => {
        const grid = document.querySelector('.tools-grid')
        if (grid) {
          grid.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
      }, 100)
    }
  }, [selectedCategory])

  if (loading) return <LoadingState message="正在加载工具数据..." />
  if (error) return <EmptyState icon="⚠️" title="加载失败" description={error} />

  return (
    <div>
      {/* Hero Section */}
      <div className="hero-section relative -mx-4 sm:-mx-6 -mt-6 mb-8 px-4 sm:px-6 pt-12 pb-10 overflow-hidden">
        <div className="absolute inset-0 hero-gradient-bg" />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-slate-50 dark:to-slate-950" />
        
        <div className="relative z-10 max-w-3xl mx-auto text-center">
          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold mb-4 leading-tight">
            <span className="hero-gradient-text">发现下一个</span>
            <br />
            <span className="hero-gradient-text-2">AI 神器</span>
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-base sm:text-lg mb-8 max-w-xl mx-auto">
            精选全球优质 AI 工具，助你高效工作、释放创造力
          </p>

          {/* Search */}
          <div className="max-w-xl mx-auto mb-8">
            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
                <svg className="w-5 h-5 text-slate-400 group-focus-within:text-indigo-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <input
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="搜索工具名称、描述或标签..."
                className="w-full pl-12 pr-16 sm:pl-14 sm:pr-20 py-3 sm:py-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 shadow-lg shadow-indigo-500/5 transition-all text-base"
              />
              <div className="absolute inset-y-0 right-0 pr-5 flex items-center">
                <kbd className="hidden sm:inline-flex items-center px-2 py-1 text-xs text-slate-400 bg-slate-100 dark:bg-slate-800 rounded-lg font-mono border border-slate-200 dark:border-slate-700">
                  ⌘K
                </kbd>
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="hidden sm:flex items-center justify-center gap-6 sm:gap-10 mb-8">
            <div className="text-center">
              <div className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white">
                {statsData?.total_tools || realTools.length}
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">收录工具</div>
            </div>
            <div className="w-px h-8 bg-slate-200 dark:bg-slate-700" />
            <div className="text-center">
              <div className="text-2xl sm:text-3xl font-bold text-emerald-500">
                {statsData?.new_this_week || 0}
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">本周新增</div>
            </div>
            <div className="w-px h-8 bg-slate-200 dark:bg-slate-700" />
            <div className="text-center">
              <div className="text-2xl sm:text-3xl font-bold text-indigo-500">
                {Object.keys(statsData?.category_counts || {}).length || '—'}
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">分类覆盖</div>
            </div>
          </div>

          {/* Hot categories */}
          <div className="hidden sm:grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-2xl mx-auto">
            {hotCategoryCounts.slice(0, 8).map(cat => (
              <button
                key={cat.label}
                onClick={() => setSelectedCategory(cat.label)}
                className="flex items-center gap-2 px-4 py-3 bg-white/60 dark:bg-slate-900/60 backdrop-blur-sm rounded-xl border border-slate-200/60 dark:border-slate-700/60 hover:border-indigo-300 dark:hover:border-indigo-600 hover:bg-white dark:hover:bg-slate-800 transition-all duration-200 group"
              >
                <span className="text-xl group-hover:scale-110 transition-transform">{cat.emoji}</span>
                <div className="text-left">
                  <div className="text-sm font-medium text-slate-700 dark:text-slate-300">{cat.label}</div>
                  <div className="text-xs text-slate-400">{cat.count} 个工具</div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main content with sidebar */}
      <div className="flex flex-col lg:flex-row gap-6">
        <CategorySidebar
          tools={realTools}
          selectedCategory={selectedCategory}
          onCategoryChange={setSelectedCategory}
          chinaOnly={chinaOnly}
          onChinaOnlyChange={setChinaOnly}
          categoryCounts={realCategoryCounts}
        />

        <div className="flex-1 min-w-0 space-y-6">
          {/* Scenario filter pills */}
          {allScenarios.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-slate-500 dark:text-slate-400 shrink-0">场景:</span>
              <button
                onClick={() => setSelectedScenario('all')}
                className={`px-2.5 py-1 rounded-full text-xs transition-all ${
                  selectedScenario === 'all'
                    ? 'bg-indigo-500 text-white shadow-sm'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                }`}
              >
                全部
              </button>
              {allScenarios.slice(0, 12).map(s => (
                <button
                  key={s.label}
                  onClick={() => setSelectedScenario(selectedScenario === s.label ? 'all' : s.label)}
                  className={`px-2.5 py-1 rounded-full text-xs transition-all ${
                    selectedScenario === s.label
                      ? 'bg-indigo-500 text-white shadow-sm'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                  }`}
                >
                  {s.label}
                  <span className="ml-1 opacity-60">{s.count}</span>
                </button>
              ))}
            </div>
          )}

          {/* Results count */}
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {search || selectedCategory !== 'all' || selectedScenario !== 'all'
                ? `找到 ${filteredTools.length} 个工具`
                : `共 ${realTools.length} 个工具`}
            </p>
            {(selectedCategory !== 'all' || selectedScenario !== 'all') && (
              <button
                onClick={() => { setSelectedCategory('all'); setSelectedScenario('all') }}
                className="text-xs text-indigo-500 hover:text-indigo-600 dark:text-indigo-400"
              >
                清除筛选 ✕
              </button>
            )}
          </div>

          {/* Grid - key forces complete re-mount when filter changes */}
          {filteredTools.length > 0 ? (
            <div key={`grid-${selectedCategory}-${selectedScenario}-${chinaOnly}-${search ? 's' : ''}`} className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4 tools-grid">
              {filteredTools.map((tool, idx) => (
                <ToolCard
                  key={tool.tool_id || tool.name + (tool.source || '')}
                  tool={tool}
                  onClick={setSelectedTool}
                  index={idx}
                />
              ))}
            </div>
          ) : (
            <EmptyState
              icon="🔍"
              title="没有找到匹配的工具"
              description="试试调整搜索关键词或切换分类"
            />
          )}
        </div>
      </div>

      {selectedTool && (
        <ToolDetail tool={selectedTool} onClose={() => setSelectedTool(null)} />
      )}
    </div>
  )
}
