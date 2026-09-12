from app.retrieval.corrective_rag import answer_question_corrective

question = "What was Microsoft's net income for fiscal year 2023?"
result = answer_question_corrective(question)
print(f"ANSWER: {result['answer']}")
print(f"ABSTAINED: {result['abstained']}")
print(f"EXPECTED: $72,361 million")
