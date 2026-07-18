import { useMemo } from 'react'
import type { ToolItem } from '../types'
import { useFavorites } from '../hooks/useFavorites'

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
    'bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-300',
    'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  ]
  let hash = 0
  for (let i = 0; i < tag.length; i++) {
    hash = tag.charCodeAt(i) + ((hash << 5) - hash)
  }
  return colors[Math.abs(hash) % colors.length]
}

function langColor(lang?: string): string {
  const map: Record<string, string> = {
    Python: 'text-blue-400',
    JavaScript: 'text-yellow-400',
    TypeScript: 'text-blue-300',
    Go: 'text-cyan-400',
    Rust: 'text-orange-400',
    Java: 'text-red-400',
    'C++': 'text-pink-400',
    C: 'text-gray-400',
    Ruby: 'text-red-300',
    Swift: 'text-orange-300',
    Kotlin: 'text-purple-400',
    Shell: 'text-green-400',
    Svelte: 'text-orange-300',
  }
  return lang ? (map[lang] || 'text-slate-400') : ''
}

function formatStars(stars: number | null | undefined): string {
  if (!stars) return "0"
  if (stars >= 1000) return (stars / 1000).toFixed(1) + 'k'
  return stars.toString()
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
  if (t.includes('limited') || t.includes('freemium'))
    return { label: '限量', cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' }
  return null
}

function healthDot(status?: string): { color: string; label: string } | null {
  if (!status) return null
  const s = status.toLowerCase()
  if (s.includes('active') || s === '活跃')
    return { color: 'bg-emerald-400', label: '活跃' }
  if (s.includes('moderate') || s === '一般')
    return { color: 'bg-amber-400', label: '一般' }
  if (s.includes('archived') || s === '归档')
    return { color: 'bg-red-400', label: '归档' }
  if (s.includes('silent') || s.includes('inactive') || s === '沉寂')
    return { color: 'bg-slate-400', label: '沉寂' }
  return null
}

function getDomain(url: string): string {
  try { return new URL(url).hostname } catch { return '' }
}

function getDisplayTags(tool: ToolItem): string[] {
  if (tool.tags?.function && tool.tags.function.length > 0) return tool.tags.function
  if (tool.topics && Array.isArray(tool.topics) && tool.topics.length > 0) return tool.topics
  return []
}


function audienceBadge(audience?: string): { icon: string; label: string; cls: string } | null {
  if (!audience) return null
  if (audience === 'general') return { icon: '👤', label: '通用', cls: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' }
  if (audience === 'developer') return { icon: '💻', label: '开发者', cls: 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' }
  if (audience === 'researcher') return { icon: '🔬', label: '研究', cls: 'bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' }
  return null
}

function sourceLabel(source?: string): string {
  if (!source) return ''
  const map: Record<string, string> = {
    'github-trending': 'GitHub',
    'arxiv-ai': 'ArXiv',
    'hackernews-ai': 'HN',
  }
  return map[source] || source
}

interface Props {
  tool: ToolItem
  onClick: (tool: ToolItem) => void
  index?: number
}

export default function ToolCard({ tool, onClick, index = 0 }: Props) {
  const { toggle, isFavorite } = useFavorites()
  const toolId = tool.tool_id || tool.name + (tool.source || '')
  const fav = isFavorite(toolId)
  const license = useMemo(() => licenseBadge(tool.license_tier || tool.license_type), [tool.license_tier, tool.license_type])
  const health = useMemo(() => healthDot(tool.health_status), [tool.health_status])
  const domain = getDomain(tool.url)
  const displayTags = getDisplayTags(tool)
  const src = sourceLabel(tool.source)

  return (
    <div
      className="card-hover-v2 group relative bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden cursor-pointer"
      onClick={() => onClick(tool)}
      style={{ animationDelay: `${index * 50}ms` }}
    >
      {/* China badge */}
      {tool.is_china_tool && (
        <div className="absolute top-3 right-3 z-10">
          <span className="text-[10px] px-1.5 py-0.5 bg-red-500 text-white rounded-md font-bold shadow-sm">国内</span>
        </div>
      )}

      {/* Favorite button */}
      <button
        onClick={(e) => { e.stopPropagation(); toggle(toolId) }}
        className={`absolute top-3 left-3 z-10 p-1.5 rounded-full transition-all duration-200 ${
          fav
            ? 'bg-pink-100 dark:bg-pink-900/30 text-pink-500 scale-110'
            : 'bg-white/80 dark:bg-slate-800/80 text-slate-300 dark:text-slate-500 hover:text-pink-500'
        }`}
      >
        <svg className="w-4 h-4" fill={fav ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
        </svg>
      </button>

      <div className="p-5">
        {/* Header: icon + name + stars */}
        <div className="flex items-start gap-3 mb-3">
          {/* Favicon */}
          {domain ? (
            <img
              src={`https://www.google.com/s2/favicons?domain=${domain}&sz=32`}
              alt=""
              className="w-10 h-10 rounded-xl bg-slate-100 dark:bg-slate-800 shrink-0"
              onError={(e) => {
                const el = e.target as HTMLImageElement
                el.style.display = 'none'
              }}
            />
          ) : (
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center text-white font-bold text-sm shrink-0">
              {tool.name.charAt(0).toUpperCase()}
            </div>
          )}
          
          <div className="flex-1 min-w-0 pr-6">
            <h3 className="font-bold text-base text-slate-900 dark:text-white truncate group-hover:text-indigo-500 dark:group-hover:text-indigo-400 transition-colors">
              {tool.name}
            </h3>
            {tool.full_name && tool.full_name !== tool.name && (
              <p className="text-xs text-slate-500 dark:text-slate-500 truncate mt-0.5">
                {tool.full_name}
              </p>
            )}
          </div>

          {/* Stars - only show for GitHub tools */}
          {(tool.stars ?? 0) > 0 && (
          <div className="flex items-center gap-1 text-amber-500 dark:text-amber-400 shrink-0">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
            <span className="text-sm font-bold bg-gradient-to-r from-amber-500 to-orange-500 bg-clip-text text-transparent">
              {formatStars(tool.stars)}
            </span>
          </div>
          )}
        </div>

        {/* Description - prefer AI analysis (Chinese) over raw English description */}
        <p className="text-sm text-slate-600 dark:text-slate-400 line-clamp-2 mb-2 leading-relaxed">
          {tool.ai_analysis || tool.description}
        </p>

        {/* Tags + badges */}
        <div className="flex flex-wrap items-center gap-1.5 mb-2">
          {license && (
            <span className={`badge text-[9px] ${license.cls}`}>{license.label}</span>
          )}
          {tool.category && (
            <span className="badge text-[9px] bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300 font-medium">
              {tool.category}
            </span>
          )}
          {(() => {
            const badge = audienceBadge(tool.audience)
            return badge ? (
              <span className={`badge text-[9px] ${badge.cls}`}>{badge.icon} {badge.label}</span>
            ) : null
          })()}
          {/* Scenario tags */}
          {tool.tags?.scenario?.slice(0, 2).map(tag => (
            <span key={`s-${tag}`} className="badge text-[9px] bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">🎯 {tag}</span>
          ))}
          {/* Function tags */}
          {displayTags.slice(0, 3).map(tag => (
            <span key={tag} className={`badge text-[9px] ${tagColor(tag)}`}>{tag}</span>
          ))}
          {(displayTags.length + (tool.tags?.scenario?.length || 0)) > 5 && (
            <span className="badge text-[9px] bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400">
              +{(displayTags.length + (tool.tags?.scenario?.length || 0)) - 5}
            </span>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-500 pt-3 border-t border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-3">
            {tool.language && (
              <span className={`flex items-center gap-1 ${langColor(tool.language)}`}>
                <span className="w-2 h-2 rounded-full bg-current"></span>
                {tool.language}
              </span>
            )}
            {health && (
              <span className="flex items-center gap-1">
                <span className={`w-2 h-2 rounded-full ${health.color}`}></span>
                <span className="text-slate-400">{health.label}</span>
              </span>
            )}
            {(tool.stars ?? 0) > 0 && (
            <span className="flex items-center gap-1">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
              </svg>
              {formatStars(tool.forks)}
            </span>
            )}
          </div>
          {src && (
            <span className="truncate max-w-[100px]">via {src}</span>
          )}
        </div>
      </div>
    </div>
  )
}
