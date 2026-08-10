#!/usr/bin/env python3
"""
Batch URL fix for existing tools with aggregator URLs.

Processing order (optimised for success rate):
  1. AIWW tools        – direct scraping, ~100 % success
  2. TAAFT tools       – cloudscraper, partial success
  3. ProductHunt tools – DDG search, variable success

Supports resuming from cache (skips already-verified tools).
Rate-limited to avoid bans; saves checkpoint after every batch.
"""
import json, sys, time, logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("batch_url_fix")

DATA_DIR = Path(__file__).parent.parent / "data"
sys.path.insert(0, str(Path(__file__).parent))
from pipeline.url_verifier import URLVerifier


def _classify_tools(verifier, tools):
    """Partition aggregator tools into AIWW / TAAFT / Other buckets."""
    aiww, taaft, other = [], [], []
    for tid, t in tools.items():
        if not isinstance(t, dict):
            continue
        url = t.get("url", "")
        if not verifier._is_aggregator_url(url):
            continue
        domain = verifier._extract_domain(url)
        if "aiww.com" in domain:
            aiww.append(t)
        elif "theresanaiforthat" in domain:
            taaft.append(t)
        else:
            other.append(t)
    return aiww, taaft, other


def _apply_cached(verifier, tool_list):
    """Apply cached results; return list of uncached tools."""
    uncached = []
    for t in tool_list:
        name = t.get("name", "")
        cached = verifier._cache.get(name)
        if cached and verifier._is_cache_valid(cached):
            result = cached.get("data", {})
            if result.get("official_url"):
                t["url"] = result["official_url"]
            if result.get("logo_url"):
                t["logo_url"] = result["logo_url"]
        else:
            uncached.append(t)
    return uncached


def _save_checkpoint(master_path, data, verifier):
    """Persist current state so progress is not lost."""
    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    verifier._save_cache()


def _process_batch(verifier, batch, batch_label, delay=3.0):
    """Run verifier on a single batch with rate limiting."""
    logger.info("  Processing %s (%d tools)...", batch_label, len(batch))
    try:
        verifier.verify_tools(batch, max_workers=2)
    except Exception as e:
        logger.warning("  Batch error (%s): %s", batch_label, e)
    # Small delay after each batch to avoid rate limits
    time.sleep(delay)


def _count_results(verifier, tool_list):
    fixed = sum(
        1 for t in tool_list
        if not verifier._is_aggregator_url(t.get("url", ""))
    )
    return fixed, len(tool_list) - fixed


def main():
    verifier = URLVerifier(cache_dir=DATA_DIR / "cache")

    # Load master DB
    master_path = DATA_DIR / "master_tools.json"
    with open(master_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tools = data.get("tools", {})

    # Classify
    aiww_tools, taaft_tools, other_tools = _classify_tools(verifier, tools)
    total_agg = len(aiww_tools) + len(taaft_tools) + len(other_tools)
    logger.info(
        "Aggregator tools: AIWW=%d, TAAFT=%d, Other(PH)=%d  (total=%d)",
        len(aiww_tools), len(taaft_tools), len(other_tools), total_agg,
    )

    # Filter cached
    aiww_uncached = _apply_cached(verifier, aiww_tools)
    taaft_uncached = _apply_cached(verifier, taaft_tools)
    other_uncached = _apply_cached(verifier, other_tools)

    logger.info(
        "After cache: AIWW=%d, TAAFT=%d, Other=%d need processing",
        len(aiww_uncached), len(taaft_uncached), len(other_uncached),
    )

    total_to_process = len(aiww_uncached) + len(taaft_uncached) + len(other_uncached)
    total_fixed = 0
    total_failed = 0

    # ---- Phase 1: AIWW (fast, reliable) ----
    if aiww_uncached:
        logger.info("=== Phase 1: AIWW scraping (%d tools) ===", len(aiww_uncached))
        batch_size = 25
        for i in range(0, len(aiww_uncached), batch_size):
            batch = aiww_uncached[i:i + batch_size]
            _process_batch(verifier, batch, f"AIWW batch {i // batch_size + 1}", delay=1.5)
            fixed, failed = _count_results(verifier, batch)
            total_fixed += fixed
            total_failed += failed
            _save_checkpoint(master_path, data, verifier)
            logger.info(
                "  AIWW progress: fixed=%d, remaining=%d", total_fixed, total_failed,
            )

    # ---- Phase 2: TAAFT (cloudscraper, partial success) ----
    if taaft_uncached:
        logger.info("=== Phase 2: TAAFT scraping (%d tools) ===", len(taaft_uncached))
        batch_size = 15  # smaller batches – cloudscraper is fragile
        for i in range(0, len(taaft_uncached), batch_size):
            batch = taaft_uncached[i:i + batch_size]
            _process_batch(verifier, batch, f"TAAFT batch {i // batch_size + 1}", delay=4.0)
            fixed, failed = _count_results(verifier, batch)
            total_fixed += fixed
            total_failed += failed
            _save_checkpoint(master_path, data, verifier)
            logger.info(
                "  TAAFT progress: fixed=%d, remaining=%d", total_fixed, total_failed,
            )

    # ---- Phase 3: Other (PH etc. – DDG search) ----
    if other_uncached:
        logger.info("=== Phase 3: Other/DDG search (%d tools) ===", len(other_uncached))
        batch_size = 10  # smallest batches – DDG is rate-limited
        for i in range(0, len(other_uncached), batch_size):
            batch = other_uncached[i:i + batch_size]
            _process_batch(verifier, batch, f"Other batch {i // batch_size + 1}", delay=5.0)
            fixed, failed = _count_results(verifier, batch)
            total_fixed += fixed
            total_failed += failed
            _save_checkpoint(master_path, data, verifier)
            logger.info(
                "  Other progress: fixed=%d, remaining=%d", total_fixed, total_failed,
            )

    # ---- Final stats ----
    remaining_agg = sum(
        1 for t in tools.values()
        if isinstance(t, dict) and verifier._is_aggregator_url(t.get("url", ""))
    )
    logger.info(
        "=== FINAL: %d tools with official URLs, %d still with aggregator URLs "
        "(out of %d total) ===",
        len(tools) - remaining_agg, remaining_agg, len(tools),
    )

    # Update site/tools.json too
    update_site_tools(data, verifier)


def update_site_tools(data, verifier):
    """Update site/tools.json with fixed URLs."""
    site_path = DATA_DIR / "site" / "tools.json"
    if not site_path.exists():
        return

    with open(site_path, "r", encoding="utf-8") as f:
        site_tools = json.load(f)

    # Build lookup from master DB
    master_lookup = {}
    for tid, t in data.get("tools", {}).items():
        if isinstance(t, dict) and t.get("name"):
            master_lookup[t["name"]] = t

    updated = 0
    for st in site_tools:
        if not isinstance(st, dict):
            continue
        name = st.get("name", "")
        if name in master_lookup:
            mt = master_lookup[name]
            if st.get("url") != mt.get("url") and mt.get("url"):
                st["url"] = mt["url"]
                updated += 1
            if st.get("logo_url") != mt.get("logo_url") and mt.get("logo_url"):
                st["logo_url"] = mt["logo_url"]
                updated += 1

    with open(site_path, "w", encoding="utf-8") as f:
        json.dump(site_tools, f, ensure_ascii=False, indent=2)

    logger.info("Updated site/tools.json: %d fields changed", updated)


if __name__ == "__main__":
    main()
