# Reddit VoC — Home Services

## Mission
Capture real voice-of-customer language from Reddit threads in:
- r/pestcontrol
- r/HVAC
- r/Plumbing
- r/fieldService
- r/smallbusiness
- r/entrepreneur

## Output Format
- Raw JSON per thread → research/reddit/
- Promoted concepts → research/reddit/concepts.jsonl
- Markdown summary → synthesis/reddit_voc_summary.md

## Focus terms
pest control, HVAC, plumber, scheduling, appointment, missed calls, voicemails, pricing, reviews, lead quality, no-shows, callback, quote

## Pipeline
reddit_json_scraper.py → concepts.jsonl → synthesis/reddit_voc_summary.md
