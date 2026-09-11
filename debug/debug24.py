import json
import psycopg
from app.config import settings
from app.vectorstore.store import get_vector_store
from app.retrieval.metadata_filter import extract_filter
from app.retrieval.corrective_rag import answer_question_corrective, GRADE_PROMPT, format_context, get_llm, parse_json

question = "What was Apple's net income for fiscal year 2023?"

print("=" * 70)
print("STEP 1: metadata filter extraction")
print("=" * 70)
search_filter = extract_filter(question, "ledger_chunks")
print(f"extract_filter({question!r}) -> {search_filter}")

print("\n" + "=" * 70)
print("STEP 2: embed the question itself")
print("=" * 70)
store = get_vector_store("ledger_chunks")
q_embedding = store.embeddings.embed_query(question)
print(f"Embedding dimensions: {len(q_embedding)}")
print(f"First 15 numbers: {q_embedding[:15]}")

print("\n" + "=" * 70)
print("STEP 3: vector similarity search (k=20, filtered)")
print("=" * 70)
results = store.similarity_search_with_score(question, k=20, filter=search_filter)
for i, (doc, score) in enumerate(results[:8], 1):
    print(f"#{i} score={score:.4f} table={doc.metadata.get('is_table')} section={doc.metadata.get('section')}")
    print(f"   {doc.page_content[:150]!r}")

print("\n" + "=" * 70)
print("STEP 4: pull the actual stored embedding of the top chunk from Postgres")
print("=" * 70)
top_doc = results[0][0]
dsn = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
with psycopg.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT embedding FROM langchain_pg_embedding WHERE document = %s LIMIT 1",
            (top_doc.page_content,),
        )
        row = cur.fetchone()
        raw = row[0]
        print(f"Raw type from DB: {type(raw)}")
        print(f"First 200 chars: {str(raw)[:200]}")

print("\n" + "=" * 70)
print("STEP 5: the grading step (real call)")
print("=" * 70)
context = format_context([doc for doc, _ in results])
grade_prompt_filled = GRADE_PROMPT.format(question=question, context=context[:4000])
grade_response = get_llm().invoke(grade_prompt_filled)
verdict = parse_json(grade_response.content)
print(f"Grader's raw response: {grade_response.content!r}")
print(f"Parsed verdict: {verdict}")

print("\n" + "=" * 70)
print("STEP 6: full end-to-end run through the real graph")
print("=" * 70)
result = answer_question_corrective(question)
print(f"Final answer: {result['answer']}")
print(f"Chunks used: {len(result['chunks_used'])}")
print(f"Input tokens: {result['input_tokens']}, Output tokens: {result['output_tokens']}")
print(f"Latency: {result['latency']:.2f}s")
