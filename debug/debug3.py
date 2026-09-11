from app.retrieval.corrective_rag import answer_question_corrective

questions = [
    ("Q03", "What was Walmart's net income for the fiscal year ended January 31, 2023?", "$11,680 million"),
    ("Q06", "According to Apple's fiscal year 2023 income statement, what was the operating margin (operating income divided by revenue)?", "approximately 29.8% ($114,301M operating income / $383,285M revenue)"),
    ("Q09", "According to Apple's fiscal year 2022 income statement, what was the operating margin?", "approximately 30.3% ($119,437M operating income / $394,328M revenue)"),
]

for qid, question, expected in questions:
    result = answer_question_corrective(question)
    print(f"=== {qid} ===")
    print(f"EXPECTED: {expected}")
    print(f"GOT: {result['answer']}")
    print()
