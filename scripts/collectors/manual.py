"""
手动添加工具采集器
从 data/manual/ 目录读取手动添加的工具JSON文件
"""
import json
import logging
from typing import List, Dict, Any
from pathlib import Path

from .base import BaseCollector

logger = logging.getLogger(__name__)


class Collector(BaseCollector):
    """手动添加工具采集器"""

    def collect(self) -> List[Dict[str, Any]]:
        """从data/manual目录读取手动添加的工具"""
        items = []
        manual_dir = self.data_dir / "manual"

        if not manual_dir.exists():
            logger.info(f"[{self.source_id}] Manual directory does not exist: {manual_dir}")
            return items

        # 查找所有JSON文件
        json_files = list(manual_dir.glob("*.json"))

        if not json_files:
            logger.info(f"[{self.source_id}] No JSON files found in {manual_dir}")
            return items

        for json_file in json_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 支持单个工具或工具列表
                tools = data if isinstance(data, list) else [data]

                for tool in tools:
                    item = self._parse_tool(tool, str(json_file))
                    if item:
                        items.append(item)

                logger.info(f"[{self.source_id}] Loaded {len(tools)} tools from {json_file.name}")

            except Exception as e:
                logger.warning(f"[{self.source_id}] Failed to read {json_file.name}: {e}")

        logger.info(f"[{self.source_id}] Loaded {len(items)} manual tools total")
        return items

    def _parse_tool(self, tool: Dict, source_file: str) -> Dict[str, Any]:
        """解析单个手动添加工具"""
        try:
            name = tool.get("name", "").strip()
            url = tool.get("url", "").strip()
            description = tool.get("description", "").strip()

            # 验证必填字段
            if not name or not url or not description:
                logger.warning(f"[{self.source_id}] Tool missing required fields in {source_file}: name={name}, url={url}")
                return None

            # 处理标签 - 支持两种格式：简单列表或分维度字典
            raw_tags = tool.get("tags", [])
            tags = []
            if isinstance(raw_tags, list):
                tags = [t for t in raw_tags if isinstance(t, str)]
            elif isinstance(raw_tags, dict):
                for dimension_tags in raw_tags.values():
                    if isinstance(dimension_tags, list):
                        tags.extend([t for t in dimension_tags if isinstance(t, str)])

            category = tool.get("category", "")

            return {
                "name": name,
                "url": url,
                "description": description,
                "description_zh": tool.get("description_zh", ""),
                "source": self.source_id,
                "source_url": source_file,
                "tags": tags,
                "platform": [self.source_id],
                "type": "ai_tool",
                "raw_data": {
                    "category": category,
                    "subcategory": tool.get("subcategory", ""),
                    "license_tier": tool.get("license_tier", ""),
                    "is_china_tool": tool.get("is_china_tool", False),
                },
            }
        except Exception as e:
            logger.warning(f"[{self.source_id}] Failed to parse tool: {e}")
            return None
