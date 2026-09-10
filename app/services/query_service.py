import logging
import time

from langchain_openai import ChatOpenAI

from app.vectorstore.store import get_vector_store
from app.config import settings

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """Answer the question using only the context below. If the context doesn't contain the answer, say you don't know.

Context:
{context}

Question: {question}"""


def answer_question(question, k=5, collection_name="ledger_chunks"):
    start = time.time()
    store = get_vector_store(collection_name)
    results = store.similarity_search(question, k=k)

    context = "\n\n".join(doc.page_content for doc in results)
    prompt = PROMPT_TEMPLATE.format(context=context, question=question)

    llm = ChatOpenAI(model=settings.openai_model, temperature=0, api_key=settings.openai_api_key)
    response = llm.invoke(prompt)

    latency = time.time() - start
    logger.info(f"Answered {question!r} in {latency:.2f}s using {len(results)} chunks from '{collection_name}'")

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