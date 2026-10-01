from fastapi import APIRouter, Depends

from ..deps import require_service_token
from ..rag.ingest import ingest_document
from ..schemas import KnowledgeIngestRequest, KnowledgeIngestResponse

router = APIRouter(prefix="/v1", dependencies=[Depends(require_service_token)])


@router.post("/knowledge/documents", response_model=KnowledgeIngestResponse)
def ingest(payload: KnowledgeIngestRequest):
    count = ingest_document(payload.title, payload.text)
    return KnowledgeIngestResponse(chunks_ingested=count)
