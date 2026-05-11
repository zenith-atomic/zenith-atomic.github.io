#!/usr/bin/env python3
"""Deep Reddit research for home services VOC."""
import json, requests, time, sys
from pathlib import Path

s = requests.Session()
s.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; NemoclawResearch/1.0)'})

OUT = Path('/home/ai/.openclaw/workspace/nemoclaw/research/02_reddit_voc/deep_dive2')
OUT.mkdir(parents=True, exist_ok=True)

SUBREDDITS = ['pestcontrol', 'hvacadvice', 'ProHVACR', 'plumbing', 'fieldService', 'smallbusiness']

PAIN_KEYWORDS = [
    'missed', 'call', 'phone', 'lead', 'customer', 'voicemail', 'schedule',
    'appointment', 'price', 'pricing', 'quote', 'estimate', 'review',
    'no-show', 'cancel', 'busy', 'overwhelm', 'answer',
    'response', 'slow', 'frustrat', 'complaint', 'negative',
    'unqualif', 'junk', 'cheap', 'expensive',
]

all_threads = []
for sub in SUBREDDITS:
    try:
        r = s.get(f'https://old.reddit.com/r/{sub}/hot/.json', params={'limit': 8}, timeout=15)
        threads = r.json().get('data', {}).get('children', [])
        for t in threads:
            p = t['data']
            sub_name = p['subreddit'].lower()
            score = p['score']
            comments = p['num_comments']
            title = p['title']
            text = p.get('selftext', '')
            pid = p['id']
            print(f"[{sub_name}] {score}pts {comments}c | {title[:70]}", file=sys.stderr)
            if score >= 2 and len(text) > 30:
                fname = OUT / f'{sub_name}_{pid}.json'
                with open(fname, 'w') as f:
                    json.dump(p, f, indent=2)
                all_threads.append({'sub': sub_name, 'title': title, 'score': score, 'text': text[:400]})
        time.sleep(1)
    except Exception as e:
        print(f"ERROR r/{sub}: {e}", file=sys.stderr)

print(f"\n=== COLLECTED {len(all_threads)} THREADS ===", file=sys.stderr)

print("\n=== PAIN SIGNALS BY SUBREDDIT ===\n")
for sub in sorted(set(t['sub'] for t in all_threads)):
    sub_threads = [t for t in all_threads if t['sub'] == sub]
    print(f"\n--- r/{sub} ({len(sub_threads)} threads) ---")
    for t in sub_threads:
        combined = (t['title'] + ' ' + t['text']).lower()
        pain_hits = [kw for kw in PAIN_KEYWORDS if kw in combined]
        if pain_hits:
            print(f"  [{t['score']}pts] {t['title'][:70]}")
            print(f"    Signals: {', '.join(pain_hits[:8])}")
