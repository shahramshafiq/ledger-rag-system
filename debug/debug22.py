from app.parsing.html_parser import parse_filing

filings = [
    ("Apple", r"data\filings\Apple\2023\sec-edgar-filings\AAPL\10-K\0000320193-23-000106\primary-document.html"),
    ("Walmart", r"data\filings\Walmart\2023\sec-edgar-filings\WMT\10-K\0000104169-23-000020\primary-document.html"),
    ("JPMorgan", r"data\filings\JPMorgan\2023\sec-edgar-filings\JPM\10-K\0000019617-24-000225\primary-document.html"),
]

for company, path in filings:
    sections = parse_filing(path)
    print(f"\n\n{'='*20} {company} {'='*20}")
    for section in sections:
        if "1A" in section["heading"]:
            print(f"heading={section['heading']!r}")
            full_text = " ".join(e["text"] for e in section["elements"] if e["type"] == "paragraph")
            print(full_text[:3000])
            print("...[TRUNCATED]..." if len(full_text) > 3000 else "")
            break
