# Ledger

A question-answering service over SEC 10-K filings. Ask a question about one of the companies in the
corpus, get back an answer grounded in the actual retrieved passages, plus the exact chunks used to
produce it. When the retrieved evidence isn't good enough to answer confidently, the service says so
explicitly instead of generating an unsupported guess.

Every design decision in this project (chunking strategy, retrieval technique, the corrective RAG
pipeline) was chosen based on a measurement against this project's own corpus, not general best
practice. See [`docs/NOTES.md`](docs/NOTES.md) for the full measurement journey: what was tried, what
the numbers showed, and what was rejected and why.

## Corpus

8 filings: Apple, Microsoft, Walmart, and JPMorgan Chase, fiscal years 2022 and 2023 each. Apple and
Microsoft are the same-industry pair, used to test whether the system can tell apart two competitors'
near-identical filing language.

## Setup

**Prerequisites**: Python 3.12, Docker, an OpenAI API key.

1. Clone the repo and create a virtual environment:
   ```bash
   python -m venv venv
   venv/Scripts/pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your own OpenAI API key:
   ```bash
   cp .env.example .env
   ```

3. Start Postgres with the pgvector extension:
   ```bash
   docker run --name ledger-postgres -e POSTGRES_PASSWORD=devpassword -e POSTGRES_DB=ledger -p 5432:5432 -d pgvector/pgvector:pg16
   ```
   Then enable the extension once:
   ```bash
   docker exec -it ledger-postgres psql -U postgres -d ledger -c "CREATE EXTENSION IF NOT EXISTS vector;"
   ```

4. Download the corpus (not committed to the repo, it's regenerable and ~200MB):
   ```bash
   venv/Scripts/python.exe download_filings.py
   ```

5. Ingest all 8 filings into the vector store:
   ```bash
   venv/Scripts/python.exe -m app.ingest_all
   ```

## Running the service

```bash
venv/Scripts/uvicorn app.main:app --reload --port 8000
```

**`GET /health`** — liveness check.

**`POST /query`** — ask a question, JSON body:
```json
{"question": "What was Apple's net income for fiscal year 2023?"}
```
Returns the generated answer, the exact chunks used (company, ticker, fiscal year, form type, section,
and page number where the source filing's own page markers made one extractable, enough to locate each
passage in the original document), token counts, and latency. Every factual claim in the answer cites
the chunk id(s) it came from (e.g. `"...was $96,995 million [3]."`); `invalid_citations` lists any cited
id that doesn't correspond to a chunk actually retrieved, always empty in practice, verified against a
live adversarial attempt, see `docs/NOTES.md`. If the retrieved evidence is judged insufficient after
retrying with a rewritten search query, the response has `"abstained": true` and a fixed
insufficient-evidence message instead of a generated answer.

**`POST /documents`** — ingest a new filing. `multipart/form-data` with a `file` (the filing's HTML) plus
`company`, `ticker`, `fiscal_year` fields, and an optional `form_type` (defaults to `"10-K"`). Returns a
`job_id` immediately; ingestion runs in the background.

**`GET /documents/{job_id}/stream`** — watch ingestion progress live via Server-Sent Events.

## Evaluation harness

25 hand-written questions with real, verified expected answers, grounded in each company's actual
reported financial figures (`data/golden_dataset.json`). Scores recall@5, answer correctness,
faithfulness, latency, and cost per question, one command:

```bash
venv/Scripts/python.exe -m eval.run_harness <run_label> <collection_name> [--rerank] [--filter] [--hybrid] [--corrective]
```

Results append to `eval/results.csv`, one row per question per run, so multiple pipeline configurations
sit side by side for comparison. The winning configuration:

```bash
venv/Scripts/python.exe -m eval.run_harness corrective ledger_chunks --corrective
```

## Tests

```bash
venv/Scripts/pytest tests/ -v
```

Covers metadata-filter isolation (a question naming one company never retrieves another's chunks) and
citation-ID verification (a cited chunk ID must actually correspond to a chunk that was retrieved).

## Project structure

- `app/parsing/` — turns a raw filing's HTML into structured sections, paragraphs, and tables.
- `app/chunking/` — cuts parsed sections into searchable chunks (`structure_aware.py` is the winning
  strategy; `agentic.py` is a tested alternative).
- `app/retrieval/` — the corrective RAG pipeline (`corrective_rag.py`), metadata filtering, and the
  BM25/reranker experiments (kept for the record, not used in the final pipeline).
- `app/routes/`, `app/main.py` — the FastAPI service.
- `eval/` — the evaluation harness and results.
- `tests/` — automated correctness tests.
- `debug/` — one-off investigation scripts used while diagnosing specific retrieval failures, kept for
  the record of how each bug was actually found.
- `docs/NOTES.md` — the full write-up: what was measured at each phase, what was kept, what didn't
  justify its cost.
