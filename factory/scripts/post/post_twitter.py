#!/usr/bin/env python3
"""Post a tweet using Twitter API v2 with OAuth 1.0a."""
import sys
import json
import os

try:
    import requests
    from requests_oauthlib import OAuth1
except ImportError:
    print("ERROR: requests-oauthlib not installed. Run: pip3 install requests-oauthlib", file=sys.stderr)
    sys.exit(1)

def post_tweet(post_file):
    with open(post_file) as f:
        post = json.load(f)

    content = post.get("content", "")
    if not content:
        print("ERROR: post content is empty", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("TWITTER_API_KEY", "")
    api_secret = os.environ.get("TWITTER_API_SECRET", "")
    access_token = os.environ.get("TWITTER_ACCESS_TOKEN", "")
    access_secret = os.environ.get("TWITTER_ACCESS_SECRET", "")

    if not all([api_key, api_secret, access_token, access_secret]):
        print("ERROR: Twitter OAuth credentials not set in environment", file=sys.stderr)
        sys.exit(1)

    auth = OAuth1(api_key, api_secret, access_token, access_secret)

    # Handle threads: if format is "thread", split on "\n---\n" or numbered tweets
    format_type = post.get("format", "single")
    if format_type == "thread":
        tweets = [t.strip() for t in content.split("\n---\n") if t.strip()]
        if len(tweets) <= 1:
            # Try splitting on numbered lines like "1/ " or "Tweet 1:"
            import re
            parts = re.split(r'\n(?=\d+[/.])', content)
            tweets = [t.strip() for t in parts if t.strip()] or [content]
    else:
        tweets = [content]

    tweet_ids = []
    reply_to = None

    for tweet_text in tweets:
        payload = {"text": tweet_text[:280]}  # Enforce Twitter character limit
        if reply_to:
            payload["reply"] = {"in_reply_to_tweet_id": reply_to}

        resp = requests.post(
            "https://api.twitter.com/2/tweets",
            json=payload,
            auth=auth,
            timeout=15
        )

        if resp.status_code != 201:
            print(f"ERROR: Twitter API {resp.status_code}: {resp.text}", file=sys.stderr)
            sys.exit(1)

        tweet_id = resp.json()["data"]["id"]
        tweet_ids.append(tweet_id)
        reply_to = tweet_id

    # Return URL of first tweet
    # Would need TWITTER_USER_ID to build a proper URL; use generic format
    user_id = os.environ.get("TWITTER_USER_ID", "i")
    url = f"https://twitter.com/{user_id}/status/{tweet_ids[0]}"
    print(url)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: post_twitter.py <post-json-file>", file=sys.stderr)
        sys.exit(1)
    post_tweet(sys.argv[1])
