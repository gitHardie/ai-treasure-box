"""Quick test for HN and ArXiv collectors"""
import sys, json, os
sys.path.insert(0, '.')
from collectors.base import load_config

config = load_config()
global_config = config.get('global', {})

# Test Hacker News
hn_config = [s for s in config['sources'] if s['id'] == 'hackernews-ai'][0]
from collectors.hackernews import Collector as HNC
hn = HNC(hn_config, global_config)
r1 = hn.run()
print(f"HackerNews: success={r1['success']}, count={r1.get('count', 0)}")
if r1.get('items') and len(r1.get('items', [])) > 0:
    print(f"  Sample: {r1['items'][0].get('name', '?')[:60]}")

# Test ArXiv
arxiv_config = [s for s in config['sources'] if s['id'] == 'arxiv-ai'][0]
from collectors.arxiv import Collector as AC
arxiv = AC(arxiv_config, global_config)
r2 = arxiv.run()
print(f"ArXiv: success={r2['success']}, count={r2.get('count', 0)}")
if r2.get('items') and len(r2.get('items', [])) > 0:
    print(f"  Sample: {r2['items'][0].get('name', '?')[:60]}")

# Summary
data_dir = '../data/tools'
total = 0
for d in sorted(os.listdir(data_dir)):
    dp = os.path.join(data_dir, d)
    if not os.path.isdir(dp):
        continue
    json_files = [f for f in os.listdir(dp) if f.endswith('.json')]
    if json_files:
        with open(os.path.join(dp, json_files[-1])) as f:
            data = json.load(f)
        count = data.get('count', 0)
        total += count
        print(f"  {d}: {count} items")

print(f"\nTotal collected: {total} items across all sources")
