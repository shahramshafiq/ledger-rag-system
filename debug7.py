import psycopg
from app.config import settings

dsn = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
with psycopg.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT e.document, e.cmetadata->>'section', e.cmetadata->>'is_table'
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = 'ledger_chunks'
              AND e.cmetadata->>'company' = 'Apple'
              AND e.cmetadata->>'fiscal_year' = 'FY2022'
              AND e.document LIKE '%99,803%'
            """
        )
        rows = cur.fetchall()
        print(f"Chunks containing '99,803' for Apple FY2022: {len(rows)}")
        for doc, section, is_table in rows:
            print(f"  section={section} is_table={is_table}")
            print(f"  content: {doc[:300]!r}")
            print()

        cur.execute(
            """
            SELECT e.cmetadata->>'company', COUNT(*)
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = 'ledger_chunks'
              AND (e.cmetadata->>'is_table') = 'false'
              AND length(e.document) < 60
            GROUP BY e.cmetadata->>'company'
            ORDER BY 2 DESC
            """
        )
        print("Tiny (<60 char) non-table chunks per company in ledger_chunks:")
        for company, count in cur.fetchall():
            print(f"  {company}: {count}")

        cur.execute(
            """
            SELECT e.cmetadata->>'company', e.document
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = 'ledger_chunks'
              AND (e.cmetadata->>'is_table') = 'false'
              AND length(e.document) < 60
            ORDER BY random()
            LIMIT 15
            """
        )
        print("\nSample tiny chunks:")
        for company, doc in cur.fetchall():
            print(f"  [{company}] {doc!r}")

        cur.execute(
            """
            SELECT COUNT(*)
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = 'ledger_chunks' AND (e.cmetadata->>'is_table') = 'false'
            """
        )
        print(f"\nTotal non-table chunks in ledger_chunks: {cur.fetchone()[0]}")
