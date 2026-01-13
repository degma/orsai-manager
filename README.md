# Orsai Manager

## Telegram ingest (LAN only)

Set required environment variables:

- `TELEGRAM_INGEST_SECRET` (required)
- `TELEGRAM_ADMIN_IDS` (comma-separated Telegram user IDs)

Example request:

```bash
curl -X POST http://127.0.0.1:5000/api/telegram/admin \
  -H "Content-Type: application/json" \
  -H "X-TELEGRAM_SECRET: $TELEGRAM_INGEST_SECRET" \
  -d '{"telegram_user_id":"123456","text":"/match 12 score 3-1 notes \"Great first half\""}'
```

Security note: keep this endpoint private on your LAN and protect the secret.
