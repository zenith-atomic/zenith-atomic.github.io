#!/usr/bin/env python3
"""Parse publishing_checklist.md into individual post JSON files — no LLM needed."""

import json
import re
from pathlib import Path

CHECKLIST_PATH = Path("/home/ai/.openclaw/workspace/factory/output/2026-W19/publishing_checklist.md")
QUEUE_DIR = Path("/home/ai/.openclaw/workspace/factory/queue/2026-W19")
QUEUE_DIR.mkdir(parents=True, exist_ok=True)

content = CHECKLIST_PATH.read_text()

# Split by #### pattern (each post)
posts_raw = re.split(r'\n####\s+', content)

posts = []
for chunk in posts_raw:
    if not chunk.strip() or 'Posting Checklist' in chunk:
        continue
    
    # Extract platform from header line like "Monday, Apr 28, 2026, 9:00 AM ET — Twitter — Post 1"
    header_match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)\s*ET\s*—\s*(LinkedIn|X/Twitter|Twitter|Instagram|TikTok|YouTube|blog|Pinterest)\s*—\s*Post\s*(\d+)', chunk)
    if not header_match:
        continue
    
    scheduled_time = header_match.group(1)
    platform = header_match.group(2)
    post_num = header_match.group(3)
    
    if 'Twitter' in platform:
        platform = 'X/Twitter'
    
    # Extract content inside ```text ... ```
    content_match = re.search(r'```text\s*(.*?)\s*```', chunk, re.DOTALL)
    body = content_match.group(1).strip() if content_match else ""
    
    # Extract hashtags
    hashtags = re.findall(r'#\w+', chunk)
    
    # Extract visual reference
    visual_match = re.search(r'Visual:\s*(Visual\s*\d+)', chunk)
    visual = visual_match.group(1) if visual_match else ""
    
    # Extract pillar
    pillar_match = re.search(r'Pillar:\s*(.+)', chunk)
    pillar = pillar_match.group(1).strip() if pillar_match else ""
    
    post = {
        "platform": platform,
        "content": body,
        "hashtags": hashtags,
        "scheduled_time": scheduled_time,
        "visual": visual,
        "pillar": pillar,
        "week": "2026-W19",
        "status": "pending_approval",
        "created": "2026-05-09T23:58:19Z"
    }
    posts.append(post)
    print(f"Post {post_num}: {platform} — {body[:50]}...")

print(f"\nTotal posts parsed: {len(posts)}")

# Write approval queue
approval_file = QUEUE_DIR / "approval.json"
with open(approval_file, 'w') as f:
    json.dump({"posts": posts, "week": "2026-W19", "total": len(posts)}, f, indent=2)
print(f"Written: {approval_file}")

# Write individual post files
for i, post in enumerate(posts):
    post_file = QUEUE_DIR / f"post_{i+1:03d}.json"
    with open(post_file, 'w') as f:
        json.dump(post, f, indent=2)
    print(f"Written: {post_file.name}")

print("\nDone.")