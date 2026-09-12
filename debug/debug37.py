import psycopg
from app.config import settings

dsn = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
with psycopg.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT e.cmetadata->>'company', e.cmetadata->>'fiscal_year',
                   COUNT(*) FILTER (WHERE e.cmetadata->>'page' IS NOT NULL) as with_page,
                   COUNT(*) as total
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = 'ledger_chunks'
            GROUP BY e.cmetadata->>'company', e.cmetadata->>'fiscal_year'
            ORDER BY 1, 2
            """
        )
        for company, fy, with_page, total in cur.fetchall():
            print(f"{company} {fy}: {with_page}/{total} chunks have a page number ({with_page/total*100:.0f}%)")

        cur.execute(
            """
            SELECT COUNT(*)
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = 'ledger_chunks' AND e.cmetadata->>'form_type' IS NULL
            """
        )
        print(f"\nChunks missing form_type: {cur.fetchone()[0]} (should be 0)")

        cur.execute(
            "SELECT COUNT(*) FROM langchain_pg_embedding e JOIN langchain_pg_collection c ON e.collection_id = c.uuid WHERE c.name = 'ledger_chunks'"
        )
        print(f"Total chunks: {cur.fetchone()[0]}")
