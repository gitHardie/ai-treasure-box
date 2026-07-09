"""
AI-Bot.cn 采集器
采集国内优质AI工具导航
"""
import re
import logging
from typing import List, Dict, Any

from bs4 import BeautifulSoup

from .base import BaseCollector

logger = logging.getLogger(__name__)


class Collector(BaseCollector):
    """AI-Bot.cn 采集器"""

    def collect(self) -> List[Dict[str, Any]]:
        """采集AI-Bot.cn工具列表"""
        items = []

        # 主要分类页面
        categories = [
            "",  # 首页
            "ai-chat",
            "ai-writing",
            "ai-image",
            "ai-video",
            "ai-audio",
            "ai-code",
            "ai-design",
            "ai-productivity",
        ]

        base_url = self.config.get("url", "https://ai-bot.cn")

        for cat in categories:
            url = f"{base_url}/{cat}" if cat else base_url
            try:
                resp = self.fetch(url)
                soup = BeautifulSoup(resp.text, "html.parser")
                found = self._parse_page(soup, base_url)
                items.extend(found)
                logger.info(f"[{self.source_id}] {cat or 'index'}: {len(found)} tools")
            except Exception as e:
                logger.warning(f"[{self.source_id}] Failed to fetch {cat or 'index'}: {e}")

        return self.dedup_by_url(items)

    def _parse_page(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """解析页面中的工具卡片"""
        items = []

        # ai-bot.cn 的工具卡片结构
        # 尝试多种选择器
        cards = soup.select(".tool-item, .card, .ai-tool-card, article, .entry")

        if not cards:
            # 如果没找到卡片，尝试找链接列表
            cards = soup.select("a[href*='http']")
            for card in cards[:50]:  # 限制数量
                href = card.get("href", "")
                title = card.get_text(strip=True)
                if title and len(title) > 2 and len(title) < 100:
                    if self._is_tool_link(href):
                        items.append({
                            "name": title,
                            "url": href,
                            "description": "",
                            "platform": ["ai-bot.cn"],
                            "type": "ai_tool",
                        })
            return items

        for card in cards:
            try:
                # 提取链接
                link_el = card.select_one("a[href]")
                if not link_el:
                    continue
                url = link_el.get("href", "")
                if not url.startswith("http"):
                    continue

                # 提取标题
                title_el = card.select_one("h2, h3, h4, .title, .name, strong")
                title = title_el.get_text(strip=True) if title_el else link_el.get_text(strip=True)
                if not title or len(title) < 2:
                    continue

                # 提取描述
                desc_el = card.select_one("p, .desc, .description, .summary")
                description = desc_el.get_text(strip=True) if desc_el else ""

                items.append({
                    "name": title,
                    "url": url,
                    "description": description[:300],
                    "platform": ["ai-bot.cn"],
                    "type": "ai_tool",
                })

            except Exception as e:
                logger.debug(f"Failed to parse card: {e}")
                continue

        return items

    def _is_tool_link(self, url: str) -> bool:
        """判断是否是有效的工具链接"""
        if not url.startswith("http"):
            return False
        # 排除常见非工具链接
        exclude = ["javascript:", "mailto:", "#", ".pdf", ".jpg", ".png"]
        return not any(ex in url.lower() for ex in exclude)
