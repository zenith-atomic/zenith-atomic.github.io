# Runbook — Factory Commands

Load on demand when handling `/factory ...` Telegram input.

Dispatch every `/factory <subcommand> [args]` via:

```bash
$HOME/.openclaw/workspace/factory/scripts/factory_dispatch.sh "<subcommand> [args]"
```

Pass everything after `/factory ` as a single quoted string. Examples:

| User sends | You run |
|-----------|---------|
| `/factory status` | `factory_dispatch.sh "status"` |
| `/factory inbox https://example.com` | `factory_dispatch.sh "inbox https://example.com"` |
| `/factory ingest https://example.com` | `factory_dispatch.sh "ingest https://example.com"` |
| `/factory help` | `factory_dispatch.sh "help"` |

Return script stdout as reply. Non-zero exit → show error output.

## Wiki Ingestion (PDF uploads)

When user sends a PDF document directly to the bot (mime_type `application/pdf` with `file_id`), do not wait for `/factory ingest` — act immediately:

```bash
$HOME/.openclaw/workspace/factory/scripts/wiki_ingest_cmd.sh "<file_id>" --telegram
```

Script downloads from Telegram, extracts text, runs full ingestion. Report result.

If document is not PDF, reply: `Only PDF files are supported for wiki ingestion. Send a PDF, or use /factory ingest <url> for a web page.`
