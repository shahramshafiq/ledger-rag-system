import re

from langchain_core.documents import Document

import tiktoken

encoder = tiktoken.get_encoding("cl100k_base")

def make_chunk(text, heading, metadata, is_table):
    chunk_metadata = {"section": heading, "is_table": is_table}
    chunk_metadata.update(metadata)
    return Document(page_content=text, metadata=chunk_metadata)

def count_tokens(text):
    return len(encoder.encode(text))


MIN_TOKENS = 15


def add_text_chunk(chunks, text, heading, metadata):
    # page footers ("Apple Inc. | 2022 Form 10-K | 58") and empty-section stubs ("RESERVED 33")
    # end up as their own tiny paragraph chunks whenever they sit alone between two tables or
    # section boundaries. Their embeddings are dominated by the company/year tokens they contain,
    # so they out-rank real content for exactly the entity-focused queries retrieval relies on.
    # Tables are exempt and always kept regardless of size, so no real figure is lost by dropping these.
    if count_tokens(text) < MIN_TOKENS:
        return
    chunks.append(make_chunk(text, heading, metadata, is_table=False))


def table_to_text(rows):
    # a dense multi-year financial table (many line items, three years of columns, mostly pipes and
    # digits) embeds weakly against a plain question: the row labels that actually carry the meaning
    # ("Operating income", "Net income") are diluted by the surrounding numbers. Prepending them as a
    # plain-language summary line gives the chunk's own embedding a real semantic anchor, the same
    # contextual-chunking idea from the RAG case studies, without splitting or altering the table itself.
    labels = []
    for row in rows:
        if row and row[0] and re.search(r"[A-Za-z]", row[0]):
            labels.append(row[0].strip())

    lines = [" | ".join(cell for cell in row if cell) for row in rows]
    table_text = "\n".join(lines)

    if labels:
        return f"Table reporting: {', '.join(labels)}\n{table_text}"
    return table_text

def split_oversized(text, max_tokens):
    sentences = text.split(". ")
    pieces = []
    buffer_parts, buffer_tokens = [], 0

    for i, sentence in enumerate(sentences):
        if i < len(sentences) - 1:
            sentence += "."
        sentence_tokens = count_tokens(sentence)
        if buffer_tokens + sentence_tokens > max_tokens and buffer_parts:
            pieces.append(" ".join(buffer_parts))
            buffer_parts, buffer_tokens = [], 0
        buffer_parts.append(sentence)
        buffer_tokens += sentence_tokens

    if buffer_parts:
        pieces.append(" ".join(buffer_parts))
    return pieces


def chunk_structure_aware(sections, metadata, max_tokens=512):
    chunks = []

    for section in sections:
        heading = section["heading"]
        buffer_parts = []
        buffer_tokens = 0

        for element in section["elements"]:
            if element["type"] == "table":
                if buffer_parts:
                    add_text_chunk(chunks, " ".join(buffer_parts), heading, metadata)
                    buffer_parts, buffer_tokens = [], 0
                table_text = table_to_text(element["rows"])
                chunks.append(make_chunk(table_text, heading, metadata, is_table=True))
                continue

            para_tokens = count_tokens(element["text"])

            if para_tokens > max_tokens:
                if buffer_parts:
                    add_text_chunk(chunks, " ".join(buffer_parts), heading, metadata)
                    buffer_parts, buffer_tokens = [], 0
                for piece in split_oversized(element["text"], max_tokens):
                    add_text_chunk(chunks, piece, heading, metadata)
                continue

            if buffer_tokens + para_tokens > max_tokens and buffer_parts:
                add_text_chunk(chunks, " ".join(buffer_parts), heading, metadata)
                buffer_parts, buffer_tokens = [], 0

            buffer_parts.append(element["text"])
            buffer_tokens += para_tokens

        if buffer_parts:
            add_text_chunk(chunks, " ".join(buffer_parts), heading, metadata)

    return chunks