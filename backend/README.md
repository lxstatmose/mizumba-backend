# MiZumBA Backend

FastAPI backend for the MiZumBA messenger.

## Local Setup

Run the full backend stack with Docker:

```bash
cd backend
docker compose up --build
```

This starts FastAPI, PostgreSQL and Redis. The backend applies Alembic migrations before starting.

For local Python-only development:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Whisper audio-to-text is optional because it installs heavy ML dependencies. Enable it locally with:

```bash
pip install -r requirements-whisper.txt
```

On Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Apply migrations manually:

```bash
alembic upgrade head
```

Run tests:

```bash
pip install -r requirements-dev.txt
pytest
```

Seed demo data:

```bash
python scripts/seed_demo.py
```

Demo users:

```text
demo-alice@mizumba.app / demoPassword123
demo-bob@mizumba.app / demoPassword123
```

Export OpenAPI for frontend client generation:

```bash
python scripts/export_openapi.py
```

API docs will be available at:

```text
http://localhost:8000/docs
```

## First Auth Endpoints

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/oauth/google
POST /api/v1/auth/oauth/apple
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
POST /api/v1/auth/confirm-email
POST /api/v1/auth/resend-confirmation
POST /api/v1/auth/forgot-password
POST /api/v1/auth/reset-password
POST /api/v1/auth/change-password
GET  /api/v1/auth/login-options
POST /api/v1/audio/transcribe
GET  /api/v1/users/me
PATCH /api/v1/users/me
GET  /api/v1/users/me/profile
GET  /api/v1/users/{user_id}/profile
GET  /api/v1/channels
POST /api/v1/channels
GET  /api/v1/channels/{channel_id}
PATCH /api/v1/channels/{channel_id}
POST /api/v1/channels/{channel_id}/subscribe
DELETE /api/v1/channels/{channel_id}/subscribe
GET  /api/v1/channels/{channel_id}/posts
POST /api/v1/channels/{channel_id}/posts
GET  /api/v1/chats
POST /api/v1/chats/direct
POST /api/v1/chats/group
GET  /api/v1/chats/{chat_id}
POST /api/v1/chats/{chat_id}/members
DELETE /api/v1/chats/{chat_id}/members/{user_id}
POST /api/v1/chats/{chat_id}/read
GET  /api/v1/chats/{chat_id}/messages
POST /api/v1/chats/{chat_id}/messages
POST /api/v1/files/upload
POST /api/v1/files/avatar
POST /api/v1/files/channel-cover
PATCH /api/v1/messages/{message_id}
DELETE /api/v1/messages/{message_id}
GET  /api/v1/messages/{message_id}/reactions
POST /api/v1/messages/{message_id}/reactions
DELETE /api/v1/messages/{message_id}/reactions
GET  /api/v1/notifications
POST /api/v1/notifications/read-all
POST /api/v1/notifications/{notification_id}/read
DELETE /api/v1/notifications/{notification_id}
GET  /api/v1/search?q={query}
GET  /api/v1/settings/privacy
PATCH /api/v1/settings/privacy
GET  /api/v1/settings/notifications
PATCH /api/v1/settings/notifications
GET  /api/v1/settings/blocks
POST /api/v1/settings/blocks/{user_id}
DELETE /api/v1/settings/blocks/{user_id}
GET  /metrics
WS    /api/v1/ws?token={access_token}
```

`GET /api/v1/auth/login-options` returns which auth providers the frontend should show for the user's country.

In local debug mode, email confirmation and password reset endpoints return development tokens in the response. In production, configure SMTP variables so confirmation and reset tokens are sent by email.

OAuth endpoints accept provider `id_token`s. Configure `GOOGLE_CLIENT_ID` and `APPLE_CLIENT_ID` in production.

`POST /api/v1/audio/transcribe` accepts `multipart/form-data` with `upload` and optional `language`. It uses Whisper and requires `ffmpeg` in the runtime environment.
If Whisper is disabled or not installed, this endpoint returns `503`. Docker builds skip Whisper by default; build with `--build-arg INSTALL_WHISPER=true` and set `ENABLE_WHISPER_TRANSCRIPTION=true` only when audio transcription is required on that image.

File uploads use local storage by default. For production, set `STORAGE_PROVIDER=s3` or `STORAGE_PROVIDER=cloudinary` and configure the matching credentials.

Frontend integration notes are in:

```text
FRONTEND_INTEGRATION.md
```

## WebSocket Events

WebSocket broadcasts go through Redis pub/sub channel:

```text
mizumba:websocket:events
```

If Redis is unavailable in local development, the backend falls back to in-process WebSocket delivery.

Client events:

```json
{"type":"message.send","payload":{"chat_id":"...","text":"Hello","type":"text","reply_to_id":null}}
{"type":"message.send","payload":{"chat_id":"...","text":"Photo","type":"image","attachment_url":"...","attachment_mime_type":"image/png","attachment_name":"photo.png","attachment_size":12345}}
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

## Architecture Roadmap

Implemented production-oriented additions:

```text
1. Google / Apple OAuth login endpoints.
2. SMTP email sending for confirmation and password reset.
3. Local / S3 / Cloudinary storage abstraction.
4. Message reactions and @username mention notifications.
5. Search across users, chats, messages and channels.
6. User blocks, privacy settings and notification settings.
7. Request logging, in-memory rate limiting and /metrics.
```

## Deployment

Render deploy files:

```text
../render.yaml
.env.render.example
```

Render setup checklist:

```text
1. Create the Blueprint from ../render.yaml.
2. Set FRONTEND_ORIGIN to the deployed frontend domain, for example:
   https://your-frontend.onrender.com
   Multiple domains can be comma-separated.
3. Set PUBLIC_BASE_URL to the backend domain, for example:
   https://mizumba-backend.onrender.com
4. Render injects DATABASE_URL from mizumba-postgres and REDIS_URL from mizumba-redis.
5. Fill JWT_SECRET_KEY, SMTP credentials, OAuth client IDs and cloud storage credentials.
6. Keep /health as the Render health check path.
7. After deploy, open /readiness to check database, Redis, ffmpeg and Whisper import.
```

Production WebSocket URL:

```text
wss://your-backend.onrender.com/api/v1/ws?token={access_token}
```

Render smoke checks:

```bash
curl https://your-backend.onrender.com/health
curl https://your-backend.onrender.com/readiness
curl https://your-backend.onrender.com/metrics
```

GitHub Actions runs backend import and Alembic checks from:
It also runs the unit, integration and E2E test suite.

```text
../.github/workflows/backend-ci.yml
```
