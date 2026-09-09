from sec_edgar_downloader import Downloader

filings = [
    ("AAPL", "Apple",     "2022", "2022-10-27", "2022-10-29"),
    ("AAPL", "Apple",     "2023", "2023-11-02", "2023-11-04"),
    ("MSFT", "Microsoft", "2022", "2022-07-27", "2022-07-29"),
    ("MSFT", "Microsoft", "2023", "2023-07-26", "2023-07-28"),
    ("WMT",  "Walmart",   "2022", "2022-03-17", "2022-03-19"),
    ("WMT",  "Walmart",   "2023", "2023-03-16", "2023-03-18"),
    ("JPM",  "JPMorgan",  "2022", "2023-02-20", "2023-02-22"),
    ("JPM",  "JPMorgan",  "2023", "2024-02-15", "2024-02-17"),
]

for ticker, company, year, after, before in filings:
    dl = Downloader("Shahram Shafiq", "shahramshafiqgoraya4363@gmail.com",
                     download_folder=f"data/filings/{company}/{year}")
    dl.get("10-K", ticker, after=after, before=before, download_details=True)