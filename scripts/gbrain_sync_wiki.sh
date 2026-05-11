#!/bin/bash
export OPENAI_API_KEY=$(grep GBRAIN_OPENAI_KEY ~/.openclaw/.env | cut -d= -f2-)
gbrain import ~/.openclaw/workspace/wiki --no-embed >> ~/.openclaw/workspace/logs/gbrain_sync.log 2>&1
