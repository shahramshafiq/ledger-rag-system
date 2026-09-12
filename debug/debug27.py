from app.retrieval.corrective_rag import GRADE_PROMPT, format_context, get_llm, parse_json
from app.retrieval.metadata_filter import extract_filter
from app.vectorstore.store import get_vector_store

question = "What was Microsoft's net income for fiscal year 2023?"
search_filter = extract_filter(question, "ledger_chunks")
print(f"filter: {search_filter}")

store = get_vector_store("ledger_chunks")
docs = store.similarity_search(question, k=20, filter=search_filter)
print(f"retrieved {len(docs)} chunks")

context = format_context(docs)
print(f"\ncontext length: {len(context)} chars, first 4000 used for grading")
print(f"\nDoes '72,361' appear anywhere in full context? {'72,361' in context}")
print(f"Does '72,361' appear in the TRUNCATED (first 4000 chars) context? {'72,361' in context[:4000]}")
print(f"Does 'Net income' appear in truncated context? {'Net income' in context[:4000]}")

prompt = GRADE_PROMPT.format(question=question, context=context[:4000])
response = get_llm().invoke(prompt)
print(f"\nGrader raw response: {response.content!r}")
verdict = parse_json(response.content)
print(f"Parsed verdict: {verdict}")

print(f"\n--- last 500 chars of the truncated context (what the grader saw at the end) ---")
print(context[:4000][-500:])
