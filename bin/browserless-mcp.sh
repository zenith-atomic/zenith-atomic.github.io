#!/bin/bash
source ~/.openclaw/.env
exec /home/ai/.npm-global/bin/playwright-mcp \
    --cdp-endpoint "wss://chrome.browserless.io?token=${BROWSERLESS_API_KEY}" \
    --isolated \
    "$@"
