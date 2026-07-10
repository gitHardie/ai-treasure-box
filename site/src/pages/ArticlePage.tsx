import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { QRCodeSVG } from 'qrcode.react'

interface ArticleSource {
  name: string
  url: string
}

interface Article {
  id: string
  title: string
  summary: string
  content_markdown: string
  sources: ArticleSource[]
  published_at: string
  tags: string[]
  category: string
  category_label: string
}

interface Props {
  articleId: string
  onBack: () => void
}

const categoryEmoji: Record<string, string> = {
  model_release: '🤖',
  funding: '💰',
  product_launch: '🚀',
  tech_breakthrough: '🔬',
  industry_policy: '📋',
  application: '💡',
  open_source: '📦',
  other: '📰',
}

export default function ArticlePage({ articleId, onBack }: Props) {
  const [article, setArticle] = useState<Article | null>(null)
  const [loading, setLoading] = useState(true)
  const [showQR, setShowQR] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    const loadArticle = async () => {
      try {
        const basePath = import.meta.env.BASE_URL || ''
        const res = await fetch(basePath + '/data/news/articles.json')
        if (res.ok) {
          const data = await res.json()
          const found = data.articles?.find((a: Article) => a.id === articleId)
          if (found) {
            setArticle(found)
          }
        }
      } catch (e) {
        console.error('Failed to load article:', e)
      } finally {
        setLoading(false)
      }
    }
    loadArticle()
  }, [articleId])

  const articleUrl = window.location.href
  const shareText = article ? `${article.title} - AI百宝箱 afterai.tech` : ''

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(articleUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback
      const input = document.createElement('input')
      input.value = articleUrl
      document.body.appendChild(input)
      input.select()
      document.execCommand('copy')
      document.body.removeChild(input)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-indigo-500 border-t-transparent" />
      </div>
    )
  }

  if (!article) {
    return (
      <div className="text-center py-20">
        <p className="text-4xl mb-4">📄</p>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">文章未找到</h2>
        <p className="text-slate-500 mb-4">该文章可能已被移除或链接无效</p>
        <button onClick={onBack} className="text-indigo-500 hover:text-indigo-600">
          ← 返回资讯列表
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Back button */}
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-slate-500 dark:text-slate-400 hover:text-indigo-500 transition-colors mb-6"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        返回资讯
      </button>

      {/* Article header */}
      <header className="mb-8">
        {/* Category badge */}
        <div className="flex items-center gap-2 mb-4">
          <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-300 rounded-full text-xs font-medium">
            {categoryEmoji[article.category] || '📰'} {article.category_label || article.category}
          </span>
          <span className="text-xs text-slate-400">
            {new Date(article.published_at).toLocaleDateString('zh-CN', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </span>
        </div>

        {/* Title */}
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white leading-tight mb-4">
          {article.title}
        </h1>

        {/* Summary */}
        <p className="text-base text-slate-500 dark:text-slate-400 leading-relaxed mb-6">
          {article.summary}
        </p>

        {/* Tags + Share */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          {/* Tags */}
          <div className="flex flex-wrap gap-1.5">
            {article.tags?.map(tag => (
              <span
                key={tag}
                className="px-2 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 rounded text-xs"
              >
                #{tag}
              </span>
            ))}
          </div>

          {/* Share buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyLink}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-500 hover:text-indigo-500 bg-slate-100 dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 rounded-lg transition-colors"
              title="复制链接"
            >
              {copied ? (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  已复制
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                  </svg>
                  复制链接
                </>
              )}
            </button>

            <button
              onClick={() => setShowQR(!showQR)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-500 hover:text-indigo-500 bg-slate-100 dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 rounded-lg transition-colors"
              title="二维码分享"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M4 8h4m8-4v1m-8 11v1m0 0h.01M12 16h4.01M20 8h.01M4 16h.01" />
              </svg>
              二维码
            </button>
          </div>
        </div>

        {/* QR Code popover */}
        {showQR && (
          <div className="mt-4 p-4 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 inline-block shadow-lg">
            <QRCodeSVG
              value={articleUrl}
              size={160}
              bgColor="transparent"
              fgColor="currentColor"
              className="text-slate-900 dark:text-white"
            />
            <p className="text-xs text-slate-400 mt-2 text-center">扫码阅读 · 可分享到微信</p>
          </div>
        )}
      </header>

      {/* Divider */}
      <hr className="border-slate-200 dark:border-slate-800 mb-8" />

      {/* Article content */}
      <div className="article-content">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {article.content_markdown}
        </ReactMarkdown>
      </div>

      {/* Sources */}
      {article.sources && article.sources.length > 0 && (
        <footer className="mt-12 pt-6 border-t border-slate-200 dark:border-slate-800">
          <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-3">
            📚 参考来源
          </h3>
          <ul className="space-y-2">
            {article.sources.map((source, idx) => (
              <li key={idx}>
                <a
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-indigo-500 hover:text-indigo-600 hover:underline"
                >
                  {source.name} ↗
                </a>
              </li>
            ))}
          </ul>
        </footer>
      )}
    </div>
  )
}
