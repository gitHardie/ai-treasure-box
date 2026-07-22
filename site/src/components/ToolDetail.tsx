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

function audienceInfo(audience?: string): { icon: string; label: string; desc: string; cls: string } | null {
  if (!audience) return null
  if (audience === 'general') return { icon: '👤', label: '通用', desc: '普通用户可直接使用，无需技术背景', cls: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800/50' }
  if (audience === 'developer') return { icon: '💻', label: '开发者', desc: '适合有技术背景的开发者集成使用', cls: 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 border-blue-200 dark:border-blue-800/50' }
  if (audience === 'researcher') return { icon: '🔬', label: '研究', desc: '主要面向研究人员和学术场景', cls: 'bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 border-purple-200 dark:border-purple-800/50' }
  return null
}

function aiRelevanceInfo(relevance?: string): { icon: string; label: string; desc: string; cls: string; border_cls: string } | null {
  if (!relevance) return null
  if (relevance === 'ai-core')
    return {
      icon: '🧠', label: 'AI核心',
      desc: '核心AI能力，项目以AI/机器学习为主要功能',
      cls: 'bg-gradient-to-r from-violet-500 to-indigo-500 text-white',
      border_cls: 'border-violet-300 dark:border-violet-700'
    }
  if (relevance === 'ai-powered')
    return {
      icon: '⚡', label: 'AI驱动',
      desc: 'AI驱动型产品，深度集成AI能力作为核心功能之一',
      cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
      border_cls: 'border-blue-200 dark:border-blue-800/50'
    }
  if (relevance === 'ai-enabled')
    return {
      icon: '🔗', label: 'AI集成',
      desc: '集成AI功能，AI作为辅助或增强能力',
      cls: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
      border_cls: 'border-slate-200 dark:border-slate-700'
    }
  return null
}

const tagDimensionLabels: Record<string, string> = {
  function: '🔧 功能标签',
  scenario: '🎯 场景标签',
  attribute: '📋 属性标签',
  tech: '⚙️ 技术标签',
  quality: '⭐ 质量标签',
}

function UtilityBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, score * 10))
  const color = score >= 8 ? 'bg-emerald-500' : score >= 6 ? 'bg-blue-500' : score >= 4 ? 'bg-amber-500' : 'bg-red-400'
  const label = score >= 8 ? '强烈推荐' : score >= 6 ? '值得一试' : score >= 4 ? '有一定价值' : '价值有限'
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center">
        <span className="text-xs font-medium text-slate-500 dark:text-slate-400">实用性评分</span>
        <span className="text-xs font-bold text-slate-700 dark:text-slate-300">{score}/10 · {label}</span>
      </div>
      <div className="h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function getDomain(url: string): string {
  try { return new URL(url).hostname } catch { return '' }
}

interface Props {
  tool: ToolItem
  onClose: () => void
}

