# Frontend Integration Contract

## Environment

```text
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/api/v1/ws
```

For production:

```text
VITE_API_BASE_URL=https://your-backend.onrender.com/api/v1
VITE_WS_URL=wss://your-backend.onrender.com/api/v1/ws
```

Backend CORS must include the frontend domain in `FRONTEND_ORIGIN`.
Multiple domains can be comma-separated.

## Auth

Use `Authorization: Bearer {access_token}` for protected REST endpoints.

Main flow:

```text
POST /auth/register
POST /auth/login
POST /auth/refresh
POST /auth/logout
POST /auth/oauth/google
POST /auth/oauth/apple
GET  /auth/login-options
```

When the API returns `401`, refresh the access token with `/auth/refresh`.
If refresh fails, clear local auth state and send the user to login.

## WebSocket

Connect with:

```text
{VITE_WS_URL}?token={access_token}
```

Client events:

```json
{"type":"message.send","payload":{"chat_id":"...","text":"Hello","type":"text","reply_to_id":null}}
{"type":"message.read","payload":{"chat_id":"...","message_id":"..."}}
{"type":"typing.start","payload":{"chat_id":"..."}}
{"type":"typing.stop","payload":{"chat_id":"..."}}
{"type":"ping","payload":{}}
```

Server events:

```json
{"type":"message.created","payload":{"message":{}}}
{"type":"chat.updated","payload":{"chat":{}}}
{"type":"notification.created","payload":{"notification":{}}}
{"type":"message.read","payload":{"chat_id":"...","user_id":"...","message_id":"..."}}
{"type":"typing.start","payload":{"chat_id":"...","user_id":"..."}}
{"type":"typing.stop","payload":{"chat_id":"...","user_id":"..."}}
{"type":"user.online","payload":{"user_id":"...","last_seen_at":null}}
{"type":"user.offline","payload":{"user_id":"...","last_seen_at":"..."}}
{"type":"pong","payload":{}}
```

## Files

Upload files with `multipart/form-data`:

```text
POST /files/upload
POST /files/avatar
POST /files/channel-cover
```

Use the returned `url`, `mime_type`, `original_filename` and `size_bytes` when sending message attachments.

## Errors

The API returns errors as:

```json
{"detail":"Human readable message"}
```

Rate limited responses return `429` with a `Retry-After` header.

## Smoke Checks

```text
GET /health
GET /readiness
GET /metrics
GET /docs
GET /openapi.json
```
