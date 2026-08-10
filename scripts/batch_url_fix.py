#!/usr/bin/env python3
"""
Batch URL fix for existing tools with aggregator URLs.
Supports resuming from cache (skips already-verified tools).
Runs DDG search with rate limiting to avoid timeouts.
"""
import json, sys, time, logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("batch_url_fix")

DATA_DIR = Path(__file__).parent.parent / "data"
sys.path.insert(0, str(Path(__file__).parent))
from pipeline.url_verifier import URLVerifier

def main():
    verifier = URLVerifier(cache_dir=DATA_DIR / "cache")
    
    # Load master DB
    master_path = DATA_DIR / "master_tools.json"
    with open(master_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    tools = data.get("tools", {})
    
    # Find tools with aggregator URLs
    agg_tools = []
    for tid, t in tools.items():
        if not isinstance(t, dict):
            continue
        url = t.get("url", "")
        if verifier._is_aggregator_url(url):
            agg_tools.append(t)
    
    logger.info(f"Found {len(agg_tools)} tools with aggregator URLs")
    
    # Filter out already-cached tools
    uncached = []
    for t in agg_tools:
        name = t.get("name", "")
        cached = verifier._cache.get(name)
        if cached and verifier._is_cache_valid(cached):
            # Already verified, apply cached result
            result = cached.get("data", {})
            if result.get("official_url"):
                t["url"] = result["official_url"]
            if result.get("logo_url"):
                t["logo_url"] = result["logo_url"]
        else:
            uncached.append(t)
    
    logger.info(f"Already cached: {len(agg_tools) - len(uncached)}, need search: {len(uncached)}")
    
    if not uncached:
        logger.info("All tools already cached, saving and exiting")
    else:
        # Process in batches of 20 with delays between batches
        batch_size = 20
        total_fixed = 0
        total_failed = 0
        
        for i in range(0, len(uncached), batch_size):
            batch = uncached[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(uncached) + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} tools)...")
            
            try:
                verifier.verify_tools(batch, max_workers=3)
            except Exception as e:
                logger.warning(f"Batch {batch_num} error: {e}")
            
            # Count results
            for t in batch:
                if verifier._is_aggregator_url(t.get("url", "")):
                    total_failed += 1
                else:
                    total_fixed += 1
            
            # Save after each batch (checkpoint)
            with open(master_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            verifier._save_cache()
            
            logger.info(f"Batch {batch_num} done. Fixed: {total_fixed}, Remaining: {total_failed}")
            
            # Rate limit: 2 second delay between batches
            if i + batch_size < len(uncached):
                time.sleep(2)
    
    # Final stats
    remaining_agg = sum(1 for t in tools.values() if isinstance(t, dict) and verifier._is_aggregator_url(t.get("url", "")))
    logger.info(f"=== FINAL: {len(tools) - remaining_agg} tools with official URLs, {remaining_agg} still with aggregator URLs ===")
    
    # Update site/tools.json too
    update_site_tools(data, verifier)

def update_site_tools(data, verifier):
    """Update site/tools.json with fixed URLs"""
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
    
    logger.info(f"Updated site/tools.json: {updated} fields changed")

if __name__ == "__main__":
    main()
