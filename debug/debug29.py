import json
from app.retrieval.corrective_rag import answer_question_corrective, get_llm
from eval.run_harness import JUDGE_PROMPT

question = "What was Microsoft's net income for fiscal year 2023?"
expected = "$72,361 million"

result = answer_question_corrective(question)
print(f"ANSWER: {result['answer']}\n")

chunks_used = result["chunks_used"]

# OLD context format: plain, unnumbered (what run_harness.py currently builds)
old_context = "\n\n".join(c["text"] for c in chunks_used)

# NEW context format: numbered to match the citation ids the answer actually uses
new_context = "\n\n".join(f"[{i}] {c['text']}" for i, c in enumerate(chunks_used, start=1))

for label, context in [("OLD (unnumbered)", old_context), ("NEW (numbered, matches citations)", new_context)]:
    prompt = JUDGE_PROMPT.format(
        question=question, category="direct_lookup", expected_answer=expected,
        generated_answer=result["answer"], context=context[:4000],
    )
    response = get_llm().invoke(prompt)
    content = response.content.strip()
    if content.startswith("```"):
        content = content.strip("`").removeprefix("json").strip()
    verdict = json.loads(content)
    print(f"{label} -> {verdict}")
