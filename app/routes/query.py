import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.retrieval.corrective_rag import answer_question_corrective

logger = logging.getLogger(__name__)

router = APIRouter()


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)


@router.post("/query")
def post_query(body: QueryRequest):
    result = answer_question_corrective(body.question)

    return {
        "question": body.question,
        "answer": result["answer"],
        "chunks_used": result["chunks_used"],
        "latency_seconds": round(result["latency"], 2),
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
    }