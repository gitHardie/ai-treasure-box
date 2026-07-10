import { useState, useMemo } from 'react'
import type { ToolItem } from '../types'
import { useCategories } from '../hooks/useData'

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

interface Props {
  tools: ToolItem[]
  selectedCategory: string
  onCategoryChange: (cat: string) => void
  chinaOnly: boolean
  onChinaOnlyChange: (v: boolean) => void
}

export default function CategorySidebar({ tools, selectedCategory, onCategoryChange, chinaOnly, onChinaOnlyChange }: Props) {
  const [expanded, setExpanded] = useState(true)
  const { categories: catsData } = useCategories()

  const categories = useMemo(() => {
    const allItem = { id: 'all', label: '全部工具', emoji: '🏠', count: tools.length }
    if (!catsData?.categories) return [allItem]

    const catList = Object.entries(catsData.categories)
      .sort((a, b) => b[1] - a[1])
      .map(([label, count]) => ({
        id: label,
        label,
        emoji: emojiMap[label] || '📁',
        count,
      }))

    return [allItem, ...catList]
  }, [catsData, tools.length])

  return (
    <>
      {/* Desktop sidebar */}
      <aside className={`hidden lg:block shrink-0 transition-all duration-300 ${expanded ? 'w-56' : 'w-16'}`}>
        <div className="sticky top-20 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            {expanded && <span>分类导航</span>}
            <svg className={`w-4 h-4 transition-transform ${expanded ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>

          {expanded && (
            <div className="px-3 pb-2">
              <div className="flex bg-slate-100 dark:bg-slate-800 rounded-lg p-0.5">
                <button
                  onClick={() => onChinaOnlyChange(false)}
                  className={`flex-1 text-xs py-1.5 rounded-md transition-all ${!chinaOnly ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-sm font-medium' : 'text-slate-500'}`}
                >
                  {'🌍'} 国际
                </button>
                <button
                  onClick={() => onChinaOnlyChange(true)}
                  className={`flex-1 text-xs py-1.5 rounded-md transition-all ${chinaOnly ? 'bg-white dark:bg-slate-700 text-red-600 dark:text-red-400 shadow-sm font-medium' : 'text-slate-500'}`}
                >
                  {'🇨🇳'} 国内
                </button>
              </div>
            </div>
          )}

          <nav className="px-2 pb-2 space-y-0.5 max-h-[calc(100vh-200px)] overflow-y-auto">
            {categories.map(cat => (
              <button
                key={cat.id}
                onClick={() => onCategoryChange(cat.id)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-left transition-all duration-200 group ${
                  selectedCategory === cat.id
                    ? 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <span className="text-lg shrink-0">{cat.emoji}</span>
                {expanded && (
                  <>
                    <span className="flex-1 text-sm truncate">{cat.label}</span>
                    <span className={`text-xs tabular-nums ${
                      selectedCategory === cat.id
                        ? 'text-indigo-500 dark:text-indigo-400 font-medium'
                        : 'text-slate-400 dark:text-slate-500'
                    }`}>
                      {cat.count}
                    </span>
                  </>
                )}
              </button>
            ))}
          </nav>
        </div>
      </aside>

      {/* Mobile: horizontal scroll */}
      <div className="lg:hidden -mx-4 px-4 overflow-x-auto scrollbar-hide">
        <div className="flex gap-2 pb-3 min-w-max">
          {categories.map(cat => (
            <button
              key={cat.id}
              onClick={() => onCategoryChange(cat.id)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-full text-sm whitespace-nowrap transition-all ${
                selectedCategory === cat.id
                  ? 'bg-indigo-500 text-white shadow-md shadow-indigo-500/25'
                  : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700 hover:border-indigo-300 dark:hover:border-indigo-600'
              }`}
            >
              <span>{cat.emoji}</span>
              <span>{cat.label}</span>
              <span className={`text-xs ${selectedCategory === cat.id ? 'text-indigo-200' : 'text-slate-400'}`}>
                {cat.count}
              </span>
            </button>
          ))}
        </div>
      </div>
    </>
  )
}
