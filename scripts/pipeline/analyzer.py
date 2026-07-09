"""
AI分析管道 - 对采集的工具进行AI深度分析
调用Coze工作流或直接用LLM API进行五维标签生成
"""
import json
import logging
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


# 分析Prompt模板
ANALYSIS_PROMPT = """你是一个AI工具分析专家。请对以下AI工具/项目进行深度分析。

## 工具信息
- 名称: {name}
- 来源: {source}
- 链接: {url}
- 原始描述: {description}
- 语言/技术: {language}
- 统计数据: {stats}

## 分析要求
请以JSON格式输出分析结果，包含以下字段：

1. **description_zh** (string): 中文一句话描述，简洁有力
2. **summary** (string): 2-3段详细总结，涵盖：做什么、怎么用、适合谁
3. **features** (string[]): 核心功能列表，3-7个
4. **use_cases** (string[]): 典型使用场景，3-5个
5. **pros** (string[]): 优点，2-4个
6. **cons** (string[]): 缺点/局限，1-3个
7. **alternatives** (string[]): 同类替代工具名称，2-5个
8. **tags**: 五维标签对象：
   - function (string[]): 功能分类标签，从以下选择: {function_tags}
   - scenario (string[]): 使用场景标签，从以下选择: {scenario_tags}
   - attribute (string[]): 产品属性标签，从以下选择: {attribute_tags}
   - tech (string[]): 技术特征标签，从以下选择: {tech_tags}
   - quality (string[]): 质量评估标签，从以下选择: {quality_tags}
9. **category** (string): 主分类，如: 文本生成/图像生成/开发工具/数据分析/写作辅助等
10. **pricing** (string): 定价模式: 免费/付费/Freemium/开源/API计费

只输出JSON，不要其他内容。"""


class AIAnalyzer:
    """AI分析管道"""

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.api_key = self.config.get("coze_api_key", "")
        self.api_base = self.config.get("coze_api_base", "https://api.coze.cn/v3")
        self.bot_id = self.config.get("analyzer_bot_id", "")
        self.data_dir = Path(__file__).parent.parent.parent / "data"

    def analyze_tool(self, tool_data: Dict) -> Dict:
        """
        对单个工具进行AI分析
        返回增强后的工具数据
        """
        # 构建分析Prompt
        prompt = self._build_prompt(tool_data)

        # 调用AI分析（优先Coze，降级为直接API）
        if self.bot_id and self.api_key:
            result = self._call_coze_workflow(prompt)
        else:
            result = self._call_direct_llm(prompt)

        if result:
            # 合并分析结果到原始数据
            tool_data.update(result)
            tool_data["analyzed_at"] = datetime.now(timezone.utc).isoformat()

        return tool_data

    def analyze_batch(self, tools: List[Dict], batch_size: int = 5) -> List[Dict]:
        """批量分析工具"""
        results = []
        total = len(tools)

        for i, tool in enumerate(tools):
            try:
                logger.info(f"Analyzing tool {i+1}/{total}: {tool.get('name', 'unknown')}")
                analyzed = self.analyze_tool(tool)
                results.append(analyzed)
            except Exception as e:
                logger.error(f"Failed to analyze {tool.get('name')}: {e}")
                results.append(tool)  # 保留原始数据

        return results

    def _build_prompt(self, tool_data: Dict) -> str:
        """构建分析Prompt"""
        # 导入标签列表
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from pipeline.data_model import FUNCTION_TAGS, SCENARIO_TAGS, ATTRIBUTE_TAGS, TECH_TAGS, QUALITY_TAGS

        stats_str = ""
        if tool_data.get("stars"):
            stats_str += f"Stars: {tool_data['stars']}, "
        if tool_data.get("downloads"):
            stats_str += f"Downloads: {tool_data['downloads']}, "
        if tool_data.get("likes"):
            stats_str += f"Likes: {tool_data['likes']}"

        return ANALYSIS_PROMPT.format(
            name=tool_data.get("name", ""),
            source=tool_data.get("source", ""),
            url=tool_data.get("url", ""),
            description=tool_data.get("description", "")[:500],
            language=tool_data.get("language", ""),
            stats=stats_str,
            function_tags=", ".join(FUNCTION_TAGS[:30]),  # 控制长度
            scenario_tags=", ".join(SCENARIO_TAGS[:20]),
            attribute_tags=", ".join(ATTRIBUTE_TAGS[:20]),
            tech_tags=", ".join(TECH_TAGS[:25]),
            quality_tags=", ".join(QUALITY_TAGS[:15]),
        )

    def _call_coze_workflow(self, prompt: str) -> Optional[Dict]:
        """调用Coze工作流进行AI分析"""
        try:
            url = f"{self.api_base}/workflow/run"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "workflow_id": self.bot_id,
                "parameters": {
                    "input": prompt,
                },
            }

            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
            result = resp.json()

            if result.get("code") == 0:
                output = result.get("data", "")
                return self._parse_analysis_result(output)
            else:
                logger.error(f"Coze workflow error: {result}")
                return None

        except Exception as e:
            logger.error(f"Coze workflow call failed: {e}")
            return None

    def _call_direct_llm(self, prompt: str) -> Optional[Dict]:
        """直接调用LLM API（备用方案）"""
        # MVP阶段先返回mock数据，后续接入真实LLM
        logger.warning("No Coze bot configured, using mock analysis")
        return self._mock_analysis()

    def _parse_analysis_result(self, text: str) -> Optional[Dict]:
        """解析AI返回的分析结果"""
        try:
            # 尝试提取JSON
            text = text.strip()
            if text.startswith("```"):
                # 去除markdown代码块
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]

            result = json.loads(text.strip())
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            # 尝试提取部分信息
            return self._partial_parse(text)

    def _partial_parse(self, text: str) -> Optional[Dict]:
        """尝试从不完整的JSON中提取信息"""
        import re
        result = {}

        # 尝试提取中文描述
        match = re.search(r'"description_zh"\s*:\s*"([^"]+)"', text)
        if match:
            result["description_zh"] = match.group(1)

        # 尝试提取分类
        match = re.search(r'"category"\s*:\s*"([^"]+)"', text)
        if match:
            result["category"] = match.group(1)

        return result if result else None

    def _mock_analysis(self) -> Dict:
        """Mock分析结果（开发阶段使用）"""
        return {
            "description_zh": "AI工具（待分析）",
            "summary": "该工具正在等待AI分析服务接入，将自动完成深度分析。",
            "features": ["待分析"],
            "use_cases": ["待分析"],
            "pros": ["待确认"],
            "cons": ["待确认"],
            "alternatives": [],
            "tags": {
                "function": [],
                "scenario": [],
                "attribute": [],
                "tech": [],
                "quality": ["待验证"],
            },
            "category": "未分类",
            "pricing": "未知",
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }


def generate_tool_id(source: str, name: str) -> str:
    """生成工具唯一ID"""
    slug = name.lower().replace(" ", "-").replace("/", "-")
    # 去除特殊字符
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    return f"{source}_{slug}"
