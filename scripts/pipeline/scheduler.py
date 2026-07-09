"""
AI百宝箱 - 分级采集调度器

根据运行模式和日期决定哪些源需要采集、哪些存量工具需要健康检查。

三种运行模式：
  - discovery:     每天从不同数据源发现新工具（按tier轮转）
  - health_check:  按工具活跃度分级检查存量工具
  - deep_update:   月度全量重分析
"""
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class CollectionScheduler:
    """分级采集调度器"""

    # 健康度 → 检查间隔倍数
    HEALTH_CHECK_MULTIPLIERS = {
        "active": 1,     # base * 1 (默认3天)
        "moderate": 2,   # base * 2 (默认6天)
        "dormant": 4,    # base * 4 (默认12天)
        "archived": 10,  # base * 10 (默认30天)
    }

    def __init__(self, config: Dict[str, Any], master_db_path: str = "data/master_tools.json"):
        self.config = config
        self.master_db_path = master_db_path
        self.global_config = config.get("global", {})
        self.collection_config = self.global_config.get("collection", {})
        self.sources = config.get("sources", [])

    def determine_mode(self, now: Optional[datetime] = None) -> str:
        """
        根据日期判断运行模式

        规则：
          - 每月1号: deep_update（全量重分析）
          - 每3天: health_check（存量工具检查）
          - 其他: discovery（发现新工具）
        """
        if now is None:
            now = datetime.now(timezone.utc)

        # 每月1号 → deep_update
        deep_update_day = self.collection_config.get("deep_update_day", 1)
        if now.day == deep_update_day:
            logger.info(f"[Scheduler] Mode: deep_update (day {now.day})")
            return "deep_update"

        # 每3天 → health_check
        hc_interval = self.collection_config.get("health_check_interval_days", 3)
        if now.timetuple().tm_yday % hc_interval == 0:
            logger.info(f"[Scheduler] Mode: health_check (day_of_year % {hc_interval} == 0)")
            return "health_check"

        # 其他 → discovery
        logger.info(f"[Scheduler] Mode: discovery")
        return "discovery"

    def get_discovery_sources(self) -> List[Dict[str, Any]]:
        """
        获取今天应该运行的 discovery 源

        轮转规则（按 tier）：
          - tier 1: 每天运行
          - tier 2: 隔天运行（日期 % 2 == 0）
          - tier 3: 每3天运行（日期 % 3 == 0）

        同时受 discovery_batch_size 限制（每天最多跑 N 个源）
        """
        now = datetime.now(timezone.utc)
        day_of_month = now.day

        batch_size = self.collection_config.get("discovery_batch_size", 5)

        # 过滤 schedule_mode == "discovery" 且 enabled 的源
        candidates = [
            s for s in self.sources
            if s.get("enabled", True) and s.get("schedule_mode") == "discovery"
        ]

        selected = []
        for source in candidates:
            tier = source.get("tier", 3)

            if tier == 0:
                # manual 源不参与自动轮转
                continue
            elif tier == 1:
                # tier 1 每天运行
                selected.append(source)
            elif tier == 2:
                # tier 2 隔天运行
                if day_of_month % 2 == 0:
                    selected.append(source)
            elif tier == 3:
                # tier 3 每3天运行
                if day_of_month % 3 == 0:
                    selected.append(source)

        # 限制批次大小
        if len(selected) > batch_size:
            logger.info(f"[Scheduler] Truncating discovery sources from {len(selected)} to {batch_size}")
            selected = selected[:batch_size]

        logger.info(f"[Scheduler] Discovery sources ({len(selected)}): {[s['id'] for s in selected]}")
        return selected

    def get_health_check_tools(self, master_db: Optional[Dict] = None,
                                interval_base: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        从 master DB 获取需要健康检查的工具

        根据工具的健康度等级决定检查频率：
          - active:   interval_base * 1
          - moderate: interval_base * 2
          - dormant:  interval_base * 4
          - archived: interval_base * 10

        返回需要检查的工具列表（包含其URL和源信息）
        """
        if interval_base is None:
            interval_base = self.collection_config.get("health_check_interval_days", 3)

        # 如果没传入 master_db，尝试加载
        if master_db is None:
            from pipeline.tool_database import ToolDatabase
            db = ToolDatabase(self.master_db_path)
            db.load()
            master_db = db.tools

        now = datetime.now(timezone.utc)
        tools_to_check = []

        for tool_id, tool in master_db.items():
            health = tool.get("health_status", "unknown")
            last_checked = tool.get("last_checked", "")

            # 计算检查间隔
            multiplier = self.HEALTH_CHECK_MULTIPLIERS.get(health, 4)  # unknown 按 dormant 处理
            check_interval = interval_base * multiplier

            # 判断是否需要检查
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
                tools_to_check.append({
                    "tool_id": tool_id,
                    "name": tool.get("name", ""),
                    "url": tool.get("url", ""),
                    "source": tool.get("source", ""),
                    "health_status": health,
                    "last_checked": last_checked,
                })

        logger.info(f"[Scheduler] Health check: {len(tools_to_check)} tools need checking "
                     f"(base interval={interval_base} days)")
        return tools_to_check

    def get_all_enabled_sources(self) -> List[Dict[str, Any]]:
        """获取所有启用的数据源（deep_update 模式下使用）"""
        return [s for s in self.sources if s.get("enabled", True)]

    def get_source_by_id(self, source_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取数据源配置"""
        for s in self.sources:
            if s["id"] == source_id:
                return s
        return None
