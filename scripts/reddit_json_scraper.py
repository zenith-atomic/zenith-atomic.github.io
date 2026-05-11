#!/usr/bin/env python3
"""Fetch Reddit's unofficial JSON by appending .json to Reddit page URLs.

Examples:
  python3 reddit_json_scraper.py https://www.reddit.com/r/python/
  python3 reddit_json_scraper.py --pretty https://www.reddit.com/r/python/
  python3 reddit_json_scraper.py --save-dir out https://www.reddit.com/r/python/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


USER_AGENT = "Mozilla/5.0 (compatible; OpenClaw/1.0; +https://openclaw.ai)"


def resolve_url(url: str, timeout: int = 20) -> str:
    """Follow Reddit redirects and return the final URL."""
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.geturl()


def reddit_json_url(url: str, timeout: int = 20) -> str:
    """Append .json to the resolved Reddit URL and route via old.reddit.com."""
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


def fetch(url: str, timeout: int = 20) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/plain,*/*"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def save_output(target_dir: Path, source_url: str, content: bytes) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    parts = urlsplit(source_url)
    slug = (parts.netloc + parts.path).strip("/").replace("/", "_") or "reddit"
    out_path = target_dir / f"{slug}.json"
    out_path.write_bytes(content)
    return out_path


def iter_urls(values: Iterable[str]) -> Iterable[str]:
    for value in values:
        if value.startswith("http://") or value.startswith("https://"):
            yield value
        else:
            raise ValueError(f"Invalid URL: {value}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Reddit unofficial JSON for one or more page URLs.")
    parser.add_argument("urls", nargs="+", help="Reddit page URLs")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the JSON response")
    parser.add_argument("--save-dir", type=Path, help="Optional directory to save each response as a .json file")
    parser.add_argument("--timeout", type=int, default=20, help="Request timeout in seconds (default: 20)")
    args = parser.parse_args()

    exit_code = 0
    for url in iter_urls(args.urls):
        json_url = reddit_json_url(url, timeout=args.timeout)
        try:
            content = fetch(json_url, timeout=args.timeout)
            if args.save_dir:
                out_path = save_output(args.save_dir, url, content)
                print(f"saved {out_path} <- {json_url}")
                continue

            if args.pretty:
                data = json.loads(content.decode("utf-8", errors="replace"))
                print(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                sys.stdout.buffer.write(content)
                if len(args.urls) > 1:
                    sys.stdout.buffer.write(b"\n")
        except HTTPError as e:
            exit_code = 1
            print(f"HTTP error for {json_url}: {e.code} {e.reason}", file=sys.stderr)
        except URLError as e:
            exit_code = 1
            print(f"Network error for {json_url}: {e.reason}", file=sys.stderr)
        except json.JSONDecodeError as e:
            exit_code = 1
            print(f"JSON parse error for {json_url}: {e}", file=sys.stderr)
        except ValueError as e:
            exit_code = 1
            print(str(e), file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
