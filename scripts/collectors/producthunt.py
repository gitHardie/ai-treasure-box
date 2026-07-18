"""
Product Hunt AI 采集器 v2
使用 GraphQL API 获取 AI 类产品，替代旧的 HTML 爬虫方案。

认证：
  - 使用 OAuth client_credentials 获取 access token
  - 环境变量：PH_API_KEY, PH_API_SECRET
  - Token 永不过期（除非用户撤销授权）
  - 速率限制：450-900 请求/15 分钟
"""
import os
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta

import requests

from .base import BaseCollector

logger = logging.getLogger(__name__)

PH_GRAPHQL_URL = "https://api.producthunt.com/v2/api/graphql"

# 经验证有效的 AI 相关 topics
AI_TOPICS = [
    "artificial-intelligence",
    "developer-tools",
]

POSTS_QUERY = """
query PostsByTopic($topic: String!, $first: Int!, $after: String, $postedAfter: DateTime) {
  posts(first: $first, topic: $topic, after: $after, postedAfter: $postedAfter) {
    edges {
      cursor
      node {
        id
        name
        slug
        tagline
        description
        website
        url
        votesCount
        commentsCount
        createdAt
        featuredAt
        dailyRank
        topics {
          edges {
            node { name }
          }
        }
        thumbnail { url }
        makers { id name username }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""


class Collector(BaseCollector):
    """Product Hunt GraphQL API 采集器"""

    def __init__(self, source_config: Dict, global_config: Dict = None):
        super().__init__(source_config, global_config)
        self.api_key = os.environ.get("PH_API_KEY", "")
        self.api_secret = os.environ.get("PH_API_SECRET", "")
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0

    def _get_access_token(self) -> str:
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        if not self.api_key or not self.api_secret:
            raise ValueError(
                "Product Hunt API credentials not configured. "
                "Set PH_API_KEY and PH_API_SECRET environment variables."
            )

        resp = requests.post(
            "https://api.producthunt.com/v2/oauth/token",
            json={
                "client_id": self.api_key,
                "client_secret": self.api_secret,
                "grant_type": "client_credentials",
                "scope": "public",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._token_expires_at = time.time() + 3600
        logger.info(f"[{self.source_id}] Obtained access token")
        return self._access_token

    def _graphql(self, query: str, variables: Dict = None) -> Dict:
        token = self._get_access_token()
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        resp = requests.post(
            PH_GRAPHQL_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            msgs = [e.get("message", str(e)) for e in data["errors"]]
            raise RuntimeError(f"GraphQL errors: {'; '.join(msgs)}")
        return data.get("data", {})

    def _clean_url(self, url: str) -> str:
        if not url:
            return url
        return url.split("?")[0] if "?" in url else url

    def _tool_url(self, node: Dict) -> str:
        slug = node.get("slug", "")
        if slug:
            return f"https://www.producthunt.com/products/{slug}"
        return self._clean_url(node.get("url", ""))

    def _parse_post(self, node: Dict) -> Dict[str, Any]:
        topics = [
            e["node"]["name"]
            for e in node.get("topics", {}).get("edges", [])
            if e.get("node", {}).get("name")
        ]
        makers = [
            {"name": m.get("name", ""), "username": m.get("username", "")}
            for m in node.get("makers", [])
        ]
        thumb = node.get("thumbnail") or {}
        tagline = node.get("tagline", "")
        desc = node.get("description", "").replace("&nbsp;", " ").replace("&amp;", "&")

        return {
            "name": node.get("name", ""),
            "slug": node.get("slug", ""),
            "url": self._tool_url(node),
            "description": f"{tagline}. {desc}" if tagline and desc else (tagline or desc),
            "source": self.source_id,
            "source_url": self.config.get("url", ""),
            "tags": topics,
            "platform": ["producthunt"],
            "type": "ai_tool",
            "thumbnail_url": thumb.get("url", ""),
            "raw_data": {
                "ph_id": node.get("id", ""),
                "tagline": tagline,
                "votes_count": node.get("votesCount", 0),
                "comments_count": node.get("commentsCount", 0),
                "created_at": node.get("createdAt", ""),
                "featured_at": node.get("featuredAt", ""),
                "daily_rank": node.get("dailyRank"),
                "makers": makers,
                "topics": topics,
            },
        }

    def _fetch_topic(self, topic: str, max_pages: int = 3) -> List[Dict]:
        """获取指定 topic 的 posts，支持分页"""
        posts = []
        cursor = None
        # 只采集最近半年的数据
        posted_after = (datetime.now(timezone.utc) - timedelta(days=180)).strftime("%Y-%m-%dT%H:%M:%SZ")

        for page in range(max_pages):
            variables = {"topic": topic, "first": 20, "postedAfter": posted_after}
            if cursor:
                variables["after"] = cursor
            try:
                data = self._graphql(POSTS_QUERY, variables)
                posts_data = data.get("posts", {})
                edges = posts_data.get("edges", [])
                page_info = posts_data.get("pageInfo", {})

                for edge in edges:
                    node = edge.get("node", {})
                    if node:
                        posts.append(node)

                logger.info(f"[{self.source_id}] '{topic}' p{page+1}: {len(edges)} posts")

                if not page_info.get("hasNextPage"):
                    break
                cursor = page_info.get("endCursor")
                time.sleep(1)
            except Exception as e:
                logger.error(f"[{self.source_id}] '{topic}' p{page+1} failed: {e}")
                break
        return posts

    def collect(self) -> List[Dict[str, Any]]:
        seen_ids = set()
        all_posts = []

        for topic in AI_TOPICS:
            try:
                posts = self._fetch_topic(topic, max_pages=3)
                for p in posts:
                    pid = p.get("id")
                    if pid and pid not in seen_ids:
                        seen_ids.add(pid)
                        all_posts.append(p)
                logger.info(f"[{self.source_id}] '{topic}': +{len(posts)}, unique total: {len(all_posts)}")
            except Exception as e:
                logger.error(f"[{self.source_id}] Error on '{topic}': {e}")

        items = []
        for post in all_posts:
            item = self._parse_post(post)
            if item and item.get("name"):
                items.append(item)

        logger.info(f"[{self.source_id}] Total: {len(items)} items")
        return self.apply_fetch_limit(items)
