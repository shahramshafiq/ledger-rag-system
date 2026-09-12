import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from eval.run_harness import judge_answer, check_recall
from app.retrieval.corrective_rag import answer_question_corrective
from app.utils.costs import calculate_input_cost, calculate_output_cost, calculate_total_cost
from app.config import settings

qid = sys.argv[1]
with open("data/golden_dataset.json", encoding="utf-8") as f:
    golden = json.load(f)
q = next(q for q in golden["questions"] if q["id"] == qid)

result = answer_question_corrective(q["question"])
recall = check_recall(q.get("source_document"), result["chunks_used"])
context = "\n\n".join(f"[{i}] {c['text']}" for i, c in enumerate(result["chunks_used"], start=1))
correct, faithful = judge_answer(q["question"], q["category"], q["expected_answer"], result["answer"], context)
cost = calculate_total_cost(
    calculate_input_cost(result["input_tokens"], settings.input_price),
    calculate_output_cost(result["output_tokens"], settings.output_price),
)
print(f"{qid} ({q['category']}): recall={recall} correct={correct} faithful={faithful} latency={result['latency']:.2f}s cost={cost:.5f}")
print(f"ANSWER: {result['answer'][:300]}")

# replace this question's row in results.csv (the ERROR row) with the real result
with open("eval/results.csv", encoding="utf-8") as f:
    rows = list(csv.reader(f))
header, rest = rows[0], rows[1:]
new_rows = [r for r in rest if not (r[0] == "corrective" and r[1] == qid)]
new_rows.append(["corrective", qid, q["category"], recall, correct, faithful, round(result["latency"], 2), round(cost, 5)])
with open("eval/results.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(new_rows)
print("results.csv updated")
