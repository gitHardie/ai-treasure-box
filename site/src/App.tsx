import { useState } from 'react'
import type { TabType } from './types'
import { useTheme } from './hooks/useData'
import Navbar from './components/Navbar'
import DiscoverPage from './pages/DiscoverPage'
import RankingsPage from './pages/RankingsPage'
import NewsPage from './pages/NewsPage'
import TrendsPage from './pages/TrendsPage'
import AboutPage from './pages/AboutPage'

export default function App() {
  const [activeTab, setActiveTab] = useState<TabType>('discover')
  const { isDark, toggle } = useTheme()

  const renderPage = () => {
    switch (activeTab) {
      case 'discover':
        return <DiscoverPage />
      case 'rankings':
        return <RankingsPage />
      case 'news':
        return <NewsPage />
      case 'trends':
        return <TrendsPage />
      case 'about':
        return <AboutPage />
      default:
        return <DiscoverPage />
    }
  }

  return (
    <div className="min-h-screen">
      <Navbar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        isDark={isDark}
        onToggleTheme={toggle}
      />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        {renderPage()}
      </main>
    </div>
  )
}
