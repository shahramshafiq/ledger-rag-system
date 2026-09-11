from app.services.query_service import answer_question

questions_to_debug = [
    ("Q02", "What was Microsoft's net income for fiscal year 2023?", "$72,361 million"),
    ("Q06", "According to Apple's fiscal year 2023 income statement, what was the operating margin (operating income divided by revenue)?", "approximately 29.8% ($114,301M operating income / $383,285M revenue)"),
    ("Q15", "Comparing Apple's fiscal year 2022 and fiscal year 2023 10-Ks, did net income increase or decrease, and by roughly how much?", "Decreased, from $99,803 million to $96,995 million, a decline of about $2,808 million (approximately 2.8%)"),
]

for qid, question, expected in questions_to_debug:
    result = answer_question(question)
    print(f"=== {qid} ===")
    print(f"QUESTION: {question}")
    print(f"EXPECTED: {expected}")
    print(f"GOT: {result['answer']}")
    print()