from app.retrieval.metadata_filter import extract_filter
from app.vectorstore.store import get_vector_store


def test_extract_filter_identifies_company_and_year():
    result = extract_filter("What was Apple's net income for fiscal year 2023?", "ledger_chunks")
    assert result["company"]["$in"] == ["Apple"]
    assert result["fiscal_year"]["$in"] == ["FY2023"]


def test_extract_filter_excludes_negated_year():
    result = extract_filter(
        "What was Apple's operating income specifically for fiscal year 2022 (not fiscal year 2023)?",
        "ledger_chunks",
    )
    assert result["fiscal_year"]["$in"] == ["FY2022"]


def test_filtered_search_never_leaks_another_company():
    store = get_vector_store("ledger_chunks")
    search_filter = extract_filter("What was Apple's net income for fiscal year 2023?", "ledger_chunks")

    results = store.similarity_search("net income", k=20, filter=search_filter)
    assert len(results) > 0

    for doc in results:
        assert doc.metadata["company"] == "Apple", (
            f"Metadata filter leaked a {doc.metadata['company']} chunk into an Apple-only search"
        )
        assert doc.metadata["fiscal_year"] == "FY2023"


def test_unfiltered_search_would_actually_span_multiple_companies():
    # Proves the filter above is doing real work, not passing by accident because
    # nothing would have leaked in anyway.
    store = get_vector_store("ledger_chunks")
    results = store.similarity_search("net income", k=20, filter=None)

    companies_seen = {doc.metadata["company"] for doc in results}
    assert len(companies_seen) > 1, (
        "Expected an unfiltered search to span multiple companies, if it doesn't, this "
        "test can no longer prove the metadata filter is meaningfully restricting results"
    )