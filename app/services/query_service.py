import time

from langchain_openai import ChatOpenAI

from app.vectorstore.store import get_vector_store
from app.config import settings

PROMPT_TEMPLATE = """Answer the question using only the context below. If the context doesn't contain the answer, say you don't know.

Context:
{context}

Question: {question}"""


def answer_question(question, k=5):
    start = time.time()

    store = get_vector_store()
    results = store.similarity_search(question, k=k)

    context = "\n\n".join(doc.page_content for doc in results)
    prompt = PROMPT_TEMPLATE.format(context=context, question=question)

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0, api_key=settings.openai_api_key)
    response = llm.invoke(prompt)

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
        "latency": time.time() - start,
    }