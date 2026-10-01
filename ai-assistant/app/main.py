from contextlib import asynccontextmanager

from fastapi import FastAPI

from .currency import scheduler
from .routers import chat, currency, images, knowledge, smm, translate


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="ai-assistant", lifespan=lifespan)

app.include_router(chat.router)
app.include_router(translate.router)
app.include_router(currency.router)
app.include_router(images.router)
app.include_router(knowledge.router)
app.include_router(smm.router)


@app.get("/health")
def health():
    return {"status": "ok"}
