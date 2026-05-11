#!/usr/bin/env python3
"""Reddit market research pipeline.

What it does:
- resolves Reddit shortlinks / share links
- fetches the unofficial Reddit JSON via old.reddit.com
- extracts the post, comments, pain points, and recurring concept candidates
- writes a compact JSON + Markdown summary per thread
- appends concept evidence to a local JSONL store for cross-thread promotion

Usage:
  python3 reddit_market_research.py <reddit-url> [<reddit-url> ...]
  python3 reddit_market_research.py --save-dir research/reddit <reddit-url>
  python3 reddit_market_research.py --min-promote-threads 2 <reddit-url> ...
"""

from __future__ import annotations

import argparse
import collections
import html
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


USER_AGENT = "Mozilla/5.0 (compatible; OpenClaw/1.0; +https://openclaw.ai)"
DEFAULT_OUT_DIR = Path("/home/ai/.openclaw/workspace/research/reddit")
DEFAULT_CONCEPTS_JSONL = DEFAULT_OUT_DIR / "concepts.jsonl"

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "but", "by", "can", "could",
    "did", "do", "does", "doing", "for", "from", "had", "has", "have", "he", "her", "here",
    "him", "his", "how", "i", "if", "in", "into", "is", "it", "its", "just", "like",
    "me", "my", "no", "not", "of", "on", "or", "our", "out", "over", "she", "should",
    "so", "some", "than", "that", "the", "their", "them", "then", "there", "these", "they",
    "this", "those", "to", "too", "up", "us", "was", "we", "were", "what", "when", "where",
    "which", "who", "why", "will", "with", "would", "you", "your", "yours", "im", "i'm",
    "you're", "we're", "they're", "it's", "dont", "don't", "cant", "can't", "wont", "won't",
    "need", "needs", "really", "much", "many", "one", "two", "three", "also", "get", "got",
    "going", "still", "even", "than", "then", "now", "today", "time", "thing", "things",
    "reddit", "comment", "comments", "post", "posted", "thread", "user"
}

@dataclass
class Comment:
    author: str
    score: int | None
    body: str
    depth: int


@dataclass
class ThreadData:
    source_url: str
    resolved_url: str
    title: str
    subreddit: str
    author: str
    score: int | None
    created_utc: int | None
    flair: str | None
    body: str
    comments: list[Comment]
    thumbnail: str | None
    outbound_url: str | None



def resolve_url(url: str, timeout: int = 20) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.geturl()



def reddit_json_url(url: str, timeout: int = 20) -> str:
    parts = urlsplit(resolve_url(url, timeout=timeout).strip())
    path = parts.path or "/"
    if path.endswith(".json"):
        json_path = path
    else:
        json_path = path.rstrip("/") + ".json"
    netloc = parts.netloc.replace("www.reddit.com", "old.reddit.com")
    if netloc == parts.netloc:
        netloc = "old.reddit.com"
    return urlunsplit((parts.scheme, netloc, json_path, parts.query, parts.fragment))



def fetch_json(url: str, timeout: int = 20):
    req = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urlopen(req, timeout=timeout) as resp:
        content_type = resp.headers.get("content-type", "")
        raw = resp.read()
    text = raw.decode("utf-8", errors="replace")
    if "json" not in content_type.lower() and not text.lstrip().startswith("[") and not text.lstrip().startswith("{"):
        raise ValueError(f"Non-JSON response from {url}")
    return json.loads(text)



def iter_urls(values: Iterable[str]) -> Iterable[str]:
    for value in values:
        value = value.strip()
        if value.startswith("http://") or value.startswith("https://"):
            yield value
        else:
            raise ValueError(f"Invalid URL: {value}")



def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    return text[:80] or "reddit_thread"



