---
name: send-svg-to-telegram
version: 1.0.0
description: Send SVG files as Telegram attachments. Use when asked to send an SVG image or vector graphic.
triggers:
  - "send svg"
  - "send vector"
  - "send .svg"
tools:
  - exec
mutating: false
---

# Send SVG to Telegram

Send SVG files as Telegram message attachments. Telegram renders SVG as a document attachment (not inline image).

## Contract

SVG files arrive as downloadable attachments in Telegram. The file name and SVG content are preserved.

## The Pattern

```bash
curl -s -F "chat_id=CHAT_ID" \
     -F "document=@/absolute/path/to/file.svg" \
     "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendDocument"
```

## Params

- `file_path`: absolute path to the .svg file
- `chat_id`: 5492388075 (from TOOLS.md — Nicolas's Telegram)

## Always Use sendDocument for SVG

Telegram's `sendPhoto` endpoint cannot process SVG files. Always use `sendDocument`.

## Example

```bash
CHAT_ID=5492388075
SVG_PATH=/home/ai/.openclaw/workspace/telegram-mini-app/preview.svg

curl -s -F "chat_id=$CHAT_ID" \
     -F "document=@$SVG_PATH" \
     "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendDocument"
```

## Anti-Patterns

- Using `sendPhoto` for SVG — returns 400 Bad Request: IMAGE_PROCESS_FAILED
- Using relative paths — curl needs absolute paths for file uploads
- Forgetting the `@` prefix on the file path in curl's -F flag

## Tools Used

- `exec` — curl multipart/form-data upload to Telegram Bot API