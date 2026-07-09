"""
Toolify.ai 采集器
采集toolify.ai的AI工具列表
"""
import re
import logging
from typing import List, Dict, Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseCollector

logger = logging.getLogger(__name__)


class Collector(BaseCollector):
    """Toolify.ai 采集器"""

    def collect(self) -> List[Dict[str, Any]]:
        """采集Toolify.ai工具列表"""
        items = []
        base_url = self.config.get("url", "https://www.toolify.ai")
        fetch_limit = self.config.get("fetch_limit", 30)

        # 增强User-Agent以应对反爬
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
        })

        try:
            # 先抓首页找分类链接
            resp = self.fetch(base_url)
            soup = BeautifulSoup(resp.text, "html.parser")
            categories = self._find_categories(soup, base_url)

            # 采集每个分类页面
            max_categories = 5
            for cat_name, cat_url in categories[:max_categories]:
                if len(items) >= fetch_limit:
                    break
                try:
                    cat_resp = self.fetch(cat_url)
                    cat_soup = BeautifulSoup(cat_resp.text, "html.parser")
                    cat_items = self._parse_category_page(cat_soup, cat_url, cat_name, fetch_limit - len(items))
                    items.extend(cat_items)
                    logger.info(f"[{self.source_id}] Found {len(cat_items)} tools in category: {cat_name}")
                except Exception as e:
                    logger.warning(f"[{self.source_id}] Failed to fetch category {cat_name}: {e}")

            # 如果分类采集失败，尝试直接从首页解析
            if not items:
                logger.info(f"[{self.source_id}] Fallback to parsing homepage")
                items = self._parse_homepage(soup, base_url, fetch_limit)

            logger.info(f"[{self.source_id}] Found {len(items)} tools total")

        except Exception as e:
            logger.error(f"[{self.source_id}] Failed: {e}")

        return self.dedup_by_url(items)

    def _find_categories(self, soup: BeautifulSoup, base_url: str) -> list:
        """从首页找到分类链接"""
        categories = []
        selectors = [
            "nav a[href*='/category']",
            "nav a[href*='/tool']",
            "a[href*='/category']",
            "a[href*='/topic']",
            "nav a[href^='/']",
            ".sidebar a",
            "[class*='category'] a",
            "[class*='nav'] a",
        ]

        seen = set()
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get("href", "")
                text = link.get_text(strip=True)
                if href and text and len(text) > 1 and href not in seen:
                    full_url = urljoin(base_url, href)
                    if full_url != base_url and "category" in href.lower() or "topic" in href.lower() or "tool" in href.lower():
                        seen.add(href)
                        categories.append((text, full_url))
            if len(categories) >= 5:
                break

        return categories[:5]

    def _parse_category_page(self, soup: BeautifulSoup, source_url: str, category: str, limit: int) -> List[Dict]:
        """解析分类页面工具列表"""
        items = []
        card_selectors = [
            ".tool-card",
            ".card",
            "[class*='tool']",
            "[class*='product']",
            "[class*='item']",
            "article",
        ]

        cards = []
        for selector in card_selectors:
            cards = soup.select(selector)
            if cards:
                break

        if not cards:
            # 降级：找外部链接块
            cards = self._fallback_cards(soup)

        for card in cards[:limit]:
            item = self._parse_card(card, source_url, category)
            if item:
                items.append(item)

        return items

    def _parse_homepage(self, soup: BeautifulSoup, base_url: str, limit: int) -> List[Dict]:
        """从首页直接解析工具"""
        items = []
        links = soup.select("a[href^='http']")
        seen = set()

        for link in links:
            if len(items) >= limit:
                break
            href = link.get("href", "")
            text = link.get_text(strip=True)
            if not text or len(text) < 3 or len(text) > 100:
                continue
            if href in seen or base_url in href:
                continue
            # 过滤掉导航链接
            if any(skip in href for skip in ["category", "login", "signup", "about", "privacy", "terms"]):
                continue
            seen.add(href)
            items.append({
                "name": text,
                "url": href,
                "description": "",
                "description_zh": "",
                "source": self.source_id,
                "source_url": base_url,
                "tags": [],
                "platform": [self.source_id],
                "type": "ai_tool",
                "raw_data": {},
            })

        return items

    def _fallback_cards(self, soup: BeautifulSoup) -> list:
        """降级查找工具卡片"""
        blocks = []
        for container in soup.select("div, section"):
            links = container.select("a[href^='http']")
            if links and len(container.get_text(strip=True)) > 20 and len(container.get_text(strip=True)) < 500:
                blocks.append(container)
                if len(blocks) >= 50:
                    break
        return blocks

    def _parse_card(self, card, source_url: str, category: str) -> Dict[str, Any]:
        """解析工具卡片"""
        try:
            # 查找链接
            link = card.select_one("a[href^='http']")
            if not link:
                return None

            url = link.get("href", "")
            if not url.startswith("http"):
                return None

            # 名称
            name_el = card.select_one("h2, h3, h4, h5, [class*='title'], [class*='name'], strong")
            name = name_el.get_text(strip=True) if name_el else link.get_text(strip=True)
            if not name or len(name) < 2 or len(name) > 200:
                return None

            # 描述
            desc_el = card.select_one("p, [class*='desc'], [class*='summary'], small")
            description = desc_el.get_text(strip=True) if desc_el else ""

            # 评分/排名
            score = ""
            score_el = card.select_one("[class*='score'], [class*='rank'], [class*='rating']")
            if score_el:
                score = score_el.get_text(strip=True)

            # 标签
            tags = [category] if category else []
            tag_els = card.select("[class*='tag'], [class*='label']")
            for t in tag_els:
                tag_text = t.get_text(strip=True)
                if tag_text:
                    tags.append(tag_text)

            return {
                "name": name,
                "url": url,
                "description": description[:500],
                "description_zh": "",
                "source": self.source_id,
                "source_url": source_url,
                "tags": tags,
                "platform": [self.source_id],
                "type": "ai_tool",
                "raw_data": {
                    "score": score,
                },
            }
        except Exception as e:
            logger.debug(f"[{self.source_id}] Failed to parse card: {e}")
            return None
