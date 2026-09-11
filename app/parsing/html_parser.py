import re
from bs4 import BeautifulSoup

HEADING_PATTERN = re.compile(r"^Item\s+\d+[A-Za-z]?\.", re.IGNORECASE)
FONT_SIZE_PATTERN = re.compile(r"font-size:(\d+)pt")


def clean_text(text):
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def parse_filing(html_path):
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    heading_texts = find_headings(soup)
    tables = extract_tables(soup, heading_texts)
    flat_text = clean_text(soup.get_text(separator=" "))

    sections = split_into_sections(flat_text, heading_texts)
    for section in sections:
        section["elements"] = split_section_text(section.pop("text"), tables)

    return sections


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


def split_section_text(text, tables):
    elements = []
    parts = re.split(r"(\[\[TABLE_\d+\]\])", text)
    for part in parts:
        match = re.match(r"\[\[TABLE_(\d+)\]\]", part)
        if match:
            table_id = int(match.group(1))
            elements.append({"type": "table", "rows": tables[table_id]})
        else:
            cleaned = part.strip()
            if cleaned:
                elements.append({"type": "paragraph", "text": cleaned})
    return elements