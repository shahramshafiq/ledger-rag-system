from app.services.ingestion_service import ingest_filing
from app.chunking.agentic import chunk_agentic
from app.utils.costs import calculate_input_cost, calculate_output_cost, calculate_total_cost
from app.config import settings

COLLECTION = "ledger_chunks_agentic"
cost_tracker = {"input_tokens": 0, "output_tokens": 0}

filings = [
    (r"data\filings\Apple\2022\sec-edgar-filings\AAPL\10-K\0000320193-22-000108\primary-document.html", "Apple", "AAPL", "FY2022"),
    (r"data\filings\Apple\2023\sec-edgar-filings\AAPL\10-K\0000320193-23-000106\primary-document.html", "Apple", "AAPL", "FY2023"),
    (r"data\filings\Microsoft\2022\sec-edgar-filings\MSFT\10-K\0001564590-22-026876\primary-document.html", "Microsoft", "MSFT", "FY2022"),
    (r"data\filings\Microsoft\2023\sec-edgar-filings\MSFT\10-K\0000950170-23-035122\primary-document.html", "Microsoft", "MSFT", "FY2023"),
    (r"data\filings\Walmart\2022\sec-edgar-filings\WMT\10-K\0000104169-22-000012\primary-document.html", "Walmart", "WMT", "FY2022"),
    (r"data\filings\Walmart\2023\sec-edgar-filings\WMT\10-K\0000104169-23-000020\primary-document.html", "Walmart", "WMT", "FY2023"),
    (r"data\filings\JPMorgan\2022\sec-edgar-filings\JPM\10-K\0000019617-23-000231\primary-document.html", "JPMorgan", "JPM", "FY2022"),
    (r"data\filings\JPMorgan\2023\sec-edgar-filings\JPM\10-K\0000019617-24-000225\primary-document.html", "JPMorgan", "JPM", "FY2023"),
]

for path, company, ticker, fiscal_year in filings:
    count = ingest_filing(
        path, company, ticker, fiscal_year,
        lambda sections, metadata: chunk_agentic(sections, metadata, cost_tracker=cost_tracker),
        collection_name=COLLECTION,
    )
    print(f"{company} {fiscal_year}: {count} chunks")

ingestion_cost = calculate_total_cost(
    calculate_input_cost(cost_tracker["input_tokens"], settings.input_price),
    calculate_output_cost(cost_tracker["output_tokens"], settings.output_price),
)
print(f"\nTotal agentic chunking cost: ${ingestion_cost:.4f} ({cost_tracker['input_tokens']} input / {cost_tracker['output_tokens']} output tokens)")