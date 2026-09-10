from langchain_core.documents import Document

import tiktoken

encoder = tiktoken.get_encoding("cl100k_base")

def make_chunk(text, heading, metadata, is_table):
    chunk_metadata = {"section": heading, "is_table": is_table}
    chunk_metadata.update(metadata)
    return Document(page_content=text, metadata=chunk_metadata)

def count_tokens(text):
    return len(encoder.encode(text))


def table_to_text(rows):
    lines = [" | ".join(cell for cell in row if cell) for row in rows]
    return "\n".join(lines)

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
                    chunks.append(make_chunk(" ".join(buffer_parts), heading, metadata, is_table=False))
                    buffer_parts, buffer_tokens = [], 0
                table_text = table_to_text(element["rows"])
                chunks.append(make_chunk(table_text, heading, metadata, is_table=True))
                continue

            para_tokens = count_tokens(element["text"])

            if para_tokens > max_tokens:
                if buffer_parts:
                    chunks.append(make_chunk(" ".join(buffer_parts), heading, metadata, is_table=False))
                    buffer_parts, buffer_tokens = [], 0
                for piece in split_oversized(element["text"], max_tokens):
                    chunks.append(make_chunk(piece, heading, metadata, is_table=False))
                continue

            if buffer_tokens + para_tokens > max_tokens and buffer_parts:
                chunks.append(make_chunk(" ".join(buffer_parts), heading, metadata, is_table=False))
                buffer_parts, buffer_tokens = [], 0

            buffer_parts.append(element["text"])
            buffer_tokens += para_tokens

        if buffer_parts:
            chunks.append(make_chunk(" ".join(buffer_parts), heading, metadata, is_table=False))

    return chunks