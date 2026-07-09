"""
AI百宝箱 - 主管线入口
运行采集 → 分析 → 存储 → 生成快照
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path

# 确保scripts目录在path中
sys.path.insert(0, str(Path(__file__).parent))

from collectors.base import BaseCollector, load_config, get_enabled_sources
from pipeline.analyzer import AIAnalyzer, generate_tool_id
from pipeline.data_model import Tool, DailySnapshot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_collection(source_id: str = None, tier: int = None):
    """
    执行数据采集
    :param source_id: 指定数据源ID，None则运行所有启用的
    :param tier: 指定层级，None则全部层级
    """
    config = load_config()
    global_config = config.get("global", {})

    if source_id:
        sources = [s for s in config["sources"] if s["id"] == source_id]
        if not sources:
            logger.error(f"Source '{source_id}' not found in config")
            return []
    else:
        sources = get_enabled_sources(config, tier)

    logger.info(f"Starting collection: {len(sources)} sources enabled")

    results = []
    for source_cfg in sources:
        try:
            collector = _create_collector(source_cfg, global_config)
            result = collector.run()
            results.append(result)
            logger.info(f"  [{source_cfg['id']}] {result.get('count', 0)} items collected")
        except Exception as e:
            logger.error(f"  [{source_cfg['id']}] Failed: {e}")
            results.append({"success": False, "source": source_cfg["id"], "error": str(e)})

    # 输出汇总
    success = sum(1 for r in results if r.get("success"))
    total_items = sum(r.get("count", 0) for r in results)
    logger.info(f"Collection complete: {success}/{len(results)} sources, {total_items} total items")

    return results


def run_analysis(source_id: str = None):
    """对采集的数据运行AI分析"""
    data_dir = Path(__file__).parent.parent / "data" / "tools"

    if source_id:
        source_dirs = [data_dir / source_id]
    else:
        source_dirs = [d for d in data_dir.iterdir() if d.is_dir()]

    analyzer = AIAnalyzer(_get_analyzer_config())

    total_analyzed = 0
    for source_dir in source_dirs:
        if not source_dir.exists():
            continue

        # 读取最新的采集结果
        json_files = sorted(source_dir.glob("*.json"), reverse=True)
        if not json_files:
            continue

        with open(json_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        items = data.get("items", [])
        if not items:
            continue

        logger.info(f"Analyzing {len(items)} items from {source_dir.name}")
        analyzed = analyzer.analyze_batch(items)

        # 保存分析结果
        output_dir = data_dir / f"{source_dir.name}_analyzed"
        output_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        with open(output_dir / f"{date_str}.json", "w", encoding="utf-8") as f:
            json.dump({
                "source": source_dir.name,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
                "count": len(analyzed),
                "items": analyzed,
            }, f, ensure_ascii=False, indent=2)

        total_analyzed += len(analyzed)

    logger.info(f"Analysis complete: {total_analyzed} items analyzed")
    return total_analyzed


def run_snapshot():
    """生成每日快照"""
    data_dir = Path(__file__).parent.parent / "data"
    snapshot_dir = data_dir / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 统计所有已分析的工具
    tools_dir = data_dir / "tools"
    all_tools = {}
    category_counts = {}
    tag_counts = {}

    for source_dir in tools_dir.iterdir():
        if not source_dir.is_dir():
            continue
        # 查找分析后的数据
        analyzed_dir = tools_dir / f"{source_dir.name}_analyzed"
        target_dir = analyzed_dir if analyzed_dir.exists() else source_dir

        json_files = sorted(target_dir.glob("*.json"), reverse=True)
        if not json_files:
            continue

        with open(json_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data.get("items", []):
            tool_id = generate_tool_id(data.get("source", source_dir.name), item.get("name", ""))
            if tool_id not in all_tools:
                all_tools[tool_id] = item
                cat = item.get("category", "未分类")
                category_counts[cat] = category_counts.get(cat, 0) + 1

                # 统计标签
                tags = item.get("tags", {})
                if isinstance(tags, dict):
                    for dim in ["function", "scenario", "attribute", "tech"]:
                        for tag in tags.get(dim, []):
                            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    # 加载昨日快照做对比
    yesterday_tools = _load_yesterday_tools(snapshot_dir, today)
    new_tools = []
    updated_tools = []
    removed_tools = []

    for tool_id in all_tools:
        if tool_id not in yesterday_tools:
            new_tools.append(tool_id)
        else:
            updated_tools.append(tool_id)

    for tool_id in yesterday_tools:
        if tool_id not in all_tools:
            removed_tools.append(tool_id)

    # 构建快照
    snapshot = DailySnapshot(
        date=today,
        total_tools=len(all_tools),
        new_tools=new_tools,
        updated_tools=updated_tools,
        removed_tools=removed_tools,
        category_counts=category_counts,
        tag_trends=tag_counts,
    )

    # 保存快照
    snapshot_path = snapshot_dir / f"{today}.json"
    snapshot.save(str(snapshot_path))
    logger.info(f"Snapshot saved: {len(all_tools)} tools, {len(new_tools)} new, {len(removed_tools)} removed")

    return snapshot


def _create_collector(source_cfg: Dict, global_config: Dict) -> BaseCollector:
    """动态创建采集器实例"""
    parser_name = source_cfg["parser"].replace(".py", "")

    # 导入对应的采集器模块
    module = __import__(f"collectors.{parser_name}", fromlist=["Collector"])
    collector_cls = getattr(module, "Collector")
    return collector_cls(source_cfg, global_config)


def _get_analyzer_config() -> Dict:
    """获取AI分析器配置"""
    return {
        "coze_api_key": os.environ.get("COZE_API_KEY", ""),
        "coze_api_base": os.environ.get("COZE_API_BASE", "https://api.coze.cn/v3"),
        "analyzer_bot_id": os.environ.get("ANALYZER_BOT_ID", ""),
    }


def _load_yesterday_tools(snapshot_dir: Path, today: str) -> Dict:
    """加载昨日工具列表用于对比"""
    from datetime import timedelta
    yesterday = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_file = snapshot_dir / f"{yesterday}.json"

    if yesterday_file.exists():
        with open(yesterday_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            all_ids = set(data.get("updated_tools", [])) | set(data.get("new_tools", []))
            return {tid: True for tid in all_ids}
    return {}


# === CLI入口 ===
def main():
    parser = argparse.ArgumentParser(description="AI百宝箱 - 数据管线")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # collect 命令
    collect_parser = subparsers.add_parser("collect", help="执行数据采集")
    collect_parser.add_argument("--source", help="指定数据源ID")
    collect_parser.add_argument("--tier", type=int, help="指定层级(1/2/3)")

    # analyze 命令
    analyze_parser = subparsers.add_parser("analyze", help="AI分析")
    analyze_parser.add_argument("--source", help="指定数据源ID")

    # snapshot 命令
    subparsers.add_parser("snapshot", help="生成每日快照")

    # all 命令
    all_parser = subparsers.add_parser("all", help="执行完整流程: 采集→分析→快照")
    all_parser.add_argument("--source", help="指定数据源ID")
    all_parser.add_argument("--tier", type=int, help="指定层级")

    args = parser.parse_args()

    if args.command == "collect":
        run_collection(source_id=getattr(args, "source", None), tier=getattr(args, "tier", None))
    elif args.command == "analyze":
        run_analysis(source_id=getattr(args, "source", None))
    elif args.command == "snapshot":
        run_snapshot()
    elif args.command == "all":
        run_collection(source_id=getattr(args, "source", None), tier=getattr(args, "tier", None))
        run_analysis(source_id=getattr(args, "source", None))
        run_snapshot()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
