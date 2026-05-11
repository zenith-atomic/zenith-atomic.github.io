#!/usr/bin/env python3
"""Ingest tweets from Nitter (Twitter/X front-end) into the wiki.

Usage:
  python3 twitter_ingest.py <username> [limit]
  python3 twitter_ingest.py <username> --tweet-id <id>
  python3 twitter_ingest.py <username> --save-json <output_dir>

Examples:
  python3 twitter_ingest.py elonmusk 10
  python3 twitter_ingest.py BarackObama 5
"""
import argparse, json, re, sys, time
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

USER_AGENT = "Mozilla/5.0 (compatible; NemoclawResearch/1.0)"

def fetch(url, timeout=20):
    req = Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'text/html,*/*'})
    with urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', errors='replace')

def parse_tweets(html, username, limit=10):
    tweets = []
    items = re.split(r'<div class="timeline-item[^"]*"', html)
    for item in items[1:limit+1]:
        try:
            time_match = re.search(r'<span class="tweet-date[^"]*"><a[^>]*title="([^"]*)"', item)
            timestamp = time_match.group(1) if time_match else ''
            id_match = re.search(r'href="/{}/status/(\d+)"'.format(username), item)
            tweet_id = id_match.group(1) if id_match else ''
            text_match = re.search(r'<div class="tweet-content[^"]*">(.*?)</div>', item, re.DOTALL)
            text = re.sub(r'<[^>]+>', '', text_match.group(1)).strip() if text_match else ''
            if not text:
                continue
            def get_stat(pat):
                m = re.search(pat, item)
                return m.group(1).strip() if m else '0'
            likes = get_stat(r'class="tweet-stat[^"]*">.*?(\d[\d,]*)')
            retweets = get_stat(r'class="tweet-stat[^"]*">.*?(\d[\d,]*)')
            replies = get_stat(r'class="tweet-stat[^"]*">.*?(\d[\d,]*)')
            url = f'https://twitter.com/{username}/status/{tweet_id}' if tweet_id else ''
            tweets.append({'id': tweet_id, 'timestamp': timestamp, 'text': text,
                           'likes': likes, 'retweets': retweets, 'replies': replies, 'url': url})
        except:
            continue
    return tweets

def tweets_to_md(tweets, username):
    lines = ['# @{} -- Twitter Archive'.format(username), '',
             '> Collected via Nitter | {}'.format(datetime.now().strftime('%Y-%m-%d')), '',
             'Source: https://twitter.com/{}'.format(username), '', '---', '']
    for t in tweets:
        date_str = t['timestamp'].split(' · ')[0] if t['timestamp'] else 'Unknown date'
        lines += ['', '## {}'.format(date_str), '', t['text'], '']
        stats = []
        if t['likes'] != '0': stats.append('❤ ' + t['likes'])
        if t['retweets'] != '0': stats.append('🔁 ' + t['retweets'])
        if t['replies'] != '0': stats.append('💬 ' + t['replies'])
        if stats: lines.append('  ' + ' · '.join(stats))
        if t['url']: lines.append('[🔗 Tweet](' + t['url'] + ')')
        lines += ['', '---']
    return '\n'.join(lines)

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('username', nargs='?')
    p.add_argument('limit', nargs='?', type=int, default=10)
    p.add_argument('--tweet-id')
    p.add_argument('--save-json')
    args = p.parse_args()
    if not args.username:
        print('Usage: twitter_ingest.py <username> [limit] [--tweet-id <id>] [--save-json <dir>]')
        sys.exit(1)
    username = args.username.lstrip('@')
    url = 'https://nitter.net/{}{}'.format(
        username,
        '/status/' + args.tweet_id if args.tweet_id else '')
    print('Fetching https://nitter.net/{}...'.format(username), file=sys.stderr)
    try:
        html = fetch(url)
    except HTTPError as e:
        print('HTTP Error: {} {}'.format(e.code, e.reason), file=sys.stderr)
        sys.exit(1)
    tweets = parse_tweets(html, username, args.limit)
    if not tweets:
        print('No tweets found.', file=sys.stderr)
        sys.exit(1)
    print('Found {} tweets'.format(len(tweets)), file=sys.stderr)
    if args.save_json:
        out = Path(args.save_json)
        out.mkdir(parents=True, exist_ok=True)
        for t in tweets:
            with open(out / '{}_{}.json'.format(username, t['id']), 'w') as f:
                json.dump(t, f, indent=2)
    print(tweets_to_md(tweets, username))
