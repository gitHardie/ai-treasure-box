"""
AIG123 采集器
采集aig123.com的AIGC工具信息
"""
import re
import logging
from typing import List, Dict, Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseCollector

logger = logging.getLogger(__name__)


class Collector(BaseCollector):
    """AIG123 采集器"""

    def collect(self) -> List[Dict[str, Any]]:
        """采集AIG123工具列表"""
        items = []
        base_url = self.config.get("url", "https://aig123.com")
        fetch_limit = self.config.get("fetch_limit", 20)

        try:
            resp = self.fetch(base_url)
            soup = BeautifulSoup(resp.text, "html.parser")

            # 尝试多种选择器找到工具/文章卡片
            cards = []
            selectors = [
                ".tool-card",
                ".card",
                "article",
                "[class*='tool']",
                "[class*='post']",
                "[class*='item']",
                "[class*='product']",
                "[class*='entry']",
            ]

            for selector in selectors:
                cards = soup.select(selector)
                if cards:
                    logger.info(f"[{self.source_id}] Found {len(cards)} elements with selector: {selector}")
                    break

            # 降级方案
            if not cards:
                cards = self._fallback_find(soup, base_url)

            for card in cards[:fetch_limit]:
                item = self._parse_card(card, base_url)
                if item:
                    items.append(item)

            # 尝试找分类子页面
            if not items:
                items = self._crawl_subpages(soup, base_url, fetch_limit)

            logger.info(f"[{self.source_id}] Found {len(items)} tools")

        except Exception as e:
            logger.error(f"[{self.source_id}] Failed: {e}")

        return self.dedup_by_url(items)

    def _fallback_find(self, soup: BeautifulSoup, base_url: str) -> list:
        """降级查找工具卡片"""
        blocks = []
        for container in soup.select("div, section, li"):
            links = container.select("a[href^='http']")
            if links:
                text = container.get_text(strip=True)
                if 20 < len(text) < 600:
                    blocks.append(container)
                    if len(blocks) >= 50:
                        break
        return blocks

    def _crawl_subpages(self, soup: BeautifulSoup, base_url: str, fetch_limit: int) -> List[Dict]:
        """尝试爬取子页面"""
        items = []
        visited = {base_url}

        # 找分类链接
        cat_links = soup.select("nav a[href], a[href*='/list'], a[href*='/category'], a[href*='/tag']")
        sub_urls = []
        for link in cat_links:
            href = link.get("href", "")
            if href.startswith("http") and href not in visited:
                sub_urls.append(href)
                visited.add(href)
            elif href.startswith("/") and href not in visited:
                full_url = urljoin(base_url, href)
                sub_urls.append(full_url)
                visited.add(href)

        for sub_url in sub_urls[:5]:
            if len(items) >= fetch_limit:
                break
            try:
                sub_resp = self.fetch(sub_url)
                sub_soup = BeautifulSoup(sub_resp.text, "html.parser")
                sub_cards = sub_soup.select(
                    ".card, article, [class*='tool'], [class*='item'], [class*='post'], [class*='entry']"
                )
                for card in sub_cards[:fetch_limit - len(items)]:
                    item = self._parse_card(card, sub_url)
                    if item:
                        items.append(item)
            except Exception:
                pass

        return items

    def _parse_card(self, card, source_url: str) -> Dict[str, Any]:
        """解析工具/文章卡片"""
        try:
            # 查找链接
            link = card.select_one("a[href^='http']")
            if not link:
                return None

            url = link.get("href", "")
            if not url.startswith("http"):
                return None

            # 标题
            title_el = card.select_one("h1, h2, h3, h4, h5, [class*='title'], [class*='name'], strong")
            title = title_el.get_text(strip=True) if title_el else link.get_text(strip=True)
            if not title or len(title) < 2 or len(title) > 200:
                return None

            # 描述
            desc_el = card.select_one("p, [class*='desc'], [class*='summary'], [class*='content'], small, span:not([class*='title'])")
            description = desc_el.get_text(strip=True) if desc_el else ""

            # 标签
            tags = []
            tag_els = card.select("[class*='tag'], [class*='label'], [class*='badge'], [class*='category']")
            for t in tag_els:
                tag_text = t.get_text(strip=True)
                if tag_text:
                    tags.append(tag_text)

            return {
                "name": title,
                "url": url,
                "description": description[:500],
                "description_zh": "",
                "source": self.source_id,
                "source_url": source_url,
                "tags": tags,
                "platform": [self.source_id],
                "type": "ai_tool",
                "raw_data": {},
            }
        except Exception as e:
            logger.debug(f"[{self.source_id}] Failed to parse card: {e}")
            return None
