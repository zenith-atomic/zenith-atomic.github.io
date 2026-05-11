#!/usr/bin/env python3
"""Deep Reddit research for home services VOC - targeted search."""
import json, time, sys, requests
from pathlib import Path

SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; NemoclawResearch/1.0)'})

OUT = Path('/home/ai/.openclaw/workspace/nemoclaw/research/02_reddit_voc/deep_dive')
OUT.mkdir(parents=True, exist_ok=True)

SEARCH_TERMS = [
    'missed calls AND (pest OR hvac OR plumbing)',
    'answering service AND (hvac OR pest control)',
    'lead quality AND (contractor OR service business)',
    'scheduling AND (field service OR technician)',
    'phone answering AND small business',
    'customer response time AND service business',
    'voicemail AND (business OR customer)',
    'no show AND appointment AND service',
    'review management AND local business',
    'call tracking AND small business marketing',
]

def json_get(url, params=None, timeout=20):
    r = SESSION.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()

print(f'Total threads to analyze: 30')
print(f'Output: {OUT}')

collected = []

for term in SEARCH_TERMS:
    try:
        print(f'\nSearching: {term}', file=sys.stderr)
        data = json_get(
            'https://old.reddit.com/search/.json',
            params={'q': term, 'limit': 3, 'sort': 'relevance', 't': 'month'}
        )
        threads = data.get('data', {}).get('children', [])
        for t in threads[:3]:
            post = t['data']
            sub = post.get('subreddit', '').lower()
            title = post.get('title', '')
            score = post.get('score', 0)
            comments = post.get('num_comments', 0)
            permalink = post.get('permalink', '')
            print(f'  [{sub}] {score}pts | {comments}c | {title[:60]}', file=sys.stderr)
            if score >= 2 and comments >= 1:
                fname = OUT / f'{sub}_{post["id"]}.json'
                with open(fname, 'w') as f:
                    json.dump(post, f, indent=2)
                collected.append({'sub': sub, 'title': title, 'score': score, 'comments': comments, 'permalink': permalink})
        time.sleep(1.5)
    except Exception as e:
        print(f'  ERROR: {e}', file=sys.stderr)

print(f'\nCollected {len(collected)} threads')
print(f'Saved to {OUT}')
