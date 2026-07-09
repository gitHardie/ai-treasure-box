import type { ToolItem } from '../types'

// Generate a color class based on string hash
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
  }
  return lang ? (map[lang] || 'text-slate-400') : ''
}

function formatStars(stars: number): string {
  if (stars >= 1000) {
    return (stars / 1000).toFixed(1) + 'k'
  }
  return stars.toString()
}

interface Props {
  tool: ToolItem
  onClick: (tool: ToolItem) => void
}

export default function ToolCard({ tool, onClick }: Props) {
  return (
    <div
      className="card-hover bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 cursor-pointer group"
      onClick={() => onClick(tool)}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-base text-slate-900 dark:text-white truncate group-hover:text-indigo-500 dark:group-hover:text-indigo-400 transition-colors">
            {tool.name}
          </h3>
          {tool.full_name && tool.full_name !== tool.name && (
            <p className="text-xs text-slate-500 dark:text-slate-500 mt-0.5 truncate">
              {tool.full_name}
            </p>
          )}
        </div>
        <div className="flex items-center gap-1 text-amber-500 dark:text-amber-400 ml-2 shrink-0">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
          <span className="text-sm font-medium">{formatStars(tool.stars)}</span>
        </div>
      </div>

      {/* Description */}
      <p className="text-sm text-slate-600 dark:text-slate-400 line-clamp-2 mb-3 leading-relaxed">
        {tool.description}
      </p>

      {/* Tags */}
      {tool.topics && tool.topics.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {tool.topics.slice(0, 5).map(tag => (
            <span key={tag} className={`badge ${tagColor(tag)}`}>
              {tag}
            </span>
          ))}
          {tool.topics.length > 5 && (
            <span className="badge bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400">
              +{tool.topics.length - 5}
            </span>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-500 pt-2 border-t border-slate-100 dark:border-slate-800">
        <div className="flex items-center gap-3">
          {tool.language && (
            <span className={`flex items-center gap-1 ${langColor(tool.language)}`}>
              <span className="w-2 h-2 rounded-full bg-current"></span>
              {tool.language}
            </span>
          )}
          <span className="flex items-center gap-1">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
            </svg>
            {formatStars(tool.forks)}
          </span>
        </div>
        {tool.source_name && (
          <span className="truncate max-w-[120px]">
            via {tool.source_name}
          </span>
        )}
      </div>
    </div>
  )
}
