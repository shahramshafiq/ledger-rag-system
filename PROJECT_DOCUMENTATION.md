# Ledger: Complete Project Documentation and Codebase Guide

Written 2026-09-13. Covers the entire project from assignment to final, live-verified completion,
plus a full explanation of every file in the codebase and one complete, real, worked example of how
a document gets stored and how a question finds the right piece of it.

This file is local only. It is not committed to the GitHub repo (the repo already has its own
`docs/NOTES.md`, a narrower technical measurement journal). This document is broader: it also covers
the assignment itself, the decisions behind it, and a teaching-style walkthrough of the whole codebase.

---

## Table of Contents

1. [What Ledger Is](#1-what-ledger-is)
2. [The Corpus](#2-the-corpus)
3. [The Golden Dataset](#3-the-golden-dataset)
4. [Every Technique Tried, With Real Numbers](#4-every-technique-tried-with-real-numbers)
5. [The Corrective RAG Pipeline: Build and Debugging Journey](#5-the-corrective-rag-pipeline-build-and-debugging-journey)
6. [What's Deliberately Out of Scope](#6-whats-deliberately-out-of-scope)
7. [Complete Codebase Walkthrough](#7-complete-codebase-walkthrough)
8. [The Complete Worked Example: Storage and Retrieval](#8-the-complete-worked-example-storage-and-retrieval)
9. [Current Status](#9-current-status)

---

## 1. What Ledger Is

Ledger is the third portfolio project built during the Developers Den internship, after the Event
Processing System (Project 1) and DevMate (Project 2). It is a question-answering service over SEC
10-K filings (annual reports that US public companies are legally required to file). Ask it a
question about one of the companies in its corpus, and it returns an answer grounded in the actual
retrieved passages, plus the exact chunks it used, and it explicitly declines to answer when the
evidence isn't good enough, rather than guessing.

**The one rule that defines the whole project:** every design decision has to be backed by a
measurement against Shahram's own corpus, not general best practice or a blog post's recommendation.
That is why Phase 1 (building the exam before writing any retrieval code) comes before Phase 2
(building the retrieval code itself). Without a scorer built first, there is no way to know whether
any later change actually helped.

**The five phases, in required order** (as amended by the supervisor in person on 2026-09-09, which
overrides the written spec PDF where they disagree):

1. **Golden question set + eval harness.** 25 hand-written questions (the spec originally said 40;
   the supervisor said 25 was enough), covering 6 categories, built and scored *before* any retrieval
   code existed.
2. **End-to-end baseline.** A working pipeline: parse a filing, chunk it, embed it, store it, retrieve
   the top 5 chunks for a question, generate an answer.
3. **Chunking comparison.** Try multiple chunking strategies, measure each one, keep the winner.
4. **Retrieval comparison.** Try BM25/hybrid search, a reranker, and metadata filtering, each measured
   independently, not combined, so the effect of each one is visible on its own.
5. **Abstention, citation, and injection resistance.** The system must be able to say "I don't know",
   every factual claim must cite the real chunk it came from, and the system must resist an attacker
   planting fake instructions inside a filing itself.

**The completion criterion is not a score.** Shahram must be able to point at several questions and
say exactly which phase or change made that question start working, and what it cost in latency and
money. That is the actual bar, not "did the number go up."

**Standing protocols followed throughout the whole project** (worth remembering because they shaped
a lot of small decisions): no em dashes anywhere, Claude never appears as a git contributor or
co-author (checked via GitHub's contributors API after every push, not just the repo page, which
caches separately), `.env` is never opened or viewed, and "verify, don't guess" is the actual working
method, not a slogan. Nearly every real bug in this project was found by querying the live database
directly, printing actual retrieved content, or running a real test, not by reasoning about what
*should* be happening.

---

## 2. The Corpus

Eight filings: two fiscal years each of four companies, chosen deliberately, not at random.

| Company | Ticker | Industry | Purpose |
|---|---|---|---|
| Apple | AAPL | Technology | Same-industry pair with Microsoft, on purpose |
| Microsoft | MSFT | Technology | Same-industry pair with Apple, on purpose |
| Walmart | WMT | Retail | Industry diversity |
| JPMorgan Chase | JPM | Financial Services | Industry diversity, very different filing structure |

Apple and Microsoft were picked specifically to trigger a real retrieval failure mode called
"boilerplate collision": two competitors describing very similar things in very similar language,
which makes it easy for a retrieval system to accidentally pull one company's chunk while answering
a question about the other. This is exactly what Q16 in the golden dataset tests.

**Real, XBRL-verified financial figures** (the ground truth behind the golden dataset; cross-checked
against two independent SEC EDGAR endpoints after one earlier incident where a wrong accession number
turned out to point at a Form 4, not a 10-K):

| Company | FY | Revenue / Net Sales | Operating Income | Net Income |
|---|---|---|---|---|
| Apple | 2022 | $394,328M | $119,437M | $99,803M |
| Apple | 2023 | $383,285M | $114,301M | $96,995M |
| Microsoft | 2022 | $198,270M | $83,383M | $72,738M |
| Microsoft | 2023 | $211,915M | $88,523M | $72,361M |
| Walmart | 2022 | $567,762M | - | $13,673M (attributable to Walmart) |
| Walmart | 2023 | $605,881M | - | $11,680M (attributable to Walmart) |
| JPMorgan | 2022 | - | - | $37,676M |
| JPMorgan | 2023 | - | - | $49,552M |

Walmart reports two net income numbers in its filing: a "consolidated" figure and a smaller
"attributable to Walmart" figure (the difference is the portion belonging to noncontrolling
interests). This exact ambiguity is a real, repeatedly-hit bug source across the whole project,
covered in Section 5.

**Accession numbers** (the unique ID SEC assigns to each filing), exactly as used in
[`app/ingest_all.py`](app/ingest_all.py):

| Company | FY2022 accession | FY2023 accession |
|---|---|---|
| Apple | 0000320193-22-000108 | 0000320193-23-000106 |
| Microsoft | 0001564590-22-026876 | 0000950170-23-035122 |
| Walmart | 0000104169-22-000012 | 0000104169-23-000020 |
| JPMorgan | 0000019617-23-000231 | 0000019617-24-000225 |

The filings were downloaded with the `sec-edgar-downloader` package (`download_filings.py`), which
respects SEC's rate limit (~10 requests/second) and requires a `User-Agent` header identifying who is
making the request. They are not committed to git (`.gitignore` excludes `data/filings/`, about
200MB), since they are raw, regenerable, third-party data, not source code.

---

## 3. The Golden Dataset

25 hand-written questions in [`data/golden_dataset.json`](data/golden_dataset.json), split across 6
categories per the supervisor's verbal proportional split:

| Category | Count | What it tests |
|---|---|---|
| `direct_lookup` | 5 | A single, clearly-stated figure for one company/year |
| `table_value` | 5 | A figure that only exists inside a table (e.g. operating margin, requiring reading a specific cell) |
| `company_year_specific` | 4 | Tests year-confusion: the corpus has 2 years of some companies, does the system grab the wrong one? |
| `cross_document` | 4 | Requires comparing two filings at once |
| `broad` | 3 | Corpus-wide synthesis questions naming no single company |
| `unanswerable` | 4 | Deliberately has no correct answer in the corpus, tests honest refusal |

None of the questions were generated by prompting a model against the actual retrieved chunks, since
that would leak the answer into the question itself and make the eval meaningless.

Two questions have a notable history:
- **Q12** ("According to Microsoft's fiscal year 2023 Form 10-K, Item 1A Risk Factors, what does it
  say about competitive pressure in its markets?") originally had no real answer because the fetch
  tool available at the time couldn't pull a 10MB file. Once the file was downloaded locally anyway,
  the real Item 1A section was read directly and the golden answer filled in with the verbatim quote:
  *"We face intense competition across all markets for our products and services, which may lead to
  lower revenue or operating margins."*
- **Q21** ("What are the main risk themes that recur across the four companies' most recent (fiscal
  year 2023) 10-Ks?") was deliberately left open as a genuine synthesis question. It was completed by
  reading all four companies' real Item 1A sections directly and identifying four real recurring
  themes with textual evidence in each: macroeconomic conditions, cybersecurity, competition, and
  regulatory/legal risk.

---

## 4. Every Technique Tried, With Real Numbers

This table is recomputed directly from [`eval/results.csv`](eval/results.csv) as of today, not copied
from an old summary:

| Technique | Correct | Faithful | Total cost (25 Q) | Avg latency |
|---|---|---|---|---|
| baseline (structure-aware chunks, plain vector, k=5) | 11/25 | 21/25 | $0.0174 | 2.66s |
| agentic chunking | 12/25 | 22/25 | $0.0173 | 2.40s |
| reranker (cross-encoder) | 10/25 | 23/25 | $0.0189 | 7.55s |
| metadata_filter | 13/25 | 21/25 | $0.0149 | 2.23s |
| hybrid (BM25 + vector, RRF fusion) | 12/25 | 21/25 | $0.0151 | 2.54s |
| **corrective (the production pipeline)** | **25/25** | **25/25** | **$0.3366** | **8.59s** |

### Why each one was kept or rejected

**Agentic chunking** (`app/chunking/agentic.py`): asks an LLM to decide where topic breaks fall
within a run of paragraphs, instead of using a fixed token budget. One extra LLM call per
paragraph-run at ingestion time. Result: 1 more correct answer than the structure-aware baseline, for
extra ingestion cost and complexity. Kept for comparison (`ledger_chunks_agentic` collection still
exists), not used in production.

**Reranker** (`app/reranker/reranker.py`, `cross-encoder/ms-marco-MiniLM-L6-v2`): re-scores the top 20
vector results and keeps the best 5. Result: *worse* correctness (10/25, down from 11), nearly 3x the
latency. Root cause, confirmed by direct inspection: this reranker was trained on web-search-style
question/passage pairs, and it systematically deprioritized dense financial tables in favor of
prose that merely mentions the right keywords, exactly backward for this corpus. It helped
`cross_document` questions (1/4 to 2/4) but actively hurt `direct_lookup` and
`company_year_specific`. Rejected for production.

**Metadata filtering** (`app/retrieval/metadata_filter.py`): extracts company/year from the question
text with plain regex (no LLM call, so it's essentially free) and restricts the vector search to only
matching chunks. Result: cheaper, faster, *and* more correct than baseline all at once (13/25). This
became a permanent building block, it's called inside `corrective_rag.py`'s `retrieve_node` too.

**Hybrid search / BM25** (`app/retrieval/bm25.py`, `app/retrieval/fusion.py`): combines keyword search
(Postgres full-text search) with vector search via Reciprocal Rank Fusion. Result: barely moved the
needle (12/25). Root-caused two layers deep: Postgres's `plainto_tsquery` ANDs every query word
together, so a 13-word natural question needs all 13 stemmed words present in a chunk to match at
all, which almost never happens; and even after loosening that, Postgres's `ts_rank` has no real
BM25 IDF weighting, so common boilerplate words outrank the specific words that actually distinguish
one chunk from another. A real BM25 library (like `rank_bm25`) would likely fix this, but was judged
disproportionate effort for an 8-document corpus. Kept for the record, not used in production.

**Corrective RAG** (`app/retrieval/corrective_rag.py`): the only technique that actually reached
25/25. This is the production pipeline, and its full build and debugging story is Section 5, since
that story *is* most of the real engineering work in this project.

---

## 5. The Corrective RAG Pipeline: Build and Debugging Journey

The production pipeline is a LangGraph state machine: retrieve, then grade whether what was
retrieved is good enough, and either generate an answer, rewrite the search and try again (up to 2
times), or abstain. It did not work on the first try. Here is the real sequence of bugs found and
fixed, each one found by direct evidence, not guesswork.

### Bug 1: Junk footer chunks ranking deceptively high

**Symptom:** Q15 and Q16 kept failing even after earlier fixes.
**Root cause, found by querying the live vector store directly:** page-footer text like
`"Apple Inc. | 2022 Form 10-K | 58"` was becoming its own tiny chunk with zero real content. Its
embedding was dominated by exactly the company/year tokens that an entity-focused query also
emphasizes, so it ranked deceptively high and crowded out real content.
**Fix:** `MIN_TOKENS` filter in `app/chunking/structure_aware.py` (`add_text_chunk()`), dropping any
non-table chunk under the threshold. Tables are exempt and always kept whole. Also found and fixed
`app/ingest_all.py` itself was broken (missing Apple's FY2023 filing entirely, and calling
`ingest_filing()` without the required `chunk_fn` argument), meaning it could not have produced a
working corpus recently.

### Bug 2: Retrieval depth too shallow, and a vocabulary mismatch

**Symptom:** Q15 and Q16 *still* failed after the junk was removed.
**Root cause, found via direct SQL/vector-search inspection:** Apple's real net income table for the
relevant year ranked at position #24 for a k=20 search, just past the cutoff. Separately, a
decomposed sub-question used the word "margin", but Apple's filing never uses that word near
operating income (only "Gross margin", unrelated), while Microsoft's filing does use "operating
margin" by name. A genuine vocabulary mismatch between how a question is phrased and how one specific
company's filing is written.
**Fix:** raised `k` from 20 to 30 for per-entity searches; reworded `DECOMPOSE_PROMPT` to prefer
literal financial-statement line items ("operating income", "net sales") over computed ratio names
("margin"); added a "Table reporting: [row labels]" caption to the front of every table's text before
embedding (`table_to_text()` in `structure_aware.py`), the exact "contextual chunking" technique from
Anthropic's published research (a documented 5.7% to 1.9% error-rate reduction), giving a dense
table's embedding a real semantic anchor instead of being pure numbers.

### Bug 3: JPMorgan's structural quirks (two separate bugs)

**Symptom:** a full 25-question run scored 21/25, with Q04 and Q18 (both JPMorgan questions) newly
failing.
**Root cause 1:** JPMorgan's filing incorporates its detailed financial statements by reference,
physically placing them after the "Item 15" heading rather than under "Item 8" where every other
company in the corpus keeps them. This is a real, correctly-parsed structural fact about how
JPMorgan's filing is organized, not a parsing bug.
**Root cause 2:** JPMorgan's footer text (`"118 | JPMorgan Chase & Co./2023 Form 10-K"`) tokenized to
exactly 15 tokens, one over the `MIN_TOKENS` threshold at the time, so it slipped through the junk
filter. Some of JPMorgan's footer banners were also wrapped in a real `<table>` HTML tag purely for
visual layout, which meant they bypassed the junk filter entirely (real tables are exempt from size
filtering by design).
**Fix:** widened `MIN_TOKENS` from 15 to 20; added a rule to `extract_tables()` in
`app/parsing/html_parser.py` to skip any table with fewer than 2 rows (a real financial table always
compares multiple line items across rows; a single-row "table" is layout markup, the same pattern
already used for a Walmart heading-in-a-table quirk from earlier in the project).

### Bug 4: The judge was too literal on an open-ended question

**Symptom:** every question passed except Q21 (the broad risk-themes synthesis question), even
though its actual generated answer was excellent (10 well-organized themes with specific per-company
evidence).
**Root cause:** the harness's LLM judge was grading it against one fixed reference answer too
literally for an inherently open-ended question.
**Fix:** `JUDGE_PROMPT` in `eval/run_harness.py` now takes a `category` parameter; "broad" category
answers are graded on substantive theme overlap, not exact structural match.

This reached **25/25 for the first time**, achieved honestly (by filling in genuinely missing test
data and fixing a real grading bug, not by loosening standards).

### Bug 5: Real abstention exposed a hidden truncation bug

**Symptom:** after implementing real abstention (the actual Phase 5 requirement, since the system was
never actually declining to answer before this), a full run **regressed from 25/25 to 9/25**. Every
question that needed even one search rewrite came back abstained, including ones long confirmed
working.
**Root cause, confirmed directly on Q02 (Microsoft's net income):** `grade_node` was grading on
`context[:4000]`, a flat character slice covering roughly the first 2 of what can be 20 to 80
concatenated chunks, while `generate_node` always used the full, untruncated context. This bug had
existed the entire time. It was invisible before because the old logic used to force
`sufficient=True` after 2 attempts regardless of the grader's real verdict, silently overriding
whatever the half-blind grader concluded, and generation (never truncated) usually found the real
answer anyway. Fixing the actual spec violation (making abstention real) removed that silent
safety net and exposed the pre-existing bug for the first time.
**Fix:** removed the `[:4000]` slice; `grade_node` now grades on the exact same full context
`generate_node` uses.

### Bug 6: The injection defense didn't work on the first live test

**Symptom:** the very first live test of `debug/prompt_injection_test.py` showed both attack variants
(a fake "system override" planted in body text, and the same thing planted inside a table cell)
succeeding, even against the prompt that was supposed to already be the fixed version.
**Fix, in three real iterations, each tested against the live attack before moving to the next:**
1. Stating the evidence-delimiting rule once near the top of `GENERATE_PROMPT`: body-text attack
   still succeeded.
2. Restating the same rule immediately before the question (a recency effect) and explicitly naming
   table cells as a place instructions get hidden: body-text attack now correctly failed, but the
   table-cell attack still succeeded, a genuinely different and harder attack surface (tables carry
   an implicit trust a paragraph doesn't).
3. Added one concrete worked example of correct extraction behavior, using a different fake attack
   phrase than the actual test ("HIJACKED" instead of "INJECTION SUCCESSFUL") specifically so the fix
   generalizes the underlying skill rather than pattern-matching one literal string: both attacks
   correctly failed.

### Bug 7: The same truncation bug class, a second time, in the eval judge

**Symptom:** several genuinely correct, well-cited answers were being marked `faithful=False`.
**Root cause:** `judge_answer()` in `eval/run_harness.py` *also* truncated its context to
`context[:4000]`. The cited chunks sat at character positions past 10,000, 27,000, and 31,000 in a
34,000-character context, all past the judge's own cutoff, so the judge was marking real, correctly
cited claims unfaithful simply because it never saw the cited text.
**Fix:** the judge now receives the full context, numbered to match the citation IDs the answer
actually uses.

### A structural finding, not a bug: the 200,000 tokens/minute rate limit

Removing both truncation bugs means much larger prompts get sent. This regularly triggers `429 Too
Many Requests` from OpenAI on the single largest, most multi-entity question in the set (the one
spanning all four companies). Confirmed identical on two different API keys (a temporary one and the
real, credited one), so this is an **organization-level rate limit on the Developers Den account**,
not something a different key fixes. The existing per-question `try/except` in the harness already
isolates this correctly (records `"ERROR"` and keeps going), and the corrective pipeline's own
built-in retry logic (from the OpenAI client library) usually absorbs it within the same request
without any special handling being needed.

### Final gap closures

- **`form_type` metadata:** added as a real parameter to `ingest_filing()`, defaulting to `"10-K"`
  rather than being hardcoded.
- **Exact-identifier vs. conceptual recall split** (a specific Phase 4 requirement): while computing
  this, found that Q19 and Q21's `source_document` field in the golden dataset was written as prose
  ("all four FY2023 10-Ks") instead of the `TICKER_FYXXXX_10K + ...` format the recall checker
  actually parses, silently making their recall score `None` on every run. Fixed the data format.
- **Page metadata:** the last Phase 2 field. Apple's real footer format is
  `"... | 2022 Form 10-K | 58"` (page after a final pipe); JPMorgan's real format has no pipe at all
  (`"...JPMorgan Chase & Co./2023 Form 10-K 45..."`), confirmed by testing the regex against actual
  raw extracted text, not assumed from an earlier debug session's rendering. Microsoft and Walmart
  genuinely have no such marker in their extracted text, confirmed rather than assumed, so their
  chunks honestly get `page: None`.
- **Live adversarial citation-inducement test:** retrieved only 3 real chunks, then explicitly
  instructed the model to cite "[1] through [10]" and reference "at least 8 different evidence ids."
  The model cited only `[1][2][3]`, the real range, and refused to fabricate the rest under direct
  pressure.

**Final, clean result, live-verified twice** (once at the end of the previous session, and again
today, 2026-09-13, after a full environment restart, fresh Docker container, fresh API calls):
**25/25 correct, 25/25 faithful**, both times.

---

## 6. What's Deliberately Out of Scope

Two things are *not* gaps, they were consciously decided, and should not be re-opened without a new
reason:

1. **Recursive chunking, hierarchical chunking, and the chunk-size sweep.** The supervisor's original
   verbal amendment named 4 strategies to test (agentic, recursive, hierarchical, structure-aware).
   Only agentic and structure-aware were actually built and measured. Shahram explicitly closed this
   gap: "consider it done as it is, no longer a requirement."
2. **Testing BM25/hybrid or the reranker specifically layered on top of corrective RAG** (as opposed
   to the plain pipeline, which is the only configuration actually measured in the table above). This
   remains genuinely open, by Shahram's own choice, deferred to "some later time."

---

## 7. Complete Codebase Walkthrough

### Folder structure

```
Ledger-RAG-System/
├── app/
│   ├── config.py                  # Pydantic settings (API keys, model names, prices)
│   ├── main.py                    # FastAPI app, lifespan, health checks
│   ├── ingest_all.py               # Script: ingest all 8 filings into the vector store
│   ├── routes/
│   │   ├── query.py                # POST /query
│   │   └── documents.py            # POST /documents, GET /documents/{id}/stream
│   ├── parsing/
│   │   └── html_parser.py          # Raw filing HTML -> structured sections/paragraphs/tables
│   ├── chunking/
│   │   ├── base.py                 # (empty, unused stub)
│   │   ├── structure_aware.py      # The winning chunking strategy
│   │   └── agentic.py              # The LLM-grouped chunking strategy (comparison only)
│   ├── services/
│   │   ├── ingestion_service.py    # Orchestrates parse -> chunk -> embed -> store
│   │   └── query_service.py        # The "plain" pipeline (baseline/agentic/reranker/hybrid/filter runs)
│   ├── vectorstore/
│   │   └── store.py                # get_vector_store(): the PGVector connection
│   ├── retrieval/
│   │   ├── metadata_filter.py      # Regex-based company/year extraction + DB filter
│   │   ├── bm25.py                 # Postgres full-text search
│   │   ├── fusion.py               # Reciprocal Rank Fusion
│   │   └── corrective_rag.py       # THE production pipeline (LangGraph state machine)
│   ├── reranker/
│   │   └── reranker.py             # Cross-encoder reranking (comparison only)
│   └── utils/
│       ├── costs.py                # Token cost calculation
│       ├── errors.py               # (empty, unused stub)
│       └── logging.py              # setup_logging()
├── eval/
│   ├── run_harness.py              # The eval harness: runs the golden set, scores, appends to results.csv
│   └── results.csv                 # One row per question per run, every technique ever tried
├── data/
│   ├── golden_dataset.json         # The 25 questions
│   └── filings/                    # Downloaded 10-Ks (gitignored, regenerable)
├── tests/
│   ├── test_citation_verification.py
│   └── test_metadata_filter.py
├── debug/                          # ~30 one-off investigation scripts, kept for the record
├── docs/
│   └── NOTES.md                    # The technical measurement journal
├── download_filings.py             # Script: pull the 8 filings from SEC EDGAR
└── requirements.txt
```

Two files exist but are genuinely empty and unused: `app/chunking/base.py` and `app/utils/errors.py`.
They are early stubs from before the project's real shape settled, harmless dead weight, not a bug
and not hiding anything.

### `app/config.py`

A `pydantic_settings.BaseSettings` subclass. Reads `OPENAI_API_KEY` and `DATABASE_URL` from `.env`
(both required, no default, the app fails to start without them by Pydantic's own validation).
`openai_model` defaults to `"gpt-4.1-mini"`, `embedding_model` to `"text-embedding-3-small"`.
`input_price`/`output_price` (dollars per million tokens) are used by `app/utils/costs.py`. The single
module-level `settings = Settings()` instance is imported everywhere else in the codebase that needs
configuration, so there's exactly one source of truth.

### `app/main.py`

The FastAPI application entry point. `lifespan()` is an async context manager that runs once at
startup: it calls `setup_logging()` and tries `get_vector_store()` just to confirm Postgres is
reachable, logging an error (not crashing) if it isn't. A single `@app.exception_handler(Exception)`
catches anything unhandled anywhere in the app and returns a consistent
`{"error": "INTERNAL_SERVER_ERROR", "message": "..."}` JSON shape instead of leaking a stack trace to
the client. `/health` is a trivial liveness check; `/health/ready` actually tries to connect to
Postgres and returns 503 if it can't, the difference between "the process is running" and "the
process can actually do its job." The two route modules are registered at the bottom via
`app.include_router()`.

### `app/routes/query.py`

One endpoint: `POST /query`. A Pydantic `QueryRequest` model validates the body has a non-empty
`question` string. The handler is a single line that calls
`answer_question_corrective(body.question)` and reshapes the result dict into the JSON response,
including `abstained`, `invalid_citations`, `chunks_used` (the exact evidence used), token counts, and
latency. All the real logic lives in `corrective_rag.py`, this file is intentionally thin.

### `app/routes/documents.py`

`POST /documents` accepts a multipart file upload (`company`, `ticker`, `fiscal_year`, optional
`form_type`). It validates the extension is `.html`/`.htm`, saves the raw bytes under
`data/uploads/{job_id}.html`, and schedules `run_ingestion()` as a FastAPI `BackgroundTask`, returning
a `job_id` immediately rather than making the client wait for parsing/chunking/embedding to finish.
`JOBS` is a plain in-memory Python dict mapping `job_id` to status; this is a deliberate, disclosed
architectural choice, a single-process, single-worker deployment doesn't need a distributed job store
like Project 1's Valkey, since this project only ever ingests one filing at a time.
`GET /documents/{job_id}/stream` is a Server-Sent Events endpoint: `event_generator()` polls the
`JOBS` dict once a second and yields a new `data: {...}\n\n` line only when the status actually
changed, stopping once the job reaches `"completed"` or `"failed"`, and catching
`asyncio.CancelledError` so a client disconnecting doesn't produce an ugly server-side error.

### `app/parsing/html_parser.py`

Turns one raw filing HTML file into a list of structured sections. This is the messiest, most
filing-specific code in the project, because every company's HTML is laid out slightly differently.

- **`find_headings(soup)`**: walks every tag that has an inline `style` attribute, and treats it as a
  real section heading if it's either bold (`font-weight:700` or `font-weight:bold`, both seen across
  different filings) or large (`font-size` 11pt or more), *and* its text matches
  `^Item\s+\d+[A-Za-z]?\.` (e.g. "Item 8." or "Item 1A."). This single function has to handle 4
  genuinely different real-world quirks: Apple's headings are `<span>` tags, Microsoft's are `<p>`
  tags in ALL CAPS, Walmart's heading text is split across two `<span>` elements sitting inside a
  `<table>` used only for visual alignment (handled by finding headings *before* stripping tables),
  and JPMorgan's headings aren't bold at all, only distinguished by being 12pt against a 9-10pt body.
- **`extract_tables(soup, heading_texts)`**: finds every real `<table>` tag, pulls out its rows and
  cells as plain text, and replaces the tag in the DOM with a `[[TABLE_i]]` sentinel string so the
  table's position is preserved when the rest of the page is flattened to plain text later. Two
  filters here matter a lot: a table whose flattened text starts with a heading already found is
  actually a heading laid out as a table (skipped, left as normal text), and a table with fewer than
  2 rows is layout markup, not real data (also skipped), which is what stops page-footer banners that
  happen to be wrapped in a `<table>` tag from being treated as legitimate, always-kept table content.
- **`mark_pages(flat_text)`**: replaces recurring page-footer banners (two different real patterns,
  one per pipe-separated vendor shape, one for a plain trailing-number shape) with `[[PAGE_n]]`
  sentinels, using the exact same sentinel trick as tables.
- **`split_into_sections(flat_text, heading_texts)`**: finds where each heading actually occurs in the
  flattened text (searching forward from the previous match, so a repeated heading string doesn't
  match the same spot twice) and slices the text between consecutive headings into sections.
- **`split_section_text(text, tables, page_state)`**: walks one section's text, splitting on the
  `[[TABLE_i]]` and `[[PAGE_n]]` sentinels. A page sentinel updates a shared `page_state["current"]`
  counter (mutated across the whole walk, so it's carried correctly across section boundaries too); a
  table sentinel becomes a `{"type": "table", "rows": ..., "page": current_page}` element; everything
  else becomes a `{"type": "paragraph", "text": ..., "page": current_page}` element (after stripping
  whitespace, dropped if empty).
- **`parse_filing(html_path)`** is the actual public entry point: read the file, find headings, pull
  out tables, flatten to text, mark pages, split into sections, then split each section's text into
  its typed elements. Returns a list of `{"heading": ..., "elements": [...]}` dicts.

### `app/chunking/structure_aware.py`

The winning chunking strategy, used in production.

- **`make_chunk(text, heading, metadata, is_table, page)`**: wraps text and metadata into a
  LangChain `Document` object (the standard unit LangChain and PGVector both expect).
- **`count_tokens(text)`**: uses `tiktoken`'s `cl100k_base` encoding to count tokens the same way
  OpenAI's models will, so the 512-token budget is measured in the same units the model actually sees.
- **`table_to_text(rows)`**: converts a table's rows into `" | "`-joined lines, and prepends a
  `"Table reporting: [row labels]"` caption line built from the first cell of every row that contains
  a letter. This is the contextual-chunking fix from Bug 2 above, it gives a dense numeric table's
  embedding an actual semantic anchor.
- **`add_text_chunk(chunks, text, ...)`**: the `MIN_TOKENS = 20` junk filter. Anything shorter than 20
  tokens is silently dropped rather than becoming its own chunk (this is where footer banners and
  empty-section stubs get filtered out; tables never go through this function, they're always kept).
- **`split_oversized(text, max_tokens)`**: a plain sentence-boundary splitter (splits on `". "`) used
  as a fallback when a single paragraph is already bigger than the whole 512-token chunk budget.
- **`chunk_structure_aware(sections, metadata, max_tokens=512)`**: the main function. For each
  section, it walks the elements in order. A table always immediately becomes its own chunk (flushing
  whatever prose was accumulating first). A paragraph gets added to a running buffer; if adding it
  would exceed 512 tokens, the buffer is flushed as a chunk first, then the paragraph starts a new
  buffer. An oversized single paragraph is flushed on its own via `split_oversized`. Every chunk
  carries the page number of the *first* paragraph it started with, not every page it might span.

### `app/chunking/agentic.py`

The comparison-only alternative strategy. Instead of a fixed token budget, `AGENTIC_PROMPT` asks an
LLM to look at a numbered list of paragraphs from one section and decide where natural topic breaks
occur, returning a list of paragraph indices where a new chunk should start.
`group_paragraphs_agentically()` makes that one LLM call per run of consecutive paragraphs
(`cost_tracker` is an optional dict the caller can pass in to accumulate token usage across many
calls), falls back to one chunk per paragraph if the call or its JSON parsing fails, and reuses
`table_to_text`/`split_oversized`/`count_tokens` from `structure_aware.py` rather than duplicating
them. `chunk_agentic()` drives this section by section, flushing the current paragraph run through the
LLM whenever a table is hit.

### `app/services/ingestion_service.py`

One function, `ingest_filing(html_path, company, ticker, fiscal_year, chunk_fn, form_type, collection_name)`.
It calls `parse_filing()`, then `chunk_fn(sections, metadata)` (the caller decides which chunking
strategy to use by passing either `chunk_structure_aware` or `chunk_agentic`), raises a `ValueError`
if that produced zero chunks (a real signal something's wrong with the parser for this specific file),
then calls `store.add_documents(chunks)`. This is the one place ingestion actually happens; both
`app/ingest_all.py` and `app/routes/documents.py` call through this same function rather than
duplicating the logic.

### `app/services/query_service.py`

The "plain" (non-corrective) pipeline, used only to produce the baseline/agentic/reranker/
hybrid/metadata_filter comparison rows in the results table. `answer_question()` takes flags
(`use_reranker`, `use_metadata_filter`, `use_hybrid`) that pick one retrieval path: plain vector
search, hybrid (vector + BM25 fused), or reranked (search wide, then rerank down to `top_k`). All
paths converge on the same `PROMPT_TEMPLATE` and a single LLM call. This file has no corrective loop,
no abstention, and no citation enforcement, that's the whole point of it, it exists specifically to
be the less-sophisticated baseline that `corrective_rag.py` is compared against.

### `app/vectorstore/store.py`

One function, `get_vector_store(collection_name)`. Builds an `OpenAIEmbeddings` object (this is what
actually turns text into vectors) and wraps it in a LangChain `PGVector` store pointed at the
Postgres database from `settings.database_url`, with a 5-second `connect_timeout` so a dead database
fails fast with a clear `RuntimeError` instead of hanging. Every other file that needs to read or
write chunks calls this function rather than touching Postgres directly (the two exceptions,
`bm25.py` and `metadata_filter.py`'s `get_known_companies()`, need raw SQL that LangChain's
abstraction doesn't expose, so they use `psycopg` directly).

### `app/retrieval/metadata_filter.py`

- **`get_known_companies(collection_name)`**: runs a real `SELECT DISTINCT` query against Postgres to
  get the actual list of companies currently in the collection, `@lru_cache`-d so it only hits the
  database once per process. This replaced an earlier hardcoded company list specifically because a
  hardcoded list would silently stop working the moment a new company gets ingested, an overfitting
  risk flagged during development.
- **`extract_filter(question, collection_name)`**: plain regex, no LLM call. Checks which known
  company names appear literally in the question text; finds 4-digit years with `20\d{2}`, but
  excludes any year immediately preceded by "not" or "not fiscal year" (so "not fiscal year 2023"
  correctly excludes 2023 rather than matching it), which is what makes year-confusion questions like
  Q13 work. Returns a dict shaped like `{"company": {"$in": [...]}, "fiscal_year": {"$in": [...]}}`,
  the filter format LangChain's `PGVector.similarity_search(filter=...)` expects, or `None` if nothing
  was found.

### `app/retrieval/bm25.py`

`bm25_search()` runs raw SQL against `langchain_pg_embedding` using Postgres's built-in full-text
search (`to_tsvector`/`plainto_tsquery`/`ts_rank`), joined against `langchain_pg_collection` to scope
to the right collection, and optionally filtered by company/fiscal_year the same way the vector search
is. This is not real BM25 (Postgres's `ts_rank` lacks true BM25's IDF term weighting), it is Postgres's
own keyword-ranking approximation, a distinction that mattered when interpreting hybrid search's weak
results.

### `app/retrieval/fusion.py`

`reciprocal_rank_fusion(vector_results, keyword_results, k=60, top_k=5)`: the standard RRF formula.
Each document gets a score of `1 / (k + rank + 1)` from each ranked list it appears in (rank 0 in
either list scores highest), scores from both lists are summed by matching on the document's raw text,
and the top `top_k` by combined score are returned.

### `app/reranker/reranker.py`

`get_reranker()` lazily loads a `sentence_transformers.CrossEncoder` model
(`cross-encoder/ms-marco-MiniLM-L6-v2`) once into a module-level global, so repeated calls don't
reload the model from disk. `rerank(question, documents, top_k)` scores every candidate document
against the question and returns the best `top_k`.

### `app/retrieval/corrective_rag.py`

The production pipeline. This is the most important file in the project, and Section 8 traces a real
question through it step by step, so this section covers structure rather than repeating that trace.

**State** (`RAGState`, a `TypedDict`): carries the original question, the current search query
(which changes across rewrite attempts), the accumulated list of retrieved `documents`, an `attempts`
counter, the grader's `sufficient` verdict, the final `answer`, running token counts, `company_queries`
(the cached per-entity decomposed questions), and the final `abstained`/`invalid_citations` flags.

**The five prompts**, each solving one specific problem found during debugging:
- `GRADE_PROMPT`: asks whether the retrieved context is enough to answer, tolerant of the fact that a
  real answer might need simple extraction or calculation, not perfect labeling.
- `REWRITE_PROMPT`: asks the model to rephrase a failed search query toward how a real financial
  statement would phrase the same fact (the fix for the "margin" vocabulary mismatch bug).
- `DECOMPOSE_PROMPT`: asks for one standalone, source-focused question per entity, in literal
  line-item language rather than computed-ratio language.
- `GENERATE_PROMPT`: the actual answer-writing prompt, heavily hardened against prompt injection
  (see the worked example in Section 8 for the exact reasoning built into it), and requiring a
  `[N]` citation after every factual claim.

**The nodes** (each a plain function taking and returning a partial state dict, LangGraph merges the
returned keys into the running state):
- `retrieve_node`: figures out if this question needs single-entity or multi-entity retrieval (see
  `build_entities()` below), runs the actual vector search(es), and merges new results into whatever
  was already retrieved (deduplicating by exact chunk text, so a rewrite round doesn't just pile up
  duplicates).
- `grade_node`: formats all retrieved documents with `format_context()` and asks `GRADE_PROMPT`
  whether that's enough. Defaults to `sufficient=True` if the LLM call itself throws an exception
  (fails open, so a transient API error doesn't wrongly abstain).
- `route_after_grade`: the actual decision point. Sufficient means generate. Not sufficient but still
  under `MAX_ATTEMPTS` (2) means rewrite and loop back to retrieve. Not sufficient and out of attempts
  means abstain, this is the real, working version of the spec's abstention requirement.
- `rewrite_node`: asks `REWRITE_PROMPT` for a better search query, increments `attempts`, loops back
  to `retrieve_node`.
- `generate_node`: formats context, asks `GENERATE_PROMPT`, then immediately runs `verify_citations()`
  on the model's own answer before returning it.
- `abstain_node`: returns a fixed refusal message and `abstained=True`, with **zero extra LLM calls**,
  no generation happens once the system has decided to abstain.

**Helper functions:**
- `format_context(documents)`: wraps each chunk in `<evidence id="N" source="...">` tags. This single
  function does two jobs at once: the numeric ID is what citation enforcement is checked against, and
  the `<evidence>` wrapper is what tells the model "this is data, not an instruction", the same
  untrusted-input delimiting pattern DevMate (Project 2) used for tool results, applied here to a new
  untrusted surface, the document corpus itself.
- `verify_citations(answer_text, num_chunks_provided)`: pure regex, no LLM call. Finds every `[N]` in
  the answer text and returns any that fall outside `1..num_chunks_provided`, the actual enforcement
  half of claim-level citations (not just asking nicely for one and hoping).
- `build_entities(companies, years)`: decides what counts as one independent "entity" that deserves
  its own fair, undiluted search. More than one company named means each company is its own entity.
  Exactly one company but more than one year means each year is its own entity instead. Otherwise
  (one company, one year, or nothing specific named) returns `None`, meaning "just do one simple
  search", which is the path Section 8's worked example takes.
- `decompose_query(original_question, labels)`: the LLM call behind `DECOMPOSE_PROMPT`, with a
  bare `except Exception` fallback to the original shared query if it fails, since a decomposition
  failure shouldn't crash the whole pipeline.

**The graph wiring**, right after all the node functions:
```python
workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "grade")
workflow.add_conditional_edges("grade", route_after_grade,
    {"generate": "generate", "rewrite": "rewrite", "abstain": "abstain"})
workflow.add_edge("rewrite", "retrieve")
workflow.add_edge("generate", END)
workflow.add_edge("abstain", END)
```
This is the actual retry loop: `rewrite` always goes back to `retrieve`, and the only way out of that
loop is `grade` deciding either `generate` or `abstain`.

**`answer_question_corrective(question)`** is the one public function everything else calls
(`app/routes/query.py`, `eval/run_harness.py`, `debug/*`). It builds the initial state, calls
`graph.invoke()` (LangGraph runs the whole state machine to completion), times it, and reshapes the
final state into the flat result dict the rest of the app expects, including a `chunks_used` list
that carries every piece of metadata (`section`, `company`, `ticker`, `fiscal_year`, `form_type`,
`page`, `is_table`) alongside each chunk's raw text.

### `app/utils/costs.py`

Three pure, one-line functions: input cost, output cost, and their sum, given token counts and
per-million-token prices. No side effects, easy to unit test, though it never got dedicated tests
since it's simple enough that the eval harness itself exercises it on every run.

### `app/utils/logging.py`

One function, `setup_logging()`, a thin wrapper around `logging.basicConfig` with a timestamp/level/
message format. Called once, in `app/main.py`'s `lifespan()` and again at the top of
`eval/run_harness.py`'s `run_harness()`, so both the live service and the offline harness log
consistently.

### `app/ingest_all.py`

The real, current ingestion script. A flat list of the 8 filings (path, company, ticker, fiscal_year),
each passed through `ingest_filing()` with `chunk_structure_aware`, printing a chunk count per filing
as it goes. This is what actually populated the live `ledger_chunks` collection (2,941 chunks as of
today).

### `eval/run_harness.py`

The scoring engine.
- **`check_recall(source_document, chunks_used)`**: parses the golden dataset's `source_document`
  field (format: `TICKER_FYXXXX_10K`, possibly several joined with `" + "`) into
  (ticker, fiscal_year) pairs, then checks whether any actually-retrieved chunk matches one of those
  pairs. Returns `None` (not scored) for unanswerable questions, which have no `source_document`.
- **`judge_answer(question, category, expected_answer, generated_answer, context)`**: one LLM call
  using `JUDGE_PROMPT`, which returns strict JSON `{"correct": ..., "faithful": ...}`. The prompt
  explicitly tells the judge to grade "broad" category questions on theme overlap, not exact
  structural match against the reference answer.
- **`run_harness(run_label, ...)`**: loads the golden dataset, opens `results.csv` in append mode
  (writing the header only if the file is new), and for every question: calls either
  `answer_question_corrective()` or `answer_question()` depending on which flags were passed, computes
  recall, builds a *full, untruncated*, numbered context string for the judge (matching the citation
  numbers the answer actually used), calls `judge_answer()`, computes real dollar cost from actual
  token counts, and writes one CSV row. Every question is wrapped in its own `try/except`, so one
  question erroring out (e.g. hitting the rate limit) never loses the rest of the run, it's recorded
  as `"ERROR"` and the harness moves on. `f.flush()` after every row means a crash mid-run still keeps
  everything written so far.
- The `if __name__ == "__main__":` block is the CLI: `python -m eval.run_harness <label> <collection>
  [--rerank] [--filter] [--hybrid] [--corrective]`.

### `tests/test_citation_verification.py`

6 pure unit tests against `verify_citations()`, no database or API needed: valid citations pass,
a citation beyond what was retrieved is caught, citing `[0]` or a negative number is caught, multiple
invalid citations are all reported at once, an answer with no citations at all is not treated as an
error, and duplicate valid citations don't get double-reported.

### `tests/test_metadata_filter.py`

4 tests, the Phase 4 "metadata-filter-bypass test, reviewed like authentication code":
`test_extract_filter_identifies_company_and_year` and `test_extract_filter_excludes_negated_year`
check the regex logic itself (both still touch the database once, since `extract_filter` calls the
cached `get_known_companies()` internally). The two that matter most:
`test_filtered_search_never_leaks_another_company` runs a real, live, filtered search and asserts
every single result actually belongs to the requested company. Right next to it,
`test_unfiltered_search_would_actually_span_multiple_companies` runs the *same* search with no filter
and asserts it *does* span multiple companies, proof that the filtered test isn't passing by accident
because nothing would have leaked in anyway. Both need Postgres and the embedding API live.

### `debug/`

Around 30 numbered, one-off investigation scripts (`debug1.py` through `debug38.py`, gaps where a
script was superseded), plus a few named ones (`prompt_injection_test.py`,
`clear_collection.py`, `dedupe_last_run.py`, `rerun_single_question.py`,
`citation_induction_test.py`, `verify_injection_html.py`). These are kept deliberately, not deleted,
as an honest record of how each real bug in Section 5 was actually found. They run as
`python -m debug.debugN` (the package needs `debug/__init__.py` to exist for this to work).

---

## 8. The Complete Worked Example: Storage and Retrieval

Everything below is real, captured live from the actual running system on 2026-09-13, not
reconstructed from memory.

### Part A: How a chunk actually gets stored

Take Apple's FY2023 10-K HTML file. Here is the exact real path it takes:

**1. `app/ingest_all.py`** calls
`ingest_filing(path, "Apple", "AAPL", "FY2023", chunk_structure_aware)`.

**2. Inside `ingest_filing()`** (`app/services/ingestion_service.py`):
`parse_filing(html_path)` is called first. Inside it (`app/parsing/html_parser.py`):
- `find_headings()` scans the HTML for bold or large `<span>`/`<p>` tags matching "Item N." and
  finds real headings like "Item 8. Financial Statements and Supplementary Data".
- `extract_tables()` pulls every real `<table>` (2+ rows) out of the DOM, replacing each with a
  `[[TABLE_i]]` sentinel. Apple's primary income statement table is one of these.
- `soup.get_text()` flattens everything else to plain text, and `mark_pages()` replaces Apple's real
  footer pattern (`"... | 2023 Form 10-K | 27"`) with a `[[PAGE_27]]` sentinel.
- `split_into_sections()` cuts the flattened text at each heading's real position, giving one
  `{"heading": "Item 8. ...", "text": "..."}` block per section.
- `split_section_text()` walks that block's text, converting the `[[TABLE_i]]` and `[[PAGE_27]]`
  sentinels into typed elements: `{"type": "table", "rows": [...], "page": 27}` and
  `{"type": "paragraph", "text": "...", "page": 27}`.

**3. `chunk_structure_aware(sections, metadata)`** (`app/chunking/structure_aware.py`) then walks
those elements. When it hits the income statement table element, it immediately calls
`table_to_text()`, which builds a caption from the first cell of every labeled row
(`"Net sales:, Products, Services, Total net sales, ..."`) and prepends it to the raw
pipe-joined row text. `make_chunk()` wraps that into a LangChain `Document` with
`is_table=True` and `page=27`, exempt from the `MIN_TOKENS` filter regardless of length.

**4. `store.add_documents(chunks)`** (`app/vectorstore/store.py`'s `PGVector` instance) is called
once for the whole batch. Internally, LangChain's `OpenAIEmbeddings` sends each chunk's text to
OpenAI's embeddings API and gets back a 1536-number vector (using `text-embedding-3-small`), then
`PGVector` runs one `INSERT` per chunk into the `langchain_pg_embedding` table.

**Here is that exact real row, queried directly out of Postgres right now:**

- **Row id:** `8c65f02f-7834-49e8-82e5-e894d714ca8d`
- **`cmetadata` column (jsonb):**
  ```json
  {"page": 27, "ticker": "AAPL", "company": "Apple", "section": "Item 8. Financial Statements and Supplementary Data", "is_table": true, "form_type": "10-K", "fiscal_year": "FY2023"}
  ```
- **`document` column (the actual chunk text that got embedded), in full:**
  ```
  Table reporting: Net sales:, Products, Services, Total net sales, Cost of sales:, Products, Services, Total cost of sales, Gross margin, Operating expenses:, Research and development, Selling, general and administrative, Total operating expenses, Operating income, Other income/(expense), net, Income before provision for income taxes, Provision for income taxes, Net income, Earnings per share:, Basic, Diluted, Shares used in computing earnings per share:, Basic, Diluted
  Years ended
  September 30,2023 | September 24,2022 | September 25,2021
  Net sales:
  Products | $ | 298,085 | $ | 316,199 | $ | 297,392
  Services | 85,200 | 78,129 | 68,425
  Total net sales | 383,285 | 394,328 | 365,817
  Cost of sales:
  Products | 189,282 | 201,471 | 192,266
  Services | 24,855 | 22,075 | 20,715
  Total cost of sales | 214,137 | 223,546 | 212,981
  Gross margin | 169,148 | 170,782 | 152,836
  Operating expenses:
  Research and development | 29,915 | 26,251 | 21,914
  Selling, general and administrative | 24,932 | 25,094 | 21,973
  Total operating expenses | 54,847 | 51,345 | 43,887
  Operating income | 114,301 | 119,437 | 108,949
  Other income/(expense), net | (565) | (334) | 258
  Income before provision for income taxes | 113,736 | 119,103 | 109,207
  Provision for income taxes | 16,741 | 19,300 | 14,527
  Net income | $ | 96,995 | $ | 99,803 | $ | 94,680
  ```
  (truncated here for readability; the real row also has the EPS lines)
- **`embedding` column** (Postgres `vector` type, this is what similarity search actually compares):
  1536 numbers. First 12: `[-0.0043, -0.0280, 0.0579, -0.0070, 0.0227, 0.0016, -0.0083, 0.0378, -0.0026, 0.0156, 0.0292, -0.0250]`

That's the entire storage side: HTML to headings/tables to typed elements to token-budgeted chunks
to a captioned table string to a 1536-number vector to one Postgres row. The live `ledger_chunks`
collection has 2,941 such rows.

### Part B: How a question actually finds that chunk

Question: **"What was Apple's net income for fiscal year 2023?"**

This question comes in through `POST /query` (`app/routes/query.py`), which calls
`answer_question_corrective(question)`. That starts the LangGraph state machine at `retrieve_node`.

**Step 1, `extract_filter()`** (`app/retrieval/metadata_filter.py`): checks the live list of known
companies against the question text, finds "Apple" appears literally; finds "2023" via the year
regex, no "not" nearby. Real result:
```python
{'company': {'$in': ['Apple']}, 'fiscal_year': {'$in': ['FY2023']}}
```

**Step 2, inside `retrieve_node`**: `companies = ['Apple']` (length 1), `years = ['FY2023']`
(length 1). `build_entities(['Apple'], ['FY2023'])` returns `None`, because neither condition for
multi-entity treatment is met (not more than one company, not more than one year of the same
company). So this question takes the simple path: one single call to
`store.similarity_search(question, k=20, filter=search_filter)`.

**The real top 5 results, by cosine distance** (lower is closer):

| Rank | Distance | Section | What it is |
|---|---|---|---|
| 1 | 0.2965 | Item 7 (MD&A) | Prose discussion of the financial statements |
| 2 | 0.3648 | Item 7 (MD&A) | A footnote about revenue recognition |
| 3 | 0.3901 | Item 8 | "See accompanying Notes..." boilerplate |
| 4 | 0.3948 | Item 8 | A product-category revenue table (iPhone, Mac, iPad...) |
| 5 | 0.3980 | Item 7 (MD&A) | Prose about Q4 2023 product launches |

Notice: **the actual income statement table containing $96,995M is not in the top 5.** It ranks
**#11** out of the full k=20 list. This is the real, live version of a lesson documented earlier in
the project (Bug 2, Section 5): a dense table listing 24 different line items across 3 years of
columns doesn't embed as sharply toward a single-fact question as a shorter, more conversational
prose passage does, even with the "Table reporting:" caption helping. The caption made the table
rank well enough to fit inside k=20 (it used to rank around #35 out of ~154 chunks before that fix
existed), but it still isn't a top-5 match by embedding distance alone. This is exactly why
`retrieve_node` uses k=20 (not k=5) before handing everything to the grader and generator, precision
at rank 1 was never good enough on its own for this corpus.

There is also a **second** table at rank **#14**, Apple's Consolidated Statements of Comprehensive
Income, which separately starts with "Net income" as its own first line (comprehensive income
statements restate net income before adding unrealized gains/losses). Both #11 and #14 genuinely
contain the figure.

**Step 3, `format_context()`** wraps all 20 chunks, in rank order, as:
```
<evidence id="1" source="Apple, FY2023, Item 7. Management's Discussion and Analysis...">
The following discussion should be read in conjunction with...
</evidence>

<evidence id="2" source="...">
...
</evidence>
```
...and so on through `id="20"`. The table at similarity rank #11 becomes `id="11"` here (the
`<evidence>` numbering follows retrieval rank, so it lines up 1:1 with the table above).

**Step 4, `grade_node`**: sends all 20 wrapped chunks plus `GRADE_PROMPT` to the LLM. Real response:
```json
{"sufficient": true}
```
(6,088 input tokens, 6 output tokens.) **`route_after_grade`** sees `sufficient=True` and goes
straight to `generate`, skipping `rewrite` and `abstain` entirely, no retry needed for this question.

**Step 5, `generate_node`**: sends the same 20 chunks plus `GENERATE_PROMPT` (the injection-hardened
one) to the LLM. Real answer:
```
Apple's net income for fiscal year 2023 was $96,995 million [11][14].
```
(6,706 input tokens, 21 output tokens.) The model cited exactly the two chunks that actually contain
the figure, evidence ids 11 and 14, matching the real similarity-search ranks worked out above.

**Step 6, `verify_citations("...$96,995 million [11][14].", 20)`**: extracts `{11, 14}` from the
answer text via regex, checks both are within `1..20`. Real result: `invalid_citations = []`, an
empty list, meaning every citation the model made was real.

**What comes back to the API caller**, assembled by `answer_question_corrective()`:
```json
{
  "answer": "Apple's net income for fiscal year 2023 was $96,995 million [11][14].",
  "abstained": false,
  "invalid_citations": [],
  "chunks_used": [ /* all 20 chunks, each with section/company/ticker/fiscal_year/form_type/page/is_table/text */ ],
  "latency_seconds": 5.04,
  "input_tokens": 12977,
  "output_tokens": 33
}
```
(input/output tokens summed across both the grade call and the generate call.)

### What would have happened differently

**If the grader had said `"sufficient": false`** on the first attempt: `route_after_grade` would send
control to `rewrite_node`, which asks `REWRITE_PROMPT` for a better-phrased search query, increments
`attempts` to 1, and loops back to `retrieve_node`. `retrieve_node` runs the search again with the new
query and **merges** the new results into the existing list, deduplicating by exact chunk text (so
already-found chunks don't get counted twice). This can happen up to `MAX_ATTEMPTS = 2` times total.
If the grader is still unsatisfied after the second rewrite, `route_after_grade` sends control to
`abstain_node` instead of `generate`, which returns a fixed "insufficient evidence" message and
`abstained=True`, with no generation call at all, costing nothing extra.

**If the question had named two companies** (e.g. Q16, "Between Apple's and Microsoft's fiscal year
2023 10-Ks, which company reported the higher operating margin?"): `build_entities()` would return
two entities, `[("Apple", {...filter...}), ("Microsoft", {...filter...})]`. `decompose_query()` would
be called once (its result cached in `state["company_queries"]` so it isn't repeated across rewrite
loops) to get one standalone, entity-focused question per company. `retrieve_node` then runs a
**separate** `k=30` search per entity and merges all the results together, specifically so that
whichever entity happens to have more chunks in the corpus, or happens to embed more favorably,
doesn't crowd out the other one's fair share of the final evidence set.

---

## 9. Current Status

**Project complete.** Every phase of the amended spec is built and measured. As of today,
2026-09-13, a full live re-verification was run after a complete environment restart (fresh Docker
container, fresh test run, fresh API calls, nothing recycled from an old run):

- Full test suite: **10/10 passing**, including the two tests that need a live database and a live
  embedding call.
- Fresh end-to-end harness run against the real production pipeline: **25/25 correct, 25/25
  faithful**, cost $0.3386, average latency 9.03 seconds.

Nothing is pending. The only two items not fully built are both deliberate, disclosed choices, not
gaps: recursive/hierarchical chunking (permanently descoped by Shahram), and testing hybrid
search/reranking specifically layered on top of corrective RAG (deferred by Shahram's own choice, to
be picked up later if wanted).
