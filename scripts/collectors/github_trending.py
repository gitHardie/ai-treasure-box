"""
GitHub Trending 采集器
采集GitHub每日/每周热门AI项目
"""
import re
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone
from bs4 import BeautifulSoup

from .base import BaseCollector

logger = logging.getLogger(__name__)


class Collector(BaseCollector):
    """GitHub Trending 采集器"""

    def collect(self) -> List[Dict[str, Any]]:
        """采集GitHub Trending页面"""
        items = []

        # 采集每日和每周的trending
        for since in ["daily", "weekly"]:
            url = f"{self.config.get('url', 'https://github.com/trending')}?since={since}"
            logger.info(f"[{self.source_id}] Fetching {since} trending...")

            try:
                resp = self.fetch(url)
                soup = BeautifulSoup(resp.text, "html.parser")
                repos = soup.select("article.Box-row")

                for repo in repos:
                    item = self._parse_repo(repo, since)
                    if item:
                        items.append(item)

                logger.info(f"[{self.source_id}] Found {len(repos)} repos for {since}")
            except Exception as e:
                logger.error(f"[{self.source_id}] Failed to fetch {since}: {e}")

        # 去重（同一个repo可能同时出现在daily和weekly）
        return self._dedup_by_name(items)

    def _parse_repo(self, repo_element, period: str) -> Dict[str, Any]:
        """解析单个repo元素"""
        try:
            # 仓库全名 (owner/name)
            full_name_el = repo_element.select_one("h2 a")
            if not full_name_el:
                return None
            full_name = full_name_el.get("href", "").strip("/")

            # 描述
            desc_el = repo_element.select_one("p")
            description = desc_el.get_text(strip=True) if desc_el else ""

            # 编程语言
            lang_el = repo_element.select_one("[itemprop='programmingLanguage']")
            language = lang_el.get_text(strip=True) if lang_el else ""

            # Stars 和 Forks
            links = repo_element.select("a.Link--muted")
            stars = self._parse_number(links[0].get_text(strip=True)) if len(links) > 0 else 0
            forks = self._parse_number(links[1].get_text(strip=True)) if len(links) > 1 else 0

            # 本次新增stars
            stars_today_el = repo_element.select_one("span.d-inline-block.float-sm-right")
            stars_today = 0
            if stars_today_el:
                stars_today = self._parse_number(stars_today_el.get_text(strip=True))

            # Topics/标签
            topics = []
            topic_els = repo_element.select("a.topic-tag")
            for t in topic_els:
                topics.append(t.get_text(strip=True))

            return {
                "name": full_name.split("/")[-1] if "/" in full_name else full_name,
                "full_name": full_name,
                "url": f"https://github.com/{full_name}",
                "description": description,
                "language": language,
                "stars": stars,
                "forks": forks,
                "stars_in_period": stars_today,
                "period": period,
                "topics": topics,
                "platform": ["github"],
                "license": "",  # Trending页面不直接显示
                "type": "github_project",
                "_period": period,
            }
        except Exception as e:
            logger.warning(f"[{self.source_id}] Failed to parse repo: {e}")
            return None

    def _parse_number(self, text: str) -> int:
        """解析数字文本，如 '12,345' -> 12345"""
        text = text.replace(",", "").replace("+", "").strip()
        # 处理 "1.2k" 这种格式
        match = re.match(r"([\d.]+)\s*k", text, re.IGNORECASE)
        if match:
            return int(float(match.group(1)) * 1000)
        match = re.search(r"(\d+)", text)
        return int(match.group(1)) if match else 0

    def _dedup_by_name(self, items: List[Dict]) -> List[Dict]:
        """按repo名去重，保留信息更全的"""
        seen = {}
        for item in items:
            name = item.get("full_name", item["name"])
            if name not in seen:
                seen[name] = item
            else:
                # 合并period信息
                existing = seen[name]
                if item.get("description") and not existing.get("description"):
                    existing["description"] = item["description"]
                # stars取较大值
                if item.get("stars", 0) > existing.get("stars", 0):
                    existing["stars"] = item["stars"]
        return list(seen.values())
