#!/usr/bin/env python3
"""Scrape Reddit for home services VOC data."""
import sys, time
sys.path.insert(0, '/home/ai/.openclaw/workspace/scripts')
from reddit_json_scraper import *

OUT = Path('/home/ai/.openclaw/workspace/nemoclaw/research/02_reddit_voc/raw')
OUT.mkdir(parents=True, exist_ok=True)

SUBREDDITS = ['pestcontrol', 'HVAC', 'Plumbing', 'fieldService', 'smallbusiness', 'entrepreneur']
FOCUS = 'pest control,hvac,plumber,scheduling,appointment,missed calls,voicemails,pricing,reviews,lead quality,no-shows,callback,quote'

for sub in SUBREDDITS:
    url = f'https://www.reddit.com/r/{sub}/'
    out_file = OUT / f'{sub}.json'
    print(f'Scraping r/{sub}...', file=sys.stderr)
    try:
        json_url = reddit_json_url(url)
        data = fetch(json_url)
        parsed = json.loads(data)
        threads = parsed['data']['children'] if 'data' in parsed else []
        saved = 0
        for t in threads[:5]:
            post = t.get('data', {})
            score = post.get('score', 0)
            n_c = post.get('num_comments', 0)
            if score >= 3 and n_c >= 2:
                with open(OUT / f'{sub}_{post["id"]}.json', 'w') as f:
                    json.dump(post, f, indent=2)
                saved += 1
        print(f'  r/{sub}: {saved}/{len(threads)} threads saved', file=sys.stderr)
    except Exception as e:
        print(f'  r/{sub} ERROR: {e}', file=sys.stderr)
    time.sleep(2)

print('DONE', file=sys.stderr)
