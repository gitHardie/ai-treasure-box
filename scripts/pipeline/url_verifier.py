"""
URL Verifier - unified URL verification and Logo resolution.

Runs after SearchEnricher and before ChinaDetector/AIAnalyzer.
Only replaces URLs from known tool aggregator sites (ProductHunt, AIWW, TAAFT, etc.).
GitHub repos are treated as valid official sites for open-source projects.
"""
import json
import logging
import time
import re
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Only tool aggregator sites - URLs from these need to be resolved to official sites
TOOL_AGGREGATOR_DOMAINS = {
    "producthunt.com",
    "aiww.com",
    "theresanaiforthat.com",
    "alternativeto.net",
    "futurepedia.io",
    "topai.tools",
    "toolify.ai",
    "aitools.fyi",
    "theresanaiforthat.ai",
}

# Domains that should NEVER appear as resolved official URLs
# (common false positives from search engines)
FALSE_POSITIVE_DOMAINS = {
    "google.com", "www.google.com",
    "merriam-webster.com", "www.merriam-webster.com",
    "dictionary.com", "www.dictionary.com",
    "wikipedia.org", "en.wikipedia.org",
    "amazon.com", "www.amazon.com",
    "youtube.com", "www.youtube.com",
    "twitter.com", "x.com",
    "linkedin.com", "www.linkedin.com",
    "facebook.com", "www.facebook.com",
    "reddit.com", "www.reddit.com",
    "quora.com", "www.quora.com",
    "medium.com",
    "reuters.com", "www.reuters.com",
    "britannica.com",
    "cambridge.org",
    "support.google.com",
    "espncricinfo.com",
    "tripadvisor.com",
    "visitgalway.ie",
    "primevideo.com", "www.primevideo.com",
    "thewindowsclub.com",
    "tasteofhome.com",
    "brastemp.com.br",
    "mercadolibre.com",
    "openbible.info",
    "books.google.com",
    "get.adobe.com",
    "code.visualstudio.com",
    "en.m.wikipedia.org",
}

# 30-day cache
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

    def _is_aggregator_url(self, url):
        """Check if the URL points to a known tool aggregator site."""
        domain = self._extract_domain(url)
        if not domain:
            return False
        for agg in TOOL_AGGREGATOR_DOMAINS:
            if domain == agg or domain.endswith("." + agg):
                return True
        return False

    def _is_false_positive(self, url):
        """Check if the resolved URL is a known false positive."""
        if not url:
            return True
        domain = self._extract_domain(url)
        if not domain:
            return True
        for fp in FALSE_POSITIVE_DOMAINS:
            if domain == fp or domain.endswith("." + fp):
                return True
        # Also reject URLs with path depth > 3 (likely not homepages)
        path = urlparse(url).path.rstrip("/")
        if path.count("/") > 2:
            return True
        return False

    def _resolve_official_url(self, tool):
        """Try to resolve the real official URL for a product from aggregator."""
        name = tool.get("name", "")
        
        # Strategy 1: Use search results from SearchEnricher (already cached)
        search_data = tool.get("_search", {})
        top_results = search_data.get("top_results", [])
        for result in top_results:
            href = result.get("href", "")
            if href and not self._is_aggregator_url(href) and not self._is_false_positive(href):
                domain = self._extract_domain(href)
                # Skip GitHub - for OSS projects, the original GitHub URL is fine
                if domain == "github.com":
                    continue
                logger.info("[URLVerifier] %s -> resolved from search: %s", name, href)
                return href

        # Strategy 2: Targeted DuckDuckGo search with stricter filtering
        try:
            from duckduckgo_search import DDGS
            query = '"' + name + '" official website'
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
            for r in results:
                href = r.get("href", "")
                if href and not self._is_aggregator_url(href) and not self._is_false_positive(href):
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
            return cached.get("data", {})

        result = {}
        domain = self._extract_domain(original_url)

        if self._is_aggregator_url(original_url):
            # This URL points to an aggregator - try to find real official URL
            logger.info("[URLVerifier] %s: aggregator URL detected (%s)", name, original_url)
            official_url = self._resolve_official_url(tool)
            if official_url:
                official_domain = self._extract_domain(official_url)
                result = {
                    "official_url": official_url,
                    "logo_url": self._fetch_logo(official_domain),
                    "domain": official_domain,
                }
                logger.info("[URLVerifier] %s: %s -> %s", name, original_url, official_url)
            else:
                # Could not resolve - keep original but still set logo
                result = {
                    "official_url": None,
                    "logo_url": self._fetch_logo(domain) if domain else "",
                    "domain": domain,
                }
        else:
            # URL is not from aggregator - keep as-is, just set logo
            if domain:
                result = {
                    "official_url": None,
                    "logo_url": self._fetch_logo(domain),
                    "domain": domain,
                }

        self._cache[name] = {"timestamp": time.time(), "data": result}
        return result

    def verify_tools(self, tools, max_workers=3):
        """Main entry: concurrently verify all tools."""
        if not tools:
            return tools

        logger.info("[URLVerifier] Verifying URLs for %d tools...", len(tools))

        # First pass: count how many need verification
        agg_count = sum(1 for t in tools if self._is_aggregator_url(t.get("url", "")))
        logger.info("[URLVerifier] %d tools from aggregator sites need URL resolution", agg_count)

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
                    tool["url"] = result["official_url"]
                    updated_count += 1

                if result.get("logo_url"):
                    tool["logo_url"] = result["logo_url"]

        self._save_cache()
        logger.info("[URLVerifier] Complete: %d URLs resolved out of %d aggregator tools (%d total)",
                     updated_count, agg_count, len(tools))
        return tools
