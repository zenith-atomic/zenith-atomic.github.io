# Tool Guidance — Research Agent

## IMPORTANT: search tool hierarchy

`web_search` is rate-limited and blocked by bot detection. **Never use it as primary.** Use it only if the browser search fails twice.

## Primary: Steel MCP browser tools

These run inside the Steel headless Chrome container — real browser fingerprint, bypasses bot detection.

- `search` — **use this first for all queries**. Performs a real browser search.
- `navigate` — go directly to a URL (creator profiles, trending pages, social feeds)
- `scroll_down` / `scroll_up` — read more content on a page
- `click` — click a button or link
- `go_back` — navigate back
- `save_unmarked_screenshot` — capture the current page visually

Good search patterns for `search`:
- "[topic] trending [platform] [month year]"
- "top [niche] creators viral content 2026"
- "[competitor name] content strategy recent"
- "best performing hooks [niche] [platform]"

## Secondary: web_fetch
Quick content reads for articles, newsletters, or JSON feeds — no JS rendering needed.

## Last resort: web_search
Only use if `search` (Steel) fails. Do not retry more than once — fall back to `web_fetch` or `navigate` instead.

## read / write / exec
You do not need these. Your output is text only.
