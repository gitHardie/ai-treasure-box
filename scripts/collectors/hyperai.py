"""
HyperAI 新闻采集器
通过RSS采集AI新闻资讯
"""
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone

import feedparser

from .base import BaseCollector

logger = logging.getLogger(__name__)


class Collector(BaseCollector):
    """HyperAI RSS 采集器"""

    def collect(self) -> List[Dict[str, Any]]:
        """采集HyperAI RSS feed"""
        items = []
        url = self.config.get("url", "https://hyper.ai/feed")

        try:
            resp = self.fetch(url)
            feed = feedparser.parse(resp.text)

            for entry in feed.entries:
                item = self._parse_entry(entry)
                if item:
                    items.append(item)

            logger.info(f"[{self.source_id}] Found {len(feed.entries)} entries")

        except Exception as e:
            logger.error(f"[{self.source_id}] Failed to parse RSS: {e}")

        return items

    def _parse_entry(self, entry) -> Dict[str, Any]:
        """解析RSS条目"""
        try:
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = entry.get("summary", "")
            published = entry.get("published", "")

            # 清理HTML标签
            if summary:
                from bs4 import BeautifulSoup
                summary = BeautifulSoup(summary, "html.parser").get_text(strip=True)

            # 提取标签/分类
            categories = []
            if hasattr(entry, "tags"):
                categories = [tag.term for tag in entry.tags if tag.term]

            return {
                "name": title,
                "title": title,
                "url": link,
                "description": summary[:500],  # 限制长度
                "published_at": published,
                "categories": categories,
                "platform": ["hyperai"],
                "type": "news",
            }
        except Exception as e:
            logger.warning(f"[{self.source_id}] Failed to parse entry: {e}")
            return None
