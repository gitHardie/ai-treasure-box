"""
Search Enricher - DuckDuckGo search enrichment for AI tools.

Provides search-based signals to the LLM analyzer.
Features: disk cache (7-day TTL), concurrent search, graceful degradation.
"""
import json
import os
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Domains considered as aggregator sites (not official sites)
AGGREGATOR_DOMAINS = {
    "github.com",
    "producthunt.com",
    "alternativeto.net",
    "theregister.com",
    "en.wikipedia.org",
    "reddit.com",
    "news.ycombinator.com",
    "medium.com",
    "dev.to",
    "techcrunch.com",
    "venturebeat.com",
    "stackoverflow.com",
    "npmjs.com",
    "pypi.org",
    "huggingface.co",
    "youtube.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "g2.com",
    "capterra.com",
}

# Cache TTL in seconds (7 days)
CACHE_TTL_SECONDS = 7 * 24 * 3600

POPULARITY_HOT_MIN = 5
POPULARITY_WARM_MIN = 3
POPULARITY_MODERATE_MIN = 1

class SearchEnricher:
    """Enrich tool data with DuckDuckGo search results."""

    def __init__(self, cache_dir=None):
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent.parent / "data" / "cache"
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / "search_cache.json"
        self._cache = {}
        self._load_cache()

    def _load_cache(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as fh:
                    self._cache = json.load(fh)
                logger.info("[Search] Loaded cache with %d entries", len(self._cache))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("[Search] Failed to load cache: %s", e)
                self._cache = {}
        else:
            self._cache = {}

    def _save_cache(self):
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as fh:
                json.dump(self._cache, fh, ensure_ascii=False, indent=2)
            logger.info("[Search] Saved cache with %d entries", len(self._cache))
        except OSError as e:
            logger.warning("[Search] Failed to save cache: %s", e)

    def _is_cache_valid(self, entry):
        timestamp = entry.get("timestamp", 0)
        age = time.time() - timestamp
        return age < CACHE_TTL_SECONDS

    def _is_official_site(self, href):
        if not href:
            return False
        try:
            domain = urlparse(href).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            for agg_domain in AGGREGATOR_DOMAINS:
                if domain == agg_domain or domain.endswith("." + agg_domain):
                    return False
            return True
        except Exception:
            return False

    def _compute_popularity_tier(self, result_count, has_official):
        if result_count >= POPULARITY_HOT_MIN and has_official:
            return "hot"
        elif result_count >= POPULARITY_WARM_MIN:
            return "warm"
        elif result_count >= POPULARITY_MODERATE_MIN:
            return "moderate"
        else:
            return "cold"

    def _empty_result(self):
        return {
            "result_count": 0,
            "top_snippets": [],
            "has_official_site": False,
            "popularity_tier": "cold",
        }

    def _search_single_tool(self, tool):
        tool_name = tool.get("name", "")
        query = chr(34) + tool_name + chr(34) + " AI tool"
        logger.info("[Search] Searching: %s", query)
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=8))
            if not results:
                return self._empty_result()
            snippets = []
            for r in results[:3]:
                title = (r.get("title") or "").strip()
                body = (r.get("body") or "").strip()
                snippet = (title + " " + body).strip()
                if snippet:
                    snippets.append(snippet)
            has_official = False
            for r in results:
                href = r.get("href", "")
                if self._is_official_site(href):
                    has_official = True
                    break
            result_count = len(results)
            popularity_tier = self._compute_popularity_tier(result_count, has_official)
            logger.info("[Search] %s: %d results, tier=%s", tool_name, result_count, popularity_tier)
            return {
                "result_count": result_count,
                "top_snippets": snippets,
                "has_official_site": has_official,
                "popularity_tier": popularity_tier,
            }
        except ImportError:
            logger.warning("[Search] duckduckgo_search not installed")
            return self._empty_result()
        except Exception as e:
            logger.warning("[Search] Search failed: %s", e)
            return self._empty_result()

    def enrich(self, tools):
        """Enrich tools with search data. Adds _search field."""
        if not tools:
            return tools
        tools_to_search = []
        for idx, tool in enumerate(tools):
            tool_id = tool.get("id", "")
            cached = self._cache.get(tool_id)
            if cached and self._is_cache_valid(cached):
                tool["_search"] = cached.get("data", self._empty_result())
            else:
                tools_to_search.append(tool)
        cache_hits = len(tools) - len(tools_to_search)
        if cache_hits > 0:
            logger.info("[Search] Cache hits: %d/%d", cache_hits, len(tools))
        if tools_to_search:
            logger.info("[Search] Searching %d tools via DuckDuckGo...", len(tools_to_search))
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {}
                for i, tool in enumerate(tools_to_search):
                    future = executor.submit(self._search_single_tool, tool)
                    futures[future] = i
                for future in as_completed(futures):
                    i = futures[future]
                    tool = tools_to_search[i]
                    tool_id = tool.get("id", "")
                    try:
                        search_data = future.result()
                    except Exception as e:
                        logger.warning("[Search] Unexpected error: %s", e)
                        search_data = self._empty_result()
                    tool["_search"] = search_data
                    self._cache[tool_id] = {
                        "timestamp": time.time(),
                        "data": search_data,
                    }
            self._save_cache()
        logger.info("[Search] Enrichment complete for %d tools", len(tools))
        return tools
