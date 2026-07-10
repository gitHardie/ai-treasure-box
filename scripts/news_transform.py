#!/usr/bin/env python3
"""
News data transformer: converts agent-collab JSON format to website format.

Input:  data/news/daily/YYYY-MM-DD/{morning,evening}.json
Output: data/news/latest.json  (for ticker + list)
        data/news/articles.json (for article detail page)
"""

import json
import os
import glob
from datetime import datetime, timezone
from pathlib import Path

CATEGORY_LABELS = {
    'model_release': '模型发布',
    'funding': '融资收购',
    'product_launch': '产品发布',
    'tech_breakthrough': '技术突破',
    'industry_policy': '行业政策',
    'application': '应用落地',
    'open_source': '开源动态',
    'other': '其他',
}

REPO_ROOT = Path(__file__).resolve().parent.parent
NEWS_DIR = REPO_ROOT / 'data' / 'news'
DAILY_DIR = NEWS_DIR / 'daily'


def load_daily_files():
    """Load all daily briefing JSON files."""
    all_articles = []
    if not DAILY_DIR.exists():
        return all_articles

    for json_file in sorted(DAILY_DIR.glob('**/*.json'), reverse=True):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            date_str = data.get('date', '')
            session = data.get('session', '')
            articles = data.get('articles', [])

            for i, article in enumerate(articles):
                article_id = f"{date_str}-{session}-{i+1:03d}"
                article['id'] = article_id
                article['category_label'] = CATEGORY_LABELS.get(
                    article.get('category', 'other'), '其他'
                )
                all_articles.append(article)

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Failed to parse {json_file}: {e}")
            continue

    return all_articles


def merge_with_legacy():
    """Merge new format with legacy curated.json if it exists."""
    legacy_path = NEWS_DIR / 'curated.json'
    if not legacy_path.exists():
        return []

    try:
        with open(legacy_path, 'r', encoding='utf-8') as f:
            legacy = json.load(f)

        items = legacy.get('items', [])
        # Convert legacy items to new format
        converted = []
        for i, item in enumerate(items):
            converted.append({
                'id': f"legacy-{i+1:03d}",
                'title': item.get('title', ''),
                'summary': item.get('description', ''),
                'content_markdown': item.get('description', ''),
                'sources': [{'name': item.get('source', ''), 'url': item.get('url', '')}],
                'published_at': item.get('published_at', ''),
                'tags': item.get('tags', []),
                'category': 'other',
                'category_label': '其他',
            })
        return converted
    except Exception:
        return []


def build_latest_json(articles):
    """Build latest.json for ticker and list view."""
    items = []
    for article in articles:
        source_names = ', '.join(s.get('name', '') for s in article.get('sources', []))
        items.append({
            'title': article['title'],
            'url': article.get('sources', [{}])[0].get('url', ''),
            'description': article.get('summary', ''),
            'source': source_names or article.get('sources', [{}])[0].get('name', ''),
            'published_at': article.get('published_at', article.get('original_time', '')),
            'collected_at': datetime.now(timezone.utc).isoformat(),
            'tags': article.get('tags', []),
            'category': article.get('category', 'other'),
            'category_label': article.get('category_label', '其他'),
            'article_id': article.get('id', ''),
            'summary': article.get('summary', ''),
        })

    # Sort by published_at descending
    items.sort(key=lambda x: x.get('published_at', ''), reverse=True)

    return {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'source': 'multi-source',
        'source_name': '多源综合',
        'count': len(items),
        'items': items,
    }


def build_articles_json(articles):
    """Build articles.json for article detail page."""
    # Ensure published_at is always set
    for a in articles:
        if not a.get('published_at') and a.get('original_time'):
            a['published_at'] = a['original_time']
    
    sorted_articles = sorted(
        articles,
        key=lambda x: x.get('published_at', ''),
        reverse=True
    )

    return {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'count': len(sorted_articles),
        'articles': sorted_articles,
    }


def main():
    print("📰 News Transform: Starting...")

    # Load new format articles
    articles = load_daily_files()
    print(f"  Found {len(articles)} articles from daily files")

    # Merge with legacy data
    legacy = merge_with_legacy()
    if legacy:
        print(f"  Merged {len(legacy)} legacy articles")
        articles.extend(legacy)

    if not articles:
        print("  No articles found, skipping")
        return

    # Build output files
    latest = build_latest_json(articles)
    articles_data = build_articles_json(articles)

    # Write latest.json
    latest_path = REPO_ROOT / "data" / "site" / "news" / "latest.json"
    with open(latest_path, 'w', encoding='utf-8') as f:
        json.dump(latest, f, ensure_ascii=False, indent=2)
    print(f"  ✅ Wrote {latest_path}")

    # Write articles.json
    articles_path = REPO_ROOT / "data" / "site" / "news" / "articles.json"
    with open(articles_path, 'w', encoding='utf-8') as f:
        json.dump(articles_data, f, ensure_ascii=False, indent=2)
    print(f"  ✅ Wrote {articles_path}")

    print(f"📰 News Transform: Done! {len(articles)} total articles")


if __name__ == '__main__':
    main()
