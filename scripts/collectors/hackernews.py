"""
Hacker News AI 采集器
通过Algolia API采集AI相关热帖
"""
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone

from .base import BaseCollector

logger = logging.getLogger(__name__)


class Collector(BaseCollector):
    """Hacker News AI 采集器"""

    def collect(self) -> List[Dict[str, Any]]:
        """通过Algolia HN API采集AI相关帖子"""
        items = []
        params = self.config.get("params", {})

        url = self.config.get("url", "https://hn.algolia.com/api/v1/search")

        try:
            resp = self.fetch_json(url, params={
                "query": params.get("query", "AI OR LLM OR GPT"),
                "tags": params.get("tags", "story"),
                "hitsPerPage": params.get("hitsPerPage", 30),
                "numericFilters": "points>20",
            })

            hits = resp.get("hits", [])
            for hit in hits:
                item = self._parse_hit(hit)
                if item:
                    items.append(item)

            logger.info(f"[{self.source_id}] Found {len(hits)} stories")

        except Exception as e:
            logger.error(f"[{self.source_id}] Failed: {e}")

        return items

    def _parse_hit(self, hit: Dict) -> Dict[str, Any]:
        """解析HN帖子"""
        try:
            story_url = hit.get("url", "")
            if not story_url:
                return None

            return {
                "name": hit.get("title", ""),
                "title": hit.get("title", ""),
                "url": story_url,
                "hn_url": f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                "description": hit.get("title", ""),
                "points": hit.get("points", 0),
                "num_comments": hit.get("num_comments", 0),
                "author": hit.get("author", ""),
                "published_at": hit.get("created_at", ""),
                "platform": ["hackernews"],
                "type": "news",
            }
        except Exception as e:
            logger.warning(f"[{self.source_id}] Failed to parse hit: {e}")
            return None
