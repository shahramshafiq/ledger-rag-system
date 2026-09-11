from app.retrieval.corrective_rag import decompose_query
from app.vectorstore.store import get_vector_store

question = "Between Apple's and Microsoft's fiscal year 2023 10-Ks, which company reported the higher operating margin?"
entity_queries, tokens = decompose_query(question, ["Apple", "Microsoft"])
print(f"New decomposed queries: {entity_queries}")

store = get_vector_store("ledger_chunks")
apple_query = entity_queries.get("Apple")
entity_filter = {"company": {"$in": ["Apple"]}, "fiscal_year": {"$in": ["FY2023"]}}
results = store.similarity_search_with_score(apple_query, k=30, filter=entity_filter)

print(f"\nRank of Apple FY2023 chunks for new query {apple_query!r} (k=30):")
for i, (doc, score) in enumerate(results, 1):
    has_figure = "Operating income" in doc.page_content and "114,301" in doc.page_content
    marker = "  <-- HAS Operating income + 114,301" if has_figure else ""
    print(f"  #{i} score={score:.4f} table={doc.metadata.get('is_table')} section={doc.metadata.get('section')}{marker}")
