"""
HuggingFace Spaces 采集器
采集HuggingFace热门在线AI演示空间
"""
import logging
from typing import List, Dict, Any

from .base import BaseCollector

logger = logging.getLogger(__name__)


class Collector(BaseCollector):
    """HuggingFace Spaces 采集器"""

    def collect(self) -> List[Dict[str, Any]]:
        """采集HuggingFace trending spaces"""
        items = []
        params = self.config.get("params", {})
        sort_by = params.get("sort", "trending")
        limit = self.config.get("fetch_limit", params.get("limit", 30))

        url = self.config.get("url", "https://huggingface.co/api/spaces")

        try:
            resp = self.fetch_json(url, params={
                "sort": sort_by,
                "limit": limit,
            })

            for space in resp:
                item = self._parse_space(space)
                if item:
                    items.append(item)

            logger.info(f"[{self.source_id}] Found {len(resp)} spaces")

        except Exception as e:
            logger.error(f"[{self.source_id}] Failed to fetch spaces: {e}")

        return self._dedup_by_id(items)

    def _parse_space(self, space: Dict) -> Dict[str, Any]:
        """解析单个space数据"""
        try:
            space_id = space.get("id", "")
            if not space_id:
                return None

            author = space.get("author", "")
            last_modified = space.get("lastModified", "")
            likes = space.get("likes", 0)
            sdk = space.get("sdk", "")
            tags = space.get("tags", [])
            pipeline_tag = space.get("pipeline_tag", "")

            # name取id最后一部分
            name = space_id.split("/")[-1] if "/" in space_id else space_id

            # 构造描述
            desc_parts = []
            if pipeline_tag:
                desc_parts.append(f"Pipeline: {pipeline_tag}")
            if sdk:
                desc_parts.append(f"SDK: {sdk}")
            if tags:
                # 过滤掉license类标签
                meaningful_tags = [
                    t for t in tags[:10]
                    if not t.startswith("license:") and not t.startswith("size_")
                ]
                if meaningful_tags:
                    desc_parts.append("Tags: " + ", ".join(meaningful_tags))

            description = " | ".join(desc_parts) if desc_parts else f"HuggingFace Space: {space_id}"

            # 构建标签列表
            space_tags = []
            if pipeline_tag:
                space_tags.append(pipeline_tag)
            for tag in tags[:15]:
                if not tag.startswith("license:") and not tag.startswith("size_") and tag not in space_tags:
                    space_tags.append(tag)

            return {
                "name": name,
                "full_name": space_id,
                "url": f"https://huggingface.co/spaces/{space_id}",
                "description": description,
                "description_zh": "",
                "source": self.source_id,
                "source_url": "https://huggingface.co/api/spaces",
                "tags": space_tags,
                "platform": [self.source_id],
                "type": "ai_tool",
                "raw_data": {
                    "author": author,
                    "likes": likes,
                    "sdk": sdk,
                    "pipeline_tag": pipeline_tag,
                    "last_modified": last_modified,
                },
            }
        except Exception as e:
            logger.warning(f"[{self.source_id}] Failed to parse space: {e}")
            return None

    def _dedup_by_id(self, items: List[Dict]) -> List[Dict]:
        """按space_id去重"""
        seen = {}
        for item in items:
            key = item.get("full_name", item["name"])
            if key not in seen:
                seen[key] = item
        return list(seen.values())
