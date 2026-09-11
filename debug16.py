from app.vectorstore.store import get_vector_store

store = get_vector_store("ledger_chunks")
query = "What was JPMorgan Chase's net income for fiscal year 2023?"
entity_filter = {"company": {"$in": ["JPMorgan"]}, "fiscal_year": {"$in": ["FY2023"]}}
results = store.similarity_search_with_score(query, k=50, filter=entity_filter)

for i, (doc, score) in enumerate(results, 1):
    has_figure = "49,552" in doc.page_content
    marker = "  <-- HAS 49,552" if has_figure else ""
    if i <= 30 or has_figure:
        print(f"  #{i} score={score:.4f} {doc.page_content[:70]!r}{marker}")
