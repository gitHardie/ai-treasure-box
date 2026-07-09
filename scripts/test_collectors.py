"""Test all collectors"""
import sys, json, os
sys.path.insert(0, '.')
from collectors.base import load_config

config = load_config()
global_config = config.get('global', {})

# Test HuggingFace
hf_config = [s for s in config['sources'] if s['id'] == 'huggingface-models'][0]
from collectors.huggingface import Collector as HFC
hf = HFC(hf_config, global_config)
r1 = hf.run()
print(f"HuggingFace: {r1['count']} items")

# Test HyperAI RSS
hy_config = [s for s in config['sources'] if s['id'] == 'hyperai'][0]
from collectors.hyperai import Collector as HRC
hy = HRC(hy_config, global_config)
r2 = hy.run()
print(f"HyperAI: {r2['count']} items")

# Show data quality
data_dir = '../data/tools'
for d in sorted(os.listdir(data_dir)):
    dp = os.path.join(data_dir, d)
    if not os.path.isdir(dp):
        continue
    for f in sorted(os.listdir(dp)):
        if not f.endswith('.json'):
            continue
        fp = os.path.join(dp, f)
        with open(fp) as jf:
            data = json.load(jf)
        print(f"\n--- {d}/{f} ({data['count']} items) ---")
        if data['items']:
            sample = data['items'][0]
            print(f"  Name: {sample.get('name', '?')}")
            print(f"  URL: {sample.get('url', '?')}")
            desc = sample.get('description', '?')[:100]
            print(f"  Desc: {desc}")
