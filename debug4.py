from app.retrieval.corrective_rag import answer_question_corrective

questions = [
    ("Q09", "According to Apple's fiscal year 2022 income statement, what was the operating margin?", "approximately 30.3% ($119,437M operating income / $394,328M revenue)"),
    ("Q13", "What was Apple's operating income specifically for fiscal year 2022 (not fiscal year 2023)?", "$119,437 million"),
    ("Q15", "Comparing Apple's fiscal year 2022 and fiscal year 2023 10-Ks, did net income increase or decrease, and by roughly how much?", "Decreased, from $99,803 million to $96,995 million, a decline of about $2,808 million (approximately 2.8%)"),
    ("Q16", "Between Apple's and Microsoft's fiscal year 2023 10-Ks, which company reported the higher operating margin?", "Microsoft (approximately 41.8%) reported a higher operating margin than Apple (approximately 29.8%)"),
    ("Q19", "Across all four companies in the corpus, which one reported the highest net income in fiscal year 2023?", "Apple, at $96,995 million (vs. Microsoft $72,361M, JPMorgan $49,552M, Walmart $11,680M)"),
]

for qid, question, expected in questions:
    result = answer_question_corrective(question)
    print(f"=== {qid} ===")
    print(f"EXPECTED: {expected}")
    print(f"GOT: {result['answer']}")
    print(f"CHUNKS USED ({len(result['chunks_used'])} total):")
    for c in result["chunks_used"]:
        print(f"  {c['company']} {c['fiscal_year']}, {c['section']}, table={c['is_table']}")
    print()
