#!/usr/bin/env python3
"""
一次性存量清理脚本：对现有 master_tools.json 中的工具应用新的收录规则。
使用本地评分引擎（_infer_audience_utility 的逻辑）对每个工具打分，
然后按分类阈值过滤。
"""
import json
import yaml
import sys
import os
from datetime import datetime, timezone

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'sources.yaml')
    with open(config_path) as f:
        return yaml.safe_load(f)

def get_inclusion_rules(config):
    return config.get('global', {}).get('inclusion', {}).get('rules', {})

# ========== 从 analyzer.py 复制的评分逻辑 ==========

GENERAL_KEYWORDS = [
    "app", "website", "online", "tool", "platform", "service",
    "free", "免费", "在线", "工具", "助手", "生成", "创作",
    "写作", "翻译", "图片", "视频", "音频", "设计", "ppt",
    "office", "email", "calendar", "note", "chat", "bot",
    "editor", "player", "viewer", "converter"
]
DEV_KEYWORDS = [
    "sdk", "api", "library", "framework", "cli", "terminal",
    "plugin", "extension", "vscode", "npm", "pip", "docker",
    "kubernetes", "ci/cd", "devops", "deploy", "test", "debug",
    "compiler", "lint", "build", "package", "module", "crate",
    "runtime", "interpreter", "bundler", "linter", "formatter"
]
RESEARCH_KEYWORDS = [
    "paper", "论文", "arxiv", "benchmark", "dataset", "model",
    "transformer", "attention", "neural", "training", "inference",
    "evaluation", "experiment", "method", "approach", "algorithm",
    "state-of-the-art", "sota", "ablation", "baseline"
]

INFRA_SIGNALS = [
    "test framework", "unit test", "testing library",
    "ci/cd", "build tool", "package manager", "bundler",
    "runtime", "compiler", "transpiler", "linter", "formatter",
    "orm", "database driver", "http client", "logging"
]

PRODUCT_SIGNALS = [
    "try it", "试用", "sign up", "注册", "get started",
    "官网", "website", "online tool", "web app", "saas",
    "download", "安装", "chrome extension", "vscode extension"
]

def infer_audience_utility(name, desc, category, source, raw):
    text = f"{name} {desc}".lower()
    stars = raw.get("stargazers_count", 0) or 0

    general_score = sum(1 for kw in GENERAL_KEYWORDS if kw in text)
    dev_score = sum(1 for kw in DEV_KEYWORDS if kw in text)
    research_score = sum(1 for kw in RESEARCH_KEYWORDS if kw in text)

    if research_score > general_score and research_score > dev_score:
        audience = "researcher"
    elif dev_score > general_score:
        audience = "developer"
    else:
        audience = "general"

    # Base score by source
    if source in ("producthunt-ai", "theresanaiforthat", "aibot", "aishenqi"):
        base_score = 7
    elif source in ("aigcrank", "hyperai"):
        base_score = 6
    elif source == "github-trending":
        base_score = 4
    elif source == "arxiv-ai":
        base_score = 3
    elif source == "hackernews-ai":
        base_score = 5
    else:
        base_score = 5

    # Audience adjustment
    if audience == "general":
        base_score += 2
    elif audience == "researcher":
        base_score -= 1

    # Stars adjustment
    if stars > 5000:
        base_score += 1
    elif stars > 1000:
        pass

    # Product signals
    if any(kw in text for kw in PRODUCT_SIGNALS):
        base_score += 1

    # Pure paper penalty
    if source == "arxiv-ai" and not any(kw in text for kw in ["tool", "platform", "service", "app", "website"]):
        base_score = min(base_score, 3)

    # Pure infra penalty
    if any(kw in text for kw in INFRA_SIGNALS):
        base_score = min(base_score, 4)

    utility = max(1, min(10, base_score))
    return audience, utility


