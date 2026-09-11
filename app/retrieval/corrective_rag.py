import json
import logging
import time
from typing import List, TypedDict

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from app.config import settings
from app.retrieval.metadata_filter import extract_filter
from app.vectorstore.store import get_vector_store

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2

GRADE_PROMPT = """Question: {question}

Retrieved context:
{context}

Does this context contain enough information to answer the question? Respond with strict JSON only, no markdown: {{"sufficient": true or false}}"""

REWRITE_PROMPT = """This search query did not retrieve enough information to answer the question below.

Original question: {question}
Search query that was tried: {search_query}

Rewrite the search query to more closely match how this fact would actually be phrased inside a company's
financial statements (e.g. "total operating income", specific line-item names) rather than conversational
phrasing. Return only the rewritten search query text, nothing else, no quotes."""

GENERATE_PROMPT = """Answer the question using only the context below. If the context doesn't contain the answer, say you don't know.

Context:
{context}

Question: {question}"""


class RAGState(TypedDict):
    original_question: str
    search_query: str
    documents: List[Document]
    attempts: int
    sufficient: bool
    answer: str
    input_tokens: int
    output_tokens: int


def get_llm():
    return ChatOpenAI(model=settings.openai_model, temperature=0, api_key=settings.openai_api_key)


def parse_json(content):
    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`").removeprefix("json").strip()
    return json.loads(content)


def retrieve_node(state):
    store = get_vector_store("ledger_chunks")
    search_filter = extract_filter(state["original_question"])
    docs = store.similarity_search(state["search_query"], k=5, filter=search_filter)
    return {"documents": docs}


def grade_node(state):
    if state["attempts"] >= MAX_ATTEMPTS:
        return {"sufficient": True}

    context = "\n\n".join(d.page_content for d in state["documents"])
    prompt = GRADE_PROMPT.format(question=state["original_question"], context=context[:4000])

    try:
        response = get_llm().invoke(prompt)
        result = parse_json(response.content)
        sufficient = bool(result.get("sufficient"))
        return {
            "sufficient": sufficient,
            "input_tokens": state.get("input_tokens", 0) + response.usage_metadata["input_tokens"],
            "output_tokens": state.get("output_tokens", 0) + response.usage_metadata["output_tokens"],
        }
    except Exception:
        logger.exception("Grading failed, defaulting to sufficient")
        return {"sufficient": True}


def route_after_grade(state):
    return "generate" if state["sufficient"] else "rewrite"


def rewrite_node(state):
    prompt = REWRITE_PROMPT.format(question=state["original_question"], search_query=state["search_query"])
    response = get_llm().invoke(prompt)
    new_query = response.content.strip().strip('"')
    logger.info(f"Rewriting search query: {state['search_query']!r} -> {new_query!r}")
    return {
        "search_query": new_query,
        "attempts": state["attempts"] + 1,
        "input_tokens": state.get("input_tokens", 0) + response.usage_metadata["input_tokens"],
        "output_tokens": state.get("output_tokens", 0) + response.usage_metadata["output_tokens"],
    }


def generate_node(state):
    context = "\n\n".join(d.page_content for d in state["documents"])
    prompt = GENERATE_PROMPT.format(context=context, question=state["original_question"])
    response = get_llm().invoke(prompt)
    return {
        "answer": response.content,
        "input_tokens": state.get("input_tokens", 0) + response.usage_metadata["input_tokens"],
        "output_tokens": state.get("output_tokens", 0) + response.usage_metadata["output_tokens"],
    }


workflow = StateGraph(RAGState)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("grade", grade_node)
workflow.add_node("rewrite", rewrite_node)
workflow.add_node("generate", generate_node)

workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "grade")
workflow.add_conditional_edges("grade", route_after_grade, {"generate": "generate", "rewrite": "rewrite"})
workflow.add_edge("rewrite", "retrieve")
workflow.add_edge("generate", END)

graph = workflow.compile()


def answer_question_corrective(question):
    start = time.time()

    result = graph.invoke({
        "original_question": question,
        "search_query": question,
        "documents": [],
        "attempts": 0,
        "sufficient": False,
        "answer": "",
        "input_tokens": 0,
        "output_tokens": 0,
    })

    latency = time.time() - start
    logger.info(f"Corrective RAG answered {question!r} in {latency:.2f}s after {result['attempts']} rewrite(s)")

    chunks_used = [
        {
            "section": doc.metadata.get("section"),
            "company": doc.metadata.get("company"),
            "fiscal_year": doc.metadata.get("fiscal_year"),
            "is_table": doc.metadata.get("is_table"),
            "text": doc.page_content,
        }
        for doc in result["documents"]
    ]

    return {
        "answer": result["answer"],
        "chunks_used": chunks_used,
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "latency": latency,
    }