"""
AI百宝箱 - 数据模型定义
五维标签体系 + 完整数据Schema
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import hashlib


# ===== 五维标签体系 =====
# 维度1: 功能分类
FUNCTION_TAGS = [
    "文本生成", "图像生成", "视频生成", "音频生成", "代码生成",
    "数据分析", "文档处理", "翻译", "搜索", "对话",
    "图像编辑", "视频编辑", "音频编辑", "PPT制作", "写作辅助",
    "设计辅助", "编程辅助", "数据分析", "客服机器人", "教育工具",
    "办公效率", "营销工具", "SEO工具", "社交媒体", "电商工具",
    "开发工具", "测试工具", "部署工具", "监控工具", "安全工具",
    "数据标注", "模型训练", "模型评估", "向量数据库", "RAG",
    "Agent框架", "工作流编排", "知识库", "提示词工程", "微调工具",
]

# 维度2: 使用场景
SCENARIO_TAGS = [
    "个人使用", "团队协作", "企业级", "开发者", "设计师",
    "写作者", "营销人员", "研究人员", "教师", "学生",
    "产品经理", "运营人员", "客服人员", "数据分析师", "自由职业",
    "内容创作", "学术研究", "商业应用", "开源项目", "政府机构",
]

# 维度3: 产品属性
ATTRIBUTE_TAGS = [
    "免费", "付费", "开源", "闭源", "API服务",
    "SaaS", "本地部署", "移动端", "桌面端", "浏览器插件",
    "中文支持", "英文优先", "多语言", "离线可用", "在线服务",
    "实时处理", "批量处理", "低代码", "无代码", "需编程",
]

# 维度4: 技术特征
TECH_TAGS = [
    "GPT-4", "Claude", "Gemini", "Llama", "Mistral",
    "Stable Diffusion", "DALL-E", "Midjourney", "Sora", "Whisper",
    "Transformer", "Diffusion", "GAN", "RLHF", "RAG",
    "向量检索", "Embedding", "Fine-tuning", "Prompt Engineering", "Multi-modal",
    "语音识别", "图像识别", "自然语言处理", "计算机视觉", "强化学习",
]

# 维度5: 质量评估
QUALITY_TAGS = [
    "热门", "新星", "经典", "小众精品", "实验性",
    "高活跃", "低活跃", "已停更", "即将上线", "Beta",
    "口碑好", "争议中", "推荐", "待验证", "独家",
]


@dataclass
class Tags:
    """五维标签"""
    function: List[str] = field(default_factory=list)    # 功能分类
    scenario: List[str] = field(default_factory=list)    # 使用场景
    attribute: List[str] = field(default_factory=list)   # 产品属性
    tech: List[str] = field(default_factory=list)        # 技术特征
    quality: List[str] = field(default_factory=list)     # 质量评估

    def to_dict(self) -> Dict:
        return {
            "function": self.function,
            "scenario": self.scenario,
            "attribute": self.attribute,
            "tech": self.tech,
            "quality": self.quality,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Tags":
        return cls(
            function=data.get("function", []),
            scenario=data.get("scenario", []),
            attribute=data.get("attribute", []),
            tech=data.get("tech", []),
            quality=data.get("quality", []),
        )


@dataclass
class ToolStats:
    """工具统计数据"""
    stars: Optional[int] = None
    forks: Optional[int] = None
    downloads: Optional[int] = None
    monthly_visits: Optional[int] = None
    growth_rate: Optional[float] = None      # 增长率(%)
    rank_position: Optional[int] = None      # 排名位置
    rank_source: Optional[str] = None        # 排名来源


@dataclass
class Tool:
    """AI工具/项目 核心数据模型"""
    # === 基础信息 ===
    id: str                                    # 唯一标识 = source + "_" + slug
    name: str                                  # 工具名称
    slug: str                                  # URL友好标识
    source: str                                # 数据来源ID
    source_url: str                            # 原始来源URL
    url: str                                   # 工具官网URL
    description: str                           # 简短描述(一句话)
    description_zh: str = ""                   # 中文描述

    # === 详细分析（AI生成） ===
    summary: str = ""                          # 详细总结(2-3段)
    features: List[str] = field(default_factory=list)   # 核心功能列表
    use_cases: List[str] = field(default_factory=list)  # 典型使用场景
    pros: List[str] = field(default_factory=list)       # 优点
    cons: List[str] = field(default_factory=list)       # 缺点
    alternatives: List[str] = field(default_factory=list)  # 替代品

    # === 五维标签 ===
    tags: Tags = field(default_factory=Tags)

    # === 元数据 ===
    category: str = ""                         # 主分类
    subcategory: str = ""                      # 子分类
    language: List[str] = field(default_factory=list)    # 支持语言
    platform: List[str] = field(default_factory=list)    # 平台
    pricing: str = ""                          # 定价模式
    pricing_detail: str = ""                   # 定价详情
    license: str = ""                          # 开源协议

    # === 统计 ===
    stats: Optional[ToolStats] = None

    # === 关联 ===
    related_tools: List[str] = field(default_factory=list)  # 关联工具ID
    parent_tool: Optional[str] = None                        # 所属产品(如果是子产品)

    # === 时间戳 ===
    first_seen: str = ""                       # 首次发现时间 ISO8601
    last_updated: str = ""                     # 最后更新时间
    collected_at: str = ""                     # 本次采集时间
    content_hash: str = ""                     # 内容指纹(用于变更检测)

    # === 原始数据 ===
    raw_data: Dict[str, Any] = field(default_factory=dict)  # 原始采集数据

    def compute_hash(self) -> str:
        """计算内容指纹，用于检测变更"""
        content = f"{self.name}|{self.description}|{self.url}|{self.pricing}"
        return hashlib.md5(content.encode()).hexdigest()

    def to_dict(self) -> Dict:
        d = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "source": self.source,
            "source_url": self.source_url,
            "url": self.url,
            "description": self.description,
            "description_zh": self.description_zh,
            "summary": self.summary,
            "features": self.features,
            "use_cases": self.use_cases,
            "pros": self.pros,
            "cons": self.cons,
            "alternatives": self.alternatives,
            "tags": self.tags.to_dict(),
            "category": self.category,
            "subcategory": self.subcategory,
            "language": self.language,
            "platform": self.platform,
            "pricing": self.pricing,
            "pricing_detail": self.pricing_detail,
            "license": self.license,
            "stats": asdict(self.stats) if self.stats else None,
            "related_tools": self.related_tools,
            "parent_tool": self.parent_tool,
            "first_seen": self.first_seen,
            "last_updated": self.last_updated,
            "collected_at": self.collected_at,
            "content_hash": self.content_hash,
            "raw_data": self.raw_data,
        }
        return d

    def save(self, filepath: str):
        """保存为JSON文件"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "Tool":
        """从JSON文件加载"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict) -> "Tool":
        tags_data = data.get("tags", {})
        stats_data = data.get("stats")
        return cls(
            id=data["id"],
            name=data["name"],
            slug=data["slug"],
            source=data["source"],
            source_url=data.get("source_url", ""),
            url=data.get("url", ""),
            description=data.get("description", ""),
            description_zh=data.get("description_zh", ""),
            summary=data.get("summary", ""),
            features=data.get("features", []),
            use_cases=data.get("use_cases", []),
            pros=data.get("pros", []),
            cons=data.get("cons", []),
            alternatives=data.get("alternatives", []),
            tags=Tags.from_dict(tags_data),
            category=data.get("category", ""),
            subcategory=data.get("subcategory", ""),
            language=data.get("language", []),
            platform=data.get("platform", []),
            pricing=data.get("pricing", ""),
            pricing_detail=data.get("pricing_detail", ""),
            license=data.get("license", ""),
            stats=ToolStats(**stats_data) if stats_data else None,
            related_tools=data.get("related_tools", []),
            parent_tool=data.get("parent_tool"),
            first_seen=data.get("first_seen", ""),
            last_updated=data.get("last_updated", ""),
            collected_at=data.get("collected_at", ""),
            content_hash=data.get("content_hash", ""),
            raw_data=data.get("raw_data", {}),
        )


@dataclass
class NewsItem:
    """新闻/资讯条目"""
    id: str
    title: str
    url: str
    source: str
    published_at: str
    summary: str = ""
    summary_zh: str = ""
    tags: Tags = field(default_factory=Tags)
    related_tools: List[str] = field(default_factory=list)
    collected_at: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RankingSnapshot:
    """排名快照（用于历史对比）"""
    date: str                              # YYYY-MM-DD
    source: str                            # 排名来源
    items: List[Dict[str, Any]] = field(default_factory=list)
    # 每个item: {"name": str, "rank": int, "score": float, "tool_id": str}


@dataclass
class DailySnapshot:
    """每日快照（用于历史沉淀）"""
    date: str                              # YYYY-MM-DD
    total_tools: int = 0
    new_tools: List[str] = field(default_factory=list)      # 新增工具ID
    updated_tools: List[str] = field(default_factory=list)  # 更新工具ID
    removed_tools: List[str] = field(default_factory=list)  # 消失工具ID
    category_counts: Dict[str, int] = field(default_factory=dict)
    tag_trends: Dict[str, int] = field(default_factory=dict)
    top_new_entries: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)

    def save(self, filepath: str):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
