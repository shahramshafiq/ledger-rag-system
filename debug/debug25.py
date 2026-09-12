import csv
from collections import defaultdict

rows = defaultdict(list)
with open("eval/results.csv", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        rows[row["run_label"]].append(row)

def p95(values):
    values = sorted(values)
    idx = int(round(0.95 * (len(values) - 1)))
    return values[idx]

for label, qs in rows.items():
    latencies = [float(r["latency_sec"]) for r in qs if r["latency_sec"]]
    print(f"{label}: avg={sum(latencies)/len(latencies):.2f}s  p95={p95(latencies):.2f}s  n={len(latencies)}")

print()
corrective = rows["corrective"]
unanswerable = [r for r in corrective if r["category"] == "unanswerable"]
answerable = [r for r in corrective if r["category"] != "unanswerable"]

correct_refusals = sum(1 for r in unanswerable if r["correct"] == "True")
incorrect_refusals = sum(1 for r in answerable if r["correct"] == "False" and r["category"] not in ())

print(f"Unanswerable questions (should refuse): {len(unanswerable)}, correctly refused: {correct_refusals} ({correct_refusals/len(unanswerable)*100:.0f}%)")
print(f"Answerable questions (should NOT refuse): {len(answerable)}, wrongly marked incorrect: {sum(1 for r in answerable if r['correct']=='False')}")
for r in answerable:
    if r["correct"] == "False":
        print(f"  {r['question_id'] if 'question_id' in r else r.get('question_id')}: correct=False")
