#!/usr/bin/env python3
"""firecrawl.py — self-hosted Firecrawl replacement (no API key required).

Uses requests + stdlib html.parser to fetch URLs and convert to clean markdown.
Steel Browser (localhost:3000) is used as a fallback for JS-heavy pages.

Subcommands:
  scrape  <url>              Fetch one URL → markdown (stdout or --out file)
  batch   <url> [url ...]    Fetch multiple URLs → JSON array of results
  crawl   <url>              Recursively crawl a site → JSON manifest

Examples:
  python3 firecrawl.py scrape https://example.com
  python3 firecrawl.py scrape https://example.com --out result.md
  python3 firecrawl.py scrape https://example.com --format json
  python3 firecrawl.py batch https://a.com https://b.com --out results.json
  python3 firecrawl.py crawl https://example.com --depth 2 --limit 20
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.robotparser
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    sys.exit("requests is required: python3 -m pip install requests")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
STEEL_BASE_URL = "http://127.0.0.1:3000"
DEFAULT_TIMEOUT = 20
DEFAULT_DEPTH = 2
DEFAULT_LIMIT = 50

# Tags whose entire subtree we drop (boilerplate)
_DROP_TAGS = {
    "script", "style", "noscript", "iframe", "object", "embed",
    "nav", "header", "footer", "aside", "form", "button", "select",
    "input", "textarea", "label", "svg", "canvas", "figure",
    "advertisement", "ads", "cookie-banner",
}

# Tags we convert to markdown constructs
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_BLOCK_TAGS = {
    "p", "div", "section", "article", "main", "details", "summary",
    "li", "dt", "dd", "blockquote", "pre", "table", "thead", "tbody",
    "tfoot", "tr", "th", "td", "hr", "br",
}
_INLINE_TAGS = {"a", "strong", "b", "em", "i", "u", "s", "code", "span", "mark"}


# ---------------------------------------------------------------------------
# HTTP session
# ---------------------------------------------------------------------------

def _make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session


_SESSION: Optional[requests.Session] = None


def session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = _make_session()
    return _SESSION


# ---------------------------------------------------------------------------
# Steel Browser fallback (JS-heavy pages)
# ---------------------------------------------------------------------------

def _steel_available() -> bool:
    try:
        r = requests.get(f"{STEEL_BASE_URL}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def _fetch_via_steel(url: str) -> Optional[str]:
    """Use Steel Browser CDP to get fully-rendered page HTML."""
    try:
        r = requests.post(
            f"{STEEL_BASE_URL}/scrape",
            json={"url": url, "waitFor": 2000},
            timeout=30,
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("html") or data.get("content")
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# HTML → Markdown converter
# ---------------------------------------------------------------------------

class _HTMLToMarkdown(HTMLParser):
    """Single-pass HTML parser that emits markdown."""

    def __init__(self, base_url: str = "") -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self._out: list[str] = []
        self._depth: dict[str, int] = {}
        self._drop_depth = 0          # nesting depth inside a dropped tag
        self._link_href: Optional[str] = None
        self._link_text: list[str] = []
        self._in_link = False
        self._in_code = False
        self._in_pre = False
        self._in_table = False
        self._list_stack: list[str] = []   # 'ul' or 'ol'
        self._ol_counters: list[int] = []
        self._td_buf: list[str] = []
        self._th_buf: list[str] = []
        self._row_cells: list[str] = []
        self._is_header_row = False
        self._table_has_header = False
        self._pending_newlines = 0

    # helpers ----------------------------------------------------------------

    def _flush_newlines(self) -> None:
        if self._pending_newlines:
            self._out.append("\n" * self._pending_newlines)
            self._pending_newlines = 0

    def _ensure_blank(self) -> None:
        self._pending_newlines = max(self._pending_newlines, 2)

    def _ensure_newline(self) -> None:
        self._pending_newlines = max(self._pending_newlines, 1)

    def _emit(self, text: str) -> None:
        if not text:
            return
        self._flush_newlines()
        self._out.append(text)

    def _resolve(self, href: str) -> str:
        if href and self.base_url:
            return urljoin(self.base_url, href)
        return href

    # interface --------------------------------------------------------------

    def handle_starttag(self, tag: str, attrs_list: list) -> None:
        tag = tag.lower()
        attrs = dict(attrs_list)

        # Inside a dropped subtree — keep counting nesting
        if self._drop_depth > 0:
            if tag in _DROP_TAGS:
                self._drop_depth += 1
            return

        # Enter a dropped subtree
        if tag in _DROP_TAGS:
            self._drop_depth += 1
            return

        # Track nesting for all other tags
        self._depth[tag] = self._depth.get(tag, 0) + 1

        if tag in _HEADING_TAGS:
            level = int(tag[1])
            self._ensure_blank()
            self._emit("#" * level + " ")

        elif tag == "p":
            self._ensure_blank()

        elif tag == "br":
            self._ensure_newline()

        elif tag == "hr":
            self._ensure_blank()
            self._emit("---")
            self._ensure_blank()

        elif tag == "a":
            href = attrs.get("href", "")
            self._link_href = self._resolve(href)
            self._link_text = []
            self._in_link = True

        elif tag in ("strong", "b"):
            self._emit("**")

        elif tag in ("em", "i"):
            self._emit("*")

        elif tag in ("u", "s"):
            pass  # ignore

        elif tag == "code" and not self._in_pre:
            self._in_code = True
            self._emit("`")

        elif tag == "pre":
            self._in_pre = True
            self._ensure_blank()
            self._emit("```")
            self._ensure_newline()

        elif tag == "blockquote":
            self._ensure_blank()

        elif tag in ("ul", "ol"):
            self._list_stack.append(tag)
            if tag == "ol":
                self._ol_counters.append(0)
            self._ensure_newline()

        elif tag == "li":
            self._ensure_newline()
            indent = "  " * (len(self._list_stack) - 1)
            if self._list_stack and self._list_stack[-1] == "ol":
                self._ol_counters[-1] += 1
                self._emit(f"{indent}{self._ol_counters[-1]}. ")
            else:
                self._emit(f"{indent}- ")

        elif tag == "table":
            self._in_table = True
            self._ensure_blank()
            self._table_has_header = False

        elif tag in ("thead",):
            self._is_header_row = True

        elif tag == "tr":
            self._row_cells = []

        elif tag in ("th", "td"):
            self._is_header_row = self._is_header_row or tag == "th"

        elif tag in ("div", "section", "article", "main"):
            self._ensure_newline()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if self._drop_depth > 0:
            if tag in _DROP_TAGS:
                self._drop_depth -= 1
            return

        self._depth[tag] = max(0, self._depth.get(tag, 0) - 1)

        if tag in _HEADING_TAGS:
            self._ensure_blank()

        elif tag == "p":
            self._ensure_blank()

        elif tag == "a":
            self._in_link = False
            text = "".join(self._link_text).strip()
            href = self._link_href or ""
            if href and href.startswith(("http", "/")):
                if text:
                    self._emit(f"[{text}]({href})")
                else:
                    self._emit(href)
            else:
                self._emit(text)
            self._link_href = None
            self._link_text = []

        elif tag in ("strong", "b"):
            self._emit("**")

        elif tag in ("em", "i"):
            self._emit("*")

        elif tag == "code" and not self._in_pre:
            self._in_code = False
            self._emit("`")

        elif tag == "pre":
            self._in_pre = False
            self._ensure_newline()
            self._emit("```")
            self._ensure_blank()

        elif tag == "blockquote":
            self._ensure_blank()

        elif tag in ("ul", "ol"):
            if self._list_stack:
                popped = self._list_stack.pop()
                if popped == "ol" and self._ol_counters:
                    self._ol_counters.pop()
            self._ensure_newline()

        elif tag == "li":
            self._ensure_newline()

        elif tag in ("th", "td"):
            cell_text = "".join(self._out).strip() if not self._row_cells else ""
            # Capture via buffer trick: grab since last separator
            # Simple approach: accumulate into row_cells from handle_data
            pass

        elif tag == "tr":
            if self._row_cells:
                line = "| " + " | ".join(c.strip() for c in self._row_cells) + " |"
                self._emit(line)
                self._ensure_newline()
                if self._is_header_row and not self._table_has_header:
                    sep = "| " + " | ".join("---" for _ in self._row_cells) + " |"
                    self._emit(sep)
                    self._ensure_newline()
                    self._table_has_header = True
            self._row_cells = []
            self._is_header_row = False

        elif tag == "table":
            self._in_table = False
            self._ensure_blank()

        elif tag in ("thead", "tbody", "tfoot"):
            pass

        elif tag in ("div", "section", "article", "main"):
            self._ensure_newline()

    def handle_data(self, data: str) -> None:
        if self._drop_depth > 0:
            return
        if self._in_pre:
            self._flush_newlines()
            self._out.append(data)
            return

        text = re.sub(r"\s+", " ", data)
        if not text.strip():
            if text and self._out and not self._out[-1].endswith("\n"):
                self._out.append(" ")
            return

        if self._in_link:
            self._link_text.append(text)
            return

        if self._in_table and self._depth.get("td", 0) > 0:
            self._row_cells.append(text)
            return
        if self._in_table and self._depth.get("th", 0) > 0:
            self._row_cells.append(text)
            return

        if self._depth.get("blockquote", 0) > 0:
            self._flush_newlines()
            for line in text.splitlines():
                self._out.append(f"> {line}\n")
            return

        self._emit(text)

    def result(self) -> str:
        raw = "".join(self._out)
        # Collapse excessive blank lines
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def html_to_markdown(html: str, base_url: str = "") -> str:
    parser = _HTMLToMarkdown(base_url=base_url)
    parser.feed(html)
    return parser.result()


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------

class _MetaExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.description = ""
        self.author = ""
        self.og_title = ""
        self.og_description = ""
        self.og_image = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs_list: list) -> None:
        tag = tag.lower()
        attrs = dict(attrs_list)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = attrs.get("name", "").lower()
            prop = attrs.get("property", "").lower()
            content = attrs.get("content", "")
            if name == "description":
                self.description = content
            elif name == "author":
                self.author = content
            elif prop == "og:title":
                self.og_title = content
            elif prop == "og:description":
                self.og_description = content
            elif prop == "og:image":
                self.og_image = content

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False


def _extract_meta(html: str) -> dict:
    ext = _MetaExtractor()
    ext.feed(html)
    return {
        "title": (ext.og_title or ext.title or "").strip(),
        "description": (ext.og_description or ext.description or "").strip(),
        "author": ext.author.strip(),
        "og_image": ext.og_image.strip(),
    }


# ---------------------------------------------------------------------------
# Core fetch
# ---------------------------------------------------------------------------

def fetch_url(url: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Fetch a URL and return {url, markdown, metadata, html, status_code, error}."""
    result: dict = {
        "url": url,
        "markdown": "",
        "metadata": {},
        "status_code": None,
        "error": None,
        "via": "requests",
    }
    try:
        resp = session().get(url, timeout=timeout, allow_redirects=True)
        result["status_code"] = resp.status_code
        result["url"] = resp.url  # final URL after redirects

        content_type = resp.headers.get("content-type", "")
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            result["error"] = f"non-HTML content-type: {content_type}"
            return result

        html = resp.text
        meta = _extract_meta(html)
        markdown = html_to_markdown(html, base_url=result["url"])

        # If markdown is suspiciously short, try Steel Browser
        if len(markdown) < 200 and _steel_available():
            steel_html = _fetch_via_steel(result["url"])
            if steel_html and len(steel_html) > len(html):
                html = steel_html
                markdown = html_to_markdown(html, base_url=result["url"])
                result["via"] = "steel-browser"

        result["metadata"] = meta
        result["markdown"] = markdown

    except requests.exceptions.Timeout:
        result["error"] = f"timeout after {timeout}s"
    except requests.exceptions.TooManyRedirects:
        result["error"] = "too many redirects"
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"connection error: {e}"
    except Exception as e:
        result["error"] = str(e)

    return result


