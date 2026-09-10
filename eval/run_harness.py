def run_harness(run_label, collection_name="ledger_chunks"):
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
                result = answer_question(q["question"], collection_name=collection_name)
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
    run_harness(label, collection_name=collection)