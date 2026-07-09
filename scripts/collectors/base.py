"""
AI百宝箱 - 采集器基类 v2

新增：
  - fetch_limit 支持：从配置读取每次采集限制数量
  - save_results 增加时间戳和模式标记
"""
import os
import json
import time
import hashlib
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """采集器基类"""

    def __init__(self, source_config: Dict, global_config: Dict = None):
        self.config = source_config
        self.global_config = global_config or {}
        self.source_id = source_config["id"]
        self.source_name = source_config["name"]
        self.fetch_limit = source_config.get("fetch_limit", 0)  # 0 表示不限制
        self.schedule_mode = source_config.get("schedule_mode", "discovery")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.global_config.get("user_agent", "AI-Treasure-Box/2.0"),
            "Accept": "text/html,application/json,*/*",
        })
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.tools_dir = self.data_dir / "tools"
        self.tools_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def collect(self) -> List[Dict[str, Any]]:
        """
        执行采集，返回原始数据列表
        每个dict至少包含: name, url, description
        """
        pass

    def fetch(self, url: str, **kwargs) -> requests.Response:
        """带重试和限流的HTTP请求"""
        retries = self.global_config.get("retry_times", 3)
        delay = self.global_config.get("retry_delay", 15)
        timeout = self.global_config.get("request_timeout", 30)

        for attempt in range(retries):
            try:
                resp = self.session.get(url, timeout=timeout, **kwargs)
                resp.raise_for_status()
                return resp
            except requests.exceptions.RequestException as e:
                logger.warning(f"[{self.source_id}] Request failed (attempt {attempt+1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(delay * (attempt + 1))
                else:
                    raise

    def fetch_json(self, url: str, **kwargs) -> Any:
        """请求并返回JSON"""
        resp = self.fetch(url, **kwargs)
        return resp.json()

    def dedup_by_url(self, items: List[Dict]) -> List[Dict]:
        """按URL去重"""
        seen = set()
        result = []
        for item in items:
            url = item.get("url", "")
            if url and url not in seen:
                seen.add(url)
                result.append(item)
        return result

    def apply_fetch_limit(self, items: List[Dict]) -> List[Dict]:
        """应用采集数量限制"""
        if self.fetch_limit and self.fetch_limit > 0 and len(items) > self.fetch_limit:
            logger.info(f"[{self.source_id}] Applying fetch_limit: {len(items)} -> {self.fetch_limit}")
            return items[:self.fetch_limit]
        return items

    def save_results(self, items: List[Dict], date_str: str = None, mode: str = None):
        """
        保存采集结果
        
        增加：
          - mode 标记（discovery/health_check/deep_update）
          - fetch_limit 信息
        """
        if not date_str:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if not mode:
            mode = self.schedule_mode

        output_dir = self.tools_dir / self.source_id
        output_dir.mkdir(parents=True, exist_ok=True)

        filepath = output_dir / f"{date_str}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "source": self.source_id,
                "source_name": self.source_name,
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "mode": mode,
                "fetch_limit": self.fetch_limit,
                "count": len(items),
                "items": items,
            }, f, ensure_ascii=False, indent=2)

        logger.info(f"[{self.source_id}] Saved {len(items)} items to {filepath}")
        return filepath

    def run(self) -> Dict[str, Any]:
        """运行采集流程"""
        logger.info(f"[{self.source_id}] Starting collection from {self.source_name}")
        start_time = time.time()

        try:
            raw_items = self.collect()
            if not raw_items:
                logger.warning(f"[{self.source_id}] No items collected")
                return {"success": False, "count": 0, "error": "No items collected"}

            # 去重
            deduped = self.dedup_by_url(raw_items)
            logger.info(f"[{self.source_id}] Collected {len(raw_items)} items, {len(deduped)} after dedup")

            # 应用数量限制
            limited = self.apply_fetch_limit(deduped)

            # 保存（带模式标记）
            filepath = self.save_results(limited, mode=self.schedule_mode)

            elapsed = time.time() - start_time
            return {
                "success": True,
                "source": self.source_id,
                "count": len(limited),
                "elapsed_seconds": round(elapsed, 2),
                "output_file": str(filepath),
            }

        except Exception as e:
            logger.error(f"[{self.source_id}] Collection failed: {e}")
            return {
                "success": False,
                "source": self.source_id,
                "error": str(e),
                "elapsed_seconds": round(time.time() - start_time, 2),
            }


def load_config() -> Dict:
    """加载sources.yaml配置"""
    config_path = Path(__file__).parent.parent.parent / "config" / "sources.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_enabled_sources(config: Dict, tier: int = None) -> List[Dict]:
    """获取已启用的数据源"""
    sources = [s for s in config["sources"] if s.get("enabled", True)]
    if tier is not None:
        sources = [s for s in sources if s.get("tier") == tier]
    return sources


def get_collector(source_config: Dict, global_config: Dict = None) -> BaseCollector:
    """根据配置动态加载对应的采集器"""
    parser_name = source_config["parser"].replace(".py", "")
    module = __import__(
        f"collectors.{parser_name}",
        fromlist=[parser_name]
    )
    collector_class = getattr(module, "Collector")
    return collector_class(source_config, global_config)