def clean_text(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text



def extract_listing(data) -> dict:
    if isinstance(data, list):
        if not data:
            raise ValueError("Empty Reddit response")
        return data[0]
    return data



def collect_comments(children: Sequence[dict], depth: int = 0, max_depth: int = 2, limit: int = 40) -> list[Comment]:
    comments: list[Comment] = []
    for child in children or []:
        kind = child.get("kind")
        body = child.get("data", {})
        if kind != "t1":
            continue
        comment_body = clean_text(body.get("body", ""))
        if comment_body in {"[removed]", "[deleted]", ""}:
            replies = body.get("replies")
            if isinstance(replies, dict):
                nested = replies.get("data", {}).get("children", [])
                comments.extend(collect_comments(nested, depth + 1, max_depth, limit))
            continue
        comments.append(
            Comment(
                author=body.get("author", "[unknown]"),
                score=body.get("score"),
                body=comment_body,
                depth=depth,
            )
        )
        if len(comments) >= limit:
            break
        if depth < max_depth:
            replies = body.get("replies")
            if isinstance(replies, dict):
                nested = replies.get("data", {}).get("children", [])
                comments.extend(collect_comments(nested, depth + 1, max_depth, limit - len(comments)))
                if len(comments) >= limit:
                    break
    return comments



def extract_thread(url: str, timeout: int = 20, max_comments: int = 40, max_depth: int = 2) -> ThreadData:
    json_url = reddit_json_url(url, timeout=timeout)
    payload = fetch_json(json_url, timeout=timeout)
    listing = extract_listing(payload)
    post = listing.get("data", {}).get("children", [])[0].get("data", {})

    comments: list[Comment] = []
    if len(payload) > 1:
        comment_listing = payload[1]
        children = comment_listing.get("data", {}).get("children", [])
        comments = collect_comments(children, depth=0, max_depth=max_depth, limit=max_comments)

    return ThreadData(
        source_url=url,
        resolved_url=resolve_url(url, timeout=timeout),
        title=clean_text(post.get("title", "")),
        subreddit=post.get("subreddit", ""),
        author=post.get("author", ""),
        score=post.get("score"),
        created_utc=post.get("created_utc"),
        flair=post.get("link_flair_text"),
        body=clean_text(post.get("selftext", "")),
        comments=comments,
        thumbnail=post.get("thumbnail"),
        outbound_url=post.get("url_overridden_by_dest") or post.get("url"),
    )



def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9'\-]*", text.lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 2]



def phrase_counts(texts: Sequence[str], max_n: int = 3, focus_terms: Sequence[str] | None = None) -> collections.Counter[str]:
    counter: collections.Counter[str] = collections.Counter()
    focus_terms = [term.lower().strip() for term in (focus_terms or []) if term and term.strip()]
    for text in texts:
        toks = tokenize(text)
        for n in range(2, max_n + 1):
            for i in range(0, len(toks) - n + 1):
                phrase = " ".join(toks[i : i + n])
                if any(w in STOPWORDS for w in phrase.split()):
                    continue
                if len(phrase) < 4:
                    continue
                if focus_terms and not any(term in phrase for term in focus_terms):
                    continue
                counter[phrase] += 1
    return counter



def canonicalize_phrases(counter: collections.Counter[str]) -> list[dict]:
    items = []
    for phrase, count in counter.items():
        items.append({"concept": phrase, "count": count, "evidence": phrase})
    # collapse counts by canonical concept
    collapsed: dict[str, dict] = {}
    for item in items:
        key = item["concept"]
        bucket = collapsed.setdefault(key, {"concept": key, "count": 0, "evidence": []})
        bucket["count"] += item["count"]
        if item["evidence"] not in bucket["evidence"]:
            bucket["evidence"].append(item["evidence"])
    # sort by count desc then length
    return sorted(collapsed.values(), key=lambda x: (-x["count"], len(x["concept"])))



def pick_repeated_concepts(concepts: list[dict], threshold: int = 2) -> list[dict]:
    return [c for c in concepts if c["count"] >= threshold]



def build_summary(thread: ThreadData, concepts: list[dict], repeated: list[dict]) -> str:
    comments = thread.comments[:8]
    lines = []
    lines.append(f"# Reddit Research: {thread.title}")
    lines.append("")
    lines.append(f"- Source: {thread.source_url}")
    lines.append(f"- Resolved: {thread.resolved_url}")
    lines.append(f"- Subreddit: r/{thread.subreddit}")
    lines.append(f"- Author: {thread.author}")
    if thread.score is not None:
        lines.append(f"- Score: {thread.score}")
    if thread.flair:
        lines.append(f"- Flair: {thread.flair}")
    if thread.outbound_url:
        lines.append(f"- Link: {thread.outbound_url}")
    lines.append("")
    lines.append("## Summary")
    if thread.body:
        lines.append(thread.body[:500])
    else:
        lines.append("No body text.")
    lines.append("")
    lines.append("## Repeated Concepts")
    if repeated:
        for item in repeated[:12]:
            lines.append(f"- {item['concept']} ({item['count']})")
    else:
        lines.append("- (none above threshold)")
    lines.append("")
    lines.append("## Top Comments")
    if comments:
        for c in comments:
            prefix = f"- @{c.author}"
            if c.score is not None:
                prefix += f" [{c.score}]"
            lines.append(f"{prefix}: {c.body[:280]}")
    else:
        lines.append("- (no comments collected)")
    return "\n".join(lines).strip() + "\n"



def save_thread_outputs(thread: ThreadData, concepts: list[dict], repeated: list[dict], out_dir: Path) -> Tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(f"{thread.subreddit}_{thread.title}")
    json_path = out_dir / f"{slug}.json"
    md_path = out_dir / f"{slug}.md"

    payload = {
        "source_url": thread.source_url,
        "resolved_url": thread.resolved_url,
        "title": thread.title,
        "subreddit": thread.subreddit,
        "author": thread.author,
        "score": thread.score,
        "created_utc": thread.created_utc,
        "flair": thread.flair,
        "body": thread.body,
        "thumbnail": thread.thumbnail,
        "outbound_url": thread.outbound_url,
        "comments": [c.__dict__ for c in thread.comments],
        "concepts": concepts,
        "repeated_concepts": repeated,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    md_path.write_text(build_summary(thread, concepts, repeated))
    return json_path, md_path



def append_concepts_jsonl(store: Path, thread: ThreadData, concepts: list[dict]) -> None:
    store.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "source_url": thread.source_url,
        "resolved_url": thread.resolved_url,
        "title": thread.title,
        "subreddit": thread.subreddit,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "concepts": concepts,
    }
    with store.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")



def load_aggregate_counts(store: Path) -> Dict[str, set[str]]:
    by_concept: Dict[str, set[str]] = collections.defaultdict(set)
    if not store.exists():
        return by_concept
    with store.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            source_id = record.get("resolved_url") or record.get("source_url") or record.get("title") or "unknown"
            for concept in record.get("concepts", []):
                name = concept.get("concept")
                if name:
                    by_concept[name].add(source_id)
    return by_concept



def main() -> int:
    parser = argparse.ArgumentParser(description="Turn Reddit threads into lean market research artifacts.")
    parser.add_argument("urls", nargs="+", help="Reddit thread/share URLs")
    parser.add_argument("--save-dir", type=Path, default=DEFAULT_OUT_DIR, help=f"Output directory (default: {DEFAULT_OUT_DIR})")
    parser.add_argument("--aggregate-file", type=Path, default=DEFAULT_CONCEPTS_JSONL, help=f"JSONL store for repeated concepts (default: {DEFAULT_CONCEPTS_JSONL})")
    parser.add_argument("--max-comments", type=int, default=40, help="Max comments to collect per thread")
    parser.add_argument("--max-depth", type=int, default=2, help="Max comment tree depth to walk")
    parser.add_argument("--min-promote-threads", type=int, default=2, help="Minimum number of distinct threads before a concept is considered promoted")
    parser.add_argument("--timeout", type=int, default=20, help="Network timeout in seconds")
    parser.add_argument("--focus", type=str, default="", help="Optional comma-separated focus terms to narrow concept extraction")
    parser.add_argument("--no-aggregate", action="store_true", help="Do not append to the aggregate concept store")
    args = parser.parse_args()

    focus_terms = [term.strip() for term in args.focus.split(",") if term.strip()]

    exit_code = 0
    all_outputs: list[tuple[Path, Path]] = []
    for url in iter_urls(args.urls):
        try:
            thread = extract_thread(url, timeout=args.timeout, max_comments=args.max_comments, max_depth=args.max_depth)
            texts = [thread.title, thread.body] + [c.body for c in thread.comments]
            counts = phrase_counts(texts, max_n=3, focus_terms=focus_terms)
            concepts = canonicalize_phrases(counts)
            repeated = pick_repeated_concepts(concepts, threshold=2)

            if not args.no_aggregate:
                append_concepts_jsonl(args.aggregate_file, thread, concepts)

            json_path, md_path = save_thread_outputs(thread, concepts, repeated, args.save_dir)
            all_outputs.append((json_path, md_path))

            aggregate_counts = load_aggregate_counts(args.aggregate_file)
            promoted = [
                {"concept": name, "threads": len(threads)}
                for name, threads in aggregate_counts.items()
                if len(threads) >= args.min_promote_threads
            ]
            promoted.sort(key=lambda x: (-x["threads"], x["concept"]))

            print(f"saved {json_path}")
            print(f"saved {md_path}")
            if promoted:
                print("promote:")
                for item in promoted[:12]:
                    print(f"  - {item['concept']} ({item['threads']} threads)")
            else:
                print("promote: (none yet)")
        except (HTTPError, URLError, ValueError, json.JSONDecodeError) as e:
            exit_code = 1
            print(f"error for {url}: {e}", file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
