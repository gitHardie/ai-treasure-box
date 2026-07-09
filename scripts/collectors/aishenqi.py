"""
AI神器集 采集器
采集aishenqi.net的AI工具导航
"""
import re
import logging
from typing import List, Dict, Any

from bs4 import BeautifulSoup

from .base import BaseCollector

logger = logging.getLogger(__name__)


class Collector(BaseCollector):
    """AI神器集 采集器"""

    def collect(self) -> List[Dict[str, Any]]:
        """采集AI神器集工具列表"""
        items = []
        base_url = self.config.get("url", "https://aishenqi.net")

        try:
            resp = self.fetch(base_url)
            soup = BeautifulSoup(resp.text, "html.parser")

            # 尝试找到所有工具卡片
            # aishenqi.net 通常使用卡片布局
            cards = soup.select(".tool-card, .card, .item, article, [class*='tool']")

            if not cards:
                # 降级：找所有带链接的区块
                cards = self._find_tool_blocks(soup)

            for card in cards:
                item = self._parse_card(card)
                if item:
                    items.append(item)

            # 也尝试找分类链接，爬取子页面
            cat_links = soup.select("a[href*='category'], a[href*='tag'], nav a")
            visited = {base_url}
            for link in cat_links[:10]:  # 限制子页面数量
                href = link.get("href", "")
                if href.startswith("http") and href not in visited:
                    visited.add(href)
                    try:
                        sub_resp = self.fetch(href)
                        sub_soup = BeautifulSoup(sub_resp.text, "html.parser")
                        sub_cards = sub_soup.select(".tool-card, .card, .item, article, [class*='tool']")
                        for card in sub_cards:
                            item = self._parse_card(card)
                            if item:
                                items.append(item)
                    except Exception:
                        pass

            logger.info(f"[{self.source_id}] Found {len(items)} tools")

        except Exception as e:
            logger.error(f"[{self.source_id}] Failed: {e}")

        return self.dedup_by_url(items)

    def _find_tool_blocks(self, soup: BeautifulSoup) -> list:
        """当标准选择器失败时，尝试找工具区块"""
        blocks = []
        # 找所有包含外部链接的div/section
        for container in soup.select("div, section, li"):
            links = container.select("a[href^='http']")
            if links and len(container.get_text(strip=True)) > 10:
                # 只取最内层的有链接的容器
                has_inner = False
                for child in container.children:
                    if hasattr(child, 'select') and child.select("a[href^='http']"):
                        has_inner = True
                        break
                if not has_inner:
                    blocks.append(container)
                if len(blocks) >= 200:
                    break
        return blocks

    def _parse_card(self, card) -> Dict[str, Any]:
        """解析工具卡片"""
        try:
            # 链接
            link = card.select_one("a[href^='http']")
            if not link:
                return None
            url = link.get("href", "")

            # 标题
            title_el = card.select_one("h2, h3, h4, h5, .title, .name, strong, b")
            title = title_el.get_text(strip=True) if title_el else link.get_text(strip=True)
            if not title or len(title) < 2 or len(title) > 200:
                return None

            # 描述
            desc_el = card.select_one("p, .desc, .description, .summary, small, span:not(.title)")
            description = desc_el.get_text(strip=True) if desc_el else ""

            # 分类/标签
            tags = []
            tag_els = card.select(".tag, .label, .category, .badge")
            for t in tag_els:
                tags.append(t.get_text(strip=True))

            return {
                "name": title,
                "url": url,
                "description": description[:300],
                "tags": tags,
                "platform": ["aishenqi"],
                "type": "ai_tool",
            }
        except Exception:
            return None
