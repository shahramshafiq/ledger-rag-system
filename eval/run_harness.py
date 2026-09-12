import csv
import json
import logging
import sys
from pathlib import Path

from langchain_openai import ChatOpenAI

from app.config import settings
from app.services.query_service import answer_question
from app.retrieval.corrective_rag import answer_question_corrective
from app.utils.costs import calculate_input_cost, calculate_output_cost, calculate_total_cost
from app.utils.logging import setup_logging

logger = logging.getLogger(__name__)

GOLDEN_DATASET_PATH = Path("data/golden_dataset.json")
RESULTS_PATH = Path("eval/results.csv")

TICKER = {"Apple": "AAPL", "Microsoft": "MSFT", "Walmart": "WMT", "JPMorgan": "JPM"}

JUDGE_PROMPT = """You are grading a RAG system's answer to a question.

Question: {question}
Question category: {category}
Expected answer: {expected_answer}
Generated answer: {generated_answer}
Retrieved context: {context}

Respond with only strict JSON, nothing else: {{"correct": true or false, "faithful": true or false}}
"correct" means the generated answer matches the expected answer's meaning. For a "broad" category question,
the expected answer is a reference set of themes/points, not the one exact required scope or phrasing: mark
the generated answer correct if it substantively captures the same core themes or points, even if organized
differently, worded differently, or more comprehensive. Only mark a broad-category answer incorrect if it
misses the substance entirely or states something factually wrong.
"faithful" means every claim in the generated answer is actually supported by the retrieved context, not invented."""


def check_recall(source_document, chunks_used):
    if not source_document:
        return None
    expected_pairs = []
    for part in source_document.split(" + "):
        pieces = part.split("_")
        if len(pieces) < 2:
            continue
        expected_pairs.append((pieces[0], pieces[1]))
    if not expected_pairs:
        return None
    for chunk in chunks_used:
        pair = (TICKER.get(chunk.get("company")), chunk.get("fiscal_year"))
        if pair in expected_pairs:
            return True
    return False


def judge_answer(question, category, expected_answer, generated_answer, context):
    llm = ChatOpenAI(model=settings.openai_model, temperature=0, api_key=settings.openai_api_key)
    prompt = JUDGE_PROMPT.format(
        question=question, category=category, expected_answer=expected_answer,
        generated_answer=generated_answer, context=context,
    )
    response = llm.invoke(prompt)
    content = response.content.strip()
    if content.startswith("```"):
        content = content.strip("`").removeprefix("json").strip()
    verdict = json.loads(content)
    return verdict["correct"], verdict["faithful"]

def run_harness(run_label, collection_name="ledger_chunks", use_reranker=False,
                 use_metadata_filter=False, use_hybrid=False, use_corrective=False):
    setup_logging()
    with open(GOLDEN_DATASET_PATH, encoding="utf-8") as f:
        golden = json.load(f)

    is_new_file = not RESULTS_PATH.exists()
    with open(RESULTS_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new_file:
            writer.writerow(["run_label", "question_id", "category", "recall_at_5",
                              "correct", "faithful", "latency_sec", "cost_usd"])

        for q in golden["questions"]:
            try:
                if use_corrective:
                    result = answer_question_corrective(q["question"])
                else:
                    result = answer_question(q["question"], collection_name=collection_name,
                                              use_reranker=use_reranker, use_metadata_filter=use_metadata_filter,
                                              use_hybrid=use_hybrid)
                recall = check_recall(q.get("source_document"), result["chunks_used"])
                # numbered to match the citation ids the answer itself cites (e.g. "[6]"), and no
                # longer truncated: it used to be context[:4000], the same bug just fixed in
                # grade_node, a flat character cutoff that only covers the first 1-2 of what can be
                # 20-80 chunks, so the judge was marking real, correctly-cited claims unfaithful
                # simply because the cited chunk's text was never within its own truncated view.
                context = "\n\n".join(f"[{i}] {c['text']}" for i, c in enumerate(result["chunks_used"], start=1))
                correct, faithful = judge_answer(q["question"], q["category"], q["expected_answer"], result["answer"], context)
                cost = calculate_total_cost(
                    calculate_input_cost(result["input_tokens"], settings.input_price),
                    calculate_output_cost(result["output_tokens"], settings.output_price),
                )
                writer.writerow([run_label, q["id"], q["category"], recall, correct,
                                  faithful, round(result["latency"], 2), round(cost, 5)])
                logger.info(f"{q['id']} ({q['category']}): recall={recall} correct={correct} faithful={faithful}")
            except Exception:
                logger.exception(f"Question {q['id']} failed, recording as ERROR and continuing")
                writer.writerow([run_label, q["id"], q["category"], "ERROR", "ERROR", "ERROR", None, None])
            f.flush()


if __name__ == "__main__":
    label = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    collection = sys.argv[2] if len(sys.argv) > 2 else "ledger_chunks"
    use_reranker = "--rerank" in sys.argv
    use_metadata_filter = "--filter" in sys.argv
    use_hybrid = "--hybrid" in sys.argv
    use_corrective = "--corrective" in sys.argv
    run_harness(label, collection_name=collection, use_reranker=use_reranker,
                use_metadata_filter=use_metadata_filter, use_hybrid=use_hybrid, use_corrective=use_corrective)