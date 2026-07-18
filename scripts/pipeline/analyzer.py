"""
AI分析管道 v2 - 支持批量处理

核心改动：
  - 支持批量打包20个工具调Coze工作流
  - 批次间自动暂停避免限流
  - 保留所有本地分析逻辑作为降级方案

不盲信源头描述，独立判断工具的真实功能、定价、活跃度
"""
import json
import os
import re
import time
import logging
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """AI分析器 - 对采集到的工具进行深度分析（支持批量）"""

    # 一级分类体系
    CATEGORIES = [
        "文本生成", "图像创作", "代码开发", "数据分析",
        "音视频", "办公效率", "学术研究", "开发工具",
        "设计创意", "营销推广", "教育培训", "其他",
    ]

    # 许可/定价等级
    LICENSE_TIERS = ["open-source", "freemium", "free", "paid", "source-available", "unknown"]

    # 健康度等级
    HEALTH_LEVELS = ["active", "moderate", "dormant", "archived"]

    # 受众面类型（默认值，实际从 config 读取）
    AUDIENCE_TYPES = ["general", "developer", "researcher"]

    # 默认收录规则（当 config 中无 inclusion 配置时使用）
    DEFAULT_INCLUSION_RULES = {
        "文本生成":   {"min_utility": 1},
        "图像创作":   {"min_utility": 1},
        "音视频":     {"min_utility": 1},
        "办公效率":   {"min_utility": 1},
        "设计创意":   {"min_utility": 1},
        "营销推广":   {"min_utility": 1},
        "教育培训":   {"min_utility": 1},
        "数据分析":   {"min_utility": 1},
        "代码开发":   {"min_utility": 7},
        "开发工具":   {"min_utility": 6},
        "学术研究":   {"min_utility": 5},
        "其他":       {"min_utility": 4},
    }

    def __init__(self, coze_api_key: Optional[str] = None, workflow_id: Optional[str] = None,
                 batch_size: int = 20, batch_timeout: int = 120, mode: str = "batch",
                 inclusion_rules: Optional[Dict] = None,
                 global_min_utility: int = 4):
        self.coze_api_key = coze_api_key or os.environ.get("COZE_API_KEY", "") or os.environ.get("AI_BOX_COZE", "")
        self.workflow_id = workflow_id or os.environ.get("COZE_WORKFLOW_ID", "")
        self.use_coze = bool(self.coze_api_key and self.workflow_id)
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.mode = mode  # "loop" or "batch"
        # 收录规则：优先从配置读取，否则用默认值
        self.inclusion_rules = inclusion_rules or self.DEFAULT_INCLUSION_RULES
        # 全局最低门槛：任何分类下 utility 低于此值都不收录
        self.global_min_utility = global_min_utility

    def analyze_tool(self, tool_data: Dict) -> Dict:
        """
        对单个工具进行AI分析
        返回: {
            "category": str,        # 一级分类
            "subcategory": str,     # 二级分类
            "license_tier": str,    # 许可等级
            "license_type": str,    # 具体许可证
            "tags": {...},          # 五维标签
            "ai_analysis": str,     # 分析摘要
            "ai_confidence": float, # 置信度 0-1
            "is_china_tool": bool,  # 是否国内工具
            "health_status": str,   # 健康度
        }
        """
        if self.use_coze:
            return self._analyze_with_coze(tool_data)
        else:
            return self._analyze_local(tool_data)

    # ============================
    # 批量分析接口
    # ============================

    def analyze_batch(self, tools: List[Dict]) -> List[Dict]:
        """
        批量分析工具 - 每20个打包调Coze

        如果Coze不可用，自动降级到逐个本地分析。
        """
        if not tools:
            return []

        all_results = []

        if self.use_coze:
            if self.mode == "loop":
                return self._analyze_loop_mode(tools)
            # 批量模式：打包送Coze
            for i in range(0, len(tools), self.batch_size):
                batch = tools[i:i + self.batch_size]
                batch_num = i // self.batch_size + 1
                total_batches = (len(tools) + self.batch_size - 1) // self.batch_size
                logger.info(f"Analyzing batch {batch_num}/{total_batches} ({len(batch)} tools)")

                batch_results = self._analyze_with_coze_batch(batch)
                all_results.extend(batch_results)

                # 批次间暂停避免限流
                if i + self.batch_size < len(tools):
                    time.sleep(2)
        else:
            # 降级：逐个本地分析
            logger.info(f"No Coze config, falling back to local analysis for {len(tools)} tools")
            for i, tool in enumerate(tools):
                name = tool.get("name", "unknown")
                logger.info(f"  Local analyzing [{i + 1}/{len(tools)}]: {name}")
                analysis = self._analyze_local(tool)
                # 合并原始工具数据 + 分析结果
                result = {**tool, **analysis}
                result["tool_id"] = tool.get("id", "")
                all_results.append(result)

        return all_results

    def filter_for_inclusion(self, analyzed_tools: List[Dict]) -> tuple:
        """
        根据收录规则过滤分析结果。
        
        返回: (included, excluded) 两个列表
        - included: 符合收录条件的工具
        - excluded: 被拒绝的工具（带 rejection_reason）
        """
        included = []
        excluded = []
        
        for tool in analyzed_tools:
            category = tool.get("category", "其他")
            utility = tool.get("utility_score", 5)
            should_include = tool.get("should_include", True)
            
            # 综合判断：AI 决策 + 本地规则 + 全局门槛
            rule = self.inclusion_rules.get(category, self.inclusion_rules.get("其他", {"min_utility": 4}))
            min_utility = rule.get("min_utility", 4) if isinstance(rule, dict) else 4
            # 取分类门槛和全局门槛的较大值
            effective_min = max(min_utility, self.global_min_utility)
            
            # 最终收录决策
            final_include = should_include and (utility >= effective_min)
            
            if final_include:
                included.append(tool)
            else:
                # 记录拒绝原因
                if not tool.get("rejection_reason"):
                    if utility < effective_min:
                        if utility < self.global_min_utility:
                            tool["rejection_reason"] = f"实用性{utility}分低于全局最低门槛{self.global_min_utility}分"
                        else:
                            tool["rejection_reason"] = f"实用性{utility}分低于{category}类阈值{min_utility}分"
                    else:
                        tool["rejection_reason"] = "AI评估不建议收录"
                excluded.append(tool)
        
        logger.info(f"[Filter] Included: {len(included)}, Excluded: {len(excluded)}")
        if excluded:
            by_cat = {}
            for t in excluded:
                cat = t.get("category", "其他")
                by_cat[cat] = by_cat.get(cat, 0) + 1
            logger.info(f"[Filter] Excluded by category: {by_cat}")
        
        return included, excluded

    def _analyze_with_coze_batch(self, tools: List[Dict]) -> List[Dict]:
        """
        将多个工具打包成一次Coze调用

        构建包含多个工具的prompt，要求Coze返回JSON数组，
        解析返回结果，匹配回每个工具。
        """
        prompt = self._build_batch_prompt(tools)

        try:
            resp = requests.post(
                "https://api.coze.cn/v1/workflow/run",
                headers={
                    "Authorization": f"Bearer {self.coze_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "workflow_id": self.workflow_id,
                    "parameters": {"input": prompt}
                },
                timeout=self.batch_timeout
            )

            if resp.status_code == 200:
                result = resp.json()
                if result.get("code") == 0:
                    raw_data = result.get("data")

                    # 解析返回数据
                    if isinstance(raw_data, str):
                        try:
                            data_obj = json.loads(raw_data)
                        except (json.JSONDecodeError, TypeError):
                            data_obj = {"output": raw_data}
                    else:
                        data_obj = raw_data if isinstance(raw_data, dict) else {}

                    # 提取 output
                    output_val = data_obj.get("output", data_obj)
                    if isinstance(output_val, str):
                        try:
                            parsed = json.loads(output_val)
                        except (json.JSONDecodeError, TypeError):
                            # 尝试从文本中提取JSON数组
                            parsed = self._extract_json_array(output_val)
                    elif isinstance(output_val, dict):
                        parsed = output_val
                    else:
                        parsed = data_obj

                    # 解析批量结果
                    results = self._parse_batch_response(parsed, tools)
                    logger.info(f"  Coze batch analysis OK: {len(results)}/{len(tools)} tools")
                    return results
                else:
                    logger.warning(f"Coze workflow error: code={result.get('code')}, msg={result.get('msg')}")
            else:
                logger.warning(f"Coze API HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"Coze batch analysis failed: {e}, falling back to local analysis")

        # 降级到本地分析
        return [self._fallback_local(t) for t in tools]

    def _build_batch_prompt(self, tools: List[Dict]) -> str:
        """
        构建批量分析提示词

        每个工具用编号标记，要求返回对应编号的JSON数组。
        """
        tool_entries = []
        for idx, tool in enumerate(tools, 1):
            entry = (
                f"--- 工具 #{idx} ---\n"
                f"名称: {tool.get('name', '')}\n"
                f"来源: {tool.get('source', '')}\n"
                f"URL: {tool.get('url', '')}\n"
                f"描述: {tool.get('description', '')}\n"
                f"中文描述: {tool.get('description_zh', '')}\n"
                f"Stars: {tool.get('raw_data', {}).get('stargazers_count', 'N/A')}\n"
                f"许可证: {tool.get('raw_data', {}).get('license', 'N/A')}\n"
                f"最后更新: {tool.get('raw_data', {}).get('pushed_at', 'N/A')}\n"
            )
            tool_entries.append(entry)

        tools_text = "\n".join(tool_entries)
        count = len(tools)

        return f"""请分析以下 {count} 个AI工具/项目，对每个给出独立判断（不要照搬描述）。

这是一个面向普通用户和AI爱好者的工具导航站，不是开发者资源库。请从"普通用户是否能用"的角度来评估。

{tools_text}

请返回一个JSON数组，包含 {count} 个对象，按编号顺序对应。格式如下：
[
  {{
    "index": 1,
    "category": "一级分类(文本生成/图像创作/代码开发/数据分析/音视频/办公效率/学术研究/开发工具/设计创意/营销推广/教育培训/其他)",
    "subcategory": "二级分类",
    "audience": "general/developer/researcher",
    "utility_score": 5,
    "should_include": true,
    "rejection_reason": "",
    "license_tier": "open-source/freemium/free/paid/source-available/unknown",
    "license_type": "具体许可证如MIT/Apache等",
    "tags": {{
      "function": ["功能标签"],
      "scenario": ["场景标签"],
      "attribute": ["属性标签"],
      "tech": ["技术标签"],
      "quality": ["质量标签"]
    }},
    "ai_analysis": "1-2句精炼中文概述，说明这个工具做什么、解决什么问题。要简洁有力，不要照搬英文描述",
    "features": ["3个以内核心功能亮点，每个5-10字中文"],
    "best_for": "一句话说明最适合谁用、在什么场景下用",
    "notable": "一句话评价：这个工具的独特优势或值得关注的理由",
    "ai_confidence": 0.8,
    "is_china_tool": false,
    "health_status": "active/moderate/dormant/archived"
  }}
]

重要评估标准：
- audience: general=普通用户也能直接用; developer=只有开发者才会用; researcher=主要面向研究人员
- utility_score: 1-10分，评估对目标受众的实用价值。纯学术理论=1-3; 纯SDK/CLI工具(无UI)=3-5; 有产品形态但小众=5-7; 普通人也能直接上手用=7-10
- should_include: 是否适合收录到工具导航站。判断标准：
  * audience=general 的几乎都收
  * audience=developer 且 utility_score>=6 才收（有产品形态、有明确使用场景的DevTool）
  * 纯学术论文（无可用产品/服务）、纯SDK库、纯CLI工具、测试框架 → 不收
  * 如果一个工具"普通人完全用不上"，should_include=false
- rejection_reason: 如果should_include=false，简要说明原因（如"纯学术论文"、"纯CLI工具"、"SDK无产品形态"等）

注意：必须返回恰好 {count} 个对象的JSON数组，index从1到{count}。"""

    def _parse_batch_response(self, response_data: Any, tools: List[Dict]) -> List[Dict]:
        """
        解析批量响应，匹配回每个工具

        支持多种返回格式：
        - JSON数组: [{index:1, ...}, {index:2, ...}]
        - JSON对象: {results: [{index:1, ...}, ...]}
        - 字符串中的JSON数组
        """
        results = []

        # 如果是字符串，尝试解析JSON
        if isinstance(response_data, str):
            try:
                response_data = json.loads(response_data)
            except (json.JSONDecodeError, TypeError):
                response_data = self._extract_json_array(response_data)

        # 提取数组
        items = []
        if isinstance(response_data, list):
            items = response_data
        elif isinstance(response_data, dict):
            # 尝试常见字段
            for key in ["results", "items", "analyses", "data", "output"]:
                if key in response_data and isinstance(response_data[key], list):
                    items = response_data[key]
                    break
            if not items:
                # 可能整个就是一个分析结果
                items = [response_data]

        # 构建 index -> analysis 映射
        analysis_map = {}
        for item in items:
            if isinstance(item, dict):
                idx = item.get("index", len(analysis_map) + 1)
                analysis_map[idx] = item

        # 匹配回每个工具 - 合并原始数据 + 分析结果
        for idx, tool in enumerate(tools, 1):
            analysis = analysis_map.get(idx)
            if analysis and isinstance(analysis, dict):
                analysis_result = dict(analysis)
            else:
                # 降级到本地分析
                analysis_result = self._analyze_local(tool)

            # 关键：合并原始工具数据（name, url, source, id等）+ 分析结果
            result = {**tool, **analysis_result}
            result["id"] = tool.get("id", "")
            result["tool_id"] = tool.get("id", "")
            results.append(result)

        return results

    def _extract_json_array(self, text: str) -> Any:
        """尝试从文本中提取JSON数组"""
        # 找第一个 [ 和最后一个 ]
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        return text

    def _fallback_local(self, tool: Dict) -> Dict:
        """本地分析降级方案"""
        analysis = self._analyze_local(tool)
        result = {**tool, **analysis}
        result["id"] = tool.get("id", "")
        result["tool_id"] = tool.get("id", "")
        return result

    # ============================
    # 单工具 Coze 分析（保留）
    # ============================

    def _analyze_with_coze(self, tool_data: Dict) -> Dict:
        """使用Coze工作流分析（单工具模式，兼容旧逻辑）"""
        prompt = self._build_analysis_prompt(tool_data)

        try:
            resp = requests.post(
                "https://api.coze.cn/v1/workflow/run",
                headers={
                    "Authorization": f"Bearer {self.coze_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "workflow_id": self.workflow_id,
                    "parameters": {"input": prompt}
                },
                timeout=self.batch_timeout
            )

            if resp.status_code == 200:
                result = resp.json()
                if result.get("code") == 0:
                    raw_data = result.get("data")

                    if isinstance(raw_data, str):
                        try:
                            data_obj = json.loads(raw_data)
                        except (json.JSONDecodeError, TypeError):
                            data_obj = {"ai_analysis": raw_data}
                    else:
                        data_obj = raw_data if isinstance(raw_data, dict) else {}

                    output_val = data_obj.get("output", data_obj)
                    if isinstance(output_val, str):
                        try:
                            analysis = json.loads(output_val)
                        except (json.JSONDecodeError, TypeError):
                            analysis = {"ai_analysis": output_val, "ai_confidence": 0.5}
                    elif isinstance(output_val, dict):
                        analysis = output_val
                    else:
                        analysis = data_obj

                    logger.info(f"  Coze analysis OK for: {tool_data.get('name', '?')}")
                    return analysis
                else:
                    logger.warning(f"Coze workflow error: code={result.get('code')}, msg={result.get('msg')}")
            else:
                logger.warning(f"Coze API HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"Coze analysis failed: {e}, falling back to local analysis")

        return self._analyze_local(tool_data)


    # ============================
    # 循环模式：逐个工具调Coze
    # ============================

    def _analyze_loop_mode(self, tools: List[Dict]) -> List[Dict]:
        """循环模式：逐个工具调Coze工作流，并行3个"""
        results, total = [], len(tools)

        def analyze_one(idx_tool):
            idx, tool = idx_tool
            name = tool.get("name", "unknown")
            logger.info(f"  [Loop] Analyzing [{idx+1}/{total}]: {name}")
            analysis = self._analyze_single_with_coze(tool)
            return {**tool, **analysis, "id": tool.get("id",""), "tool_id": tool.get("id","")}

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(analyze_one, (i, t)): i for i, t in enumerate(tools)}
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    idx = futures[future]
                    tool = tools[idx]
                    logger.warning(f"  [Loop] Failed for {tool.get('name','?')}: {e}")
                    analysis = self._analyze_local(tool)
                    results.append({**tool, **analysis, "id": tool.get("id",""), "tool_id": tool.get("id","")})

        id_order = {t.get("id",""): i for i, t in enumerate(tools)}
        results.sort(key=lambda r: id_order.get(r.get("id",""), 999))
        logger.info(f"[Loop] Complete: {len(results)}/{total} tools analyzed")
        return results

    def _analyze_single_with_coze(self, tool: Dict) -> Dict:
        """发送单个工具到Coze工作流分析"""
        prompt = self._build_single_tool_prompt(tool)
        try:
            resp = requests.post(
                "https://api.coze.cn/v1/workflow/run",
                headers={"Authorization": f"Bearer {self.coze_api_key}", "Content-Type": "application/json"},
                json={"workflow_id": self.workflow_id, "parameters": {"input": prompt}},
                timeout=self.batch_timeout
            )
            if resp.status_code == 200:
                result = resp.json()
                if result.get("code") == 0:
                    raw_data = result.get("data")
                    analysis = self._parse_coze_response_data(raw_data)
                    return self._normalize_analysis(analysis, tool)
                else:
                    logger.warning(f"  Coze error: code={result.get('code')}, msg={result.get('msg')}")
            else:
                logger.warning(f"  Coze HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"  Coze single failed: {e}")
        return self._analyze_local(tool)

    def _build_single_tool_prompt(self, tool: Dict) -> str:
        """构建单工具分析提示词"""
        name = tool.get("name", "")
        url = tool.get("url", "")
        desc = tool.get("description", "")
        desc_zh = tool.get("description_zh", "")
        source = tool.get("source", "")
        stars = tool.get("stars", 0) or tool.get("raw_data", {}).get("stargazers_count", 0)
        license_info = tool.get("license", "") or tool.get("raw_data", {}).get("license", "N/A")
        topics = ", ".join(tool.get("topics", [])[:10]) or "无"
        language = tool.get("language", "N/A")
        pushed_at = tool.get("raw_data", {}).get("pushed_at", "N/A")
        forks = tool.get("forks", 0) or tool.get("raw_data", {}).get("forks_count", 0)
        cats = "/".join(self.CATEGORIES)
        tiers = "/".join(self.LICENSE_TIERS)
        levels = "/".join(self.HEALTH_LEVELS)

        return (
            "请独立分析以下AI工具（不要照搬描述，给出你的判断）。\n\n"
            f"名称: {name}\n来源: {source}\nURL: {url}\n描述: {desc}\n"
            f"中文描述: {desc_zh or '无'}\nStars: {stars}\nForks: {forks}\n"
            f"语言: {language}\n许可证: {license_info}\n更新: {pushed_at}\n标签: {topics}\n\n"
            "请严格按以下JSON格式返回（只返回JSON，不要其他文字）：\n"
            '{"category":"' + cats + '中选一个","subcategory":"二级分类",'
            '"license_tier":"' + tiers + '中选一个","license_type":"具体许可证或空字符串",'
            '"tags":{"function":["功能标签"],"scenario":["场景标签"],"attribute":["属性标签"],"tech":["技术标签"],"quality":["质量标签"]},'
            '"ai_analysis":"2-3句中文说明这工具做什么、适合谁",'
            '"ai_confidence":0.8,"is_china_tool":false,"health_status":"' + levels + '中选一个"}'
        )

    def _parse_coze_response_data(self, raw_data):
        """解析Coze工作流返回数据（处理嵌套格式）"""
        if isinstance(raw_data, str):
            try: data_obj = json.loads(raw_data)
            except: return {"output": raw_data}
        elif isinstance(raw_data, dict): data_obj = raw_data
        else: return raw_data
        output_val = data_obj.get("output", data_obj)
        if isinstance(output_val, str):
            try: return json.loads(output_val)
            except: return self._extract_json_array(output_val)
        elif isinstance(output_val, dict): return output_val
        elif isinstance(output_val, list): return output_val
        return data_obj

    def _normalize_analysis(self, analysis, tool=None) -> Dict:
        """标准化分析结果到统一格式"""
        if not isinstance(analysis, dict):
            return self._analyze_local(tool) if tool else self._empty_analysis()
        r = {}
        cat = analysis.get("category", "")
        r["category"] = cat if cat in self.CATEGORIES else (self._fuzzy_match_category(cat) or (self._analyze_local(tool)["category"] if tool else "其他"))
        r["subcategory"] = analysis.get("subcategory", "")

        # 新增：受众面和收录决策
        audience = analysis.get("audience", "")
        r["audience"] = audience if audience in self.AUDIENCE_TYPES else "developer"
        try:
            utility = max(1, min(10, int(analysis.get("utility_score", analysis.get("utility", 5)))))
        except (ValueError, TypeError):
            utility = 5
        r["utility_score"] = utility
        r["should_include"] = self._eval_inclusion(r["category"], utility, analysis)
        r["rejection_reason"] = analysis.get("rejection_reason", "") or analysis.get("reject_reason", "")

        lt = analysis.get("license_tier", "unknown")
        r["license_tier"] = lt if lt in self.LICENSE_TIERS else "unknown"
        r["license_type"] = analysis.get("license_type", "")
        rt = analysis.get("tags", {})
        if isinstance(rt, dict):
            r["tags"] = {k: (rt.get(k, []) if isinstance(rt.get(k), list) else []) for k in ["function","scenario","attribute","tech","quality"]}
        else:
            r["tags"] = {"function":[],"scenario":[],"attribute":[],"tech":[],"quality":[]}
        ai = analysis.get("ai_analysis") or analysis.get("summary") or analysis.get("analysis") or analysis.get("description") or ""
        if not ai and tool: ai = self._analyze_local(tool).get("ai_analysis", "")
        r["ai_analysis"] = ai
        # 丰富分析字段
        features = analysis.get("features", [])
        r["features"] = features if isinstance(features, list) else []
        r["best_for"] = analysis.get("best_for", "") or ""
        r["notable"] = analysis.get("notable", "") or ""
        try: conf = max(0.0, min(1.0, float(analysis.get("ai_confidence", analysis.get("confidence", 0.7)))))
        except: conf = 0.5
        r["ai_confidence"] = conf
        r["is_china_tool"] = bool(analysis.get("is_china_tool", False))
        hs = analysis.get("health_status", "unknown")
        r["health_status"] = hs if hs in self.HEALTH_LEVELS else "unknown"
        return r

    def _eval_inclusion(self, category: str, utility_score: int, analysis: Dict) -> bool:
        """
        根据分类和实用性评分判断是否收录。
        优先使用 AI 的 should_include 判断，再用本地规则兜底。
        """
        # 如果 AI 已经给了明确的 should_include，且合理，则采纳
        ai_decision = analysis.get("should_include")
        if ai_decision is not None:
            # AI 说不收，且分类确实需要门槛 -> 采纳
            # AI 说收，但分类门槛很高 -> 用本地规则复核
            pass

        # 本地规则：按分类的最低实用性阈值 + 全局门槛
        rule = self.inclusion_rules.get(category, self.inclusion_rules.get("其他", {"min_utility": 4}))
        min_utility = rule.get("min_utility", 4) if isinstance(rule, dict) else 4
        effective_min = max(min_utility, self.global_min_utility)
        return utility_score >= effective_min

    def _fuzzy_match_category(self, text) -> Optional[str]:
        if not text: return None
        t = text.lower()
        for c in self.CATEGORIES:
            if c in t or t in c: return c
        kw_map = {"文本生成":["text","写作","chat","翻译"],"图像创作":["image","图片","绘图"],"代码开发":["code","编程","开发"],
                  "数据分析":["data","分析"],"音视频":["audio","video","语音"],"办公效率":["office","办公","效率"],
                  "学术研究":["研究","论文"],"开发工具":["tool","cli","工具"],"设计创意":["design","设计"],
                  "营销推广":["marketing","营销"],"教育培训":["education","教育","学习"]}
        for c, kws in kw_map.items():
            if any(k in t for k in kws): return c
        return None

    def _empty_analysis(self) -> Dict:
        return {"category":"其他","subcategory":"","audience":"developer","utility_score":1,
                "should_include":False,"rejection_reason":"无法分析",
                "license_tier":"unknown","license_type":"",
                "tags":{"function":[],"scenario":[],"attribute":[],"tech":[],"quality":[]},
                "ai_analysis":"","features":[],"best_for":"","notable":"",
                "ai_confidence":0.0,"is_china_tool":False,"health_status":"unknown"}

    # ============================
    # 本地规则分析引擎（完整保留）
    # ============================

    def _analyze_local(self, tool_data: Dict) -> Dict:
        """本地规则分析（不依赖Coze时的降级方案）"""
        name = tool_data.get("name", "")
        desc = (tool_data.get("description", "") + " " + tool_data.get("description_zh", "")).lower()
        url = tool_data.get("url", "").lower()
        source = tool_data.get("source", "")
        topics = tool_data.get("topics", [])
        raw = tool_data.get("raw_data", {})

        # === 许可类型识别 ===
        license_type = raw.get("license", "")
        if isinstance(license_type, dict):
            license_type = license_type.get("name", "") or license_type.get("key", "")
        license_tier = self._detect_license_tier(tool_data, license_type)

        # === 分类推断 ===
        category, subcategory = self._infer_category(name, desc, topics, source)

        # === 五维标签 ===
        tags = self._generate_tags(name, desc, topics, raw)

        # === 健康度 ===
        health = self._assess_health(tool_data)

        # === 国内工具判断 ===
        is_china = self._is_china_tool(url, desc, source)

        # 本地推断受众面和实用性评分
        audience, utility = self._infer_audience_utility(name, desc, category, source, raw)
        should_include = self._eval_inclusion(category, utility, {})

        # === 丰富分析内容 ===
        rich = self._generate_rich_analysis(name, desc, category, license_tier,
                                             source, raw, audience, utility)

        return {
            "category": category,
            "subcategory": subcategory,
            "audience": audience,
            "utility_score": utility,
            "should_include": should_include,
            "rejection_reason": "" if should_include else f"本地评估: 分类={category} 实用性={utility} 低于阈值",
            "license_tier": license_tier,
            "license_type": str(license_type) if license_type else "",
            "tags": tags,
            "ai_analysis": rich["ai_analysis"],
            "features": rich["features"],
            "best_for": rich["best_for"],
            "notable": rich["notable"],
            "ai_confidence": 0.6,  # 本地分析置信度较低
            "is_china_tool": is_china,
            "health_status": health,
        }

    def _detect_license_tier(self, tool: Dict, license_type: str) -> str:
        """检测许可/定价等级"""
        desc = (tool.get("description", "") + " " + tool.get("description_zh", "")).lower()
        url = tool.get("url", "").lower()

        # 开源许可证检测
        open_source_licenses = [
            "mit", "apache-2.0", "gpl-2.0", "gpl-3.0", "bsd-2-clause",
            "bsd-3-clause", "isc", "mpl-2.0", "lgpl-2.1", "lgpl-3.0",
            "agpl-3.0", "unlicense", "apache", "gpl", "bsd", "mpl", "lgpl", "agpl"
        ]
        if license_type.lower().replace(" ", "-") in open_source_licenses:
            return "open-source"

        # GitHub 仓库有 license 文件
        raw = tool.get("raw_data", {})
        if raw.get("has_license") or (raw.get("license") and raw["license"] != "NOASSERTION"):
            return "open-source"

        # 免费/付费关键词检测
        free_keywords = ["free", "免费", "open source", "开源", "no cost", "gratis"]
        paid_keywords = ["pricing", "subscription", "付费", "计划", "pro", "enterprise", "$", "pricing page"]
        freemium_keywords = ["free tier", "free plan", "免费版", "limited", "限量", "freemium", "basic plan"]

        has_paid = any(kw in desc for kw in paid_keywords)
        has_free = any(kw in desc for kw in free_keywords)
        has_freemium = any(kw in desc for kw in freemium_keywords)

        if has_freemium:
            return "freemium"
        elif has_paid and not has_free:
            return "paid"
        elif has_free:
            return "free"

        # 源站特征
        source = tool.get("source", "")
        if source in ["github-trending", "huggingface-models", "huggingface-spaces"]:
            return "open-source"
        elif source in ["aishenqi", "aibot", "toolify-ai", "aigcrank", "aig123"]:
            if "开源" in desc or "github" in url:
                return "open-source"
            return "unknown"

        return "unknown"

    def _infer_audience_utility(self, name: str, desc: str, category: str, source: str, raw: Dict) -> tuple:
        """
        本地推断受众面和实用性评分。
        返回 (audience, utility_score)
        """
        text = f"{name} {desc}".lower()
        stars = raw.get("stargazers_count", 0) or 0

        # === 受众面推断 ===
        general_keywords = [
            "app", "website", "online", "tool", "platform", "service",
            "free", "免费", "在线", "工具", "助手", "生成", "创作",
            "写作", "翻译", "图片", "视频", "音频", "设计", "ppt",
            "office", "email", "calendar", "note", "chat", "bot",
            "editor", "player", "viewer", "converter"
        ]
        dev_keywords = [
            "sdk", "api", "library", "framework", "cli", "terminal",
            "plugin", "extension", "vscode", "npm", "pip", "docker",
            "kubernetes", "ci/cd", "devops", "deploy", "test", "debug",
            "compiler", "lint", "build", "package", "module", "crate",
            "runtime", "interpreter", "bundler", "linter", "formatter"
        ]
        research_keywords = [
            "paper", "论文", "arxiv", "benchmark", "dataset", "model",
            "transformer", "attention", "neural", "training", "inference",
            "evaluation", "experiment", "method", "approach", "algorithm",
            "state-of-the-art", "sota", "ablation", "baseline"
        ]

        general_score = sum(1 for kw in general_keywords if kw in text)
        dev_score = sum(1 for kw in dev_keywords if kw in text)
        research_score = sum(1 for kw in research_keywords if kw in text)

        if research_score > general_score and research_score > dev_score:
            audience = "researcher"
        elif dev_score > general_score:
            audience = "developer"
        else:
            audience = "general"

        # === 实用性评分 ===
        # 基准分：不同来源的默认基准不同
        if source in ("producthunt-ai", "theresanaiforthat", "aibot", "aishenqi"):
            base_score = 7  # 产品导航站的工具通常有产品形态，可直接使用
        elif source in ("aigcrank", "hyperai"):
            base_score = 6
        elif source == "github-trending":
            base_score = 4  # GitHub 工具需要看是否有产品形态
        elif source == "arxiv-ai":
            base_score = 3  # 论文默认低分
        elif source == "hackernews-ai":
            base_score = 5
        else:
            base_score = 5

        # 受众调整
        if audience == "general":
            base_score += 2  # 普通人能用，加分
        elif audience == "researcher":
            base_score -= 1

        # Stars 微调（不影响大局）
        if stars > 5000:
            base_score += 1
        elif stars > 1000:
            base_score += 0  # 1000+ stars 只是及格线，不额外加分

        # 产品形态信号加分
        product_signals = [
            "try it", "试用", "sign up", "注册", "get started",
            "官网", "website", "online tool", "web app", "saas",
            "download", "安装", "chrome extension", "vscode extension"
        ]
        if any(kw in text for kw in product_signals):
            base_score += 1

        # 纯论文/纯库 惩罚
        if source == "arxiv-ai" and not any(kw in text for kw in ["tool", "platform", "service", "app", "website"]):
            base_score = min(base_score, 3)

        # 纯开发基础设施惩罚（测试框架、CI 工具、包管理器等对普通用户无用）
        infra_signals = [
            "test framework", "unit test", "testing library",
            "ci/cd", "build tool", "package manager", "bundler",
            "runtime", "compiler", "transpiler", "linter", "formatter",
            "orm", "database driver", "http client", "logging"
        ]
        if any(kw in text for kw in infra_signals):
            base_score = min(base_score, 4)

        utility = max(1, min(10, base_score))
        return audience, utility

    def _infer_category(self, name: str, desc: str, topics: List[str], source: str) -> tuple:
        """推断一级和二级分类"""
        text = f"{name} {desc} {' '.join(topics)}".lower()

        category_rules = [
            ("代码开发", ["code", "编程", "developer", "debug", "ide", "compiler",
                         "git", "api", "sdk", "framework", "编程辅助"]),
            ("开发工具", ["devtool", "deploy", "docker", "kubernetes", "ci/cd",
                         "monitor", "运维", "devops", "cli", "terminal", "debug"]),
            ("图像创作", ["image", "图片", "绘画", "draw", "paint", "midjourney",
                         "stable diffusion", "dall-e", "生成图", "图像", "photo", "svg"]),
            ("音视频", ["audio", "video", "语音", "视频", "music", "speech",
                       "whisper", "tts", "stt", "播客", "sound"]),
            ("数据分析", ["data", "分析", "analytics", "visualization", "图表",
                         "统计", "dashboard", "bi", "etl"]),
            ("办公效率", ["office", "办公", "document", "ppt", "excel", "pdf",
                         "email", "日程", "笔记", "notion", "calendar", "todo"]),
            ("学术研究", ["research", "论文", "paper", "arxiv", "学术", "scholar",
                         "citation", "模型", "model", "benchmark", "dataset"]),
            ("设计创意", ["design", "设计", "ui", "ux", "figma", "creative",
                         "logo", "品牌", "原型", "wireframe"]),
            ("营销推广", ["marketing", "营销", "seo", "social", "ads", "推广",
                         "content", "增长", "growth", "campaign"]),
            ("教育培训", ["education", "教育", "learn", "学习", "课程", "教学",
                         "tutor", "培训", "quiz", "flashcard"]),
            ("文本生成", ["chat", "chatbot", "gpt", "llm", "text", "writing",
                         "翻译", "写作", "对话", "文案", "摘要", "copilot", "assistant"]),
        ]

        best_cat = "其他"
        best_score = 0

        for cat, keywords in category_rules:
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_cat = cat

        subcategory_map = {
            "文本生成": self._infer_text_subcategory(text),
            "图像创作": self._infer_image_subcategory(text),
            "代码开发": self._infer_code_subcategory(text),
            "数据分析": self._infer_data_subcategory(text),
            "办公效率": self._infer_office_subcategory(text),
            "学术研究": self._infer_research_subcategory(text),
        }

        subcategory = subcategory_map.get(best_cat, "")
        return best_cat, subcategory

    def _infer_text_subcategory(self, text: str) -> str:
        if any(kw in text for kw in ["chat", "对话", "聊天", "chatbot"]):
            return "聊天助手"
        if any(kw in text for kw in ["writing", "写作", "文案", "copy"]):
            return "文案写作"
        if any(kw in text for kw in ["翻译", "translate"]):
            return "翻译"
        if any(kw in text for kw in ["摘要", "summary", "summarize"]):
            return "摘要提取"
        if any(kw in text for kw in ["agent", "工作流", "workflow", "自动化"]):
            return "AI Agent"
        return "通用文本"

    def _infer_image_subcategory(self, text: str) -> str:
        if any(kw in text for kw in ["edit", "编辑", "修图", "enhance"]):
            return "图像编辑"
        if any(kw in text for kw in ["generate", "生成", "create", "创建"]):
            return "图像生成"
        if any(kw in text for kw in ["remove bg", "抠图", "background"]):
            return "图像抠图"
        if any(kw in text for kw in ["upscale", "超分", "enhance", "放大"]):
            return "图像增强"
        return "图像处理"

    def _infer_code_subcategory(self, text: str) -> str:
        if any(kw in text for kw in ["copilot", "completion", "补全", "autocomplete"]):
            return "代码补全"
        if any(kw in text for kw in ["review", "审查", "lint"]):
            return "代码审查"
        if any(kw in text for kw in ["debug", "调试", "fix"]):
            return "调试工具"
        if any(kw in text for kw in ["refactor", "重构", "optimize"]):
            return "代码优化"
        return "开发辅助"

    def _infer_data_subcategory(self, text: str) -> str:
        if any(kw in text for kw in ["visualization", "图表", "chart", "plot"]):
            return "数据可视化"
        if any(kw in text for kw in ["scrape", "爬虫", "crawl", "extract"]):
            return "数据采集"
        if any(kw in text for kw in ["etl", "pipeline", "transform"]):
            return "数据处理"
        return "数据分析"

    def _infer_office_subcategory(self, text: str) -> str:
        if any(kw in text for kw in ["email", "邮件", "mail"]):
            return "邮件工具"
        if any(kw in text for kw in ["note", "笔记", "notebook"]):
            return "笔记工具"
        if any(kw in text for kw in ["calendar", "日程", "schedule"]):
            return "日程管理"
        if any(kw in text for kw in ["pdf", "document", "文档"]):
            return "文档处理"
        return "办公助手"

    def _infer_research_subcategory(self, text: str) -> str:
        if any(kw in text for kw in ["论文", "paper", "arxiv"]):
            return "论文工具"
        if any(kw in text for kw in ["dataset", "数据", "benchmark"]):
            return "数据资源"
        if any(kw in text for kw in ["model", "模型", "training"]):
            return "模型研究"
        return "学术工具"

    def _generate_tags(self, name: str, desc: str, topics: List[str], raw: Dict) -> Dict:
        """生成五维标签"""
        text = f"{name} {desc} {' '.join(topics)}".lower()

        function_tags = []
        scenario_tags = []
        attribute_tags = []
        tech_tags = []
        quality_tags = []

        # === 功能标签 (function) ===
        func_keywords = {
            "文本生成": ["generate text", "text generation", "文本生成", "write"],
            "图像生成": ["generate image", "image generation", "图像生成", "生图", "text-to-image"],
            "代码生成": ["code generation", "代码生成", "生成代码", "codegen"],
            "对话": ["chat", "conversation", "对话", "聊天"],
            "翻译": ["translate", "翻译", "localization"],
            "数据分析": ["analyze", "analysis", "分析", "统计"],
            "语音识别": ["speech recognition", "语音识别", "asr", "stt"],
            "语音合成": ["tts", "text-to-speech", "语音合成", "voice"],
            "视频生成": ["video generation", "视频生成", "video"],
            "搜索": ["search", "搜索", "retrieval", "检索"],
            "自动化": ["automate", "automation", "自动化", "workflow"],
        }
        for tag, keywords in func_keywords.items():
            if any(kw in text for kw in keywords):
                function_tags.append(tag)

        # === 场景标签 (scenario) ===
        scenario_keywords = {
            "个人开发者": ["personal", "individual", "个人", "独立开发"],
            "企业团队": ["enterprise", "team", "企业", "团队", "collaboration"],
            "内容创作": ["content", "creator", "创作", "内容"],
            "教育学习": ["education", "learn", "教育", "学习", "study"],
            "学术研究": ["research", "paper", "学术", "研究"],
            "商业营销": ["marketing", "business", "商业", "营销"],
            "日常办公": ["office", "productivity", "办公", "效率"],
            "设计工作": ["design", "设计", "creative", "创意"],
        }
        for tag, keywords in scenario_keywords.items():
            if any(kw in text for kw in keywords):
                scenario_tags.append(tag)

        # === 属性标签 (attribute) ===
        if "免费" in text or "free" in text:
            attribute_tags.append("免费")
        if "中文" in text or "chinese" in text:
            attribute_tags.append("中文支持")
        if "api" in text:
            attribute_tags.append("API服务")
        if "plugin" in text or "插件" in text or "extension" in text:
            attribute_tags.append("浏览器插件")
        if "open source" in text or "开源" in text:
            attribute_tags.append("开源")
        if "self-host" in text or "self host" in text or "本地部署" in text:
            attribute_tags.append("本地部署")
        if "mobile" in text or "移动端" in text or "ios" in text or "android" in text:
            attribute_tags.append("移动端")

        # === 技术标签 (tech) ===
        tech_map = {
            "gpt-4": "GPT-4", "gpt4": "GPT-4", "gpt-3.5": "GPT-3.5",
            "claude": "Claude", "gemini": "Gemini", "llama": "Llama",
            "mistral": "Mistral", "stable diffusion": "Stable Diffusion",
            "diffusion": "Diffusion", "transformer": "Transformer",
            "rag": "RAG", "embedding": "Embedding", "multimodal": "Multi-modal",
            "fine-tune": "Fine-tuning", "fine tuning": "Fine-tuning",
            "langchain": "LangChain", "llamaindex": "LlamaIndex",
            "pytorch": "PyTorch", "tensorflow": "TensorFlow",
        }
        for kw, tag in tech_map.items():
            if kw in text:
                tech_tags.append(tag)

        # === 质量标签 (quality) ===
        stars = raw.get("stargazers_count", 0) or raw.get("stars", 0) or 0
        if isinstance(stars, str):
            try:
                stars = int(stars)
            except (ValueError, TypeError):
                stars = 0

        if stars > 10000:
            quality_tags.append("热门")
        elif stars > 5000:
            quality_tags.append("口碑好")
        elif stars > 1000:
            quality_tags.append("受关注")
        elif stars > 100:
            quality_tags.append("成长中")
        else:
            quality_tags.append("新星")

        pushed_at = raw.get("pushed_at", "")
        if pushed_at:
            try:
                dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
                days = (datetime.now(timezone.utc) - dt).days
                if days <= 7:
                    quality_tags.append("高活跃")
                elif days <= 30:
                    quality_tags.append("活跃")
                elif days > 180:
                    quality_tags.append("低活跃")
            except:
                pass

        return {
            "function": list(set(function_tags)),
            "scenario": list(set(scenario_tags)),
            "attribute": list(set(attribute_tags)),
            "tech": list(set(tech_tags)),
            "quality": list(set(quality_tags)),
        }

    def _assess_health(self, tool: Dict) -> str:
        """评估健康度"""
        raw = tool.get("raw_data", {})
        updated = raw.get("pushed_at") or raw.get("updated_at") or raw.get("last_updated", "")

        if not updated:
            return "unknown"

        try:
            if isinstance(updated, str):
                dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            else:
                dt = updated

            now = datetime.now(timezone.utc)
            days = (now - dt).days

            if days <= 30:
                return "active"
            elif days <= 180:
                return "moderate"
            elif days <= 365:
                return "dormant"
            else:
                return "archived"
        except:
            return "unknown"

    def _is_china_tool(self, url: str, desc: str, source: str) -> bool:
        """判断是否国内工具"""
        china_domains = [".cn", ".com.cn", ".net.cn", ".org.cn"]
        china_keywords = ["国内", "中国", "国产", "本土"]

        if any(url.endswith(d) for d in china_domains):
            return True

        if source in ["aishenqi", "aigcrank", "aibot", "toolify-ai", "aig123"]:
            return True

        china_url_patterns = [
            "baidu.com", "aliyun.com", "tencent.com", "bytedance.com",
            "zhipuai.cn", "moonshot.cn", "baichuan-ai.com", "01.ai",
            "deepseek.com", "volcengine.com", "bcebos.com"
        ]
        if any(pattern in url for pattern in china_url_patterns):
            return True

        return False

    def _generate_summary(self, name: str, desc: str, category: str, license_tier: str) -> str:
        """生成分析摘要（简版，兼容旧字段）"""
        tier_desc = {
            "open-source": "开源项目",
            "freemium": "免费限量",
            "free": "免费工具",
            "paid": "付费产品",
            "source-available": "源码可见",
            "unknown": "定价未知",
        }
        tier_text = tier_desc.get(license_tier, "定价未知")

        desc_clean = desc.strip()
        if len(desc_clean) > 200:
            desc_clean = desc_clean[:200] + "..."

        return f"{name} 属于{category}领域，{tier_text}。{desc_clean}"

    def _generate_rich_analysis(self, name: str, desc: str, category: str,
                                license_tier: str, source: str, raw: Dict,
                                audience: str, utility: int) -> Dict:
        """
        生成更丰富的分析内容，包含功能亮点、适合人群、特色评价。
        本地降级时使用，比 _generate_summary 更详细。
        """
        text = f"{name} {desc}".lower()
        desc_clean = desc.strip().rstrip('.')

        # === 一句话概述（ai_analysis）===
        tier_desc = {
            "open-source": "开源",
            "freemium": "免费增值",
            "free": "免费",
            "paid": "付费",
            "source-available": "源码可见",
            "unknown": "",
        }
        tier_text = tier_desc.get(license_tier, "")

        # 从英文描述中提取关键词作为中文概述的补充
        # 提取描述中的核心动作词（去除常见停用词）
        desc_short = desc_clean[:60].strip().rstrip('.,;!')
        # 如果描述太长或含英文句子，截取到第一个句号/句号位置
        if len(desc_short) > 50:
            desc_short = desc_clean[:50].strip().rstrip('.,;!') + "..."

        # 根据受众面调整概述风格 - 生成纯中文概述，不嵌入英文原文
        if audience == "general":
            tier_part = f"{tier_text}" if tier_text else ""
            overview = f"{name} 是一款{category}领域的{tier_part}工具".replace("的的", "的").rstrip("，, ")
            overview += "，适合普通用户直接使用，无需技术背景。"
        elif audience == "developer":
            tier_part = f"{tier_text}" if tier_text else ""
            overview = f"{name} 是一个面向开发者的{category}类{tier_part}项目".replace("的的", "的").rstrip("，, ")
            overview += "，适合有技术背景的用户集成到工作流中使用。"
        elif audience == "researcher":
            tier_part = f"{tier_text}" if tier_text else ""
            overview = f"{name} 是{category}领域的{tier_part}研究工具".replace("的的", "的").rstrip("，, ")
            overview += "，主要面向研究人员和学术场景。"
        else:
            overview = f"{name} 属于{category}领域。"

        # === 功能亮点 (features) ===
        features = []
        feature_keywords = {
            "AI驱动": ["ai", "gpt", "llm", "neural", "model", "machine learning", "deep learning"],
            "实时处理": ["real-time", "realtime", "live", "streaming", "实时"],
            "多语言支持": ["multilingual", "multi-language", "多语言", "i18n", "localization"],
            "API接口": ["api", "rest", "graphql", "endpoint", "webhook"],
            "浏览器扩展": ["chrome extension", "firefox", "browser extension", "浏览器插件"],
            "云端部署": ["cloud", "saas", "hosted", "在线", "云端"],
            "本地运行": ["local", "offline", "本地", "离线", "self-hosted"],
            "开源免费": ["open-source", "open source", "free", "mit", "apache"],
            "自动化": ["automation", "automate", "auto", "自动化", "workflow", "pipeline"],
            "可视化": ["visualization", "visual", "dashboard", "chart", "图表", "可视化"],
            "协作功能": ["collaborate", "collaboration", "team", "share", "协作", "团队"],
            "跨平台": ["cross-platform", "multi-platform", "windows", "macos", "linux", "跨平台"],
            "数据导入导出": ["import", "export", "convert", "导入", "导出", "转换"],
            "插件/扩展系统": ["plugin", "extension", "addon", "插件", "扩展"],
            "CLI工具": ["cli", "command line", "terminal", "命令行"],
            "SDK集成": ["sdk", "library", "framework", "集成"],
        }
        for feat_name, keywords in feature_keywords.items():
            if any(kw in text for kw in keywords):
                features.append(feat_name)
            if len(features) >= 3:
                break

        # 如果没提取到特征，根据分类给默认特征
        if not features:
            default_features = {
                "文本生成": ["文本处理", "智能生成"],
                "图像创作": ["图像处理", "视觉创作"],
                "代码开发": ["开发辅助", "代码工具"],
                "数据分析": ["数据处理", "分析工具"],
                "音视频": ["媒体处理", "音视频工具"],
                "办公效率": ["效率提升", "办公辅助"],
                "学术研究": ["研究工具", "学术资源"],
                "开发工具": ["开发辅助", "工程工具"],
                "设计创意": ["设计工具", "创意设计"],
                "营销推广": ["营销工具", "推广助手"],
                "教育培训": ["教育资源", "学习工具"],
                "其他": ["实用工具"],
            }
            features = default_features.get(category, ["实用工具"])

        # === 适合人群 (best_for) ===
        audience_map = {
            "general": "普通用户、AI爱好者，无需技术背景即可使用",
            "developer": "开发者和技术人员，适合集成到工作流中",
            "researcher": "研究人员和学者，适合学术研究和论文工作",
        }
        best_for = audience_map.get(audience, "对AI工具感兴趣的用户")

        # === 特色评价 (notable) ===
        stars = raw.get("stargazers_count", 0) or 0
        notable_parts = []

        if stars >= 10000:
            notable_parts.append(f"GitHub {stars/1000:.0f}k+ Stars，社区高度认可")
        elif stars >= 5000:
            notable_parts.append(f"GitHub {stars/1000:.1f}k Stars，社区关注度高")
        elif stars >= 1000:
            notable_parts.append(f"GitHub {stars/1000:.1f}k Stars，有一定社区基础")

        if license_tier == "open-source":
            notable_parts.append("完全开源，可自由部署和修改")
        elif license_tier == "free":
            notable_parts.append("免费使用，零成本上手")
        elif license_tier == "freemium":
            notable_parts.append("提供免费层，高级功能按需付费")

        # 实用性评价
        if utility >= 8:
            notable_parts.append("实用性极高，强烈推荐")
        elif utility >= 6:
            notable_parts.append("实用性良好，值得一试")
        elif utility >= 4:
            notable_parts.append("有一定实用价值")

        notable = "；".join(notable_parts[:3]) if notable_parts else "值得关注的工具"

        return {
            "ai_analysis": overview,
            "features": features,
            "best_for": best_for,
            "notable": notable,
        }

    def _build_analysis_prompt(self, tool: Dict) -> str:
        """构建Coze分析提示词（单工具模式）"""
        return f"""请分析以下AI工具，给出独立判断（不要照搬描述）：

工具名称: {tool.get('name', '')}
来源: {tool.get('source', '')}
URL: {tool.get('url', '')}
描述: {tool.get('description', '')}
中文描述: {tool.get('description_zh', '')}
Stars: {tool.get('raw_data', {}).get('stargazers_count', 'N/A')}
许可证: {tool.get('raw_data', {}).get('license', 'N/A')}
最后更新: {tool.get('raw_data', {}).get('pushed_at', 'N/A')}

请返回JSON格式：
{{
  "category": "一级分类(文本生成/图像创作/代码开发/数据分析/音视频/办公效率/学术研究/开发工具/设计创意/营销推广/教育培训/其他)",
  "subcategory": "二级分类",
  "license_tier": "open-source/freemium/free/paid/source-available/unknown",
  "license_type": "具体许可证如MIT/Apache等",
  "tags": {{
    "function": ["功能标签"],
    "scenario": ["场景标签"],
    "attribute": ["属性标签"],
    "tech": ["技术标签"],
    "quality": ["质量标签"]
  }},
  "ai_analysis": "1-2句精炼中文概述，说明这个工具做什么、解决什么问题。要简洁有力，不要照搬英文描述",
  "features": ["3个以内核心功能亮点，每个5-10字中文"],
  "best_for": "一句话说明最适合谁用、在什么场景下用",
  "notable": "一句话评价：这个工具的独特优势或值得关注的理由",
  "ai_confidence": 0.8,
  "is_china_tool": false,
  "health_status": "active/moderate/dormant/archived"
}}"""


def generate_tool_id(source: str, name: str) -> str:
    """生成工具唯一ID"""
    slug = name.lower().replace(" ", "-").replace("/", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    return f"{source}_{slug}"
