import { useMemo, useRef, useEffect, useState } from 'react'
import type { NewsItem } from '../types'

interface Props {
  items: NewsItem[]
}

export default function NewsTicker({ items }: Props) {
  const trackRef = useRef<HTMLDivElement>(null)
  const [paused, setPaused] = useState(false)
  const [needsScroll, setNeedsScroll] = useState(false)

  const visibleItems = useMemo(() => 
    items.filter(i => i.title && i.url).slice(0, 20),
    [items]
  )

  useEffect(() => {
    if (!trackRef.current) return
    const check = () => {
      if (!trackRef.current) return
      setNeedsScroll(trackRef.current.scrollWidth > trackRef.current.parentElement!.clientWidth)
    }
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [visibleItems.length])

  if (visibleItems.length === 0) return null

  const tagColors: Record<string, string> = {
    '🔴': 'bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400 border-rose-200 dark:border-rose-800',
    '🟠': 'bg-orange-50 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400 border-orange-200 dark:border-orange-800',
    '🔵': 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 border-blue-200 dark:border-blue-800',
    '🟢': 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800',
    '🟡': 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 border-amber-200 dark:border-amber-800',
    '🟣': 'bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 border-purple-200 dark:border-purple-800',
    '⚡': 'bg-yellow-50 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 border-yellow-200 dark:border-yellow-800',
  }

  const tickerItems = visibleItems.map((item, index) => {
    const tag = (item.tags && item.tags[0]) || null
    const displayTag = tag && tag.length <= 2 ? tag : null
    const tagText = tag && tag.length > 2 ? tag : null
    const href = item.article_id ? `#/news/${item.article_id}` : item.url

    return (
      <a
        key={`${item.url}-${index}`}
        href={href}
        className="group inline-flex items-center gap-1.5 sm:gap-2 whitespace-nowrap mr-4 sm:mr-8 text-xs sm:text-sm text-slate-600 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
        target={item.article_id ? undefined : '_blank'}
        rel={item.article_id ? undefined : 'noopener noreferrer'}
      >
        {displayTag && (
          <span className={`text-[10px] sm:text-xs px-1.5 py-0.5 rounded-full border font-medium ${tagColors[displayTag] || 'bg-slate-50 text-slate-600 dark:bg-slate-800 dark:text-slate-400 border-slate-200 dark:border-slate-700'}`}>
            {displayTag}
          </span>
        )}
        {tagText && (
          <span className="text-[10px] sm:text-xs px-1.5 sm:px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-medium border border-slate-200 dark:border-slate-700">
            {tagText}
          </span>
        )}
        <span className="font-medium">{item.title}</span>
        <svg className="w-3 h-3 opacity-0 -ml-2 group-hover:opacity-100 group-hover:ml-0 transition-all" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </a>
    )
  })

  return (
    <div 
      className="w-full bg-gradient-to-r from-indigo-50/80 via-white to-purple-50/80 dark:from-slate-800/80 dark:via-slate-900 dark:to-slate-800/80 border-b border-slate-200/50 dark:border-slate-700/50 backdrop-blur-sm"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      <div className="max-w-7xl mx-auto flex items-center gap-2 sm:gap-3 py-2 sm:py-2.5 px-4 sm:px-6">
        <span className="hidden sm:flex flex-shrink-0 items-center gap-1.5 text-[11px] font-bold text-indigo-600 dark:text-indigo-400 tracking-wide">
          <span className="relative flex h-1.5 w-1.5">
            <span className={`absolute inline-flex h-full w-full rounded-full bg-indigo-400 ${paused ? '' : 'animate-ping'} opacity-75`}></span>
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-indigo-500"></span>
          </span>
          <span className="uppercase">快讯</span>
        </span>
        <span className="sm:hidden flex-shrink-0 text-[11px] font-bold text-indigo-600 dark:text-indigo-400">快讯</span>

        <div className="flex-1 overflow-hidden relative">
          <div className="absolute left-0 top-0 bottom-0 w-4 sm:w-6 bg-gradient-to-r from-white dark:from-slate-900 to-transparent z-10 pointer-events-none"></div>
          <div className="absolute right-0 top-0 bottom-0 w-4 sm:w-6 bg-gradient-to-l from-white dark:from-slate-900 to-transparent z-10 pointer-events-none"></div>

          <div
            ref={trackRef}
            className={`flex ${needsScroll && !paused ? 'animate-ticker-scroll' : ''} items-center gap-0`}
            style={{
              width: needsScroll ? 'max-content' : '100%',
              justifyContent: needsScroll ? undefined : 'center',
            }}
          >
            {tickerItems}
            {needsScroll && !paused && tickerItems}
          </div>
        </div>

        <a 
          href="#/news"
          className="flex-shrink-0 text-[11px] sm:text-xs font-medium text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors flex items-center gap-0.5 sm:gap-1"
        >
          更多
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </a>
      </div>
    </div>
  )
}
