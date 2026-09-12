from app.retrieval.corrective_rag import verify_citations


def test_valid_citations_pass():
    answer = "Net income was $96,995 million [1]. Revenue was $383,285 million [2]."
    assert verify_citations(answer, num_chunks_provided=2) == []


def test_citation_beyond_what_was_retrieved_is_caught():
    # only 2 chunks were actually given to the model, but it cites a 3rd that doesn't exist
    answer = "Net income was $96,995 million [1]. Some other claim [3]."
    assert verify_citations(answer, num_chunks_provided=2) == [3]


def test_citation_of_zero_or_negative_is_caught():
    # not a realistic id under this scheme (ids start at 1), guards against off-by-one mistakes
    answer = "A claim with a bad citation [0]."
    assert verify_citations(answer, num_chunks_provided=5) == [0]


def test_multiple_invalid_citations_all_reported():
    answer = "Claim one [7]. Claim two [9]. Claim three [2] is fine."
    assert verify_citations(answer, num_chunks_provided=3) == [7, 9]


def test_no_citations_is_not_an_error():
    assert verify_citations("An answer with no citations at all.", num_chunks_provided=5) == []


def test_duplicate_valid_citations_do_not_duplicate_in_output():
    answer = "Claim one [1]. Claim two also cites [1] again."
    assert verify_citations(answer, num_chunks_provided=2) == []
