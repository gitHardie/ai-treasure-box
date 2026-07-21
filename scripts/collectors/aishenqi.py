"""
AI神器集 采集器
采集aishenqi.net的AI工具导航

v2: 修复编码问题、过滤导航页面、清理名称后缀
"""
import re
import logging
from typing import List, Dict, Any, Set
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import BaseCollector

logger = logging.getLogger(__name__)

# 导航/聚合类页面关键词 — 这些不是工具，是aishenqi自己的导航页面
NAVIGATION_KEYWORDS = [
    "排行榜", "更多神器", "发现更多", "AI导航", "导航站",
    "热门推荐", "最新收录", "热门推荐", "工具分类",
    "关于我们", "友情链接", "投稿", "广告合作",
]

# 名称清理：去掉 "是什么"、"怎么样" 等 SEO 后缀
NAME_SUFFIX_RE = re.compile(r'(是什么|怎么样|好用吗|评测|官网|入口)$')


class Collector(BaseCollector):
    """AI神器集 采集器"""

    def collect(self) -> List[Dict[str, Any]]:
        """采集AI神器集工具列表"""
        items = []
        base_url = self.config.get("url", "https://aishenqi.net")
        base_domain = urlparse(base_url).netloc

        try:
            resp = self.fetch(base_url)
            # 修复编码：优先用 apparent_encoding 检测实际编码
            html_text = self._decode_response(resp)
            soup = BeautifulSoup(html_text, "html.parser")

            # aishenqi.net 是 WordPress 站点，工具以卡片形式列出
            # 每个卡片通常包含一个工具名称链接和描述
            cards = soup.select(".tool-card, .card, .item, article, [class*='tool']")

            if not cards:
                cards = self._find_tool_blocks(soup, base_domain)

            seen_urls: Set[str] = set()
            for card in cards:
                item = self._parse_card(card, base_domain, seen_urls)
                if item:
                    items.append(item)

            # 爬取分类子页面（只爬工具列表页，跳过标签/排行页）
            cat_links = soup.select("a[href*='category']")
            visited = {base_url, base_url + "/", base_url + "/#"}
            for link in cat_links[:10]:
                href = link.get("href", "")
                if href.startswith("http") and href not in visited:
                    visited.add(href)
                    try:
                        sub_resp = self.fetch(href)
                        sub_html = self._decode_response(sub_resp)
                        sub_soup = BeautifulSoup(sub_html, "html.parser")
                        sub_cards = sub_soup.select(".tool-card, .card, .item, article, [class*='tool']")
                        for card in sub_cards:
                            item = self._parse_card(card, base_domain, seen_urls)
                            if item:
                                items.append(item)
                    except Exception:
                        pass

            logger.info(f"[{self.source_id}] Found {len(items)} valid tools (filtered navigation pages)")

        except Exception as e:
            logger.error(f"[{self.source_id}] Failed: {e}")

        return self.dedup_by_url(items)

    def _decode_response(self, resp) -> str:
        """修复编码：尝试多种编码检测策略"""
        # 策略1: 从 HTML meta 标签中找 charset
        content_type = resp.headers.get("Content-Type", "")
        html_bytes = resp.content

        # 尝试从 meta 标签提取编码
        meta_match = re.search(
            rb'<meta[^>]+charset=["\']?([^"\'\s;>]+)',
            html_bytes[:2000],
            re.IGNORECASE,
        )
        if meta_match:
            charset = meta_match.group(1).decode("ascii", errors="ignore").strip()
            try:
                return html_bytes.decode(charset)
            except (UnicodeDecodeError, LookupError):
                pass

        # 策略2: 用 apparent_encoding (chardet/chardet2)
        if hasattr(resp, 'apparent_encoding') and resp.apparent_encoding:
            try:
                return html_bytes.decode(resp.apparent_encoding)
            except (UnicodeDecodeError, LookupError):
                pass

        # 策略3: UTF-8 优先
        try:
            return html_bytes.decode("utf-8")
        except UnicodeDecodeError:
            pass

        # 策略4: GBK
        try:
            return html_bytes.decode("gbk")
        except UnicodeDecodeError:
            pass

        # 兜底: 替换错误字符
        return html_bytes.decode("utf-8", errors="replace")

    def _find_tool_blocks(self, soup: BeautifulSoup, base_domain: str) -> list:
        """当标准选择器失败时，尝试找工具区块"""
        blocks = []
        for container in soup.select("div, section, li"):
            links = container.select("a[href^='http']")
            if links and len(container.get_text(strip=True)) > 10:
                # 检查链接是否指向外部工具站（非aishenqi自身）
                is_external = False
                for link in links:
                    href = link.get("href", "")
                    if href.startswith("http"):
                        link_domain = urlparse(href).netloc
                        if link_domain != base_domain and "aishenqi" not in link_domain:
                            is_external = True
                            break
                if not is_external:
                    continue
                blocks.append(container)
                if len(blocks) >= 200:
                    break
        return blocks

    def _is_navigation_page(self, title: str, url: str, base_domain: str) -> bool:
        """判断是否为导航/聚合页面（不是工具）"""
        # 检查标题是否包含导航关键词
        for kw in NAVIGATION_KEYWORDS:
            if kw in title:
                return True

        # 检查URL是否是aishenqi的内部页面
        parsed = urlparse(url)
        path = parsed.path.lower()
        # tag页面、排行页面、工具分类页面
        if "/tooltag/" in path or "/tag/" in path or "/rank" in path:
            return True

        # 检查URL域名是否为aishenqi自身的导航页
        if "aishenqi.net" in parsed.netloc and parsed.path in ("", "/", "/#"):
            return True

        return False

    def _clean_name(self, name: str) -> str:
        """清理工具名称，去掉SEO后缀"""
        name = name.strip()
        # 去掉 "是什么" "怎么样" 等后缀
        name = NAME_SUFFIX_RE.sub("", name)
        return name.strip()

    def _parse_card(self, card, base_domain: str, seen_urls: Set[str]) -> Dict[str, Any] | None:
        """解析工具卡片"""
        try:
            # 找到所有外部链接
            all_links = card.select("a[href^='http']")
            if not all_links:
                return None

            # 找到工具的实际URL（非aishenqi自身的链接）
            tool_url = None
            for link in all_links:
                href = link.get("href", "")
                if href.startswith("http"):
                    link_domain = urlparse(href).netloc
                    if link_domain != base_domain and "aishenqi" not in link_domain:
                        tool_url = href
                        break

            # 如果没有外部链接，跳过（可能是导航链接）
            if not tool_url:
                return None

            # 去重
            if tool_url in seen_urls:
                return None
            seen_urls.add(tool_url)

            # 标题
            title_el = card.select_one("h2, h3, h4, h5, .title, .name, strong, b")
            title = title_el.get_text(strip=True) if title_el else all_links[0].get_text(strip=True)
            if not title or len(title) < 2 or len(title) > 200:
                return None

            # 清理名称
            title = self._clean_name(title)
            if not title or len(title) < 2:
                return None

            # 过滤导航页面
            if self._is_navigation_page(title, tool_url, base_domain):
                return None

            # 描述
            desc_el = card.select_one("p, .desc, .description, .summary, small, span:not(.title)")
            description = desc_el.get_text(strip=True) if desc_el else ""
            # 过滤纯数字描述（如 "(317)"）
            if description and re.match(r'^[\(\[]?\d+[\)\]]?$', description):
                description = ""

            # 分类/标签
            tags = []
            tag_els = card.select(".tag, .label, .category, .badge")
            for t in tag_els:
                tag_text = t.get_text(strip=True)
                if tag_text and len(tag_text) < 50:
                    tags.append(tag_text)

            return {
                "name": title,
                "url": tool_url,
                "description": description[:300],
                "tags": tags,
                "platform": ["aishenqi"],
                "type": "ai_tool",
            }
        except Exception:
            return None
