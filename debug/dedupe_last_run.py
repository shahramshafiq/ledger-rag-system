import csv

with open("eval/results.csv", encoding="utf-8") as f:
    rows = list(csv.reader(f))

header, rest = rows[0], rows[1:]
label = "corrective"
non_target = [r for r in rest if r[0] != label]
target = [r for r in rest if r[0] == label]

# keep only the LAST occurrence of each question_id for this label (the most recent run)
last_by_qid = {}
for r in target:
    last_by_qid[r[1]] = r
deduped_target = [last_by_qid[qid] for qid in sorted(last_by_qid, key=lambda q: int(q[1:]))]

print(f"Had {len(target)} '{label}' rows, kept {len(deduped_target)} (most recent per question)")

with open("eval/results.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(non_target)
    writer.writerows(deduped_target)
