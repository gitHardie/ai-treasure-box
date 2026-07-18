export interface ToolTags {
  function: string[]
  scenario: string[]
  attribute: string[]
  tech: string[]
  quality: string[]
}

export interface ToolItem {
  name: string
  full_name: string
  url: string
  description: string
  language?: string
  stars?: number
  forks?: number
  topics?: string[]
  platform: string[]
  type: string
  id?: string
  tool_id?: string
  source?: string
  source_name?: string
  collected_at?: string
  rank_change?: number
  license_tier?: string
  license_type?: string
  health_status?: string
  ai_analysis?: string
  ai_confidence?: number
  is_china_tool?: boolean
  category?: string
  subcategory?: string
  audience?: string
  utility_score?: number
  should_include?: boolean
  tags?: ToolTags
  features?: string[]
  best_for?: string
  notable?: string
}

export interface ToolsJsonData {
  generated_at: string
  count: number
  tools: ToolItem[]
}

export interface CategoriesData {
  generated_at: string
  categories: Record<string, number>
  subcategories: Record<string, number>
}

export interface StatsData {
  generated_at: string
  total_tools: number
  new_this_week?: number
  category_counts: Record<string, number>
  health_counts: Record<string, number>
  license_counts: Record<string, number>
  source_counts: Record<string, number>
  updated_at: string
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
  category?: string
  category_label?: string
  article_id?: string
  summary?: string
}

export interface NewsData {
  source: string
  source_name: string
  collected_at: string
  count: number
  items: NewsItem[]
}

export interface NewsArticle {
  id: string
  title: string
  summary: string
  content_markdown: string
  content_html?: string
  sources: { name: string; url: string }[]
  published_at: string
  tags: string[]
  category: string
  category_label: string
}

export interface ArticlesData {
  generated_at: string
  count: number
  articles: NewsArticle[]
}

export interface SnapshotData {
  date: string
  total_tools: number
  new_this_week?: number
  categories: Record<string, number>
  top_tools?: { name: string; stars: number }[]
}

export interface RankingItem extends ToolItem {
  rank: number
  prev_rank?: number
  rank_change: number
}

export type TabType = "discover" | "rankings" | "news" | "trends" | "favorites" | "about"

export interface CategoryInfo {
  id: string
  label: string
  emoji: string
  count: number
  subcategories?: { id: string; label: string; count: number }[]
}
