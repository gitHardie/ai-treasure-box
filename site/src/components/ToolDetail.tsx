import type { ToolItem } from '../types'

function formatStars(stars: number | null | undefined): string {
  if (!stars) return "0"
  if (stars >= 1000) return (stars / 1000).toFixed(1) + 'k'
  return stars.toString()
}

function tagColor(tag: string): string {
  const colors = [
    'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
    'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
    'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
    'bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-300',
    'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-300',
    'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300',
    'bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-300',
  ]
  let hash = 0
  for (let i = 0; i < tag.length; i++) {
    hash = tag.charCodeAt(i) + ((hash << 5) - hash)
  }
  return colors[Math.abs(hash) % colors.length]
}

function licenseBadge(tier?: string): { label: string; cls: string } | null {
  if (!tier) return null
  const t = tier.toLowerCase()
  if (t.includes('open') || t.includes('mit') || t.includes('apache'))
    return { label: '开源', cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' }
  if (t.includes('free'))
    return { label: '免费', cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' }
  if (t.includes('paid') || t.includes('pro') || t.includes('premium'))
    return { label: '付费', cls: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400' }
  if (t.includes('freemium'))
    return { label: '免费增值', cls: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400' }
  return { label: tier, cls: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400' }
}

function healthDot(status?: string): { color: string; label: string } | null {
  if (!status) return null
  const s = status.toLowerCase()
  if (s.includes('active') || s === '活跃') return { color: 'bg-emerald-400', label: '活跃' }
  if (s.includes('moderate') || s === '一般') return { color: 'bg-amber-400', label: '一般' }
  if (s.includes('archived') || s === '归档') return { color: 'bg-red-400', label: '归档' }
  if (s.includes('silent') || s.includes('inactive') || s === '沉寂') return { color: 'bg-slate-400', label: '沉寂' }
  return null
}

const tagDimensionLabels: Record<string, string> = {
  function: '🔧 功能标签',
  scenario: '🎯 场景标签',
  attribute: '📋 属性标签',
  tech: '⚙️ 技术标签',
  quality: '⭐ 质量标签',
}

interface Props {
  tool: ToolItem
  onClose: () => void
}

export default function ToolDetail({ tool, onClose }: Props) {
  const license = licenseBadge(tool.license_tier || tool.license_type)
  const health = healthDot(tool.health_status)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fade-in" />
      <div
        className="relative bg-white dark:bg-slate-900 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto animate-slide-up border border-slate-200 dark:border-slate-700"
        onClick={e => e.stopPropagation()}
      >
        <div className="h-2 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 rounded-t-2xl" />
        <button
          className="absolute top-4 right-4 p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          onClick={onClose}
        >
          <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <div className="p-6">
          {/* Title section */}
          <div className="mb-6">
            <div className="flex items-start gap-4">
              <div className="flex-1">
                <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
                  {tool.name}
                </h2>
                {tool.full_name && tool.full_name !== tool.name && (
                  <p className="text-sm text-slate-500 mt-1">{tool.full_name}</p>
                )}
                <div className="flex flex-wrap gap-2 mt-2">
                  {tool.category && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded-lg text-xs font-medium">
                      {'📁'} {tool.category}
                    </span>
                  )}
                  {tool.subcategory && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-lg text-xs font-medium">
                      {'📂'} {tool.subcategory}
                    </span>
                  )}
                  {license && (
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium ${license.cls}`}>
                      {'📜'} {license.label}
                    </span>
                  )}
                  {health && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-slate-50 dark:bg-slate-800 rounded-lg text-xs font-medium text-slate-600 dark:text-slate-400">
                      <span className={`w-2 h-2 rounded-full ${health.color}`} />
                      {health.label}
                    </span>
                  )}
                </div>
              </div>
              <a
                href={tool.url}
                target="_blank"
                rel="noopener noreferrer"
                className="shrink-0 inline-flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg text-sm font-medium transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
                {'访问'}
              </a>
            </div>
          </div>

          {/* AI Analysis */}
          {tool.ai_analysis && (
            <div className="mb-6 p-4 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20 rounded-xl border border-indigo-100 dark:border-indigo-800/30">
              <h3 className="text-sm font-semibold text-indigo-700 dark:text-indigo-300 mb-2 flex items-center gap-1.5">
                <span>{'🤖'}</span> AI {'分析'}
                {tool.ai_confidence && (
                  <span className="ml-auto text-xs font-normal text-indigo-400 dark:text-indigo-500">
                    {'置信度'}: {(tool.ai_confidence * 100).toFixed(0)}%
                  </span>
                )}
              </h3>
              <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                {tool.ai_analysis}
              </p>
            </div>
          )}

          {/* Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
            <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3 text-center">
              <div className="text-2xl font-bold text-amber-500">{formatStars(tool.stars)}</div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">Stars</div>
            </div>
            <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3 text-center">
              <div className="text-2xl font-bold text-indigo-500">{formatStars(tool.forks)}</div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">Forks</div>
            </div>
            {tool.language && (
              <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3 text-center">
                <div className="text-2xl font-bold text-slate-700 dark:text-slate-300">{tool.language}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">{'语言'}</div>
              </div>
            )}
            <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3 text-center">
              <div className="text-sm font-medium text-slate-700 dark:text-slate-300 truncate">{tool.type || 'N/A'}</div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">{'类型'}</div>
            </div>
          </div>

          {/* Description */}
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">{'描述'}</h3>
            <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
              {tool.description || '暂无描述'}
            </p>
          </div>

          {/* Five-dimension tags */}
          {tool.tags && (
            <div className="mb-6 space-y-3">
              <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">{'标签详情'}</h3>
              {Object.entries(tool.tags).map(([dim, tags]) => {
                if (!Array.isArray(tags) || tags.length === 0) return null
                return (
                  <div key={dim}>
                    <div className="text-xs text-slate-500 dark:text-slate-400 mb-1.5">
                      {tagDimensionLabels[dim] || dim}
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {tags.map((tag: string) => (
                        <span key={tag} className={`badge text-xs ${tagColor(tag)}`}>
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* Topics */}
          {tool.topics && tool.topics.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">GitHub Topics</h3>
              <div className="flex flex-wrap gap-2">
                {tool.topics.map(tag => (
                  <span key={tag} className={`badge ${tagColor(tag)}`}>
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Source info */}
          <div className="flex items-center gap-4 text-xs text-slate-500 dark:text-slate-500 pt-4 border-t border-slate-100 dark:border-slate-800">
            {tool.source_name && (
              <span>{'数据来源'}: {tool.source_name}</span>
            )}
            {tool.collected_at && (
              <span>{'采集时间'}: {new Date(tool.collected_at).toLocaleString('zh-CN')}</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
