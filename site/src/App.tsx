import { useState, useEffect, useCallback } from 'react'
import type { TabType, ToolItem } from './types'
import { useTools, useTheme } from './hooks/useData'
import { useFavorites } from './hooks/useFavorites'
import Navbar from './components/Navbar'
import CommandPalette from './components/CommandPalette'
import DiscoverPage from './pages/DiscoverPage'
import RankingsPage from './pages/RankingsPage'
import NewsPage from './pages/NewsPage'
import TrendsPage from './pages/TrendsPage'
import FavoritesPage from './pages/FavoritesPage'
import AboutPage from './pages/AboutPage'
import ToolDetail from './components/ToolDetail'
import NewsTicker from './components/NewsTicker'

function parseHash(): { tab: TabType; articleId: string | null } {
  const hash = window.location.hash
  // Format: #/news, #/news/article-id, #/discover, etc.
  if (hash.startsWith('#/')) {
    const parts = hash.slice(2).split('/')
    const tabName = parts[0] as TabType
    const articleId = parts[1] || null
    const validTabs: TabType[] = ['discover', 'rankings', 'news', 'trends', 'favorites', 'about']
    if (validTabs.includes(tabName)) {
      return { tab: tabName, articleId }
    }
  }
  return { tab: 'discover', articleId: null }
}

export default function App() {
  const [activeTab, setActiveTab] = useState<TabType>(() => parseHash().tab)
  const [newsArticleId, setNewsArticleId] = useState<string | null>(() => parseHash().articleId)
  const { isDark, toggle } = useTheme()
  const { tools } = useTools()
  const { count: favoriteCount } = useFavorites()
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [selectedTool, setSelectedTool] = useState<ToolItem | null>(null)

  // Handle hash changes for deep linking
  useEffect(() => {
    const handleHashChange = () => {
      const { tab, articleId } = parseHash()
      setActiveTab(tab)
      if (tab === 'news') {
        setNewsArticleId(articleId)
      }
    }
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  // Update hash when tab changes via navbar
  const handleTabChange = useCallback((tab: TabType) => {
    setActiveTab(tab)
    setNewsArticleId(null)
    if (tab === 'discover') {
      history.replaceState(null, '', window.location.pathname)
    } else {
      window.location.hash = `#/${tab}`
    }
  }, [])

  // Handle closing article detail
  const handleArticleBack = useCallback(() => {
    setNewsArticleId(null)
    window.location.hash = '#/news'
  }, [])

  // Cmd+K / Ctrl+K shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setPaletteOpen(prev => !prev)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const handleToolSelectFromPalette = useCallback((tool: ToolItem) => {
    setSelectedTool(tool)
  }, [])

  const renderPage = () => {
    switch (activeTab) {
      case 'discover': return <DiscoverPage />
      case 'rankings': return <RankingsPage />
      case 'news': return <NewsPage articleId={newsArticleId} onArticleBack={handleArticleBack} />
      case 'trends': return <TrendsPage />
      case 'favorites': return <FavoritesPage />
      case 'about': return <AboutPage />
      default: return <DiscoverPage />
    }
  }

  return (
    <div className="min-h-screen">
      <Navbar
        activeTab={activeTab}
        onTabChange={handleTabChange}
        isDark={isDark}
        onToggleTheme={toggle}
        onSearchOpen={() => setPaletteOpen(true)}
        favoriteCount={favoriteCount}
      />
      <NewsTicker />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 pb-24 md:pb-6">
        <div className="page-transition">
          {renderPage()}
        </div>
      </main>

      <CommandPalette
        tools={tools}
        isOpen={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onSelect={handleToolSelectFromPalette}
      />

      {selectedTool && (
        <ToolDetail tool={selectedTool} onClose={() => setSelectedTool(null)} />
      )}
    </div>
  )
}
