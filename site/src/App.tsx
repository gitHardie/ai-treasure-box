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

export default function App() {
  const [activeTab, setActiveTab] = useState<TabType>('discover')
  const { isDark, toggle } = useTheme()
  const { tools } = useTools()
  const { count: favoriteCount } = useFavorites()
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [selectedTool, setSelectedTool] = useState<ToolItem | null>(null)

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
      case 'news': return <NewsPage />
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
        onTabChange={setActiveTab}
        isDark={isDark}
        onToggleTheme={toggle}
        onSearchOpen={() => setPaletteOpen(true)}
        favoriteCount={favoriteCount}
      />
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
