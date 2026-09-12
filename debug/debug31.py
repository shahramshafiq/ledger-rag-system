from app.retrieval.corrective_rag import answer_question_corrective
from eval.run_harness import judge_answer

question = "What was Microsoft's net income for fiscal year 2023?"
expected = "$72,361 million"

result = answer_question_corrective(question)
context = "\n\n".join(f"[{i}] {c['text']}" for i, c in enumerate(result["chunks_used"], start=1))
print(f"ANSWER: {result['answer']}")
print(f"context length now passed to judge: {len(context)} chars (previously capped at 4000)")

correct, faithful = judge_answer(question, "direct_lookup", expected, result["answer"], context)
print(f"correct={correct}, faithful={faithful}")
