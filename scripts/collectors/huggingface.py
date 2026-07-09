"""
HuggingFace Models 采集器
采集HuggingFace热门AI模型
"""
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone

from .base import BaseCollector

logger = logging.getLogger(__name__)


class Collector(BaseCollector):
    """HuggingFace Models 采集器"""

    def collect(self) -> List[Dict[str, Any]]:
        """采集HuggingFace trending models"""
        items = []
        params = self.config.get("params", {})

        # 按不同任务类型采集
        task_filters = params.get("filter", ["text-generation", "image-generation"])
        sort_by = params.get("sort", "trending")
        limit = params.get("limit", 100)

        for task in task_filters:
            try:
                url = self.config.get("url", "https://huggingface.co/api/models")
                resp = self.fetch_json(url, params={
                    "sort": sort_by,
                    "limit": limit,
                    "pipeline_tag": task,
                })

                for model in resp:
                    item = self._parse_model(model, task)
                    if item:
                        items.append(item)

                logger.info(f"[{self.source_id}] Found {len(resp)} models for task={task}")

            except Exception as e:
                logger.error(f"[{self.source_id}] Failed for task={task}: {e}")

        # 去重
        return self._dedup_by_id(items)

    def _parse_model(self, model: Dict, task: str) -> Dict[str, Any]:
        """解析单个模型数据"""
        try:
            model_id = model.get("modelId", model.get("id", ""))
            if not model_id:
                return None

            # 基本信息
            tags = model.get("tags", [])
            pipeline_tag = model.get("pipeline_tag", task)

            # 下载量
            downloads = model.get("downloads", 0)
            likes = model.get("likes", 0)

            # 库信息
            library = model.get("library_name", "")

            # 提取描述
            description = model.get("cardData", {}).get("short_description", "")
            if not description:
                description = f"HuggingFace model: {model_id}"

            # 构建标签
            hf_tags = []
            for tag in tags[:20]:  # 限制标签数量
                if not tag.startswith("license:") and not tag.startswith("size_"):
                    hf_tags.append(tag)

            return {
                "name": model_id.split("/")[-1] if "/" in model_id else model_id,
                "full_name": model_id,
                "url": f"https://huggingface.co/{model_id}",
                "description": description,
                "pipeline_tag": pipeline_tag,
                "library": library,
                "downloads": downloads,
                "likes": likes,
                "tags": hf_tags,
                "platform": ["huggingface"],
                "type": "ai_model",
                "created_at": model.get("createdAt", ""),
                "last_modified": model.get("lastModified", ""),
            }
        except Exception as e:
            logger.warning(f"[{self.source_id}] Failed to parse model: {e}")
            return None

    def _dedup_by_id(self, items: List[Dict]) -> List[Dict]:
        """按model_id去重"""
        seen = {}
        for item in items:
            key = item.get("full_name", item["name"])
            if key not in seen:
                seen[key] = item
        return list(seen.values())
