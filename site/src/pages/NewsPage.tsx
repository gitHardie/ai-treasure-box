import { useNews } from '../hooks/useData'
import LoadingState from '../components/LoadingState'
import EmptyState from '../components/EmptyState'

export default function NewsPage() {
  const { news, loading, error } = useNews()

  if (loading) {
    return <LoadingState message="正在加载资讯..." />
  }

  if (error) {
    return <EmptyState icon="⚠️" title="加载失败" description={error} />
  }

  if (news.length === 0) {
    return <EmptyState icon="📰" title="暂无资讯" description="资讯数据采集中，请稍后再来" />
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          📰 AI 资讯
        </h2>
        <span className="text-sm text-slate-500 dark:text-slate-400">
          共 {news.length} 条
        </span>
      </div>

      <div className="space-y-3">
        {news.map((item, idx) => (
          <a
            key={idx}
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 card-hover group"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <h3 className="font-medium text-slate-900 dark:text-white group-hover:text-indigo-500 dark:group-hover:text-indigo-400 transition-colors line-clamp-2">
                  {item.title}
                </h3>
                {item.description && (
                  <p className="text-sm text-slate-500 dark:text-slate-400 mt-2 line-clamp-2 leading-relaxed">
                    {item.description}
                  </p>
                )}
                <div className="flex items-center gap-3 mt-3">
                  {item.source && (
                    <span className="text-xs text-slate-400 dark:text-slate-500">
                      {item.source}
                    </span>
                  )}
                  {(item.published_at || item.collected_at) && (
                    <span className="text-xs text-slate-400 dark:text-slate-500">
                      {new Date(item.published_at || item.collected_at || '').toLocaleDateString('zh-CN')}
                    </span>
                  )}
                </div>
              </div>
              <svg className="w-5 h-5 text-slate-300 dark:text-slate-600 group-hover:text-indigo-400 transition-colors shrink-0 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </div>
            {item.tags && item.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-3">
                {item.tags.map(tag => (
                  <span key={tag} className="badge bg-indigo-50 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-300">
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </a>
        ))}
      </div>
    </div>
  )
}
