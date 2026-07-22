"""
AI-Bot.cn 采集器 v2
采集国内优质AI工具导航 - 只采集外部工具URL，排除导航页面

v2改动:
- 排除ai-bot.cn自身域名的链接（只采集外部工具URL）
- 修复编码问题（meta charset检测 + apparent_encoding）
- 过滤导航/聚合页面
- 过滤SEO标题（"是什么"/"怎么样"/"好用吗"）
"""
import re
import logging
from typing import List, Dict, Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import BaseCollector

logger = logging.getLogger(__name__)

# ai-bot.cn 自身域名（这些不是工具URL，要排除）
SELF_DOMAINS = {"ai-bot.cn", "www.ai-bot.cn"}

# 导航/聚合站域名（这些页面不应作为工具URL）
NAVIGATION_DOMAINS = {
    "ai-bot.cn", "www.ai-bot.cn",
    "toolify.ai", "www.toolify.ai",
    "aitools.fyi", "www.aitools.fyi",
}

# SEO后缀（应清理的标题后缀）
SEO_SUFFIX_RE = re.compile(
    r'(是什么|怎么样|好用吗|推荐|评测|排行榜|大全|有哪些|哪个好)$',
    re.IGNORECASE
)


class Collector(BaseCollector):
    """AI-Bot.cn 采集器 v2"""

    def collect(self) -> List[Dict[str, Any]]:
        """采集AI-Bot.cn工具列表"""
        items = []

        categories = [
            "",          # 首页
            "ai-chat",
            "ai-writing",
            "ai-image",
            "ai-video",
            "ai-code",
            "ai-design",
        ]

        base_url = self.config.get("url", "https://ai-bot.cn")

        for cat in categories:
            url = f"{base_url}/{cat}" if cat else base_url
            try:
                resp = self.fetch(url)
                # Fix encoding
                text = self._decode_response(resp)
                soup = BeautifulSoup(text, "html.parser")
                found = self._parse_page(soup, base_url)
                items.extend(found)
                logger.info(f"[{self.source_id}] {cat or 'index'}: {len(found)} tools")
            except Exception as e:
                logger.warning(f"[{self.source_id}] Failed to fetch {cat or 'index'}: {e}")

        return self.dedup_by_url(items)

    def _decode_response(self, resp) -> str:
        """修复编码问题"""
        # 1. 尝试从 meta charset 获取
        if resp.content:
            match = re.search(
                rb'<meta[^>]+charset=["\']?([^"\'\s;>]+)',
                resp.content[:2000],
                re.IGNORECASE
            )
            if match:
                charset = match.group(1).decode("ascii", errors="ignore")
                try:
                    return resp.content.decode(charset)
                except (UnicodeDecodeError, LookupError):
                    pass

        # 2. 尝试 apparent_encoding
        if hasattr(resp, 'apparent_encoding') and resp.apparent_encoding:
            try:
                return resp.content.decode(resp.apparent_encoding)
            except (UnicodeDecodeError, LookupError):
                pass

        # 3. 尝试常见中文编码
        for enc in ["utf-8", "gbk", "gb2312", "gb18030"]:
            try:
                return resp.content.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue

        # 4. Fallback
        return resp.text

    def _is_external_tool_url(self, url: str) -> bool:
        """判断是否是有效的外部工具URL（排除自身域名和导航站）"""
        if not url or not url.startswith("http"):
            return False

        try:
            domain = urlparse(url).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
        except Exception:
            return False

        # 排除自身域名
        if domain in SELF_DOMAINS:
            return False

        # 排除导航/聚合站
        if domain in NAVIGATION_DOMAINS:
            return False

        # 排除非http链接
        exclude = ["javascript:", "mailto:", "#", ".pdf", ".jpg", ".png", ".gif"]
        if any(ex in url.lower() for ex in exclude):
            return False

        return True

    def _clean_name(self, name: str) -> str:
        """清理SEO标题后缀"""
        name = name.strip()
        # 去掉SEO后缀
        name = SEO_SUFFIX_RE.sub("", name)
        return name.strip()

    def _is_navigation_title(self, title: str) -> bool:
        """判断是否是导航页面标题（不是工具名）"""
        nav_keywords = [
            "热门工具", "最新收录", "最新文章", "工具大全",
            "排行榜", "分类导航", "精选推荐", "编辑推荐",
            "热门文章", "推荐工具", "工具列表"
        ]
        for kw in nav_keywords:
            if kw in title:
                return True
        return False

    def _parse_page(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """解析页面中的工具卡片"""
        items = []

        # ai-bot.cn 的工具卡片结构
        cards = soup.select(".tool-item, .card, .ai-tool-card, article, .entry")

        if not cards:
            # 如果没找到卡片，尝试找链接列表
            links = soup.select("a[href*='http']")
            for link in links[:100]:
                href = link.get("href", "")
                title = link.get_text(strip=True)

                if not title or len(title) < 2 or len(title) > 100:
                    continue
                if not self._is_external_tool_url(href):
                    continue
                if self._is_navigation_title(title):
                    continue

                clean_title = self._clean_name(title)
                if not clean_title or len(clean_title) < 2:
                    continue

                items.append({
                    "name": clean_title,
                    "url": href,
                    "description": "",
                    "platform": ["ai-bot.cn"],
                    "type": "ai_tool",
                })
            return items

        for card in cards:
            try:
                # 提取链接 - 优先找外部链接
                link_els = card.select("a[href]")
                tool_url = None
                for link_el in link_els:
                    href = link_el.get("href", "")
                    if self._is_external_tool_url(href):
                        tool_url = href
                        break

                if not tool_url:
                    continue

                # 提取标题
                title_el = card.select_one("h2, h3, h4, .title, .name, strong")
                title = title_el.get_text(strip=True) if title_el else ""
                if not title:
                    title = link_el.get_text(strip=True)

                if not title or len(title) < 2:
                    continue
                if self._is_navigation_title(title):
                    continue

                clean_title = self._clean_name(title)
                if not clean_title:
                    continue

                # 提取描述
                desc_el = card.select_one("p, .desc, .description, .summary")
                description = desc_el.get_text(strip=True) if desc_el else ""

                items.append({
                    "name": clean_title,
                    "url": tool_url,
                    "description": description[:300],
                    "platform": ["ai-bot.cn"],
                    "type": "ai_tool",
                })

            except Exception as e:
                logger.debug(f"Failed to parse card: {e}")
                continue

        return items
