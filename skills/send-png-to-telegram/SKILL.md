---
name: send-png-to-telegram
version: 1.0.0
description: Send PNG/JPG images as Telegram photo attachments. Use when asked to send an image or screenshot.
triggers:
  - "send png"
  - "send image"
  - "send screenshot"
  - "send photo"
  - "send .png"
  - "send .jpg"
tools:
  - exec
  - browser
mutating: false
---

# Send PNG/JPG to Telegram

Send raster image files as Telegram photo attachments. Images arrive inline in the chat.

## Contract

PNG, JPG, JPEG, and WebP files sent via `sendPhoto` appear as inline images in Telegram.

## The Pattern

```bash
curl -s -F "chat_id=CHAT_ID" \
     -F "photo=@/absolute/path/to/image.png" \
     "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendPhoto"
```

## Params

- `file_path`: absolute path to the image file (.png, .jpg, .webp)
- `chat_id`: 5492388075 (from TOOLS.md — Nicolas's Telegram)

## Workflow When You Have a URL But No Local File

1. Use browser to navigate to the URL
2. Use browser screenshot to capture and save as PNG
3. Send the saved PNG via curl `sendPhoto`

## Example

```bash
CHAT_ID=5492388075
IMG_PATH=/tmp/screenshot.png

curl -s -F "chat_id=$CHAT_ID" \
     -F "photo=@$IMG_PATH" \
     "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendPhoto"
```

## Anti-Patterns

- Using `sendDocument` for images that should appear inline — they arrive as files instead
- Using relative paths — curl needs absolute paths
- Forgetting the `@` prefix on the file path
- SVG files must use sendDocument (see send-svg-to-telegram skill)

## Tools Used

- `exec` — curl multipart/form-data upload
- `browser` — capture screenshots from URLs (navigate → snapshot → screenshot)