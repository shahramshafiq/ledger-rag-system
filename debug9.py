from app.vectorstore.store import get_vector_store

store = get_vector_store("ledger_chunks")
query = "What was Apple's net income for fiscal year 2022?"
entity_filter = {"company": {"$in": ["Apple"]}, "fiscal_year": {"$in": ["FY2022"]}}
results = store.similarity_search_with_score(query, k=30, filter=entity_filter)

print(f"Rank of each Apple FY2022 chunk for the net-income query (k=30):")
for i, (doc, score) in enumerate(results, 1):
    has_figure = "99,803" in doc.page_content
    marker = "  <-- HAS '99,803'" if has_figure else ""
    print(f"  #{i} score={score:.4f} table={doc.metadata.get('is_table')} section={doc.metadata.get('section')}{marker}")
