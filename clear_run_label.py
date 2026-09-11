import csv
import sys

label = sys.argv[1]
path = "eval/results.csv"

with open(path, encoding="utf-8") as f:
    rows = list(csv.reader(f))

header, rest = rows[0], rows[1:]
kept = [r for r in rest if r[0] != label]
print(f"Removed {len(rest) - len(kept)} rows with label '{label}', kept {len(kept)}")

with open(path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(kept)
