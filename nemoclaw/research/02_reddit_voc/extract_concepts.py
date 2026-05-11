#!/usr/bin/env python3
"""Extract VOC concepts from scraped Reddit threads — clean phrase extraction."""
import json, sys, re
from pathlib import Path
from collections import defaultdict

RAW = Path('/home/ai/.openclaw/workspace/nemoclaw/research/02_reddit_voc/raw')
OUT = RAW.parent / 'concepts.jsonl'

# Strong home-services pain indicators
PAIN_SIGNALS = {
    'missed call', 'missed appointment', 'missed call', 'phone tag', 'voicemail',
    'can t reach', 'no show', 'no-show', 'no answer', 'not answering', 'unanswered',
    'can t get', 'keep missing', 'caller', 'call back', 'callback', 'answering service',
    'hold time', 'on hold', 'wait time', 'scheduling', 'book appointment',
    'appointment', 'pricing', 'quote', 'estimate', 'bid', 'cost', 'expensive',
    'cheaper', 'too expensive', 'afford', 'budget', 'rate', 'fee', 'charge',
    'review', 'reviews', 'reputation', 'rating', 'yelp', 'google review',
    'complaint', 'negative review', 'bad review', '1 star', 'star rating',
    'lead quality', 'junk lead', 'fake lead', 'spam lead', 'unqualified lead',
    'lead', 'prospect', 'customer', 'client', 'caller', 'phone call',
    'response time', 'slow response', 'delayed', 'never heard back',
    'field service', 'technician', 'contractor', 'dispatch', 'technician',
    'answering', 'busy', 'overwhelmed', 'swamped', 'short-staffed',
    '24/7', 'after hours', 'emergency', 'urgent', 'same day',
}

STOPWORDS = {'the', 'and', 'for', 'was', 'that', 'with', 'this', 'have', 'from',
             'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was',
             'were', 'been', 'their', 'what', 'so', 'were', 'some', 'has',
             'more', 'him', 'his', 'how', 'its', 'may', 'than', 'been',
             'will', 'one', 'our', 'out', 'about', 'who', 'get', 'which',
             'just', 'like', 'use', 'used', 'using', 'make', 'made', 'know',
             'think', 'thought', 'want', 'need', 'doing', 'don', 'didn',
             'really', 've', 'll', 'don', 'doesn', 'isn', 'aren', 'won'}

def clean_phrase(text, min_words=2, max_words=4):
    text = re.sub(r'[^a-z0-9 ]', ' ', text.lower())
    words = [w for w in text.split() if len(w) > 2 and w not in STOPWORDS]
    phrases = []
    for n in range(min_words, max_words+1):
        for i in range(len(words)-n+1):
            phrase = ' '.join(words[i:i+n])
            if len(phrase) > 6:
                phrases.append(phrase)
    return phrases

def has_pain(text):
    text = text.lower()
    return any(signal in text for signal in PAIN_SIGNALS)

def score_post(post):
    score = post.get('score', 0)
    comments = post.get('num_comments', 0)
    text = (post.get('title', '') + ' ' + post.get('selftext', '')).lower()
    pain_hits = sum(1 for s in PAIN_SIGNALS if s in text)
    return score * comments * pain_hits

concepts = defaultdict(int)
thread_count = defaultdict(int)
thread_data = []

for f in sorted(RAW.glob('*.json')):
    try:
        post = json.load(open(f))
    except:
        continue
    if score_post(post) < 3:
        continue
    sub = f.stem.rsplit('_', 1)[0]
    text = post.get('title', '') + ' ' + post.get('selftext', '')
    if not has_pain(text):
        continue
    phrases = clean_phrase(text)
    for phrase in phrases:
        concepts[phrase] += 1
        thread_count[phrase] += 1
    if phrases:
        thread_data.append({'subreddit': sub, 'title': post.get('title'), 'score': post.get('score'), 'id': post.get('id')})

# Only keep phrases that appear in 2+ threads
promoted = {t for t, c in concepts.items() if thread_count[t] >= 2}
ranked = sorted(promoted, key=lambda t: concepts[t], reverse=True)

print(f'Raw concepts: {len(concepts)}')
print(f'Promoted (2+ threads): {len(ranked)}')
print(f'Threads with signal: {len(thread_data)}')
print()
print('TOP CONCEPTS:')
for t in ranked[:50]:
    print(f'  [{thread_count[t]} threads] {t}')

with open(OUT, 'w') as f:
    for t in ranked:
        f.write(json.dumps({'concept': t, 'evidence_count': concepts[t], 'threads': thread_count[t]}) + '\n')

print(f'\nSaved {len(ranked)} concepts to {OUT}')
