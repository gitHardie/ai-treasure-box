"""
URL Verifier - unified URL verification and Logo resolution.

Runs after SearchEnricher and before ChinaDetector/AIAnalyzer.
Only replaces URLs from known tool aggregator sites (ProductHunt, TAAFT, etc.).
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

# Domains to skip when extracting links from aggregator pages
SCRAPER_SKIP_DOMAINS = {
    "theresanaiforthat", "taaft", "aiww",
    "youtube", "discord", "twitter", "x.com",
    "facebook", "linkedin", "reddit", "instagram",
    "tiktok", "pinterest", "snapchat", "tumblr",
    "github.com/topics", "apps.apple.com", "play.google.com",
    "microsoft.com/store", "chrome.google.com",
}

# 30-day cache for successful results
CACHE_TTL_SECONDS = 30 * 24 * 3600
# 1-day cache for failed results (allow retry)
CACHE_TTL_FAIL_SECONDS = 24 * 3600


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
        """Check if cache entry is still valid.
        
        Successful results use 30-day TTL, failed results use 1-day TTL.
        """
        timestamp = entry.get("timestamp", 0)
        age = time.time() - timestamp
        data = entry.get("data", {})
        if data.get("official_url"):
            return age < CACHE_TTL_SECONDS
        else:
            return age < CACHE_TTL_FAIL_SECONDS

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

    @staticmethod
    def _clean_url(url):
        """Strip tracking/UTM parameters from a URL, return homepage root."""
        try:
            parsed = urlparse(url)
            clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
            return clean
        except Exception:
            return url

    def _should_skip_scraper_link(self, url):
        """Check if a link found on an aggregator page should be skipped."""
        domain = self._extract_domain(url)
        if not domain:
            return True
        for skip in SCRAPER_SKIP_DOMAINS:
            if skip in domain:
                return True
        # Skip if it's any known aggregator
        if self._is_aggregator_url(url):
            return True
        return False

    # ------------------------------------------------------------------ #
    # Strategy 0: Direct page scraping for accessible aggregators        #
    # ------------------------------------------------------------------ #

    def _scrape_aiww(self, url):
        """Scrape AIWW page to extract official website URL.

        AIWW pages have a link with class 'a-url' pointing to the tool's
        official site (with utm_source=aiww tracking params).
        Includes retry logic for transient network failures.
        """
        try:
            import requests as req
            session = req.Session()
            session.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            })
            # Retry up to 2 times for transient failures
            r = None
            for attempt in range(3):
                try:
                    r = session.get(url, timeout=20, allow_redirects=True)
                    if r.status_code == 200:
                        break
                    logger.warning(
                        "[URLVerifier] AIWW HTTP %d for %s (attempt %d)",
                        r.status_code, url, attempt + 1,
                    )
                except (req.exceptions.ConnectionError, req.exceptions.Timeout) as e:
                    logger.warning(
                        "[URLVerifier] AIWW network error for %s (attempt %d): %s",
                        url, attempt + 1, e,
                    )
                    if attempt < 2:
                        time.sleep(2 * (attempt + 1))  # 2s, 4s backoff
            if r is None or r.status_code != 200:
                return None
            if r.status_code == 200:
                # Primary pattern: class containing 'a-url' with href
                match = re.search(
                    r'class="[^"]*a-url[^"]*"[^>]*href="([^"]+)"', r.text
                )
                if not match:
                    # Fallback: any link with utm_source=aiww
                    match = re.search(
                        r'href="(https?://[^"]*[?&]utm_source=aiww[^"]*)"',
                        r.text,
                    )
                if match:
                    raw_url = match.group(1)
                    clean_url = self._clean_url(raw_url)
                    if not self._is_false_positive(clean_url):
                        logger.info(
                            "[URLVerifier] AIWW scrape: %s -> %s", url, clean_url
                        )
                        return clean_url
        except ImportError:
            logger.warning("[URLVerifier] requests not installed for AIWW scrape")
        except Exception as e:
            logger.warning("[URLVerifier] AIWW scrape failed for %s: %s", url, e)
        return None

    def _scrape_taaft(self, url):
        """Scrape TAAFT page using cloudscraper to extract official website URL.

        TAAFT uses Cloudflare protection; cloudscraper may bypass it.
        External links with ref=taaft or utm_source=taaft point to the tool site.
        """
        try:
            import cloudscraper
            scraper = cloudscraper.create_scraper(
                browser={
                    "browser": "chrome",
                    "platform": "windows",
                    "desktop": True,
                }
            )
            r = scraper.get(url, timeout=20)
            if r.status_code == 200:
                # Find all external links
                links = re.findall(r'href="(https?://[^"]+)"', r.text)
                for link in links:
                    # Look for links with TAAFT tracking params
                    if "ref=taaft" in link or "utm_source=taaft" in link:
                        clean_url = self._clean_url(link)
                        if not self._should_skip_scraper_link(clean_url):
                            if not self._is_false_positive(clean_url):
                                logger.info(
                                    "[URLVerifier] TAAFT scrape: %s -> %s",
                                    url,
                                    clean_url,
                                )
                                return clean_url

                # Fallback: if no tracking-param links found, look for the
                # "Visit website" / "Get this tool" button pattern
                visit_match = re.search(
                    r'(?:visit|get\s+this|go\s+to|official)\s*(?:website|site|tool)?'
                    r'[^>]*href="(https?://[^"]+)"',
                    r.text,
                    re.IGNORECASE,
                )
                if visit_match:
                    clean_url = self._clean_url(visit_match.group(1))
                    if (
                        not self._should_skip_scraper_link(clean_url)
                        and not self._is_false_positive(clean_url)
                    ):
                        logger.info(
                            "[URLVerifier] TAAFT scrape (fallback): %s -> %s",
                            url,
                            clean_url,
                        )
                        return clean_url
            else:
                logger.warning(
                    "[URLVerifier] TAAFT scrape HTTP %d for %s", r.status_code, url
                )
        except ImportError:
            logger.warning("[URLVerifier] cloudscraper not installed")
        except Exception as e:
            logger.warning("[URLVerifier] TAAFT scrape failed for %s: %s", url, e)
        return None

    # ------------------------------------------------------------------ #
    # Main resolution pipeline                                           #
    # ------------------------------------------------------------------ #

    def _resolve_official_url(self, tool):
        """Try to resolve the real official URL for a product from aggregator."""
        name = tool.get("name", "")
        url = tool.get("url", "")
        domain = self._extract_domain(url)

        # ---- Strategy 0a: Direct scrape for AIWW (high success rate) ----
        if "aiww.com" in domain:
            result = self._scrape_aiww(url)
            if result:
                return result

        # ---- Strategy 0b: Direct scrape for TAAFT (cloudscraper) --------
        if "theresanaiforthat.com" in domain or "theresanaiforthat.ai" in domain:
            result = self._scrape_taaft(url)
            if result:
                return result

        # ---- Strategy 1: Use search results from SearchEnricher ----------
        search_data = tool.get("_search", {})
        top_results = search_data.get("top_results", [])
        for result in top_results:
            href = result.get("href", "")
            if href and not self._is_aggregator_url(href) and not self._is_false_positive(href):
                logger.info("[URLVerifier] %s -> resolved from search: %s", name, href)
                return href

        # ---- Strategy 2: Targeted DuckDuckGo search ----------------------
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS

            # Use a more specific query excluding known aggregators
            query = '"' + name + '" official website -producthunt -theresanaiforthat -aiww -toolify'
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=8))
            for r in results:
                href = r.get("href", "")
                if href and not self._is_aggregator_url(href) and not self._is_false_positive(href):
                    logger.info("[URLVerifier] %s -> DDG: %s", name, href)
                    return href

            # Second attempt with different query
            query2 = '"' + name + '" site -producthunt -theresanaiforthat -aiww'
            with DDGS() as ddgs:
                results2 = list(ddgs.text(query2, max_results=5))
            for r in results2:
                href = r.get("href", "")
                if href and not self._is_aggregator_url(href) and not self._is_false_positive(href):
                    logger.info("[URLVerifier] %s -> DDG (alt): %s", name, href)
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

    def _cache_key(self, tool):
        """Generate a cache key that includes the source domain to avoid collisions.
        
        Different sources (AIWW, TAAFT, PH) for the same tool name should have
        separate cache entries, since scraping success varies by source.
        """
        name = tool.get("name", "")
        original_url = tool.get("url", "")
        source_domain = self._extract_domain(original_url)
        return f"{name}|{source_domain}"

    def _verify_single_tool(self, tool):
        """Verify URL and logo for a single tool."""
        name = tool.get("name", "")
        original_url = tool.get("url", "")
        cache_key = self._cache_key(tool)

        # Check cache - but allow retry for failed results
        cached = self._cache.get(cache_key)
        if cached and self._is_cache_valid(cached):
            data = cached.get("data", {})
            # If cache hit but failed (no official_url for aggregator URL), allow retry
            if data.get("official_url") or not self._is_aggregator_url(original_url):
                return data
            # Failed result - check if we should use shorter TTL
            age = time.time() - cached.get("timestamp", 0)
            if age < CACHE_TTL_FAIL_SECONDS:
                return data
            # Past short TTL - retry

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

        self._cache[cache_key] = {"timestamp": time.time(), "data": result}
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
