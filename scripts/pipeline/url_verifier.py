"""
URL Verifier - unified URL verification and Logo resolution.

Runs after collector output and before AI analysis.
"""
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

AGGREGATOR_DOMAINS = {
    "producthunt.com", "aiww.com",
    "theresanaiforthat.com",
    "alternativeto.net", "github.com",
    "medium.com", "dev.to",
    "reddit.com", "news.ycombinator.com",
    "techcrunch.com", "venturebeat.com",
    "npmjs.com", "pypi.org",
    "reddit.com", "techcrunch.com",
    "huggingface.co",
    "youtube.com", "twitter.com",
    "x.com", "linkedin.com",
    "g2.com", "capterra.com",
    "stackoverflow.com",
    "en.wikipedia.org",
}

CACHE_TTL_SECONDS = 30 * 24 * 3600


class URLVerifier:
    """Unified URL verification and Logo resolution module."""

    def __init__(self, cache_dir=None):
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent.parent / "data" / "cache"
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / "url_verify_cache.json"
        self._cache = {}
        self._load_cache()

    def _load_cache(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as fh:
                    self._cache = json.load(fh)
                logger.info("[URLVerifier] Loaded cache with %d entries", len(self._cache))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("[URLVerifier] Failed to load cache: %s", e)
                self._cache = {}
        else:
            self._cache = {}

    def _save_cache(self):
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as fh:
                json.dump(self._cache, fh, ensure_ascii=False, indent=2)
            logger.info("[URLVerifier] Saved cache with %d entries", len(self._cache))
        except OSError as e:
            logger.warning("[URLVerifier] Failed to save cache: %s", e)

    def _is_cache_valid(self, entry):
        timestamp = entry.get("timestamp", 0)
        age = time.time() - timestamp
        return age < CACHE_TTL_SECONDS

    @staticmethod
    def _extract_domain(url):
        """Extract domain from URL (strip www prefix)."""
        if not url:
            return ""
        try:
            domain = urlparse(url).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return ""

    def _needs_verification(self, url):
        """Check if the URL points to an aggregator site."""
        domain = self._extract_domain(url)
        if not domain:
            return False
        for agg in AGGREGATOR_DOMAINS:
            if domain == agg or domain.endswith("." + agg):
                return True
        return False

    def _resolve_official_url(self, tool):
        """Try to resolve the real official URL for a product."""
        name = tool.get("name", "")
        # Strategy 1: Use search results from SearchEnricher
        search_data = tool.get("_search", {})
        top_results = search_data.get("top_results", [])
        for result in top_results:
            href = result.get("href", "")
            if href and not self._needs_verification(href):
                domain = self._extract_domain(href)
                if domain == "github.com":
                    continue
                logger.info("[URLVerifier] %s -> resolved from search: %s", name, href)
                return href
        # Strategy 2: DuckDuckGo targeted search
        try:
            from duckduckgo_search import DDGS
            query = chr(34) + name + chr(34) + " official website"
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
            for r in results:
                href = r.get("href", "")
                if href and not self._needs_verification(href):
                    domain = self._extract_domain(href)
                    if domain == "github.com":
                        continue
                    logger.info("[URLVerifier] %s -> DDG: %s", name, href)
                    return href
        except ImportError:
            logger.warning("[URLVerifier] duckduckgo_search not installed")
        except Exception as e:
            logger.warning("[URLVerifier] DDG search failed for %s: %s", name, e)
        return None

    @staticmethod
    def _fetch_logo(domain):
        """Get product logo URL via Clearbit."""
        if not domain:
            return ""
        return "https://logo.clearbit.com/" + domain

    def _verify_single_tool(self, tool):
        """Verify URL and logo for a single tool."""
        name = tool.get("name", "")
        original_url = tool.get("url", "")
        # Check cache
        cached = self._cache.get(name)
        if cached and self._is_cache_valid(cached):
            logger.info("[URLVerifier] %s: cache hit", name)
            return cached.get("data", {})
        result = {}
        if self._needs_verification(original_url):
            logger.info("[URLVerifier] %s: needs verification (%s)", name, original_url)
            official_url = self._resolve_official_url(tool)
            if official_url:
                domain = self._extract_domain(official_url)
                result = {"official_url": official_url, "logo_url": self._fetch_logo(domain), "domain": domain}
            else:
                domain = self._extract_domain(original_url)
                result = {"official_url": None, "logo_url": self._fetch_logo(domain), "domain": domain}
        else:
            domain = self._extract_domain(original_url)
            if domain:
                result = {"official_url": None, "logo_url": self._fetch_logo(domain), "domain": domain}
        self._cache[name] = {"timestamp": time.time(), "data": result}
        return result

    def verify_tools(self, tools, max_workers=3):
        """Main entry: concurrently verify all tools."""
        if not tools:
            return tools
        logger.info("[URLVerifier] Verifying URLs for %d tools...", len(tools))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for i, tool in enumerate(tools):
                future = executor.submit(self._verify_single_tool, tool)
                futures[future] = i
            updated_count = 0
            for future in as_completed(futures):
                i = futures[future]
                tool = tools[i]
                try:
                    result = future.result()
                except Exception as e:
                    logger.warning("[URLVerifier] Error: %s", e)
                    continue
                if not result:
                    continue
                if result.get("official_url"):
                    old_url = tool.get("url", "")
                    tool["url"] = result["official_url"]
                    logger.info("[URLVerifier] %s: %s -> %s", tool.get("name",""), old_url, result["official_url"])
                    updated_count += 1
                if result.get("logo_url"):
                    tool["logo_url"] = result["logo_url"]
        self._save_cache()
        logger.info("[URLVerifier] Complete: %d URLs updated out of %d tools", updated_count, len(tools))
        return tools

