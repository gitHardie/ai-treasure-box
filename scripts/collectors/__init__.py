"""
AI百宝箱 - 采集器包
"""
from .base import BaseCollector, load_config, get_enabled_sources, get_collector
from .github_trending import Collector as GitHubTrendingCollector
from .huggingface import Collector as HuggingFaceCollector
from .hyperai import Collector as HyperAICollector

__all__ = [
    "BaseCollector",
    "load_config",
    "get_enabled_sources",
    "get_collector",
    "GitHubTrendingCollector",
    "HuggingFaceCollector",
    "HyperAICollector",
]
