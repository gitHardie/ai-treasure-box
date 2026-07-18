"""
There's An AI For That (TAAFT) 采集器
采集 theresanaiforthat.com 首页的 AI 工具列表。

注意：该网站有 Cloudflare 保护，仅首页可访问（~19 个工具）。
详情页、列表页和 sitemap 均被 403 拦截。
作为补充数据源使用，与 Product Hunt 互补。
"""
import logging
from typing import List, Dict, Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseCollector

logger = logging.getLogger(__name__)


class Collector(BaseCollector):
    """TAAFT 首页采集器"""

    def collect(self) -> List[Dict[str, Any]]:
        items = []
        base_url = self.config.get("url", "https://theresanaiforthat.com")

        # 增强 UA
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        })

        try:
            resp = self.fetch(base_url)
            soup = BeautifulSoup(resp.text, "html.parser")

            # TAAFT 首页工具名链接使用 .tools-name-heading-link
            heading_links = soup.select(".tools-name-heading-link")
            if not heading_links:
                # 降级：使用 .tools-name-main-link
                heading_links = soup.select(".tools-name-main-link")

            logger.info(f"[{self.source_id}] Found {len(heading_links)} tool links")

            # 用 heading-link 去重（同一工具有两个 main-link）
            seen_urls = set()
            for link in heading_links:
                href = link.get("href", "")
                if not href or href in seen_urls:
                    continue
                seen_urls.add(href)

                name = link.get_text(strip=True)
                if not name or len(name) < 2:
                    continue

                # 找父容器获取更多信息
                row = link.find_parent(class_=lambda c: c and any(
                    x in (c if isinstance(c, list) else [c])
                    for x in ["listing-table-cell", "home-today-name-cell"]
                ))

                tagline = ""
                if row:
                    tagline_el = row.select_one(".tools-name-tagline")
                    if tagline_el:
                        tagline = tagline_el.get_text(strip=True)

                # TAAFT 页面 URL 作为工具链接
                tool_url = href if href.startswith("http") else urljoin(base_url, href)

                items.append({
                    "name": name,
                    "url": tool_url,
                    "description": tagline,
                    "source": self.source_id,
                    "source_url": base_url,
                    "tags": ["ai-tool-directory"],
                    "platform": ["taaft"],
                    "type": "ai_tool",
                    "raw_data": {
                        "slug": href.rstrip("/").split("/")[-1] if href else "",
                    },
                })

            logger.info(f"[{self.source_id}] Parsed {len(items)} unique tools")

        except Exception as e:
            logger.error(f"[{self.source_id}] Failed: {e}")

        return self.dedup_by_url(items)
