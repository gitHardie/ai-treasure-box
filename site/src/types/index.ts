export interface ToolItem {
  name: string
  full_name: string
  url: string
  description: string
  language?: string
  stars: number
  forks: number
  topics: string[]
  platform: string[]
  type: string
  source?: string
  source_name?: string
  collected_at?: string
  rank_change?: number
  license_tier?: string
  license_type?: string
  health_status?: string
  ai_analysis?: string
  is_china_tool?: boolean
  category?: string
  subcategory?: string
}

export interface ToolData {
  source: string
  source_name: string
  collected_at: string
  count: number
  items: ToolItem[]
}

export interface NewsItem {
  title: string
  url: string
  description?: string
  source?: string
  published_at?: string
  collected_at?: string
  tags?: string[]
}

export interface NewsData {
  source: string
  source_name: string
  collected_at: string
  count: number
  items: NewsItem[]
}

export interface SnapshotData {
  date: string
  total_tools: number
  new_this_week: number
  categories: Record<string, number>
  top_tools?: { name: string; stars: number }[]
}

export interface RankingItem extends ToolItem {
  rank: number
  prev_rank?: number
  rank_change: number
}

export type TabType = 'discover' | 'rankings' | 'news' | 'trends' | 'favorites' | 'about'

export interface CategoryInfo {
  id: string
  label: string
  emoji: string
  count: number
  subcategories?: { id: string; label: string; count: number }[]
}
