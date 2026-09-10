def reciprocal_rank_fusion(vector_results, keyword_results, k=60, top_k=5):
    scores = {}
    docs_by_key = {}

    for rank, doc in enumerate(vector_results):
        key = doc.page_content
        scores[key] = scores.get(key, 0) + 1 / (k + rank + 1)
        docs_by_key[key] = doc

    for rank, doc in enumerate(keyword_results):
        key = doc.page_content
        scores[key] = scores.get(key, 0) + 1 / (k + rank + 1)
        docs_by_key[key] = doc

    ranked_keys = sorted(scores, key=scores.get, reverse=True)
    return [docs_by_key[key] for key in ranked_keys[:top_k]]