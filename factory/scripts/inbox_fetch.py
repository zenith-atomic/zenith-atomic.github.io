#!/usr/bin/env python3
"""
Fetch a URL and extract clean text + title.
Uses stdlib only — no pip installs required.
Outputs JSON: {"title": "...", "text": "...", "url": "..."}
"""
import sys
import json
import re
import urllib.request
import urllib.error
import html.parser


class TextExtractor(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.title = ""
        self._in_title = False
        self._skip_tags = {"script", "style", "nav", "footer", "header", "noscript", "svg"}
        self._skip_depth = 0
        self._current_tag = ""

    def handle_starttag(self, tag, attrs):
        self._current_tag = tag
        if tag == "title":
            self._in_title = True
        if tag in self._skip_tags:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in self._skip_tags:
            self._skip_depth = max(0, self._skip_depth - 1)
        # Add paragraph breaks on block elements
        if tag in {"p", "div", "br", "h1", "h2", "h3", "h4", "li", "tr"}:
            self.text_parts.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self.text_parts.append(stripped)

    def get_text(self):
        raw = " ".join(self.text_parts)
        # Collapse multiple spaces and normalize newlines
        raw = re.sub(r" {2,}", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def fetch(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; OpenClaw-Inbox/1.0)",
        "Accept": "text/html,application/xhtml+xml,*/*",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        content_type = resp.headers.get("Content-Type", "")
        if "html" not in content_type and "text" not in content_type:
            return {"title": url, "text": f"[Non-HTML content: {content_type}]", "url": url}
        charset = "utf-8"
        if "charset=" in content_type:
            charset = content_type.split("charset=")[-1].strip().split(";")[0]
        raw_html = resp.read().decode(charset, errors="replace")

    parser = TextExtractor()
    parser.feed(raw_html)

    title = parser.title.strip() or url
    text = parser.get_text()

    # Truncate to ~8000 chars to stay within LLM context
    if len(text) > 8000:
        text = text[:8000] + "\n\n[truncated]"

    return {"title": title, "text": text, "url": url}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: inbox_fetch.py <url>"}))
        sys.exit(1)

    url = sys.argv[1]
    try:
        result = fetch(url)
        print(json.dumps(result))
    except urllib.error.URLError as e:
        print(json.dumps({"error": f"URL error: {e.reason}", "url": url}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e), "url": url}))
        sys.exit(1)
