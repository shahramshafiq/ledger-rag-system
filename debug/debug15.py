from app.parsing.html_parser import find_headings, clean_text
from bs4 import BeautifulSoup

path = r"data\filings\JPMorgan\2023\sec-edgar-filings\JPM\10-K\0000019617-24-000225\primary-document.html"
with open(path, encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

headings = find_headings(soup)
print(f"Total headings found (in document order): {len(headings)}")
for i, h in enumerate(headings):
    print(f"  {i}: {h!r}")