export default function ToolDetail({ tool, onClose }: Props) {
  const license = licenseBadge(tool.license_tier || tool.license_type)
  const health = healthDot(tool.health_status)
  const aud = audienceInfo(tool.audience)
  const domain = getDomain(tool.url)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fade-in" />
      <div
        className="relative bg-white dark:bg-slate-900 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto animate-slide-up border border-slate-200 dark:border-slate-700"
        onClick={e => e.stopPropagation()}
      >
        {/* Top gradient bar */}
        <div className="h-2 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 rounded-t-2xl" />
        
        {/* Close button */}
        <button
          className="absolute top-4 right-4 p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors z-10"
          onClick={onClose}
        >
          <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <div className="p-6 pr-14">
          {/* ===== Header ===== */}
          <div className="mb-5">
            <div className="flex items-start gap-3">
              {domain ? (
                <img
                  src={`https://www.google.com/s2/favicons?domain=${domain}&sz=40`}
                  alt=""
                  className="w-12 h-12 rounded-xl bg-slate-100 dark:bg-slate-800 shrink-0"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                />
              ) : (
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center text-white font-bold text-lg shrink-0">
                  {tool.name.charAt(0).toUpperCase()}
                </div>
              )}
              <div className="flex-1 min-w-0">
                <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                  {tool.name}
                </h2>
                {tool.full_name && tool.full_name !== tool.name && (
                  <p className="text-sm text-slate-500 mt-0.5">{tool.full_name}</p>
                )}
              </div>
            </div>

            {/* Badges row */}
            <div className="flex flex-wrap gap-2 mt-3">
              {(() => {
                const arb = aiRelevanceInfo(tool.ai_relevance)
                return arb ? (
                  <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold border ${arb.cls} ${arb.border_cls}`}>
                    {arb.icon} {arb.label}
                  </span>
                ) : null
              })()}
              {tool.category && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded-lg text-xs font-medium">
                  📁 {tool.category}
                </span>
              )}
              {aud && (
                <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium border ${aud.cls}`}>
                  {aud.icon} {aud.label}
                </span>
              )}
              {license && (
                <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium ${license.cls}`}>
                  📜 {license.label}
                </span>
              )}
              {health && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-slate-50 dark:bg-slate-800 rounded-lg text-xs font-medium text-slate-600 dark:text-slate-400">
                  <span className={`w-2 h-2 rounded-full ${health.color}`} />
                  {health.label}
                </span>
              )}
              {tool.is_china_tool && (
                <span className="inline-flex items-center px-2.5 py-1 bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-lg text-xs font-medium">
                  🇨🇳 国内可用
                </span>
              )}
            </div>
          </div>

          {/* ===== AI Analysis Section ===== */}
          <div className="mb-5 p-4 bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 dark:from-indigo-900/20 dark:via-purple-900/15 dark:to-pink-900/10 rounded-xl border border-indigo-100 dark:border-indigo-800/30 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-indigo-700 dark:text-indigo-300 flex items-center gap-1.5">
                <span>🤖</span> AI 分析
                {tool.ai_confidence && (
                  <span className="ml-1 text-xs font-normal text-indigo-400 dark:text-indigo-500">
                    置信度 {(tool.ai_confidence * 100).toFixed(0)}%
                  </span>
                )}
              </h3>
              {(tool.stars ?? 0) > 0 && (
                <span className="flex items-center gap-1 text-amber-500">
                  <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                  <span className="text-xs font-bold">{formatStars(tool.stars)}</span>
                </span>
              )}
            </div>

            {/* AI Relevance description */}
            {(() => {
              const arb = aiRelevanceInfo(tool.ai_relevance)
              return arb ? (
                <p className="text-[11px] text-indigo-400 dark:text-indigo-500 italic">
                  {arb.icon} {arb.desc}
                </p>
              ) : null
            })()}

            {/* Overview */}
            {tool.ai_analysis && (
              <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                {tool.ai_analysis}
              </p>
            )}

            {/* Utility score */}
            {(tool.utility_score ?? 0) > 0 && (
              <UtilityBar score={tool.utility_score!} />
            )}

            {/* Features */}
            {tool.features && tool.features.length > 0 && (
              <div>
                <span className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5 block">核心功能</span>
                <div className="flex flex-wrap gap-1.5">
                  {tool.features.map((feat, i) => (
                    <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 bg-white/70 dark:bg-slate-800/70 text-indigo-700 dark:text-indigo-300 rounded-md text-xs border border-indigo-100 dark:border-indigo-800/40">
                      ✦ {feat}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Best for */}
            {tool.best_for && (
              <div className="flex items-start gap-2">
                <span className="text-xs shrink-0 mt-0.5">🎯</span>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  <span className="font-medium text-slate-700 dark:text-slate-300">适合：</span>
                  {tool.best_for}
                </p>
              </div>
            )}

            {/* Notable */}
            {tool.notable && (
              <div className="flex items-start gap-2">
                <span className="text-xs shrink-0 mt-0.5">💡</span>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  <span className="font-medium text-slate-700 dark:text-slate-300">亮点：</span>
                  {tool.notable}
                </p>
              </div>
            )}

            {/* Audience hint */}
            {aud && (
              <p className="text-[11px] text-indigo-400 dark:text-indigo-500 italic">
                {aud.desc}
              </p>
            )}
          </div>

          {/* ===== Stats Grid ===== */}
          {(tool.stars ?? 0) > 0 || tool.language || tool.type ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5" style={{gridTemplateColumns: 'repeat(auto-fill, minmax(110px, 1fr))'}}>
              {(tool.stars ?? 0) > 0 && (
                <>
                  <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3 text-center">
                    <div className="text-xl font-bold text-amber-500">{formatStars(tool.stars)}</div>
                    <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">Stars</div>
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3 text-center">
                    <div className="text-xl font-bold text-indigo-500">{formatStars(tool.forks)}</div>
                    <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">Forks</div>
                  </div>
                </>
              )}
              {tool.language && (
                <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3 text-center">
                  <div className="text-base font-bold text-slate-700 dark:text-slate-300">{tool.language}</div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">语言</div>
                </div>
              )}
              <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3 text-center">
                <div className="text-sm font-medium text-slate-700 dark:text-slate-300 truncate">{tool.type || 'N/A'}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">类型</div>
              </div>
            </div>
          ) : null}

          {/* ===== Description ===== */}
          <div className="mb-5">
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">描述</h3>
            <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
              {tool.description || '暂无描述'}
            </p>
          </div>

          {/* ===== Five-dimension tags ===== */}
          {tool.tags && Object.values(tool.tags).some(v => Array.isArray(v) && v.length > 0) && (
            <div className="mb-5 space-y-3">
              <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">标签详情</h3>
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

          {/* ===== Topics ===== */}
          {tool.topics && tool.topics.length > 0 && (
            <div className="mb-5">
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

          {/* ===== Footer ===== */}
          <div className="flex items-center justify-between pt-4 border-t border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-500">
              {tool.collected_at && (
                <span>采集: {new Date(tool.collected_at).toLocaleDateString('zh-CN')}</span>
              )}
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
              访问
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
