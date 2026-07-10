import { useNews } from '../hooks/useData'

export default function NewsTicker() {
  const { news } = useNews()

  if (news.length === 0) return null

  const tickerItems = news.slice(0, 10)

  const handleArticleClick = (articleId?: string, e?: React.MouseEvent) => {
    if (e) e.preventDefault()
    if (articleId) {
      window.location.hash = `#/news/${articleId}`
    } else {
      window.location.hash = '#/news'
    }
    // Dispatch custom event for App to pick up
    window.dispatchEvent(new HashChangeEvent('hashchange'))
  }

  return (
    <div className="relative -mx-4 sm:-mx-6 mb-6 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
      <div className="max-w-7xl mx-auto flex items-center h-10 px-4 sm:px-6">
        {/* Label */}
        <div className="flex items-center gap-1.5 shrink-0 mr-4">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
          </span>
          <span className="text-xs font-bold text-red-500 dark:text-red-400 whitespace-nowrap">快讯</span>
        </div>

        {/* Scrolling track */}
        <div className="flex-1 overflow-hidden relative">
          <div className="ticker-track flex items-center gap-8 animate-ticker-scroll">
            {tickerItems.map((item, idx) => (
              <a
                key={idx}
                href={item.article_id ? `#/news/${item.article_id}` : '#/news'}
                onClick={(e) => handleArticleClick(item.article_id, e)}
                className="flex items-center gap-2 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400 hover:text-indigo-500 dark:hover:text-indigo-400 transition-colors shrink-0"
              >
                <span className="text-xs text-slate-400 dark:text-slate-500">
                  {item.published_at ? new Date(item.published_at).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) : ''}
                </span>
                <span className="line-clamp-1">{item.title}</span>
              </a>
            ))}
            {/* Duplicate for seamless loop */}
            {tickerItems.map((item, idx) => (
              <a
                key={`dup-${idx}`}
                href={item.article_id ? `#/news/${item.article_id}` : '#/news'}
                onClick={(e) => handleArticleClick(item.article_id, e)}
                className="flex items-center gap-2 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400 hover:text-indigo-500 dark:hover:text-indigo-400 transition-colors shrink-0"
              >
                <span className="text-xs text-slate-400 dark:text-slate-500">
                  {item.published_at ? new Date(item.published_at).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) : ''}
                </span>
                <span className="line-clamp-1">{item.title}</span>
              </a>
            ))}
          </div>
        </div>

        {/* More link */}
        <a
          href="#/news"
          onClick={(e) => handleArticleClick(undefined, e)}
          className="shrink-0 ml-4 text-xs text-slate-400 hover:text-indigo-500 transition-colors"
        >
          更多 →
        </a>
      </div>
    </div>
  )
}
