# SNP ESB — core service

Internal Django service (ESB core): social-media / marketplace post management and file-conversion utilities. Password + PassKey auth, no public sign-up, RU/HY/EN interface, not indexed by search engines.

## Run

Requires Docker Compose **v2.20+** (for the `include:` directive — check with `docker compose version`; anything from the last couple of years is fine). Run `docker compose config` once if you want to sanity-check how the merged config resolves before starting anything.

```
docker compose up --build
```

This one command starts **everything**: `web` (gunicorn, :8000), `celery_worker`, `celery_beat`, `db` (Postgres), `redis` — and, via Compose's `include:` (see the top of `docker-compose.yml`), the separate `ai-assistant/` stack too (`api` on :8001, its own `ai_db`). They're still independently deployable (`cd ai-assistant && docker compose up` works on its own), but the root command now brings both up together on one Docker network, so `web`/`celery_worker` reach ai-assistant at `http://api:8000` with no extra setup. On first boot the `web` container runs migrations, compiles translations, generates `static/images/favicon.ico` from the brand logo, and collects static files.

Create an admin account (there is no public registration):

```
docker compose exec web python manage.py createsuperuser
```

Then open http://localhost:8000/admin/ to manage users/posts, and http://localhost:8000/ for the app itself.

## Configuration

Copy `.env.example` to `.env` and adjust for your environment — a working `.env` with development-only secrets is already included so `docker compose up` works out of the box, **but `SECRET_KEY` and `POSTGRES_PASSWORD` must be changed before any real deployment.**

PassKeys require either `localhost` or HTTPS (`WEBAUTHN_RP_ID` / `WEBAUTHN_ORIGIN` in `.env`) — adjust these if you deploy behind a real domain.

## Adding a PassKey

Password login always works. A signed-in user can add a PassKey for this device from the "Безопасность" (Security) page in the top bar — it's a convenience on top of password login, not a replacement.

## Integration API

- `/api/v1/` — token-authenticated (`rest_framework.authtoken`; issue tokens to service accounts from `/admin/`), read/write `posts/`, `sales-posts/`, read-only `conversion-history/`. This is the surface other ESB components are meant to consume.
- `/api/internal/` — session-authenticated, powers the site's own upload/status-polling UI only.

## ai-assistant

"AI" (chat + SMM tool) and automatic post translation/currency localization are powered by the separate `ai-assistant/` service — see `ai-assistant/README.md`. `docker compose up --build` from this directory starts it automatically (via `include:`); no separate step needed.

It's reached at `AI_ASSISTANT_BASE_URL` with a `AI_ASSISTANT_SERVICE_TOKEN` matching ai-assistant's `SERVICE_TOKEN` — both already set to matching dev defaults in the included `.env` files. Django only ever proxies to it; the browser never talks to ai-assistant directly.

**Running them apart instead** (e.g. deploying ai-assistant on a different host): run `cd ai-assistant && docker compose up --build` on its own there, and point this project's `AI_ASSISTANT_BASE_URL` at wherever it's reachable from — `http://host.docker.internal:8001` if it's a separately-started stack on the same machine (add back `extra_hosts: ["host.docker.internal:host-gateway"]` on the `web`/`celery_worker` services in that case), or its real network address otherwise.

## social-publisher

Publishing a Post to Facebook, Instagram, Telegram, Threads, X, VK and MAX is powered by the separate `social-publisher/` service — see `social-publisher/README.md`. Also started automatically via `include:`, reached at `SOCIAL_PUBLISHER_BASE_URL` with a `SOCIAL_PUBLISHER_SERVICE_TOKEN` matching its `SERVICE_TOKEN`. The "Отправить во все соцсети" button on a post's detail page calls it; any platform with no credentials configured in `social-publisher/.env` is simply skipped, the rest still go out.
