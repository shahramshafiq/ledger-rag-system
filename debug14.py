import psycopg
from app.config import settings

dsn = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
with psycopg.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT e.document, e.cmetadata->>'section'
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = 'ledger_chunks'
              AND e.cmetadata->>'company' = 'JPMorgan'
              AND e.cmetadata->>'fiscal_year' = 'FY2023'
              AND (e.cmetadata->>'is_table') = 'true'
              AND e.cmetadata->>'section' = 'Item 8. Financial Statements and Supplementary Data.'
              AND e.document LIKE '%Net income%'
            """
        )
        rows = cur.fetchall()
        print(f"Item 8 TABLE chunks mentioning 'Net income' for JPMorgan FY2023: {len(rows)}")
        for doc, section in rows[:5]:
            print(f"  content: {doc[:250]!r}")
            print()

        cur.execute(
            """
            SELECT COUNT(*)
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = 'ledger_chunks'
              AND e.cmetadata->>'company' = 'JPMorgan'
              AND e.cmetadata->>'fiscal_year' = 'FY2023'
              AND e.cmetadata->>'section' = 'Item 8. Financial Statements and Supplementary Data.'
            """
        )
        print(f"Total chunks under JPMorgan FY2023 Item 8: {cur.fetchone()[0]}")

        cur.execute(
            """
            SELECT e.document
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = 'ledger_chunks'
              AND e.cmetadata->>'company' = 'JPMorgan'
              AND e.cmetadata->>'fiscal_year' = 'FY2023'
              AND e.cmetadata->>'section' = 'Item 8. Financial Statements and Supplementary Data.'
            ORDER BY random()
            LIMIT 5
            """
        )
        print("\nSample Item 8 chunks for JPMorgan FY2023:")
        for (doc,) in cur.fetchall():
            print(f"  {doc[:200]!r}")
            print()
