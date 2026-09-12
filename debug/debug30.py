from app.retrieval.corrective_rag import answer_question_corrective

question = "What was Microsoft's net income for fiscal year 2023?"
result = answer_question_corrective(question)
chunks_used = result["chunks_used"]

numbered_context = "\n\n".join(f"[{i}] {c['text']}" for i, c in enumerate(chunks_used, start=1))
print(f"Total context length: {len(numbered_context)} chars, judge truncates to first 4000")
print(f"Total chunks: {len(chunks_used)}")

truncated = numbered_context[:4000]
for cited_id in [6, 16, 19]:
    marker = f"[{cited_id}] "
    present = marker in truncated
    full_present = marker in numbered_context
    print(f"Chunk [{cited_id}]: present in truncated context = {present}, present in full context = {full_present}")

# find where each cited chunk actually starts
for cited_id in [6, 16, 19]:
    marker = f"[{cited_id}] "
    idx = numbered_context.find(marker)
    print(f"[{cited_id}] starts at character position {idx} (truncation cutoff is 4000)")
