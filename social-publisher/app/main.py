from fastapi import FastAPI

from .routers import publish

app = FastAPI(title="social-publisher")

app.include_router(publish.router)


@app.get("/health")
def health():
    return {"status": "ok"}
