import logging

from app.parsing.html_parser import parse_filing
from app.vectorstore.store import get_vector_store

logger = logging.getLogger(__name__)


def ingest_filing(html_path, company, ticker, fiscal_year, chunk_fn, form_type="10-K", collection_name="ledger_chunks"):
    sections = parse_filing(html_path)
    metadata = {"company": company, "ticker": ticker, "fiscal_year": fiscal_year, "form_type": form_type}
    chunks = chunk_fn(sections, metadata)

    if not chunks:
        raise ValueError(f"No chunks produced for {company} {fiscal_year}, check the parser against this file")

    store = get_vector_store(collection_name)
    store.add_documents(chunks)

    logger.info(f"Ingested {company} {fiscal_year} into '{collection_name}': {len(chunks)} chunks")
    return len(chunks)