def main():
    # Load data
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    master_path = os.path.join(data_dir, 'master_tools.json')
    rejected_path = os.path.join(data_dir, 'rejected_tools.json')
    
    with open(master_path) as f:
        master_data = json.load(f)
    
    tools = master_data['tools']
    config = load_config()
    rules = get_inclusion_rules(config)
    
    print(f"=== 存量工具清理 ===")
    print(f"总工具数: {len(tools)}")
    print(f"收录规则: ")
    for cat, rule in rules.items():
        min_u = rule.get('min_utility', 4) if isinstance(rule, dict) else 4
        print(f"  {cat}: >= {min_u}")
    print()
    
    # Score and filter
    included = {}
    rejected = []
    cat_stats = {}  # category -> {total, kept, removed}
    
    for tid, tool in tools.items():
        name = tool.get('name', '')
        desc = tool.get('description', '') or ''
        category = tool.get('category', '其他')
        source = tool.get('source', '')
        raw = tool.get('raw_data', {})
        
        # Score
        audience, utility = infer_audience_utility(name, desc, category, source, raw)
        
        # Apply rule
        rule = rules.get(category, rules.get('其他', {'min_utility': 4}))
        min_utility = rule.get('min_utility', 4) if isinstance(rule, dict) else 4
        
        should_include = utility >= min_utility
        
        # Stats
        if category not in cat_stats:
            cat_stats[category] = {'total': 0, 'kept': 0, 'removed': 0}
        cat_stats[category]['total'] += 1
        
        if should_include:
            # Add new fields to the tool
            tool['audience'] = audience
            tool['utility_score'] = utility
            tool['should_include'] = True
            included[tid] = tool
            cat_stats[category]['kept'] += 1
        else:
            # Rejected
            rejection_reason = f"实用性{utility}分低于{category}类阈值{min_utility}分"
            rejected_tool = {
                'tool_id': tid,
                'name': name,
                'category': category,
                'source': source,
                'audience': audience,
                'utility_score': utility,
                'min_utility_required': min_utility,
                'rejection_reason': rejection_reason,
                'url': tool.get('url', ''),
                'description': desc[:200],
                'rejected_at': datetime.now(timezone.utc).isoformat()
            }
            rejected.append(rejected_tool)
            cat_stats[category]['removed'] += 1
    
    # Print report
    print(f"=== 过滤结果 ===")
    print(f"保留: {len(included)}")
    print(f"移除: {len(rejected)}")
    print()
    
    print(f"=== 按分类统计 ===")
    print(f"{'分类':<12} {'总数':>5} {'保留':>5} {'移除':>5} {'移除率':>8}")
    print("-" * 40)
    for cat in sorted(cat_stats.keys(), key=lambda x: -cat_stats[x]['removed']):
        s = cat_stats[cat]
        rate = f"{s['removed']/s['total']*100:.0f}%" if s['total'] > 0 else "0%"
        print(f"{cat:<12} {s['total']:>5} {s['kept']:>5} {s['removed']:>5} {rate:>8}")
    
    print(f"\n=== 被移除工具明细（前30个）===")
    # Sort by category then utility
    rejected_sorted = sorted(rejected, key=lambda x: (x['category'], x['utility_score']))
    for i, r in enumerate(rejected_sorted[:30]):
        print(f"  [{r['category']}] {r['name']} (utility={r['utility_score']}, src={r['source']})")
        if r['description']:
            print(f"    -> {r['description'][:80]}")
    
    if len(rejected) > 30:
        print(f"  ... 还有 {len(rejected) - 30} 个")
    
    # Write results
    # Backup first
    backup_path = master_path + '.bak'
    with open(backup_path, 'w') as f:
        json.dump(master_data, f, ensure_ascii=False, indent=2)
    print(f"\n已备份原始数据到: {backup_path}")
    
    # Update master
    master_data['tools'] = included
    master_data['metadata']['total_tools'] = len(included)
    master_data['metadata']['last_cleanup'] = datetime.now(timezone.utc).isoformat()
    master_data['metadata']['cleanup_removed'] = len(rejected)
    
    with open(master_path, 'w') as f:
        json.dump(master_data, f, ensure_ascii=False, indent=2)
    print(f"已更新 master_tools.json: {len(tools)} -> {len(included)}")
    
    # Append to rejected.json
    existing_rejected = []
    if os.path.exists(rejected_path):
        try:
            with open(rejected_path) as f:
                existing_rejected = json.load(f)
        except:
            existing_rejected = []
    
    existing_rejected.extend(rejected)
    with open(rejected_path, 'w') as f:
        json.dump(existing_rejected, f, ensure_ascii=False, indent=2)
    print(f"已记录 {len(rejected)} 个被拒工具到 rejected_tools.json (累计: {len(existing_rejected)})")
    
    # Write cleanup report
    report = {
        'cleanup_date': datetime.now(timezone.utc).isoformat(),
        'before_count': len(tools),
        'after_count': len(included),
        'removed_count': len(rejected),
        'category_stats': cat_stats,
        'removed_details': rejected
    }
    report_path = os.path.join(data_dir, 'cleanup_report.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"清理报告已保存到: {report_path}")


if __name__ == '__main__':
    main()
