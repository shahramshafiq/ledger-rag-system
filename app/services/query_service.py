import logging
import time

from langchain_openai import ChatOpenAI

from app.vectorstore.store import get_vector_store
from app.reranker.reranker import rerank
from app.retrieval.metadata_filter import extract_filter
from app.retrieval.bm25 import bm25_search
from app.retrieval.fusion import reciprocal_rank_fusion
from app.config import settings

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """Answer the question using only the context below. If the context doesn't contain the answer, say you don't know.

Context:
{context}

Question: {question}"""


def answer_question(question, k=5, collection_name="ledger_chunks", use_reranker=False,
                     retrieve_k=20, use_metadata_filter=False, use_hybrid=False):
    start = time.time()
    store = get_vector_store(collection_name)
    search_filter = extract_filter(question) if use_metadata_filter else None

    if use_hybrid:
        vector_results = store.similarity_search(question, k=retrieve_k, filter=search_filter)
        keyword_results = bm25_search(question, collection_name, k=retrieve_k, search_filter=search_filter)
        results = reciprocal_rank_fusion(vector_results, keyword_results, top_k=k)
    elif use_reranker:
        candidates = store.similarity_search(question, k=retrieve_k, filter=search_filter)
        results = rerank(question, candidates, top_k=k)
    else:
        results = store.similarity_search(question, k=k, filter=search_filter)

    context = "\n\n".join(doc.page_content for doc in results)
    prompt = PROMPT_TEMPLATE.format(context=context, question=question)

    llm = ChatOpenAI(model=settings.openai_model, temperature=0, api_key=settings.openai_api_key)
    response = llm.invoke(prompt)

    latency = time.time() - start
    logger.info(f"Answered {question!r} in {latency:.2f}s using {len(results)} chunks "
                f"from '{collection_name}' (hybrid={use_hybrid}, reranker={use_reranker}, filter={search_filter})")

    chunks_used = [
        {
            "section": doc.metadata.get("section"),
            "company": doc.metadata.get("company"),
            "fiscal_year": doc.metadata.get("fiscal_year"),
            "is_table": doc.metadata.get("is_table"),
            "text": doc.page_content,
        }
        for doc in results
    ]

    return {
        "answer": response.content,
        "chunks_used": chunks_used,
        "input_tokens": response.usage_metadata["input_tokens"],
        "output_tokens": response.usage_metadata["output_tokens"],
        "latency": latency,
    }