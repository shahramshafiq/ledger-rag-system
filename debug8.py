import psycopg
from app.config import settings
from app.vectorstore.store import get_vector_store

dsn = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
with psycopg.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT e.document, e.cmetadata->>'section'
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = 'ledger_chunks'
              AND e.cmetadata->>'company' = 'Apple'
              AND e.cmetadata->>'fiscal_year' = 'FY2023'
              AND (e.cmetadata->>'is_table') = 'true'
              AND e.document LIKE '%Operating income%'
            """
        )
        rows = cur.fetchall()
        print(f"Apple FY2023 TABLE chunks containing 'Operating income': {len(rows)}")
        for doc, section in rows:
            print(f"  section={section}")
            print(f"  content: {doc!r}")
            print()

store = get_vector_store("ledger_chunks")
query = "What was Apple's operating margin for fiscal year 2023 as reported in its 10-K filing?"
entity_filter = {"company": {"$in": ["Apple"]}, "fiscal_year": {"$in": ["FY2023"]}}
results = store.similarity_search_with_score(query, k=30, filter=entity_filter)

print(f"\nRank of each Apple FY2023 chunk for the operating-margin query (k=30):")
for i, (doc, score) in enumerate(results, 1):
    is_op_table = doc.metadata.get("is_table") and "Operating income" in doc.page_content
    marker = "  <-- HAS 'Operating income' TABLE" if is_op_table else ""
    print(f"  #{i} score={score:.4f} table={doc.metadata.get('is_table')} section={doc.metadata.get('section')}{marker}")
