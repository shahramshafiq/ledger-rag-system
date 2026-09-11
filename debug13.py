import psycopg
from app.config import settings
from app.vectorstore.store import get_vector_store

dsn = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
with psycopg.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT e.document, e.cmetadata->>'section', e.cmetadata->>'is_table'
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = 'ledger_chunks'
              AND e.cmetadata->>'company' = 'JPMorgan'
              AND e.cmetadata->>'fiscal_year' = 'FY2023'
              AND e.document LIKE '%49,552%'
            """
        )
        rows = cur.fetchall()
        print(f"JPMorgan FY2023 chunks containing '49,552': {len(rows)}")
        for doc, section, is_table in rows:
            print(f"  section={section!r} is_table={is_table}")
            print(f"  content: {doc[:300]!r}")
            print()

        cur.execute(
            """
            SELECT DISTINCT e.cmetadata->>'section'
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = 'ledger_chunks'
              AND e.cmetadata->>'company' = 'JPMorgan'
              AND e.cmetadata->>'fiscal_year' = 'FY2023'
            """
        )
        print("All distinct sections for JPMorgan FY2023:")
        for (section,) in cur.fetchall():
            print(f"  {section!r}")

store = get_vector_store("ledger_chunks")
query = "What was JPMorgan Chase's net income for fiscal year 2023?"
entity_filter = {"company": {"$in": ["JPMorgan"]}, "fiscal_year": {"$in": ["FY2023"]}}
results = store.similarity_search_with_score(query, k=20, filter=entity_filter)
print(f"\nTop 20 for the raw Q04 query:")
for i, (doc, score) in enumerate(results, 1):
    has_figure = "49,552" in doc.page_content
    marker = "  <-- HAS 49,552" if has_figure else ""
    print(f"  #{i} score={score:.4f} table={doc.metadata.get('is_table')} section={doc.metadata.get('section')}{marker}")
