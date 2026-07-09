"""
AI百宝箱 - Master 工具数据库

管理所有已采集的AI工具，支持：
  - 工具增删改查
  - 唯一ID生成
  - 内容指纹对比（diff）
  - AI分析结果合并
  - 健康检查队列
"""
import json
import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class ToolDatabase:
    """Master工具数据库 - 管理所有已采集的AI工具"""

    def __init__(self, db_path: str = "data/master_tools.json"):
        # 确保路径相对于项目根目录
        if not os.path.isabs(db_path):
            # scripts/ 子目录下运行时，需要回退到项目根
            base = Path(__file__).parent.parent.parent
            self.db_path = str(base / db_path)
        else:
            self.db_path = db_path

        self.tools: Dict[str, Dict[str, Any]] = {}
        self.metadata: Dict[str, Any] = {}
        self._loaded = False

    def load(self) -> "ToolDatabase":
        """加载数据库"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.tools = data.get("tools", {})
                self.metadata = data.get("metadata", {})
                logger.info(f"[ToolDB] Loaded {len(self.tools)} tools from {self.db_path}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"[ToolDB] Failed to load {self.db_path}: {e}, starting with empty DB")
                self.tools = {}
                self.metadata = {}
        else:
            logger.info(f"[ToolDB] DB not found at {self.db_path}, starting with empty DB")
            self.tools = {}
            self.metadata = {}

        self._loaded = True
        return self

    def save(self):
        """保存数据库"""
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)

        self.metadata["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.metadata["total_tools"] = len(self.tools)

        data = {
            "tools": self.tools,
            "metadata": self.metadata,
        }

        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"[ToolDB] Saved {len(self.tools)} tools to {self.db_path}")

    def get_tool(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取工具"""
        return self.tools.get(tool_id)

    def add_tool(self, tool_data: Dict[str, Any]) -> str:
        """
        添加工具到数据库
        返回 tool_id
        """
        tool_id = self.compute_tool_id(
            tool_data.get("source", "unknown"),
            tool_data.get("name", "unknown"),
            tool_data.get("url", ""),
        )

        now = datetime.now(timezone.utc).isoformat()

        # 如果已存在，不覆盖（用 update_tool）
        if tool_id in self.tools:
            logger.debug(f"[ToolDB] Tool {tool_id} already exists, use update_tool instead")
            return tool_id

        tool_data["id"] = tool_id
        tool_data.setdefault("first_seen", now)
        tool_data["collected_at"] = now
        tool_data["content_hash"] = self._compute_hash(tool_data)

        self.tools[tool_id] = tool_data
        return tool_id

    def update_tool(self, tool_id: str, updates: Dict[str, Any]):
        """更新工具字段"""
        if tool_id not in self.tools:
            logger.warning(f"[ToolDB] Tool {tool_id} not found, skipping update")
            return

        now = datetime.now(timezone.utc).isoformat()
        updates["last_checked"] = now
        updates["content_hash"] = self._compute_hash({**self.tools[tool_id], **updates})

        self.tools[tool_id].update(updates)

    def compute_tool_id(self, source: str, name: str, url: str = "") -> str:
        """
        生成唯一ID: source_slug
        
        规则：source_id + name的slug化
        """
        slug = name.lower().strip()
        # 替换空格和特殊字符为连字符
        slug = "".join(c if c.isalnum() or c == "-" else "-" for c in slug)
        # 合并连续连字符
        while "--" in slug:
            slug = slug.replace("--", "-")
        slug = slug.strip("-")
        # 截断过长的slug
        if len(slug) > 80:
            slug = slug[:80]

        return f"{source}_{slug}"

    def find_tool_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """根据URL查找工具"""
        if not url:
            return None
        url_lower = url.lower().rstrip("/")
        for tool in self.tools.values():
            tool_url = tool.get("url", "").lower().rstrip("/")
            if tool_url == url_lower:
                return tool
        return None

    def find_tool_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称查找工具"""
        if not name:
            return None
        name_lower = name.lower()
        for tool in self.tools.values():
            if tool.get("name", "").lower() == name_lower:
                return tool
        return None

    def get_tools_needing_health_check(self, interval_base: int = 3) -> List[Dict[str, Any]]:
        """
        根据健康度等级获取需要检查的工具
        
        检查间隔：
          active   → interval_base * 1  (默认3天)
          moderate → interval_base * 2  (默认6天)
          dormant  → interval_base * 4  (默认12天)
          archived → interval_base * 10 (默认30天)
        """
        multipliers = {
            "active": 1,
            "moderate": 2,
            "dormant": 4,
            "archived": 10,
        }

        now = datetime.now(timezone.utc)
        result = []

        for tool_id, tool in self.tools.items():
            health = tool.get("health_status", "unknown")
            last_checked = tool.get("last_checked", "")

            multiplier = multipliers.get(health, 4)  # unknown → dormant级别
            check_interval = interval_base * multiplier

            needs_check = False
            if not last_checked:
                needs_check = True
            else:
                try:
                    checked_dt = datetime.fromisoformat(last_checked.replace("Z", "+00:00"))
                    days_since = (now - checked_dt).days
                    if days_since >= check_interval:
                        needs_check = True
                except (ValueError, TypeError):
                    needs_check = True

            if needs_check:
                result.append({**tool, "tool_id": tool_id})

        return result

    def diff_tools(self, new_items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        对比新采集数据和master DB，返回差异

        返回:
          {
            "new": [...],       # 新增工具
            "changed": [...],   # 内容变化的工具（content_hash不同）
            "unchanged": [...]  # 未变化的工具
          }
        """
        result = {"new": [], "changed": [], "unchanged": []}

        for item in new_items:
            source = item.get("source", "unknown")
            name = item.get("name", "")
            url = item.get("url", "")

            tool_id = self.compute_tool_id(source, name, url)
            existing = self.tools.get(tool_id)

            if existing is None:
                # 新工具
                item["id"] = tool_id
                result["new"].append(item)
            else:
                # 已存在，比较内容指纹
                new_hash = self._compute_hash(item)
                old_hash = existing.get("content_hash", "")

                if new_hash != old_hash:
                    item["id"] = tool_id
                    result["changed"].append(item)
                else:
                    result["unchanged"].append(item)

        logger.info(f"[ToolDB] Diff: {len(result['new'])} new, "
                     f"{len(result['changed'])} changed, "
                     f"{len(result['unchanged'])} unchanged")
        return result

    def merge_analyzed(self, analyzed_items: List[Dict[str, Any]]):
        """
        将AI分析结果合并回master DB

        analyzed_items 中每个元素至少包含 id 和 AI 分析字段
        """
        now = datetime.now(timezone.utc).isoformat()
        merged_count = 0

        for item in analyzed_items:
            tool_id = item.get("id", "")
            if not tool_id:
                # 尝试计算ID
                tool_id = self.compute_tool_id(
                    item.get("source", "unknown"),
                    item.get("name", ""),
                    item.get("url", ""),
                )

            if tool_id in self.tools:
                # 更新已有工具
                analysis_fields = [
                    "category", "subcategory", "license_tier", "license_type",
                    "tags", "ai_analysis", "ai_confidence", "is_china_tool",
                    "health_status", "summary", "features", "use_cases",
                    "pros", "cons", "alternatives",
                ]
                updates = {}
                for field_name in analysis_fields:
                    if field_name in item:
                        updates[field_name] = item[field_name]

                updates["ai_analyzed_at"] = now
                updates["last_checked"] = now
                updates["content_hash"] = self._compute_hash(item)

                self.tools[tool_id].update(updates)
                merged_count += 1
            else:
                # 新工具，直接添加
                item["id"] = tool_id
                item["first_seen"] = now
                item["collected_at"] = now
                item["ai_analyzed_at"] = now
                item["last_checked"] = now
                item["content_hash"] = self._compute_hash(item)
                self.tools[tool_id] = item
                merged_count += 1

        self.metadata["last_merge"] = now
        self.metadata["last_merge_count"] = merged_count

        logger.info(f"[ToolDB] Merged {merged_count} analyzed items into master DB")

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """获取所有工具列表"""
        return list(self.tools.values())

    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        total = len(self.tools)
        category_counts = {}
        health_counts = {}
        license_counts = {}
        source_counts = {}

        for tool in self.tools.values():
            cat = tool.get("category", "其他")
            category_counts[cat] = category_counts.get(cat, 0) + 1

            health = tool.get("health_status", "unknown")
            health_counts[health] = health_counts.get(health, 0) + 1

            lic = tool.get("license_tier", "unknown")
            license_counts[lic] = license_counts.get(lic, 0) + 1

            src = tool.get("source", "unknown")
            source_counts[src] = source_counts.get(src, 0) + 1

        return {
            "total_tools": total,
            "category_counts": category_counts,
            "health_counts": health_counts,
            "license_counts": license_counts,
            "source_counts": source_counts,
            "updated_at": self.metadata.get("updated_at", ""),
        }

    def _compute_hash(self, tool_data: Dict[str, Any]) -> str:
        """计算内容指纹，用于检测变更"""
        parts = [
            tool_data.get("name", ""),
            tool_data.get("description", ""),
            tool_data.get("url", ""),
            tool_data.get("license_tier", ""),
            tool_data.get("license_type", ""),
        ]
        content = "|".join(parts)
        return hashlib.md5(content.encode()).hexdigest()
