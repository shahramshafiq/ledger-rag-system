from app.retrieval.corrective_rag import answer_question_corrective

question = "What are the main risk themes that recur across the four companies' most recent (fiscal year 2023) 10-Ks?"
result = answer_question_corrective(question)
print("GOT:")
print(result["answer"])
print(f"\nChunks used: {len(result['chunks_used'])}")
companies_seen = set(c['company'] for c in result['chunks_used'])
print(f"Companies represented: {companies_seen}")
