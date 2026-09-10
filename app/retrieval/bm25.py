import json
import logging

import psycopg
from langchain_core.documents import Document

from app.config import settings

logger = logging.getLogger(__name__)


def bm25_search(question, collection_name, k=20, search_filter=None):
    dsn = settings.database_url.replace("postgresql+psycopg://", "postgresql://")

    conditions = [
        "c.name = %(collection)s",
        "to_tsvector('english', e.document) @@ plainto_tsquery('english', %(q)s)",
    ]
    params = {"collection": collection_name, "q": question, "k": k}

    if search_filter and "company" in search_filter:
        conditions.append("e.cmetadata->>'company' = ANY(%(companies)s)")
        params["companies"] = search_filter["company"]["$in"]
    if search_filter and "fiscal_year" in search_filter:
        conditions.append("e.cmetadata->>'fiscal_year' = ANY(%(years)s)")
        params["years"] = search_filter["fiscal_year"]["$in"]

    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT e.document, e.cmetadata,
               ts_rank(to_tsvector('english', e.document), plainto_tsquery('english', %(q)s)) AS rank
        FROM langchain_pg_embedding e
        JOIN langchain_pg_collection c ON e.collection_id = c.uuid
        WHERE {where_clause}
        ORDER BY rank DESC
        LIMIT %(k)s
    """

    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
    except Exception:
        logger.exception("BM25 search failed")
        return []

    results = []
    for text, metadata, _rank in rows:
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        results.append(Document(page_content=text, metadata=metadata))
    return results