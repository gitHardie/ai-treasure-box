import { useState, useMemo } from 'react'
import { useNews } from '../hooks/useData'
import LoadingState from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import ArticlePage from './ArticlePage'

const categoryTabs = [
  { id: 'all', label: '全部', emoji: '📰' },
  { id: 'model_release', label: '模型发布', emoji: '🤖' },
  { id: 'product_launch', label: '产品发布', emoji: '🚀' },
  { id: 'funding', label: '融资收购', emoji: '💰' },
  { id: 'tech_breakthrough', label: '技术突破', emoji: '🔬' },
  { id: 'industry_policy', label: '行业政策', emoji: '📋' },
  { id: 'application', label: '应用落地', emoji: '💡' },
  { id: 'open_source', label: '开源动态', emoji: '📦' },
]

interface Props {
  articleId?: string | null
  onArticleBack?: () => void
}

export default function NewsPage({ articleId, onArticleBack }: Props) {
  const { news, loading, error } = useNews()
  const [selectedCategory, setSelectedCategory] = useState('all')

  // If viewing an article, render article page
  if (articleId) {
    return (
      <ArticlePage
        articleId={articleId}
        onBack={() => {
          if (onArticleBack) onArticleBack()
        }}
      />
    )
  }

  // Filter news by category
  const filteredNews = useMemo(() => {
    if (selectedCategory === 'all') return news
    return news.filter(item => item.category === selectedCategory)
  }, [news, selectedCategory])

  if (loading) {
    return <LoadingState message="正在加载资讯..." />
  }

  if (error) {
    return <EmptyState icon="⚠️" title="加载失败" description={error} />
  }

  if (news.length === 0) {
    return (
      <EmptyState
        icon="📰"
        title="资讯模块建设中"
        description="我们正在搭建AI行业资讯采集管道，即将为你带来最新AI动态。你也可以先去发现页探索124+个AI工具！"
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          📰 AI 资讯
        </h2>
        <span className="text-sm text-slate-500 dark:text-slate-400">
          共 {filteredNews.length} 条
        </span>
      </div>

      {/* Category tabs */}
      <div className="flex gap-2 overflow-x-auto scrollbar-hide pb-1 -mx-4 px-4 sm:mx-0 sm:px-0">
        {categoryTabs.map(tab => {
          const count = tab.id === 'all'
            ? news.length
            : news.filter(n => n.category === tab.id).length
          if (count === 0 && tab.id !== 'all') return null
          return (
            <button
              key={tab.id}
              onClick={() => setSelectedCategory(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm whitespace-nowrap transition-all ${
                selectedCategory === tab.id
                  ? 'bg-indigo-500 text-white shadow-md shadow-indigo-500/25'
                  : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700 hover:border-indigo-300 dark:hover:border-indigo-600'
              }`}
            >
              <span>{tab.emoji}</span>
              <span>{tab.label}</span>
              {count > 0 && (
                <span className={`text-xs ${selectedCategory === tab.id ? 'text-indigo-200' : 'text-slate-400'}`}>
                  {count}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* News list */}
      <div className="space-y-3">
        {filteredNews.map((item, idx) => (
          <div
            key={idx}
            onClick={() => {
              if (item.article_id) {
                window.location.hash = `#/news/${item.article_id}`
              }
            }}
            className={`block bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 transition-all ${
              item.article_id
                ? 'cursor-pointer card-hover group'
                : ''
            }`}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <h3 className={`font-medium text-slate-900 dark:text-white transition-colors line-clamp-2 ${
                  item.article_id ? 'group-hover:text-indigo-500 dark:group-hover:text-indigo-400' : ''
                }`}>
                  {item.title}
                </h3>
                {(item.summary || item.description) && (
                  <p className="text-sm text-slate-500 dark:text-slate-400 mt-2 line-clamp-2 leading-relaxed">
                    {item.summary || item.description}
                  </p>
                )}
                <div className="flex items-center gap-3 mt-3 flex-wrap">
                  {item.category && (
                    <span className="text-xs px-2 py-0.5 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-300 rounded-full">
                      {item.category_label || item.category}
                    </span>
                  )}
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
              {item.article_id && (
                <svg className="w-5 h-5 text-slate-300 dark:text-slate-600 group-hover:text-indigo-400 transition-colors shrink-0 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              )}
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
          </div>
        ))}
      </div>
    </div>
  )
}
