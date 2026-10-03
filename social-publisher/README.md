# social-publisher

Internal microservice (ESB component): fans a post out to Facebook, Instagram, Telegram, Threads, X, VK and MAX in one call. Stateless — no database, credentials come entirely from environment variables.

## Design

Every network is a `SocialPublisher` subclass in `app/publishers/` with two methods: `is_configured()` and `async publish(request)`. The single endpoint, `POST /v1/posts/publish`, drives every registered publisher through that same interface:

- a platform with no credentials set → reported back as `skipped_unconfigured`, never called
- a platform whose call raises → reported back as `error`, isolated via `asyncio.gather` so it can't take down the others
- otherwise → called concurrently with every other requested platform, reported as `success`

This is what makes `"platforms": ["all"]` safe to call with, say, only `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` set: Telegram sends, everything else comes back `skipped_unconfigured`, nothing throws.

Media is passed in as public URLs (`media_urls`), not raw bytes. Facebook/Instagram/Threads' Graph APIs and Telegram/MAX's Bot APIs accept a URL directly; VK and X have no "post by URL" option, so their adapters download the URL and re-upload the bytes through each platform's own upload flow — an implementation detail fully contained inside `vk.py`/`x_twitter.py`, invisible to the caller.

**Production note:** Facebook/Instagram/Threads fetch `media_urls` from Meta's own servers, so that URL must be reachable from the public internet in production (this is what `SITE_BASE_URL` in the root Django service's settings controls). In local dev, with no real tokens configured anyway, this doesn't matter.

## Run

Started automatically as part of the root `docker compose up --build` (see the root `README.md`), reachable internally at `http://publisher:8000`. To run it standalone: `cd social-publisher && docker compose up --build`, reachable at `http://localhost:8002`.

Copy `.env.example` to `.env` and fill in whichever platforms you have credentials for; see the comments in that file for what each one needs.

## API

- `POST /v1/posts/publish` — header `X-Service-Token`, body `{text, platform_text?, media_urls?, platforms?}` (`platforms` defaults to `["all"]`). Returns `{results: [{platform, status, detail, external_url}]}`.
- `GET /health`

## Tests

```
cd social-publisher
pip install -r requirements.txt
pytest
```
