# ai-assistant

Standalone AI microservice: employee chat (with file/image attachments), company-knowledge RAG (local embeddings + Chroma), currency conversion with fixed "round up to a nice number" business rules (CBA primary, free fallback), and photo editing — all behind a single shared-secret header, meant to be called only by the auto-smm Django backend.

## Run

This service starts automatically as part of `docker compose up --build` in the parent `auto-smm/` directory (included via that project's `docker-compose.yml`), on the same Docker network as auto-smm — that's the normal way to run it.

It's also fully standalone if you need to run or deploy it on its own:

```
docker compose up --build
```

Starts `api` (FastAPI/uvicorn on host port **8001**) and `ai_db` (Postgres). Migrations run automatically on container start. If auto-smm is running separately (not via the parent's `include:`) and needs to reach this standalone instance, point its `AI_ASSISTANT_BASE_URL` at `http://host.docker.internal:8001` instead of the default `http://api:8000`.

## Configuration

A working `.env` with the gateway key you provided is already included — **but it contains a real API key and `SERVICE_TOKEN`; never commit it.** `SERVICE_TOKEN` here must match `AI_ASSISTANT_SERVICE_TOKEN` in auto-smm's `.env`.

## Seeding company knowledge (RAG)

```
docker compose exec api python scripts/ingest_sample_knowledge.py /path/to/doc.txt
```

or `POST /v1/knowledge/documents` with `{"title": "...", "text": "..."}` (requires the `X-Service-Token` header).

## Endpoints (all require `X-Service-Token`, except `/health`)

- `POST /v1/chat` (multipart: `external_user_id`, `message`, optional `conversation_id`, optional `files[]`) — chat turn; routes to vision Q&A or image editing automatically when an image is attached.
- `GET /v1/conversations/{external_user_id}`, `GET /v1/conversations/{id}/messages`
- `POST /v1/translate` `{text, target_language, annotate_amd_with_usd}`
- `POST /v1/convert-currency` `{amount, from_currency, to_currency}` or `{text, to_currency}`
- `GET /v1/currency/rates`
- `POST /v1/images/edit` (multipart: `image`, `prompt`, optional `high_quality`)
- `POST /v1/knowledge/documents` `{title, text}`
- `POST /v1/smm/draft` (multipart: `image`, `description`, optional `refine_instructions`) — cleans up a (usually bad-quality) product photo and drafts post copy from it + a free-text description; called again with the previous result as `image` to refine further. Powers the dashboard's "SMM инструмент".

## Verified against the live gateway — and a real reliability finding

`/v1/chat/completions`, `/v1/images/generations`, `/v1/images/edits`, and vision input (image content in a chat completion) were all tested live against `ai.tanakatatsuki.dev`.

**The gateway's image endpoints are flaky, not just size-limited.** The exact same ~15KB image returned 520, then 502, then 520 again on three immediate retries, while a slightly larger (~18KB) image succeeded once — this rules out a clean payload-size cutoff and points to genuine backend instability under load. Response to this:

- `app/files/image_prep.py` resizes/recompresses images before upload (max 1280px, JPEG quality 82) — good practice and plausibly reduces failure likelihood, but is **not** the actual fix.
- `app/llm_client.py::_with_retries` wraps every gateway call (chat, image edit, image generate) in up to 4 attempts with exponential backoff — this is what actually makes the feature usable despite the flakiness.
- Expect occasional slow responses (a request that needs 2-3 retries can take 10-15+ seconds) and the rare total failure after all retries are exhausted — both `apps/agent` views and the SMM tool surface a friendly "temporarily unavailable, try again" message in that case rather than a 500.

Separately, the gateway does reject degenerate tiny images outright (an 8×8 test image failed immediately with "Unable to process input image") — unrelated to the flakiness above, and not a concern for real photos.
