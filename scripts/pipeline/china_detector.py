"""
China Tool Detector - 通过抓取产品首页检测是否国内工具。

检测信号：
1. ICP备案号（铁证）
2. 页面语言（html lang="zh"）
3. 中文字符占比

结果缓存7天，并发抓取。
"""
import json
import re
import time
import logging
import requests
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# ICP备案号正则
ICP_RE = re.compile(
    r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤川青藏琼宁]'
    r'ICP[备证]?\d{6,14}号?[-\d]*'
)

CHINA_TLDS = {'.cn', '.com.cn', '.net.cn', '.org.cn'}
CACHE_TTL = 7 * 86400  # 7 days


def _detect_single(url: str) -> dict:
    """检测单个URL是否国内工具"""
    domain = urlparse(url).netloc.lower()
    signals = []
    likely = False

    # 1. 中国TLD
    if any(domain.endswith(tld) for tld in CHINA_TLDS):
        signals.append('cn_tld')
        likely = True

    # 2. 抓取首页
    try:
        resp = requests.get(url, timeout=5, allow_redirects=True,
                            headers={'User-Agent': 'Mozilla/5.0 (compatible; AIBotDetector/1.0)'})
        html = resp.text[:8000]

        # ICP备案号
        if ICP_RE.search(html):
            signals.append('icp')
            likely = True

        # html lang
        lang_match = re.search(r'<html[^>]+lang=["\']?([^"\'>\s]+)', html, re.IGNORECASE)
        if lang_match:
            lang = lang_match.group(1).lower()
            if lang.startswith('zh'):
                signals.append('lang_zh')
                likely = True

        # 中文字符占比
        text_only = re.sub(r'<[^>]+>', '', html)
        if len(text_only) > 30:
            chinese_chars = len(re.findall(r'[一-鿿]', text_only))
            ratio = chinese_chars / len(text_only)
            if ratio > 0.08:
                signals.append(f'zh_{ratio:.0%}')
                likely = True

    except Exception as e:
        logger.debug(f"[ChinaDetect] {url}: {e}")

    return {'likely_china': likely, 'china_signals': signals}


def _load_cache(cache_file: Path) -> dict:
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cache(cache_file: Path, cache: dict):
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"[ChinaDetect] Cache save failed: {e}")


def enrich_china_signals(tools: list, max_workers: int = 5) -> list:
    """
    并发检测所有工具的国内属性，结果写入 tool['likely_china'] 和 tool['china_signals']。
    使用磁盘缓存避免重复抓取。
    """
    if not tools:
        return tools

    data_dir = Path(__file__).parent.parent.parent / "data" / "cache"
    cache_file = data_dir / "china_detect_cache.json"
    cache = _load_cache(cache_file)
    now = time.time()

    # 分类：缓存命中 vs 需要抓取
    need_fetch = []
    for tool in tools:
        url = tool.get('url', '')
        domain = urlparse(url).netloc.lower()
        cached = cache.get(domain)
        if cached and (now - cached.get('ts', 0)) < CACHE_TTL:
            tool['likely_china'] = cached['data']['likely_china']
            tool['china_signals'] = cached['data']['china_signals']
        else:
            need_fetch.append((tool, domain))

    if not need_fetch:
        logger.info(f"[ChinaDetect] All {len(tools)} tools from cache")
        return tools

    logger.info(f"[ChinaDetect] Fetching {len(need_fetch)}/{len(tools)} homepages...")

    # 并发抓取
    updated = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for tool, domain in need_fetch:
            futures[executor.submit(_detect_single, tool.get('url', ''))] = (tool, domain)

        for future in as_completed(futures):
            tool, domain = futures[future]
            try:
                result = future.result()
            except Exception as e:
                logger.warning(f"[ChinaDetect] Error: {e}")
                result = {'likely_china': False, 'china_signals': []}

            tool['likely_china'] = result['likely_china']
            tool['china_signals'] = result['china_signals']
            cache[domain] = {'ts': now, 'data': result}
            updated[domain] = result

    _save_cache(cache_file, cache)

    china_count = sum(1 for t in tools if t.get('likely_china'))
    logger.info(f"[ChinaDetect] Done: {china_count}/{len(tools)} likely Chinese")
    return tools
