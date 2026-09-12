from app.retrieval.corrective_rag import answer_question_corrective
from eval.run_harness import judge_answer

question = "Comparing Walmart's fiscal year 2022 and fiscal year 2023 10-Ks, did net income increase or decrease?"
expected = "Decreased, from $13,673 million to $11,680 million (a decline of about 14.6%)"

result = answer_question_corrective(question)
print(f"ANSWER: {result['answer']}")
print(f"\nEXPECTED: {expected}")
print(f"\nChunks used: {len(result['chunks_used'])}")

context = "\n\n".join(f"[{i}] {c['text']}" for i, c in enumerate(result["chunks_used"], start=1))
correct, faithful = judge_answer(question, "cross_document", expected, result["answer"], context)
print(f"\ncorrect={correct}, faithful={faithful}")