# ---------------------------------------------------------------------------
# robots.txt
# ---------------------------------------------------------------------------

_robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}


def _can_fetch(url: str) -> bool:
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    if base not in _robots_cache:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"{base}/robots.txt")
        try:
            rp.read()
        except Exception:
            rp = None  # type: ignore
        _robots_cache[base] = rp  # type: ignore
    rp = _robots_cache[base]
    if rp is None:
        return True
    return rp.can_fetch(USER_AGENT, url)


# ---------------------------------------------------------------------------
# Link extractor (for crawl)
# ---------------------------------------------------------------------------

class _LinkExtractor(HTMLParser):
    def __init__(self, base_url: str, same_domain: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.same_domain = same_domain
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs_list: list) -> None:
        if tag.lower() != "a":
            return
        attrs = dict(attrs_list)
        href = attrs.get("href", "").strip()
        if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
            return
        full = urljoin(self.base_url, href)
        parsed = urlparse(full)
        if parsed.netloc == self.same_domain:
            # Strip fragment
            clean = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))
            self.links.append(clean)


def _extract_links(html: str, base_url: str, same_domain: str) -> list[str]:
    ext = _LinkExtractor(base_url=base_url, same_domain=same_domain)
    ext.feed(html)
    return list(dict.fromkeys(ext.links))  # dedup, preserve order


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_scrape(args: argparse.Namespace) -> int:
    result = fetch_url(args.url, timeout=args.timeout)
    if result["error"]:
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1

    if args.format == "json":
        output = json.dumps(result, indent=2, ensure_ascii=False)
    else:
        meta = result["metadata"]
        lines = []
        if meta.get("title"):
            lines.append(f"# {meta['title']}\n")
        if meta.get("description"):
            lines.append(f"_{meta['description']}_\n")
        if meta.get("author"):
            lines.append(f"**Author:** {meta['author']}\n")
        lines.append(f"**URL:** {result['url']}\n")
        lines.append("")
        lines.append(result["markdown"])
        output = "\n".join(lines)

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Saved to {args.out} ({len(output)} chars, via {result['via']})")
    else:
        sys.stdout.write(output)
        sys.stdout.write("\n")
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    results = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futures = {ex.submit(fetch_url, url, args.timeout): url for url in args.urls}
        for fut in as_completed(futures):
            results.append(fut.result())

    output = json.dumps(results, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Saved {len(results)} results to {args.out}")
    else:
        sys.stdout.write(output)
        sys.stdout.write("\n")

    errors = [r for r in results if r["error"]]
    if errors:
        print(f"{len(errors)} error(s):", file=sys.stderr)
        for r in errors:
            print(f"  {r['url']}: {r['error']}", file=sys.stderr)
        return 1
    return 0


def cmd_crawl(args: argparse.Namespace) -> int:
    start_url = args.url
    parsed_start = urlparse(start_url)
    same_domain = parsed_start.netloc

    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(start_url, 0)])
    manifest: list[dict] = []
    skipped: list[str] = []

    print(f"Crawling {start_url} (depth={args.depth}, limit={args.limit})…", file=sys.stderr)

    while queue and len(manifest) < args.limit:
        url, depth = queue.popleft()
        if url in visited:
            continue
        visited.add(url)

        if not _can_fetch(url):
            skipped.append(url)
            print(f"  [robots.txt blocked] {url}", file=sys.stderr)
            continue

        print(f"  [{depth}] {url}", file=sys.stderr)
        result = fetch_url(url, timeout=args.timeout)

        if result["error"]:
            print(f"    Error: {result['error']}", file=sys.stderr)
            continue

        manifest.append(result)

        if depth < args.depth:
            # Extract links from raw html (re-fetch would be wasteful; re-parse markdown links)
            resp = session().get(url, timeout=args.timeout)
            links = _extract_links(resp.text, base_url=url, same_domain=same_domain)
            for link in links:
                if link not in visited:
                    queue.append((link, depth + 1))

        if args.delay:
            time.sleep(args.delay)

    output_data = {
        "start_url": start_url,
        "pages_crawled": len(manifest),
        "pages_skipped": len(skipped),
        "results": manifest,
    }
    output = json.dumps(output_data, indent=2, ensure_ascii=False)

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Saved {len(manifest)} pages to {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(output)
        sys.stdout.write("\n")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Self-hosted Firecrawl replacement — web scraping to markdown.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # scrape
    p_scrape = sub.add_parser("scrape", help="Fetch one URL and convert to markdown")
    p_scrape.add_argument("url", help="URL to fetch")
    p_scrape.add_argument("--out", "-o", help="Output file path (default: stdout)")
    p_scrape.add_argument("--format", choices=["markdown", "json"], default="markdown",
                          help="Output format (default: markdown)")
    p_scrape.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)

    # batch
    p_batch = sub.add_parser("batch", help="Fetch multiple URLs → JSON array")
    p_batch.add_argument("urls", nargs="+", help="URLs to fetch")
    p_batch.add_argument("--out", "-o", help="Output JSON file")
    p_batch.add_argument("--concurrency", type=int, default=5)
    p_batch.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)

    # crawl
    p_crawl = sub.add_parser("crawl", help="Recursively crawl a site")
    p_crawl.add_argument("url", help="Start URL")
    p_crawl.add_argument("--depth", type=int, default=DEFAULT_DEPTH,
                         help=f"Max link depth (default: {DEFAULT_DEPTH})")
    p_crawl.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                         help=f"Max pages to crawl (default: {DEFAULT_LIMIT})")
    p_crawl.add_argument("--out", "-o", help="Output JSON file")
    p_crawl.add_argument("--delay", type=float, default=0.5,
                         help="Seconds between requests (default: 0.5)")
    p_crawl.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.cmd == "scrape":
        return cmd_scrape(args)
    elif args.cmd == "batch":
        return cmd_batch(args)
    elif args.cmd == "crawl":
        return cmd_crawl(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
