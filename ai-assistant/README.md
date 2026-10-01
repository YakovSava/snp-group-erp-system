# ai-assistant

Standalone AI microservice: employee chat (with file/image attachments), company-knowledge RAG (local embeddings + Chroma), currency conversion with fixed "round up to a nice number" business rules (CBA primary, free fallback), and photo editing — all behind a single shared-secret header, meant to be called only by the auto-smm Django backend.

## Run

```
docker compose up --build
```

Starts `api` (FastAPI/uvicorn on host port **8001**) and `db` (Postgres). Migrations run automatically on container start.

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

## Verified against the live gateway

`/v1/chat/completions`, `/v1/images/generations`, and `/v1/images/edits` were all tested live against `ai.tanakatatsuki.dev` — a real 256×256 image posted to `/v1/images/edits` with "make it blue" came back correctly edited, confirming `app/llm_client.py::edit_image` matches the gateway's actual request/response shape. One real finding: the gateway rejects degenerate tiny images (an 8×8 test image failed with "Unable to process input image") — not a concern for real photos, just don't expect it to handle trivially small inputs.
