import re
from bs4 import BeautifulSoup

path = r"data\filings\JPMorgan\2023\sec-edgar-filings\JPM\10-K\0000019617-24-000225\primary-document.html"
with open(path, encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")
flat = re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()

# find a known real occurrence from earlier this session
idx = flat.find("JPMorgan Chase & Co./2023 Form 10-K")
print(f"Found literal string at index {idx}")
print(f"Surrounding text: {flat[max(0,idx-30):idx+50]!r}")

pattern = re.compile(r"\b(\d{1,4})\s*\|\s*.{3,60}?Form\s*10-K\b")
snippet = flat[max(0,idx-30):idx+50]
m = pattern.search(snippet)
print(f"Pattern match on snippet: {m}")
if m:
    print(f"  captured: {m.group(1)}")
