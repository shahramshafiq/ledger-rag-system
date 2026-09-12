from app.retrieval.corrective_rag import answer_question_corrective

question = "What was Apple's operating income specifically for fiscal year 2022 (not fiscal year 2023)?"
result = answer_question_corrective(question)
print(f"ANSWER: {result['answer']}")
print(f"ABSTAINED: {result['abstained']}")
print(f"INVALID CITATIONS: {result['invalid_citations']}")
print(f"\nSample chunk metadata (first 3 used):")
for c in result["chunks_used"][:3]:
    print(f"  company={c['company']} fiscal_year={c['fiscal_year']} section={c['section'][:40]} is_table={c['is_table']}")
