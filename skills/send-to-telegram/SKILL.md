---
name: send-to-telegram
version: 1.0.0
description: Send files and images as Telegram attachments. Use when asked to send an image or file to the chat.
triggers:
  - "send image"
  - "send file"
  - "send attachment"
  - "attach"
tools:
  - exec
mutating: false
---

# Send to Telegram

Send local files as Telegram message attachments (not as URL links).

## Contract

Files sent via this skill arrive as actual Telegram message attachments, not as text messages with URLs.

## The Pattern (bash + Telegram Bot API)

```bash
curl -s -F "chat_id=CHAT_ID" -F "document=@/path/to/file" "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendDocument"
curl -s -F "chat_id=CHAT_ID" -F "photo=@/path/to/image.png" "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendPhoto"
```

For images: use `sendPhoto` endpoint. For other files: use `sendDocument`.

## Params

- `file_path`: absolute path to the file
- `chat_id`: Telegram chat ID (int or string)
- `mime_type`: `image/svg+xml`, `image/png`, etc. (for photo endpoint)

## Get Your Chat ID

Check `TOOLS.md` or use:
```bash
curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getUpdates" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['result'][0]['message']['chat']['id'])"
```

## Anti-Patterns

- Sending URLs instead of actual file attachments when asked for a file/image
- Using `wget` or `python` instead of `curl` for multipart/form-data (curl is simplest)

## Example

```bash
# For SVG files: send as document (photo endpoint can't process SVG)
curl -s -F "chat_id=CHAT_ID" -F "document=@/path/to/file.svg" "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendDocument"

# For images (PNG, JPG, etc.): use sendPhoto
curl -s -F "chat_id=CHAT_ID" -F "photo=@/path/to/image.png" "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendPhoto"
```

**SVG note:** Telegram can't render SVG inline — send as `sendDocument` not `sendPhoto`.
**PNG conversion:** If you need a raster image, use the browser screenshot approach.

## Tools Used

- `exec` — curl call to Telegram Bot API with multipart/form-data