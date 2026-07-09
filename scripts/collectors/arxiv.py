"""
ArXiv AI论文 采集器
通过ArXiv API采集最新AI论文
"""
import logging
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from datetime import datetime, timezone

from .base import BaseCollector

logger = logging.getLogger(__name__)


class Collector(BaseCollector):
    """ArXiv AI论文 采集器"""

    # ArXiv Atom命名空间
    ATOM_NS = "{http://www.w3.org/2005/Atom}"
    ARXIV_NS = "{http://arxiv.org/schemas/atom}"

    def collect(self) -> List[Dict[str, Any]]:
        """采集ArXiv最新AI论文"""
        items = []
        params = self.config.get("params", {})

        url = self.config.get("url", "http://export.arxiv.org/api/query")

        try:
            resp = self.fetch(url, params={
                "search_query": params.get("search_query", "cat:cs.AI"),
                "max_results": params.get("max_results", 50),
                "sortBy": params.get("sortBy", "submittedDate"),
                "sortOrder": "descending",
            })

            # 解析Atom XML
            root = ET.fromstring(resp.content)
            entries = root.findall(f"{self.ATOM_NS}entry")

            for entry in entries:
                item = self._parse_entry(entry)
                if item:
                    items.append(item)

            logger.info(f"[{self.source_id}] Found {len(entries)} papers")

        except Exception as e:
            logger.error(f"[{self.source_id}] Failed: {e}")

        return items

    def _parse_entry(self, entry) -> Dict[str, Any]:
        """解析ArXiv论文条目"""
        try:
            # 标题
            title_el = entry.find(f"{self.ATOM_NS}title")
            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            title = " ".join(title.split())  # 清理换行

            # 链接
            links = entry.findall(f"{self.ATOM_NS}link")
            url = ""
            pdf_url = ""
            for link in links:
                href = link.get("href", "")
                if link.get("type") == "text/html":
                    url = href
                elif link.get("title") == "pdf":
                    pdf_url = href
            if not url:
                # 默认abs链接
                id_el = entry.find(f"{self.ATOM_NS}id")
                url = id_el.text if id_el is not None else ""

            # 摘要
            summary_el = entry.find(f"{self.ATOM_NS}summary")
            summary = summary_el.text.strip() if summary_el is not None and summary_el.text else ""
            summary = " ".join(summary.split())

            # 作者
            authors = []
            for author in entry.findall(f"{self.ATOM_NS}author"):
                name_el = author.find(f"{self.ATOM_NS}name")
                if name_el is not None and name_el.text:
                    authors.append(name_el.text)

            # 分类
            categories = []
            for cat in entry.findall(f"{self.ATOM_NS}category"):
                term = cat.get("term", "")
                if term:
                    categories.append(term)

            # 发布时间
            published_el = entry.find(f"{self.ATOM_NS}published")
            published = published_el.text if published_el is not None else ""

            # arXiv ID
            id_el = entry.find(f"{self.ATOM_NS}id")
            arxiv_id = id_el.text.split("/abs/")[-1] if id_el is not None and id_el.text else ""

            return {
                "name": title,
                "title": title,
                "url": url,
                "pdf_url": pdf_url,
                "description": summary[:500],
                "authors": authors[:5],  # 最多5个作者
                "categories": categories,
                "arxiv_id": arxiv_id,
                "published_at": published,
                "platform": ["arxiv"],
                "type": "paper",
            }
        except Exception as e:
            logger.warning(f"[{self.source_id}] Failed to parse entry: {e}")
            return None
