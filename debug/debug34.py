import re
from bs4 import BeautifulSoup

files = {
    "Microsoft FY2023": r"data\filings\Microsoft\2023\sec-edgar-filings\MSFT\10-K\0000950170-23-035122\primary-document.html",
    "Walmart FY2023": r"data\filings\Walmart\2023\sec-edgar-filings\WMT\10-K\0000104169-23-000020\primary-document.html",
}

for name, path in files.items():
    with open(path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    flat = re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()

    print(f"=== {name} ===")
    # find occurrences of "Form 10-K" and print surrounding context to see the page-marker shape
    matches = list(re.finditer(r".{25}Form 10-K.{15}", flat))
    seen = set()
    count = 0
    for m in matches:
        snippet = m.group()
        if snippet not in seen:
            seen.add(snippet)
            print(f"  {snippet!r}")
            count += 1
        if count >= 6:
            break
    print()
