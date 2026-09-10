from app.parsing.html_parser import parse_filing
from app.chunking.structure_aware import chunk_structure_aware
from app.vectorstore.store import get_vector_store


def ingest_filing(html_path, company, ticker, fiscal_year):
    sections = parse_filing(html_path)
    metadata = {"company": company, "ticker": ticker, "fiscal_year": fiscal_year}
    chunks = chunk_structure_aware(sections, metadata)

    if not chunks:
        raise ValueError(f"No chunks produced for {company} {fiscal_year}, check the parser against this file")

    store = get_vector_store()
    store.add_documents(chunks)

    return len(chunks)