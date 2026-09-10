import csv
import json
import logging
import sys
from pathlib import Path

from langchain_openai import ChatOpenAI

from app.config import settings
from app.services.query_service import answer_question
from app.utils.costs import calculate_input_cost, calculate_output_cost, calculate_total_cost
from app.utils.logging import setup_logging

logger = logging.getLogger(__name__)

GOLDEN_DATASET_PATH = Path("data/golden_dataset.json")
RESULTS_PATH = Path("eval/results.csv")

TICKER = {"Apple": "AAPL", "Microsoft": "MSFT", "Walmart": "WMT", "JPMorgan": "JPM"}

JUDGE_PROMPT = """You are grading a RAG system's answer to a question.

Question: {question}
Expected answer: {expected_answer}
Generated answer: {generated_answer}
Retrieved context: {context}

Respond with only strict JSON, nothing else: {{"correct": true or false, "faithful": true or false}}
"correct" means the generated answer matches the expected answer's meaning.
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


def judge_answer(question, expected_answer, generated_answer, context):
    llm = ChatOpenAI(model=settings.openai_model, temperature=0, api_key=settings.openai_api_key)
    prompt = JUDGE_PROMPT.format(
        question=question, expected_answer=expected_answer,
        generated_answer=generated_answer, context=context[:4000],
    )
    response = llm.invoke(prompt)
    verdict = json.loads(response.content)
    return verdict["correct"], verdict["faithful"]

def run_harness(run_label, collection_name="ledger_chunks", use_reranker=False, use_metadata_filter=False):
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
                result = answer_question(q["question"], collection_name=collection_name,
                                          use_reranker=use_reranker, use_metadata_filter=use_metadata_filter)
                recall = check_recall(q.get("source_document"), result["chunks_used"])
                context = "\n\n".join(c["text"] for c in result["chunks_used"])
                correct, faithful = judge_answer(q["question"], q["expected_answer"], result["answer"], context)
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
    run_harness(label, collection_name=collection, use_reranker=use_reranker, use_metadata_filter=use_metadata_filter)
