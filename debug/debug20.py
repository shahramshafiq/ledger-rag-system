from app.retrieval.corrective_rag import answer_question_corrective

questions = [
    ("Q04", "What was JPMorgan Chase's net income for fiscal year 2023?", "$49,552 million"),
    ("Q15", "Comparing Apple's fiscal year 2022 and fiscal year 2023 10-Ks, did net income increase or decrease, and by roughly how much?", "Decreased, from $99,803 million to $96,995 million"),
    ("Q16", "Between Apple's and Microsoft's fiscal year 2023 10-Ks, which company reported the higher operating margin?", "Microsoft (~41.8%) higher than Apple (~29.8%)"),
    ("Q18", "Comparing JPMorgan Chase's fiscal year 2022 and fiscal year 2023 10-Ks, what was the dollar change in net income?", "Increased by ~$11,876 million, from $37,676M to $49,552M"),
    ("Q19", "Across all four companies in the corpus, which one reported the highest net income in fiscal year 2023?", "Apple, at $96,995 million"),
]

for qid, question, expected in questions:
    result = answer_question_corrective(question)
    print(f"=== {qid} ===")
    print(f"EXPECTED: {expected}")
    print(f"GOT: {result['answer'][:400]}")
    print()
