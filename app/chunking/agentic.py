import json
import logging

from langchain_openai import ChatOpenAI
from langchain_core.documents import Document

from app.config import settings
from app.chunking.structure_aware import count_tokens, split_oversized, table_to_text

logger = logging.getLogger(__name__)

AGENTIC_PROMPT = """You are grouping paragraphs from a section of a financial filing into topically coherent chunks.

Below are numbered paragraphs from the section "{heading}". Decide where natural topic breaks occur.
Return strict JSON only, no markdown: {{"chunk_starts": [list of paragraph numbers where a new chunk should start, always including 0]}}
Keep chunks reasonably sized, a few related paragraphs per chunk, not one giant chunk and not a new chunk for every single paragraph unless the topic truly changes.

Paragraphs:
{numbered_paragraphs}"""


def make_chunk(text, heading, metadata, is_table):
    chunk_metadata = {"section": heading, "is_table": is_table}
    chunk_metadata.update(metadata)
    return Document(page_content=text, metadata=chunk_metadata)


def parse_json_response(content):
    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`").removeprefix("json").strip()
    return json.loads(content)

def group_paragraphs_agentically(paragraphs, heading, cost_tracker=None):
    if len(paragraphs) <= 1:
        return [0]

    numbered = "\n".join(f"{i}: {p[:200]}" for i, p in enumerate(paragraphs))
    llm = ChatOpenAI(model=settings.openai_model, temperature=0, api_key=settings.openai_api_key)
    prompt = AGENTIC_PROMPT.format(heading=heading, numbered_paragraphs=numbered)

    try:
        response = llm.invoke(prompt)
        result = parse_json_response(response.content)
        if cost_tracker is not None:
            cost_tracker["input_tokens"] += response.usage_metadata["input_tokens"]
            cost_tracker["output_tokens"] += response.usage_metadata["output_tokens"]
        starts = sorted(set(result["chunk_starts"]) | {0})
        return [s for s in starts if 0 <= s < len(paragraphs)]
    except Exception:
        logger.exception(f"Agentic grouping failed for section {heading!r}, falling back to one chunk per paragraph")
        return list(range(len(paragraphs)))


def chunk_agentic(sections, metadata, max_tokens=512, cost_tracker=None):
    chunks = []

    for section in sections:
        heading = section["heading"]
        paragraph_run = []

        def flush_run():
            if not paragraph_run:
                return
            starts = group_paragraphs_agentically(paragraph_run, heading, cost_tracker)
            for i, start in enumerate(starts):
                end = starts[i + 1] if i + 1 < len(starts) else len(paragraph_run)
                group_text = " ".join(paragraph_run[start:end])
                if count_tokens(group_text) > max_tokens:
                    for piece in split_oversized(group_text, max_tokens):
                        chunks.append(make_chunk(piece, heading, metadata, is_table=False))
                else:
                    chunks.append(make_chunk(group_text, heading, metadata, is_table=False))
            paragraph_run.clear()

        for element in section["elements"]:
            if element["type"] == "table":
                flush_run()
                chunks.append(make_chunk(table_to_text(element["rows"]), heading, metadata, is_table=True))
            else:
                paragraph_run.append(element["text"])

        flush_run()

    return chunks
