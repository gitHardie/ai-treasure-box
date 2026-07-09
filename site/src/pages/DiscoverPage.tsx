import { useState, useMemo } from 'react'
import type { ToolItem } from '../types'
import { useTools } from '../hooks/useData'
import ToolCard from '../components/ToolCard'
import ToolDetail from '../components/ToolDetail'
import SearchBar from '../components/SearchBar'
import TagFilter from '../components/TagFilter'
import LoadingState from '../components/LoadingState'
import EmptyState from '../components/EmptyState'

export default function DiscoverPage() {
  const { tools, loading, error } = useTools()
  const [search, setSearch] = useState('')
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [selectedTool, setSelectedTool] = useState<ToolItem | null>(null)

  // Extract all unique tags
  const allTags = useMemo(() => {
    const tagCount = new Map<string, number>()
    tools.forEach(tool => {
      tool.topics?.forEach(tag => {
        tagCount.set(tag, (tagCount.get(tag) || 0) + 1)
      })
    })
    return Array.from(tagCount.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 30)
      .map(([tag]) => tag)
  }, [tools])

  // Filter tools
  const filteredTools = useMemo(() => {
    let result = tools

    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(tool =>
        tool.name.toLowerCase().includes(q) ||
        tool.description?.toLowerCase().includes(q) ||
        tool.topics?.some(t => t.toLowerCase().includes(q)) ||
        tool.full_name?.toLowerCase().includes(q)
      )
    }

    if (selectedTags.length > 0) {
      result = result.filter(tool =>
        selectedTags.every(tag => tool.topics?.includes(tag))
      )
    }

    return result
  }, [tools, search, selectedTags])

  const toggleTag = (tag: string) => {
    setSelectedTags(prev =>
      prev.includes(tag)
        ? prev.filter(t => t !== tag)
        : [...prev, tag]
    )
  }

  if (loading) {
    return <LoadingState message="正在加载工具数据..." />
  }

  if (error) {
    return <EmptyState icon="⚠️" title="加载失败" description={error} />
  }

  return (
    <div className="space-y-6">
      {/* Search */}
      <div className="max-w-2xl mx-auto">
        <SearchBar value={search} onChange={setSearch} />
      </div>

      {/* Tag filter */}
      {allTags.length > 0 && (
        <TagFilter
          tags={allTags}
          selectedTags={selectedTags}
          onToggleTag={toggleTag}
          onClearAll={() => setSelectedTags([])}
        />
      )}

      {/* Results count */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {search || selectedTags.length > 0
            ? `找到 ${filteredTools.length} 个工具`
            : `共 ${tools.length} 个工具`}
        </p>
      </div>

      {/* Grid */}
      {filteredTools.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTools.map(tool => (
            <ToolCard
              key={tool.name + (tool.source || '')}
              tool={tool}
              onClick={setSelectedTool}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          icon="🔍"
          title="没有找到匹配的工具"
          description="试试调整搜索关键词或清除筛选标签"
        />
      )}

      {/* Detail modal */}
      {selectedTool && (
        <ToolDetail tool={selectedTool} onClose={() => setSelectedTool(null)} />
      )}
    </div>
  )
}
