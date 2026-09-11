from app.vectorstore.store import get_vector_store
from app.chunking.structure_aware import count_tokens
import re

store = get_vector_store("ledger_chunks")
query = "What was JPMorgan Chase's net income for fiscal year 2023?"
entity_filter = {"company": {"$in": ["JPMorgan"]}, "fiscal_year": {"$in": ["FY2023"]}}
results = store.similarity_search_with_score(query, k=5, filter=entity_filter)

for i, (doc, score) in enumerate(results, 1):
    tokens = count_tokens(doc.page_content)
    print(f"#{i} tokens={tokens} score={score:.4f}")
    print(f"FULL: {doc.page_content!r}")
    print()

footer_lines = re.findall(r'\d+ \| JPMorgan Chase & Co\./\d{4} Form 10-K', results[0][0].page_content)
print(f"Footer-pattern repeats in chunk #1: {len(footer_lines)}")
