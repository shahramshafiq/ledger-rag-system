from app.vectorstore.store import get_vector_store

store = get_vector_store("ledger_chunks")
query = "What was Apple's operating income and net sales for fiscal year 2023 as reported in its 10-K?"
entity_filter = {"company": {"$in": ["Apple"]}, "fiscal_year": {"$in": ["FY2023"]}}
results = store.similarity_search_with_score(query, k=20, filter=entity_filter)

for i, (doc, score) in enumerate(results, 1):
    if doc.metadata.get("is_table"):
        print(f"#{i} table content: {doc.page_content[:200]!r}")
        print()
