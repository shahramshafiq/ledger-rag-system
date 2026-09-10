## Baseline (Phase 2): structure-aware chunking, dense retrieval, top-5, no reranking or filtering
11/25 correct, 21/25 faithful, recall@5 100% on every question where a source document could be checked.
Handles direct single-fact lookups well (4/5). Fails on computed table values like operating margin (1/5),
cross-document synthesis (1/4), and broad corpus-wide questions (0/3). Correctly declined on 3/4 unanswerable
questions. Retrieval is not the bottleneck anywhere in this baseline.

## Agentic chunking (Phase 3)
12/25 correct, 22/25 faithful, same 100% recall. Only real difference vs. structure-aware: broad questions
improved from 0/3 to 1/3. table_value and cross_document unchanged (1/5 and 1/4 respectively) despite
genuinely different chunk boundaries (verified by inspecting stored chunk text directly, not just counts).
Query-time cost was roughly the same as baseline ($0.0173 vs $0.0174), but this doesn't include the extra
ingestion-time cost: agentic chunking makes one additional LLM call per paragraph-run per section
(~150-250 extra calls across the 8-filing corpus), adding real ingestion time (minutes, not seconds) and
dollars that structure-aware doesn't pay. For a one-question gain out of 25, agentic chunking did not
clearly justify its extra cost on this corpus, consistent with the case-studies document's own warning that
agentic chunking's real-world gains are inconsistent and corpus-dependent.

## Conclusion so far
Chunking strategy is not the current bottleneck; both strategies plateau at nearly identical scores on the
two weakest categories. The next phase (retrieval: reranker, metadata filtering) targets these directly,
since recall is already 100% in both runs, the problem is which of the correctly-retrieved chunks the model
actually uses, not whether the right chunk was found.

## Reranker (Phase 4, measured independently on top of structure-aware baseline)
10/25 correct (down from 11/25 baseline), 23/25 faithful (up from 21/25), avg latency 7.55s
(up from 2.66s), p95 latency 8.16s. Helped its intended target, cross_document, from 1/4 to 2/4,
but did not improve table_value at all (1/5, unchanged) and actively hurt direct_lookup (4/5 -> 2/5)
and company_year_specific (2/4 -> 1/4). Net effect on this corpus: negative. Likely cause: the
cross-encoder (cross-encoder/ms-marco-MiniLM-L6-v2) is tuned for general web search relevance,
not financial tabular precision, it appears to deprioritize the exact table row containing the needed
number in favor of passages that read as more topically related overall. Latency also far exceeds the
few-hundred-millisecond budget the case-studies reference names for reranking in a latency-sensitive
product; mitigation would be a smaller/faster cross-encoder, batching, or reranking only on a
confidence-gated subset of queries rather than every request. On the evidence so far, this reranker
configuration does not justify its cost on this corpus and should not be combined with future runs
without further tuning (e.g. a financial-domain-tuned reranker) or a narrower application (only
cross_document-style questions, where it actually helped).