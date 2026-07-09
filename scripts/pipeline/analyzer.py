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

    def __init__(self, coze_api_key: Optional[str] = None, workflow_id: Optional[str] = None,
                 batch_size: int = 20, batch_timeout: int = 120):
        self.coze_api_key = coze_api_key or os.environ.get("COZE_API_KEY", "") or os.environ.get("AI_BOX_COZE", "")
        self.workflow_id = workflow_id or os.environ.get("COZE_WORKFLOW_ID", "")
        self.use_coze = bool(self.coze_api_key and self.workflow_id)
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout

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

        return f"""请分析以下 {count} 个AI工具，对每个工具给出独立判断（不要照搬描述）。

{tools_text}

请返回一个JSON数组，包含 {count} 个对象，按编号顺序对应。格式如下：
[
  {{
    "index": 1,
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
    "ai_analysis": "2-3句独立分析摘要，说明这个工具真正做什么、适合谁",
    "ai_confidence": 0.8,
    "is_china_tool": false,
    "health_status": "active/moderate/dormant/archived"
  }}
]

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

        # === 分析摘要 ===
        analysis = self._generate_summary(name, desc, category, license_tier)

        return {
            "category": category,
            "subcategory": subcategory,
            "license_tier": license_tier,
            "license_type": str(license_type) if license_type else "",
            "tags": tags,
            "ai_analysis": analysis,
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
        """生成分析摘要"""
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
  "ai_analysis": "2-3句独立分析摘要，说明这个工具真正做什么、适合谁",
  "ai_confidence": 0.8,
  "is_china_tool": false,
  "health_status": "active/moderate/dormant/archived"
}}"""


def generate_tool_id(source: str, name: str) -> str:
    """生成工具唯一ID"""
    slug = name.lower().replace(" ", "-").replace("/", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    return f"{source}_{slug}"
