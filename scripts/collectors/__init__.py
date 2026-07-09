"""
AI百宝箱 - 采集器包
"""
from .base import BaseCollector, load_config, get_enabled_sources, get_collector
from .github_trending import Collector as GitHubTrendingCollector
from .huggingface import Collector as HuggingFaceCollector
from .huggingface_spaces import Collector as HuggingFaceSpacesCollector
from .hyperai import Collector as HyperAICollector
from .producthunt import Collector as ProductHuntCollector
from .toolify import Collector as ToolifyCollector
from .aig123 import Collector as AIG123Collector
from .futurepedia import Collector as FuturepediaCollector
from .manual import Collector as ManualCollector

__all__ = [
    "BaseCollector",
    "load_config",
    "get_enabled_sources",
    "get_collector",
    "GitHubTrendingCollector",
    "HuggingFaceCollector",
    "HuggingFaceSpacesCollector",
    "HyperAICollector",
    "ProductHuntCollector",
    "ToolifyCollector",
    "AIG123Collector",
    "FuturepediaCollector",
    "ManualCollector",
]
