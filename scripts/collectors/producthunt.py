"""
Product Hunt AI类采集器
采集producthunt.com上AI分类下的工具
"""
import logging
from typing import List, Dict, Any

from bs4 import BeautifulSoup

from .base import BaseCollector

logger = logging.getLogger(__name__)


class Collector(BaseCollector):
    """Product Hunt AI类采集器"""

    def collect(self) -> List[Dict[str, Any]]:
        """采集Product Hunt AI分类页面"""
        items = []
        url = self.config.get("url", "https://www.producthunt.com/topics/artificial-intelligence")
        fetch_limit = self.config.get("fetch_limit", 20)

        try:
            resp = self.fetch(url)
            soup = BeautifulSoup(resp.text, "html.parser")

            # 尝试多种选择器找到工具卡片
            cards = []
            selectors = [
                "[class*='css-'] a[href*='/posts/']",
                "a[href*='/posts/']",
                "article",
                "[class*='product']",
                "[class*='item']",
                "[class*='card']",
            ]

            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    cards = elements
                    logger.info(f"[{self.source_id}] Found {len(elements)} elements with selector: {selector}")
                    break

            # 如果都没找到，尝试找所有带外部链接的块
            if not cards:
                cards = self._fallback_find(soup)

            for card in cards[:fetch_limit]:
                item = self._parse_card(card)
                if item:
                    items.append(item)

            logger.info(f"[{self.source_id}] Found {len(items)} tools")

        except Exception as e:
            logger.error(f"[{self.source_id}] Failed: {e}")

        return self.dedup_by_url(items)

    def _fallback_find(self, soup: BeautifulSoup) -> list:
        """降级方案：查找包含/posts/链接的区块"""
        results = []
        for link in soup.select("a[href*='/posts/']"):
            parent = link.parent
            if parent:
                results.append(parent)
        return results

    def _parse_card(self, card) -> Dict[str, Any]:
        """解析工具卡片"""
        try:
            # 查找链接
            link = card.select_one("a[href*='/posts/']") if card.name != "a" else card
            if not link:
                link = card.select_one("a[href^='http']")
            if not link:
                return None

            # 提取URL
            href = link.get("href", "")
            if href.startswith("/"):
                href = f"https://www.producthunt.com{href}"
            if not href.startswith("http"):
                return None

            # 提取名称
            name_el = card.select_one("h2, h3, h4, [class*='title'], [class*='name'], strong")
            if not name_el:
                name_el = link
            name = name_el.get_text(strip=True) if name_el else ""

            if not name or len(name) < 2 or len(name) > 200:
                return None

            # 提取描述
            desc_el = card.select_one("p, [class*='desc'], [class*='tagline'], small, span:not([class*='title'])")
            description = desc_el.get_text(strip=True) if desc_el else ""

            # 提取投票数
            vote = 0
            vote_el = card.select_one("[class*='vote'], [class*='count']")
            if vote_el:
                import re
                match = re.search(r"(\d+)", vote_el.get_text())
                if match:
                    vote = int(match.group(1))

            return {
                "name": name,
                "url": href,
                "description": description[:500],
                "description_zh": "",
                "source": self.source_id,
                "source_url": self.config.get("url", "https://www.producthunt.com/topics/artificial-intelligence"),
                "tags": ["product-hunt"],
                "platform": [self.source_id],
                "type": "ai_tool",
                "raw_data": {
                    "votes": vote,
                },
            }
        except Exception as e:
            logger.debug(f"[{self.source_id}] Failed to parse card: {e}")
            return None
