import re
from bs4 import BeautifulSoup

HEADING_PATTERN = re.compile(r"^Item\s+\d+[A-Za-z]?\.", re.IGNORECASE)
FONT_SIZE_PATTERN = re.compile(r"font-size:(\d+)pt")

# running page-footer banners, verified directly against the real downloaded filings, not guessed.
# Two vendor shapes seen so far: page number after a pipe ("Apple Inc. | 2022 Form 10-K | 58") or page
# number trailing directly with just a space ("JPMorgan Chase & Co./2023 Form 10-K 45", the "|" seen
# in this project's own earlier debug output turned out to be an artifact of table_to_text()'s own
# " | ".join, not real text in the filing, caught by testing the regex against the actual raw text
# instead of trusting an intermediate rendering). Capped at 3 digits so a stray 4-digit year mention
# can never be mistaken for a page number. Microsoft and Walmart's filings were checked directly too
# and simply don't repeat a page number in the extracted text this way, their HTML must render
# pagination as something that doesn't survive text extraction. For those, page stays genuinely
# unknown rather than guessed.
PAGE_MARKER_PATTERNS = [
    re.compile(r".{3,40}?Form\s*10-K\s*\|\s*(\d{1,3})\b"),
    re.compile(r"\bForm\s*10-K\s+(\d{1,3})\b"),
]


def clean_text(text):
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def parse_filing(html_path):
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    heading_texts = find_headings(soup)
    tables = extract_tables(soup, heading_texts)
    flat_text = clean_text(soup.get_text(separator=" "))
    flat_text = mark_pages(flat_text)

    sections = split_into_sections(flat_text, heading_texts)
    page_state = {"current": None}
    for section in sections:
        section["elements"] = split_section_text(section.pop("text"), tables, page_state)

    return sections


def mark_pages(flat_text):
    # replace each running page-footer banner with a [[PAGE_N]] sentinel, the same trick already used
    # for tables, so split_section_text can track "what page are we on" as it walks through the text
    # without needing to keep the banner text itself (which would otherwise still need filtering as
    # junk). Sentinel length differs from the original text, that's fine, headings are located with
    # flat_text.find() from a moving cursor, not fixed offsets, so this replacement doesn't disturb them.
    for pattern in PAGE_MARKER_PATTERNS:
        flat_text = pattern.sub(lambda m: f"[[PAGE_{m.group(1)}]]", flat_text)
    return flat_text


def extract_tables(soup, heading_texts):
    tables = {}
    for i, table_tag in enumerate(soup.find_all("table")):
        table_text = clean_text(table_tag.get_text())
        if any(table_text.startswith(h) for h in heading_texts):
            continue  # this "table" is really just a heading laid out in table cells, leave it as normal text

        rows = []
        for tr in table_tag.find_all("tr"):
            cells = [cell.get_text(strip=True) for cell in tr.find_all(["td", "th"])]
            if any(cells):
                rows.append(cells)

        if len(rows) < 2:
            continue  # a single-row "table" is layout markup (e.g. a page-footer banner reused as a
            # table for visual alignment), not real data, a real financial table always compares
            # multiple line items or periods across rows, leave it as normal text instead of dropping it

        tables[i] = rows
        table_tag.replace_with(f"[[TABLE_{i}]]")
    return tables


def find_headings(soup):
    headings = []
    for tag in soup.find_all(style=True):
        style = tag.get("style", "")
        is_bold = "font-weight:700" in style or "font-weight:bold" in style
        size_match = FONT_SIZE_PATTERN.search(style)
        is_large = bool(size_match) and int(size_match.group(1)) >= 11
        if not (is_bold or is_large):
            continue
        text = clean_text(tag.get_text())
        if HEADING_PATTERN.match(text):
            headings.append(text)
    return headings


def split_into_sections(flat_text, heading_texts):
    positions = []
    search_from = 0
    for heading in heading_texts:
        idx = flat_text.find(heading, search_from)
        if idx == -1:
            continue
        positions.append((idx, heading))
        search_from = idx + len(heading)

    sections = []
    for i, (start, heading) in enumerate(positions):
        text_start = start + len(heading)
        text_end = positions[i + 1][0] if i + 1 < len(positions) else len(flat_text)
        sections.append({"heading": heading, "text": flat_text[text_start:text_end]})

    return sections


def split_section_text(text, tables, page_state):
    elements = []
    parts = re.split(r"(\[\[TABLE_\d+\]\]|\[\[PAGE_\d+\]\])", text)
    for part in parts:
        page_match = re.match(r"\[\[PAGE_(\d+)\]\]", part)
        if page_match:
            page_state["current"] = int(page_match.group(1))
            continue

        table_match = re.match(r"\[\[TABLE_(\d+)\]\]", part)
        if table_match:
            table_id = int(table_match.group(1))
            elements.append({"type": "table", "rows": tables[table_id], "page": page_state["current"]})
        else:
            cleaned = part.strip()
            if cleaned:
                elements.append({"type": "paragraph", "text": cleaned, "page": page_state["current"]})
    return elements