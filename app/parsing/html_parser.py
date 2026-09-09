import re
from bs4 import BeautifulSoup

HEADING_PATTERN = re.compile(r"^Item\s+\d+[A-Za-z]?\.")


def clean_text(text):
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def parse_filing(html_path):
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    tables = extract_tables(soup)
    heading_texts = find_headings(soup)
    flat_text = clean_text(soup.get_text(separator=" "))

    sections = split_into_sections(flat_text, heading_texts)
    for section in sections:
        section["elements"] = split_section_text(section.pop("text"), tables)

    return sections


def extract_tables(soup):
    tables = {}
    for i, table_tag in enumerate(soup.find_all("table")):
        rows = []
        for tr in table_tag.find_all("tr"):
            cells = [cell.get_text(strip=True) for cell in tr.find_all(["td", "th"])]
            if any(cells):
                rows.append(cells)
        tables[i] = rows
        table_tag.replace_with(f"[[TABLE_{i}]]")
    return tables


def find_headings(soup):
    headings = []
    for span in soup.find_all("span"):
        style = span.get("style", "")
        if "font-weight:700" not in style:
            continue
        text = clean_text(span.get_text())
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
