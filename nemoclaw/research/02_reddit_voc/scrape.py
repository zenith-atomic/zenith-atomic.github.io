#!/usr/bin/env python3
import json, time, sys
from pathlib import Path
from urllib.request import Request, urlopen

USER_AGENT = "Mozilla/5.0 (compatible; OpenClaw/1.0; +https://openclaw.ai)"

def reddit_json_url(url, timeout=20):
    from urllib.parse import urlsplit, urlunsplit
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as r:
        base = r.geturl().strip()
    parts = urlsplit(base)
    path = parts.path.rstrip("/") + ".json"
    netloc = parts.netloc.replace("www.reddit.com", "old.reddit.com")
    return urlunsplit((parts.scheme, netloc, path, parts.query, ""))

def fetch(url, timeout=20):
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(req, timeout=timeout) as r:
        return r.read()

OUT = Path('/home/ai/.openclaw/workspace/nemoclaw/research/02_reddit_voc/raw')
OUT.mkdir(parents=True, exist_ok=True)

SUBREDDITS = ['pestcontrol', 'HVAC', 'Plumbing', 'fieldService', 'smallbusiness', 'entrepreneur']

for sub in SUBREDDITS:
    url = f'https://www.reddit.com/r/{sub}/'
    print(f'Scraping r/{sub}...', file=sys.stderr)
    try:
        jurl = reddit_json_url(url)
        data = json.loads(fetch(jurl))
        threads = data.get('data', {}).get('children', [])
        saved = 0
        for t in threads[:5]:
            post = t.get('data', {})
            if post.get('score', 0) >= 3 and post.get('num_comments', 0) >= 2:
                fname = OUT / f'{sub}_{post["id"]}.json'
                with open(fname, 'w') as f:
                    json.dump(post, f, indent=2)
                saved += 1
        print(f'  r/{sub}: {saved}/{len(threads)} saved', file=sys.stderr)
    except Exception as e:
        print(f'  r/{sub} ERROR: {e}', file=sys.stderr)
    time.sleep(2)

print('DONE', file=sys.stderr)
