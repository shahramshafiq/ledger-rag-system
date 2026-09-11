import sys
import psycopg
from app.config import settings

collection_name = sys.argv[1] if len(sys.argv) > 1 else "ledger_chunks"

dsn = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
with psycopg.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM langchain_pg_embedding
            WHERE collection_id = (SELECT uuid FROM langchain_pg_collection WHERE name = %s)
            """,
            (collection_name,),
        )
        print(f"Deleted {cur.rowcount} chunks from '{collection_name}'")
        conn.commit()
