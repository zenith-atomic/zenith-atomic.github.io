# Runbook — Research Agent Web Scraping

Load when research agent hits a JS-heavy or gated site.

## Sequence

1. **Detect JS-gating.** Page returns only CSS/JS or "not yet built" 404 → mark JS-heavy, switch strategy.
2. **Try firecrawl first:** `python3 /home/ai/.openclaw/workspace/scripts/firecrawl.py scrape <url> --out /tmp/page.md`
3. **If firecrawl fails — steel-browser navigate:** `steel-browser__navigate` on same URL, wait 5–8 seconds for JS to render.
4. **Still blocked — alternate path:** Try site's blog index or sitemap. Index pages often static even when article pages gated.
5. **All fail — abort.** Mark page as "JS-gated, content not verified" and skip. Do NOT synthesize from general knowledge. Log exactly what failed and why.

## Known JS-gated sites (firecrawl first)

ServiceTitan, Housecall Pro, HubSpot, Kajabi, Thinkific.

## Token budget rule

If steel-browser or web_search burns >500k tokens on single source without extracting content → abort that source, flag it, report token cost in completion log.
