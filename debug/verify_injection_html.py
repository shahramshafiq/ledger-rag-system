import tempfile
from app.parsing.html_parser import parse_filing
from app.chunking.structure_aware import chunk_structure_aware
from debug.prompt_injection_test import INJECTED_BODY_TEXT_HTML, INJECTED_TABLE_CELL_HTML, ATTACK_PHRASE

for name, html in [("BODY", INJECTED_BODY_TEXT_HTML), ("TABLE", INJECTED_TABLE_CELL_HTML)]:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        path = f.name
    sections = parse_filing(path)
    print(f"=== {name}: {len(sections)} section(s) found ===")
    for s in sections:
        print(f"  heading={s['heading']!r}, {len(s['elements'])} element(s)")
        for e in s["elements"]:
            print(f"    type={e['type']}, has_attack_phrase={ATTACK_PHRASE in str(e)}")

    chunks = chunk_structure_aware(sections, {"company": "InjectionTestCo", "ticker": "INJ", "fiscal_year": "TEST"})
    print(f"  -> {len(chunks)} chunk(s) produced, attack phrase present in a chunk: {any(ATTACK_PHRASE in c.page_content for c in chunks)}")
    print()
