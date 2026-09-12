import psycopg
from app.config import settings

dsn = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
with psycopg.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT e.cmetadata->>'form_type', COUNT(*)
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = 'ledger_chunks'
            GROUP BY e.cmetadata->>'form_type'
            """
        )
        for form_type, count in cur.fetchall():
            print(f"form_type={form_type!r}: {count} chunks")

        cur.execute("SELECT COUNT(*) FROM langchain_pg_embedding e JOIN langchain_pg_collection c ON e.collection_id = c.uuid WHERE c.name = 'ledger_chunks'")
        print(f"Total chunks in ledger_chunks: {cur.fetchone()[0]}")
