import { useState, useEffect, useRef, useCallback } from 'react'
import type { ToolItem } from '../types'

interface Props {
  tools: ToolItem[]
  isOpen: boolean
  onClose: () => void
  onSelect: (tool: ToolItem) => void
}

interface SearchResult {
  tool: ToolItem
  matchType: string
}

const RECENT_KEY = 'ai-treasure-recent-searches'

function getRecentSearches(): string[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function addRecentSearch(term: string) {
  const recent = getRecentSearches().filter(s => s !== term)
  recent.unshift(term)
  localStorage.setItem(RECENT_KEY, JSON.stringify(recent.slice(0, 8)))
}

export default function CommandPalette({ tools, isOpen, onClose, onSelect }: Props) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [recentSearches, setRecentSearches] = useState<string[]>(getRecentSearches())
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const results: SearchResult[] = query.trim()
    ? (() => {
        const q = query.toLowerCase()
        const matched = tools
          .filter(tool =>
            tool.name.toLowerCase().includes(q) ||
            tool.description?.toLowerCase().includes(q) ||
            tool.topics?.some(t => t.toLowerCase().includes(q)) ||
            tool.full_name?.toLowerCase().includes(q) ||
            tool.category?.toLowerCase().includes(q)
          )
          .slice(0, 10)
          .map(tool => ({
            tool,
            matchType: tool.name.toLowerCase().includes(q) ? '名称匹配' :
                       tool.topics?.some(t => t.toLowerCase().includes(q)) ? '标签匹配' : '描述匹配'
          }))
        return matched
      })()
    : []

  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setSelectedIndex(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [isOpen])

  const handleSelect = useCallback((tool: ToolItem) => {
    if (query.trim()) addRecentSearch(query.trim())
    setRecentSearches(getRecentSearches())
    onSelect(tool)
    onClose()
  }, [query, onSelect, onClose])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex(prev => Math.min(prev + 1, results.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex(prev => Math.max(prev - 1, 0))
    } else if (e.key === 'Enter' && results[selectedIndex]) {
      e.preventDefault()
      handleSelect(results[selectedIndex].tool)
    } else if (e.key === 'Escape') {
      onClose()
    }
  }

  useEffect(() => {
    const el = listRef.current?.children[selectedIndex] as HTMLElement
    el?.scrollIntoView({ block: 'nearest' })
  }, [selectedIndex])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[100]" onClick={onClose}>
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-fade-in" />
      
      {/* Panel */}
      <div className="relative flex justify-center pt-[15vh] px-4" onClick={e => e.stopPropagation()}>
        <div className="w-full max-w-2xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden animate-slide-up">
          {/* Search Input */}
          <div className="flex items-center px-5 border-b border-slate-200 dark:border-slate-700">
            <svg className="w-5 h-5 text-slate-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={e => { setQuery(e.target.value); setSelectedIndex(0) }}
              onKeyDown={handleKeyDown}
              placeholder="搜索工具名称、描述、标签..."
              className="flex-1 px-4 py-4 bg-transparent text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none text-lg"
            />
            <kbd className="hidden sm:inline-flex items-center px-2 py-1 text-xs text-slate-400 bg-slate-100 dark:bg-slate-800 rounded font-mono">
              ESC
            </kbd>
          </div>

          {/* Results */}
          <div ref={listRef} className="max-h-[50vh] overflow-y-auto">
            {results.length > 0 ? (
              <div className="p-2">
                {results.map((result, idx) => (
                  <button
                    key={result.tool.name + (result.tool.source || '')}
                    onClick={() => handleSelect(result.tool)}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-left transition-colors ${
                      idx === selectedIndex
                        ? 'bg-indigo-50 dark:bg-indigo-900/20'
                        : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'
                    }`}
                  >
                    <img
                      src={`https://www.google.com/s2/favicons?domain=${new URL(result.tool.url).hostname}&sz=32`}
                      alt=""
                      className="w-8 h-8 rounded-lg shrink-0 bg-slate-100 dark:bg-slate-800"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-slate-900 dark:text-white truncate">
                          {result.tool.name}
                        </span>
                        {result.tool.is_china_tool && (
                          <span className="text-[10px] px-1.5 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded font-medium">国内</span>
                        )}
                        <span className="text-xs text-slate-400">{result.matchType}</span>
                      </div>
                      <p className="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5">
                        {result.tool.description}
                      </p>
                    </div>
                    <div className="text-xs text-amber-500 font-medium shrink-0">
                      ★ {result.tool.stars >= 1000 ? (result.tool.stars / 1000).toFixed(1) + 'k' : result.tool.stars}
                    </div>
                  </button>
                ))}
              </div>
            ) : query.trim() ? (
              <div className="py-12 text-center">
                <span className="text-3xl mb-3 block">🔍</span>
                <p className="text-sm text-slate-500 dark:text-slate-400">未找到匹配的工具</p>
              </div>
            ) : (
              <div className="p-4">
                {recentSearches.length > 0 && (
                  <>
                    <p className="text-xs font-medium text-slate-500 dark:text-slate-400 px-3 mb-2">最近搜索</p>
                    <div className="flex flex-wrap gap-2 px-3">
                      {recentSearches.slice(0, 6).map(term => (
                        <button
                          key={term}
                          onClick={() => { setQuery(term); inputRef.current?.focus() }}
                          className="px-3 py-1.5 text-xs bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 rounded-full hover:bg-indigo-50 dark:hover:bg-indigo-900/20 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
                        >
                          {term}
                        </button>
                      ))}
                    </div>
                  </>
                )}
                <div className="mt-4 px-3">
                  <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2">快捷提示</p>
                  <div className="space-y-1.5 text-xs text-slate-400">
                    <div className="flex items-center gap-2">
                      <kbd className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 rounded font-mono text-[10px]">↑↓</kbd>
                      <span>导航结果</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <kbd className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 rounded font-mono text-[10px]">↵</kbd>
                      <span>打开选中</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <kbd className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 rounded font-mono text-[10px]">esc</kbd>
                      <span>关闭面板</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-5 py-3 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between text-xs text-slate-400">
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1">
                <kbd className="px-1 py-0.5 bg-slate-100 dark:bg-slate-800 rounded font-mono text-[10px]">↑↓</kbd>
                选择
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1 py-0.5 bg-slate-100 dark:bg-slate-800 rounded font-mono text-[10px]">↵</kbd>
                打开
              </span>
            </div>
            <span>共收录 {tools.length} 个工具</span>
          </div>
        </div>
      </div>
    </div>
  )
}
