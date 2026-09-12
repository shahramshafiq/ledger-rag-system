from app.parsing.html_parser import parse_filing
from app.chunking.structure_aware import chunk_structure_aware

files = {
    "Apple FY2022": r"data\filings\Apple\2022\sec-edgar-filings\AAPL\10-K\0000320193-22-000108\primary-document.html",
    "JPMorgan FY2023": r"data\filings\JPMorgan\2023\sec-edgar-filings\JPM\10-K\0000019617-24-000225\primary-document.html",
    "Microsoft FY2023": r"data\filings\Microsoft\2023\sec-edgar-filings\MSFT\10-K\0000950170-23-035122\primary-document.html",
    "Walmart FY2023": r"data\filings\Walmart\2023\sec-edgar-filings\WMT\10-K\0000104169-23-000020\primary-document.html",
}

for name, path in files.items():
    sections = parse_filing(path)
    chunks = chunk_structure_aware(sections, {"company": "X", "ticker": "X", "fiscal_year": "X", "form_type": "10-K"})
    pages = [c.metadata.get("page") for c in chunks]
    with_page = sum(1 for p in pages if p is not None)
    distinct_pages = sorted(set(p for p in pages if p is not None))
    print(f"{name}: {len(chunks)} chunks, {with_page} with a page number ({with_page/len(chunks)*100:.0f}%)")
    if distinct_pages:
        print(f"  page range: {distinct_pages[0]}-{distinct_pages[-1]}, {len(distinct_pages)} distinct pages")
        # check monotonically non-decreasing (allowing for minor extraction noise)
        non_monotonic = sum(1 for i in range(1, len(pages)) if pages[i] is not None and pages[i-1] is not None and pages[i] < pages[i-1])
        print(f"  chunks where page went backwards vs previous chunk: {non_monotonic} (some expected near section boundaries)")
    else:
        print(f"  no page markers found (expected for this vendor's HTML format)")
    print(f"  first 5 chunks' pages: {pages[:5]}")
    print()
