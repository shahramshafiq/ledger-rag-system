import re
from app.parsing.html_parser import parse_filing

path = r"data\filings\Microsoft\2023\sec-edgar-filings\MSFT\10-K\0000950170-23-035122\primary-document.html"
sections = parse_filing(path)

print("All section headings found:")
for section in sections:
    print(f"  {section['heading']!r}")

for section in sections:
    if "1A" in section["heading"]:
        print(f"\n=== SECTION: {section['heading']!r} ===")
        for element in section["elements"]:
            if element["type"] == "paragraph" and re.search(r"compet", element["text"], re.IGNORECASE):
                print(element["text"])
                print("---")
