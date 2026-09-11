import json
import logging
import time
from typing import List, TypedDict

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from app.config import settings
from app.retrieval.metadata_filter import extract_filter, get_known_companies
from app.vectorstore.store import get_vector_store

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2

GRADE_PROMPT = """Question: {question}

Retrieved context:
{context}

Does this context contain enough information to answer the question, even if the answer requires simple
extraction or calculation from numbers already present? Respond "sufficient" if the needed fact or figure
is present anywhere in the context, even if not perfectly labeled. Only respond "insufficient" if the
specific information needed is genuinely absent from the context.

Respond with strict JSON only, no markdown: {{"sufficient": true or false}}"""

REWRITE_PROMPT = """This search query did not retrieve enough information to answer the question below.

Original question: {question}
Search query that was tried: {search_query}

Rewrite the search query to more closely match how this fact would actually be phrased inside a company's
financial statements (e.g. "total operating income", specific line-item names) rather than conversational
phrasing. Return only the rewritten search query text, nothing else, no quotes."""

DECOMPOSE_PROMPT = """This question requires information from multiple distinct sources: {labels}

Question: {question}

Write a standalone version of this question for each source listed, focused only on what that one source
alone would need to answer its part (e.g. if a source is "Apple FY2022", write something like "What was
Apple's net income for fiscal year 2022?"). Phrase each question using the literal line-item terms a
financial statement reports (e.g. "operating income", "net sales", "net income") rather than a computed
ratio name like "margin", since filings report raw dollar figures and not every company's filing uses
"margin" language even when it discloses the underlying numbers. Respond with strict JSON only, no markdown,
one key per source, using the exact source labels given:
{{"label1": "standalone question for source 1", "label2": "standalone question for source 2"}}"""

GENERATE_PROMPT = """Answer the question using only the context below.

Important: financial statements often report multiple similar-looking line items for the same broad concept.
When this happens, prefer the headline consolidated figure a company reports as its main result, not a
component or before-adjustment figure. Specifically:
- Prefer "net income attributable to [company]" over "consolidated net income" (the latter may include
  amounts attributable to noncontrolling interests, a smaller adjustment).
- Prefer "total operating income" over "segment operating income" (segment figures are a
  before-corporate-expense component of the total, not the final reported number).
- When a table has multiple years as columns, double-check you are reading the value from the correct
  year's column before answering.

If the context doesn't contain the answer, say you don't know.

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
    company_queries: dict


def get_llm():
    return ChatOpenAI(model=settings.openai_model, temperature=0, api_key=settings.openai_api_key)


def format_context(documents):
    parts = []
    for doc in documents:
        label = f"[{doc.metadata.get('company')}, {doc.metadata.get('fiscal_year')}, {doc.metadata.get('section')}]"
        parts.append(f"{label}\n{doc.page_content}")
    return "\n\n".join(parts)


def parse_json(content):
    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`").removeprefix("json").strip()
    return json.loads(content)


def decompose_query(original_question, labels):
    # a shared query dilutes focus whenever the question actually needs two distinct slices of
    # data at once, whether that's two companies or two years of the same company. Generating one
    # genuinely independent, standalone question per source is what fixes that, this is real query
    # decomposition, not text surgery on a shared string.
    prompt = DECOMPOSE_PROMPT.format(labels=", ".join(labels), question=original_question)
    try:
        response = get_llm().invoke(prompt)
        result = parse_json(response.content)
        tokens = (response.usage_metadata["input_tokens"], response.usage_metadata["output_tokens"])
        return result, tokens
    except Exception:
        logger.exception("Query decomposition failed, falling back to the shared query")
        return {}, (0, 0)


def build_entities(companies, years):
    # an "entity" is one independent slice of data the question needs a fair, undiluted shot at
    # retrieving. If multiple companies are involved, each company is its own entity (regardless
    # of how many years). If only one company is involved but multiple years are, each year is its
    # own entity instead. (This corpus never needs the full company x year cross product, e.g. no
    # question asks "compare Apple 2022 vs Microsoft 2023", so this simpler either/or is enough.)
    if len(companies) > 1:
        return [
            (company, {"company": {"$in": [company]}, **({"fiscal_year": {"$in": years}} if years else {})})
            for company in companies
        ]
    if years and len(years) > 1:
        return [
            (f"{companies[0]} {year}", {"company": {"$in": companies}, "fiscal_year": {"$in": [year]}})
            for year in years
        ]
    return None


def retrieve_node(state):
    store = get_vector_store("ledger_chunks")
    search_filter = extract_filter(state["original_question"], "ledger_chunks")

    # when a question spans multiple companies (named explicitly, e.g. "Apple's and Microsoft's",
    # or implicitly, e.g. a broad question naming none, which means "all of them"), or multiple
    # years of the same company, searching once against the whole filtered set lets whichever
    # entity simply has the most chunks (JPMorgan has 5-8x more than the others) or embeds most
    # favorably win most of the slots by volume, not relevance. Searching separately per entity and
    # merging gives every entity a fair, equal-sized, full-depth share of the results instead.
    known_companies = get_known_companies("ledger_chunks")
    companies = search_filter.get("company", {}).get("$in") if search_filter else None
    years = search_filter.get("fiscal_year", {}).get("$in") if search_filter else None
    if not companies:
        companies = known_companies

    entities = build_entities(companies, years)

    extra_input_tokens = 0
    extra_output_tokens = 0
    entity_queries = state.get("company_queries") or {}

    if entities:
        labels = [label for label, _ in entities]
        # decompose once per question (cached in state across rewrite rounds), not on every call
        if not entity_queries:
            entity_queries, (in_tok, out_tok) = decompose_query(state["original_question"], labels)
            extra_input_tokens += in_tok
            extra_output_tokens += out_tok

        # give each entity the same full depth a single-entity search would get, rather than
        # dividing one shared budget across them, splitting the budget fixed the "one entity wins
        # by volume" problem but reintroduced a "not enough depth for any one entity" problem.
        # k=30 not 20: a large multi-year financial-statement table (many line items, three years
        # of columns) embeds less sharply toward a single-metric question than shorter prose does,
        # so the right table can rank just past 20 even when it's the only one with the real figure.
        new_docs = []
        for label, entity_filter in entities:
            entity_query = entity_queries.get(label) or state["search_query"]
            new_docs.extend(store.similarity_search(entity_query, k=30, filter=entity_filter))
    else:
        new_docs = store.similarity_search(state["search_query"], k=20, filter=search_filter)

    existing = state.get("documents", [])
    seen = {d.page_content for d in existing}
    merged = list(existing)
    for d in new_docs:
        if d.page_content not in seen:
            merged.append(d)
            seen.add(d.page_content)

    return {
        "documents": merged,
        "company_queries": entity_queries,
        "input_tokens": state.get("input_tokens", 0) + extra_input_tokens,
        "output_tokens": state.get("output_tokens", 0) + extra_output_tokens,
    }


def grade_node(state):
    if state["attempts"] >= MAX_ATTEMPTS:
        return {"sufficient": True}

    context = format_context(state["documents"])
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
    context = format_context(state["documents"])
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
        "company_queries": {},
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