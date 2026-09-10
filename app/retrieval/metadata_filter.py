import re

COMPANY_NAMES = ["Apple", "Microsoft", "Walmart", "JPMorgan"]


def extract_filter(question):
    companies = [c for c in COMPANY_NAMES if c in question]
    years = sorted(set(f"FY{y}" for y in re.findall(r"20\d{2}", question)))

    filters = {}
    if companies:
        filters["company"] = {"$in": companies}
    if years:
        filters["fiscal_year"] = {"$in": years}

    return filters or None