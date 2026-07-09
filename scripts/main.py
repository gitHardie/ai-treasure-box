"""
AI百宝箱 - 主管线 v2

分级采集：发现 → 对比 → 批量分析 → 合并 → 生成

子命令:
  discover    发现新工具（从数据源采集）
  check       健康检查（检查存量工具状态）
  deep        深度更新（全量重分析）
  analyze     对pending工具执行AI分析
  deploy      生成网站数据
  run         完整流程（自动判断模式）
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

# 确保scripts目录在path中
sys.path.insert(0, str(Path(__file__).parent))

from collectors.base import BaseCollector, load_config, get_enabled_sources, get_collector
from pipeline.analyzer import AIAnalyzer, generate_tool_id
from pipeline.data_model import DailySnapshot
from pipeline.scheduler import CollectionScheduler
from pipeline.tool_database import ToolDatabase

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PENDING_PATH = DATA_DIR / "pending_analyze.json"
MASTER_DB_PATH = str(DATA_DIR / "master_tools.json")
SITE_DIR = DATA_DIR / "site"


def _get_config():
    """加载配置"""
    return load_config()


def _get_scheduler(config: Dict = None):
    """创建调度器"""
    if config is None:
        config = _get_config()
    return CollectionScheduler(config, master_db_path=MASTER_DB_PATH)


def _get_db() -> ToolDatabase:
    """获取并加载Master DB"""
    db = ToolDatabase(MASTER_DB_PATH)
    db.load()
    return db


def _create_analyzer(config: Dict = None) -> AIAnalyzer:
    """创建AI分析器"""
    if config is None:
        config = _get_config()
    analysis_cfg = config.get("global", {}).get("analysis", {})
    return AIAnalyzer(
        coze_api_key=os.environ.get("COZE_API_KEY", "") or os.environ.get("AI_BOX_COZE", ""),
        workflow_id=os.environ.get("COZE_WORKFLOW_ID", ""),
        batch_size=analysis_cfg.get("batch_size", 20),
        batch_timeout=analysis_cfg.get("batch_timeout", 120),
    )


def _create_collector(source_cfg: Dict, global_config: Dict) -> BaseCollector:
    """动态创建采集器实例"""
    return get_collector(source_cfg, global_config)


# ============================
# Pending 队列管理
# ============================

def save_pending(items: List[Dict[str, Any]]):
    """保存待分析队列"""
    PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)

    existing = load_pending()
    # 合并去重（按id）
    existing_ids = {item.get("id", "") for item in existing}
    new_items = [item for item in items if item.get("id", "") not in existing_ids]
    merged = existing + new_items

    with open(PENDING_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    logger.info(f"[Pending] Saved {len(new_items)} new items, total pending: {len(merged)}")
    return merged


def load_pending() -> List[Dict[str, Any]]:
    """加载待分析队列"""
    if not PENDING_PATH.exists():
        return []
    try:
        with open(PENDING_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def clear_pending():
    """清空待分析队列"""
    if PENDING_PATH.exists():
        PENDING_PATH.unlink()
    logger.info("[Pending] Cleared")


# ============================
# 子命令实现
# ============================

def cmd_discover(args):
    """发现模式：从数据源采集新工具"""
    config = _get_config()
    global_config = config.get("global", {})
    scheduler = _get_scheduler(config)
    db = _get_db()

    # 确定要采集的源
    if hasattr(args, 'source') and args.source:
        source = scheduler.get_source_by_id(args.source)
        if not source:
            logger.error(f"Source '{args.source}' not found")
            return
        sources = [source]
    else:
        sources = scheduler.get_discovery_sources()

    if not sources:
        logger.info("[Discover] No discovery sources to run today")
        return

    logger.info(f"[Discover] Running {len(sources)} sources: {[s['id'] for s in sources]}")

    all_new_items = []
    for source_cfg in sources:
        try:
            collector = _create_collector(source_cfg, global_config)
            result = collector.run()

            if result.get("success") and result.get("count", 0) > 0:
                # 读取采集结果
                items = _load_collected_items(source_cfg["id"])
                # 对比master DB
                diff = db.diff_tools(items)
                new_changed = diff["new"] + diff["changed"]
                all_new_items.extend(new_changed)
                logger.info(f"  [{source_cfg['id']}] {result['count']} items, "
                            f"{len(diff['new'])} new, {len(diff['changed'])} changed")
        except Exception as e:
            logger.error(f"  [{source_cfg['id']}] Failed: {e}")

    # 写入pending队列
    if all_new_items:
        save_pending(all_new_items)

    logger.info(f"[Discover] Complete: {len(all_new_items)} items pending for analysis")


def cmd_check(args):
    """健康检查模式：检查存量工具状态"""
    config = _get_config()
    global_config = config.get("global", {})
    scheduler = _get_scheduler(config)
    db = _get_db()

    tools_to_check = scheduler.get_health_check_tools(master_db=db.tools)

    if not tools_to_check:
        logger.info("[Check] No tools need health checking")
        return

    logger.info(f"[Check] {len(tools_to_check)} tools need health checking")

    # 将需要检查的工具加入pending（标记为health_check类型）
    for tool_info in tools_to_check:
        tool_info["_check_type"] = "health_check"

    save_pending(tools_to_check)
    logger.info(f"[Check] Added {len(tools_to_check)} tools to pending queue")


def cmd_deep(args):
    """深度更新模式：全量重分析"""
    config = _get_config()
    global_config = config.get("global", {})
    scheduler = _get_scheduler(config)
    db = _get_db()

    all_tools = db.get_all_tools()
    logger.info(f"[Deep] Full re-analysis of {len(all_tools)} tools")

    if not all_tools:
        logger.info("[Deep] No tools in master DB")
        return

    # 将所有工具加入pending（标记为deep_update类型）
    for tool in all_tools:
        tool["_check_type"] = "deep_update"

    save_pending(all_tools)
    logger.info(f"[Deep] Added {len(all_tools)} tools to pending queue for re-analysis")


def cmd_analyze(args):
    """分析模式：批量送Coze分析pending队列中的工具"""
    config = _get_config()
    pending = load_pending()

    if not pending:
        logger.info("[Analyze] No pending items to analyze")
        return

    logger.info(f"[Analyze] {len(pending)} items pending")

    analyzer = _create_analyzer(config)
    db = _get_db()

    # 批量分析
    results = analyzer.analyze_batch(pending)

    # 合并到master DB
    db.merge_analyzed(results)
    db.save()

    # 清空pending
    clear_pending()

    logger.info(f"[Analyze] Complete: {len(results)} items analyzed and merged to master DB")


def cmd_deploy(args):
    """生成网站数据"""
    db = _get_db()
    all_tools = db.get_all_tools()

    if not all_tools:
        logger.warning("[Deploy] No tools in master DB, skipping site data generation")
        return

    # 确保输出目录存在
    SITE_DIR.mkdir(parents=True, exist_ok=True)

    # 生成 tools.json - 所有工具列表
    tools_list = []
    for tool in all_tools:
        # 清理内部字段
        clean_tool = {k: v for k, v in tool.items() if not k.startswith("_")}
        tools_list.append(clean_tool)

    tools_path = SITE_DIR / "tools.json"
    with open(tools_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "count": len(tools_list),
            "tools": tools_list,
        }, f, ensure_ascii=False, indent=2)
    logger.info(f"[Deploy] Generated {tools_path} ({len(tools_list)} tools)")

    # 生成 categories.json - 分类统计
    category_counts = {}
    subcategory_counts = {}
    for tool in all_tools:
        cat = tool.get("category", "其他")
        subcat = tool.get("subcategory", "")
        category_counts[cat] = category_counts.get(cat, 0) + 1
        if subcat:
            key = f"{cat}/{subcat}"
            subcategory_counts[key] = subcategory_counts.get(key, 0) + 1

    categories_path = SITE_DIR / "categories.json"
    with open(categories_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "categories": category_counts,
            "subcategories": subcategory_counts,
        }, f, ensure_ascii=False, indent=2)
    logger.info(f"[Deploy] Generated {categories_path}")

    # 生成 stats.json - 总体统计
    stats = db.get_stats()
    stats_path = SITE_DIR / "stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            **stats,
        }, f, ensure_ascii=False, indent=2)
    logger.info(f"[Deploy] Generated {stats_path}")

    logger.info(f"[Deploy] Site data ready in {SITE_DIR}")


def cmd_run(args):
    """完整流程：自动判断模式并执行"""
    config = _get_config()
    scheduler = _get_scheduler(config)

    # 确定运行模式
    if hasattr(args, 'mode') and args.mode and args.mode != 'auto':
        mode = args.mode
    else:
        mode = scheduler.determine_mode()

    logger.info(f"[Run] Mode: {mode}")

    # 根据模式执行采集
    if mode == "discovery":
        cmd_discover(args)
    elif mode == "health_check":
        cmd_check(args)
    elif mode == "deep_update":
        cmd_deep(args)

    # 分析 + 部署
    cmd_analyze(args)
    cmd_deploy(args)


def _load_collected_items(source_id: str) -> List[Dict[str, Any]]:
    """加载某个源的最新采集结果"""
    source_dir = DATA_DIR / "tools" / source_id
    if not source_dir.exists():
        return []

    json_files = sorted(source_dir.glob("*.json"), reverse=True)
    if not json_files:
        return []

    try:
        with open(json_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("items", [])
    except (json.JSONDecodeError, IOError):
        return []


# ============================
# CLI入口
# ============================

def main():
    parser = argparse.ArgumentParser(description="AI百宝箱 - 管线 v2")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # discover
    discover_p = subparsers.add_parser("discover", help="发现新工具（从数据源采集）")
    discover_p.add_argument("--source", help="指定数据源ID")

    # check
    subparsers.add_parser("check", help="健康检查（检查存量工具状态）")

    # deep
    subparsers.add_parser("deep", help="深度更新（全量重分析）")

    # analyze
    subparsers.add_parser("analyze", help="对pending工具执行AI分析")

    # deploy
    subparsers.add_parser("deploy", help="生成网站数据")

    # run
    run_p = subparsers.add_parser("run", help="完整流程（自动判断模式）")
    run_p.add_argument("--mode", help="强制指定模式: discovery/health_check/deep_update/auto", default="auto")
    run_p.add_argument("--source", help="指定数据源ID（仅discovery模式）")

    args = parser.parse_args()

    if args.command == "discover":
        cmd_discover(args)
    elif args.command == "check":
        cmd_check(args)
    elif args.command == "deep":
        cmd_deep(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "deploy":
        cmd_deploy(args)
    elif args.command == "run":
        cmd_run(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
