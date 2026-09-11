from app.retrieval.metadata_filter import extract_filter
from app.retrieval.corrective_rag import build_entities, decompose_query
from app.vectorstore.store import get_vector_store

questions = [
    ("Q15", "Comparing Apple's fiscal year 2022 and fiscal year 2023 10-Ks, did net income increase or decrease, and by roughly how much?"),
    ("Q16", "Between Apple's and Microsoft's fiscal year 2023 10-Ks, which company reported the higher operating margin?"),
]

store = get_vector_store("ledger_chunks")

for qid, question in questions:
    print(f"========== {qid} ==========")
    search_filter = extract_filter(question, "ledger_chunks")
    companies = search_filter.get("company", {}).get("$in") if search_filter else None
    years = search_filter.get("fiscal_year", {}).get("$in") if search_filter else None
    print(f"extract_filter -> companies={companies} years={years}")

    if not companies:
        from app.retrieval.metadata_filter import get_known_companies
        companies = get_known_companies("ledger_chunks")
        print(f"  (no companies in filter, using known companies: {companies})")

    entities = build_entities(companies, years)
    print(f"build_entities -> {entities}")

    if not entities:
        print("  no entities, would use single shared search")
        continue

    labels = [label for label, _ in entities]
    entity_queries, tokens = decompose_query(question, labels)
    print(f"decompose_query -> {entity_queries}  (tokens={tokens})")

    for label, entity_filter in entities:
        entity_query = entity_queries.get(label) or question
        print(f"\n  --- entity: {label} | query used: {entity_query!r} | filter: {entity_filter} ---")
        results = store.similarity_search(entity_query, k=5, filter=entity_filter)
        for doc in results:
            preview = doc.page_content[:150].replace("\n", " ")
            print(f"    [{doc.metadata.get('is_table')}] {doc.metadata.get('section')}: {preview}")
    print()
