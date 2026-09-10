import logging

from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

_model = None


def get_reranker():
    global _model
    if _model is None:
        _model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L6-v2")
    return _model


def rerank(question, documents, top_k=5):
    if not documents:
        return documents

    model = get_reranker()
    passages = [doc.page_content for doc in documents]
    ranked = model.rank(question, passages)

    return [documents[r["corpus_id"]] for r in ranked[:top_k]]