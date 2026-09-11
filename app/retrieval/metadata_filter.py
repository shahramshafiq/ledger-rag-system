import re
from functools import lru_cache

import psycopg

from app.config import settings


@lru_cache(maxsize=8)
def get_known_companies(collection_name):
    dsn = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT e.cmetadata->>'company'
                FROM langchain_pg_embedding e
                JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                WHERE c.name = %s
                """,
                (collection_name,),
            )
            return [row[0] for row in cur.fetchall() if row[0]]


def extract_filter(question, collection_name="ledger_chunks"):
    known_companies = get_known_companies(collection_name)
    companies = [c for c in known_companies if c in question]

    # a year mentioned right after "not" (e.g. "fiscal year 2022, not fiscal year 2023")
    # is being explicitly excluded, not requested, so it must not end up in the filter
    excluded_years = set(re.findall(r"not\s+(?:fiscal\s+year\s+)?(20\d{2})", question, re.IGNORECASE))
    all_years = re.findall(r"20\d{2}", question)
    years = sorted(set(f"FY{y}" for y in all_years if y not in excluded_years))

    filters = {}
    if companies:
        filters["company"] = {"$in": companies}
    if years:
        filters["fiscal_year"] = {"$in": years}

    return filters or None
