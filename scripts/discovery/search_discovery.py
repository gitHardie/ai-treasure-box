#!/usr/bin/env python3
import json, time, logging, re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

SEARCH_QUERIES = [
    "best AI tools 2026", "new AI tool launch",
    "AI productivity tools", "AI coding assistant",
    "AI image generator new", "open source AI tool github",
    "AI agent framework",
]

EXCLUDED_DOMAINS = {
    "theregister.com", "producthunt.com", "alternativeto.net",
    "en.wikipedia.org", "reddit.com", "news.ycombinator.com",
    "medium.com", "dev.to", "techcrunch.com", "venturebeat.com",
    "stackoverflow.com", "npmjs.com", "pypi.org", "huggingface.co",
    "youtube.com", "twitter.com", "x.com", "linkedin.com",
    "g2.com", "capterra.com", "toolify.ai", "futurepedia.io",
    "theresanaiforthat.com", "github.com", "arxit.org",
    "ai-bot.cn", "aibase.com", "ainavpro.com",
}


class SearchDiscovery:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.discovery_dir = data_dir / "discovery"
        self.discovery_dir.mkdir(parents=True, exist_ok=True)
        self.existing_urls = self._load_existing_urls()

    def _load_existing_urls(self) -> Set[str]:
        urls = set()
        master_file = self.data_dir / "master_tools.json"
        if master_file.exists():
            try:
                with open(master_file, "r", encoding="utf-8") as f:
                    tools = json.load(f)
                for tool in tools:
                    url = tool.get("url", "").lower().strip().rstrip("/")
                    if url: urls.add(urlparse(url).netloc)
            except Exception as e:
                logger.warning("Failed to load master: %s", e)
        manual_dir = self.data_dir / "manual"
        if manual_dir.exists():
            for json_file in manual_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    tools = data if isinstance(data, list) else [data]
                    for tool in tools:
                        url = tool.get("url", "").lower().strip().rstrip("/")
                        if url: urls.add(urlparse(url).netloc)
                except Exception: pass
        logger.info("Loaded %d existing URLs for dedup", len(urls))
        return urls

    def _is_excluded(self, url: str) -> bool:
        try:
            domain = urlparse(url).netloc.lower()
            if domain.startswith("www."): domain = domain[4:]
            for excluded in EXCLUDED_DOMAINS:
                if domain == excluded or domain.endswith("." + excluded):
                    return True
            if domain in self.existing_urls: return True
            return False
        except Exception: return True

    def search_and_discover(self) -> List[Dict]:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            logger.error("duckduckgo_search not installed")
            return []
        candidates = []
        seen_domains = set()
        with DDGS() as ddgs:
            for query in SEARCH_QUERIES:
                logger.info("Searching: %s", query)
                try:
                    results = list(ddgs.text(query, max_results=10))
                    for result in results:
                        url = result.get("href", "")
                        if not url or self._is_excluded(url): continue
                        dk = urlparse(url).netloc.lower()
                        if dk in seen_domains: continue
                        seen_domains.add(dk)
                        candidates.append({
                            "url": url, "title": result.get("title", ""),
                            "snippet": result.get("body", ""),
                            "source_query": query,
                            "discovered_at": datetime.now().isoformat(),
                        })
                    time.sleep(1)
                except Exception as e:
                    logger.warning("Search failed: %s", e)
                    continue
        logger.info("Discovered %d candidates", len(candidates))
        return candidates

    def save_candidates(self, candidates: List[Dict]):
        if not candidates:
            logger.info("No candidates to save")
            return
        today = datetime.now().strftime("%Y-%m-%d")
        output_file = self.discovery_dir / f"candidates_{today}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(candidates, f, ensure_ascii=False, indent=2)
        logger.info("Saved %d candidates to %s", len(candidates), output_file)


def main():
    logging.basicConfig(level=logging.INFO,
                       format="%(asctime)s [%(levelname)s] %(message)s")
    data_dir = Path(__file__).parent.parent.parent / "data"
    discovery = SearchDiscovery(data_dir)
    candidates = discovery.search_and_discover()
    discovery.save_candidates(candidates)
    print(f"Discovered {len(candidates)} candidates")


if __name__ == "__main__":
    main()
