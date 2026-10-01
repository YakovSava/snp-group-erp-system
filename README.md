# SNP ESB — core service

Internal Django service (ESB core): social-media / marketplace post management and file-conversion utilities. Password + PassKey auth, no public sign-up, RU/HY/EN interface, not indexed by search engines.

## Run

```
docker compose up --build
```

This starts `web` (gunicorn, :8000), `celery_worker`, `celery_beat`, `db` (Postgres) and `redis`. On first boot the `web` container runs migrations, compiles translations, generates `static/images/favicon.ico` from the brand logo, and collects static files.

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
