from app.vectorstore.store import get_vector_store
from app.chunking.structure_aware import count_tokens

store = get_vector_store("ledger_chunks")

query = "What was Apple's net income for fiscal year 2022?"
entity_filter = {"company": {"$in": ["Apple"]}, "fiscal_year": {"$in": ["FY2022"]}}
results = store.similarity_search_with_score(query, k=10, filter=entity_filter)

for doc, score in results:
    tokens = count_tokens(doc.page_content)
    print(f"score={score:.4f} tokens={tokens} table={doc.metadata.get('is_table')} section={doc.metadata.get('section')}")
    print(f"  FULL CONTENT: {doc.page_content!r}")
    print()
