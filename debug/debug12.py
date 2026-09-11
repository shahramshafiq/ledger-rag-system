from app.vectorstore.store import get_vector_store

store = get_vector_store("ledger_chunks")
query = "What was Apple's operating income and net sales for fiscal year 2023 as reported in its 10-K?"
entity_filter = {"company": {"$in": ["Apple"]}, "fiscal_year": {"$in": ["FY2023"]}}
results = store.similarity_search_with_score(query, k=154, filter=entity_filter)

for i, (doc, score) in enumerate(results, 1):
    if doc.metadata.get("is_table") and "114,301" in doc.page_content:
        print(f"FOUND at rank #{i} out of {len(results)}, score={score:.4f}")
        print(doc.page_content[:200])
