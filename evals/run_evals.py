# evals/run_evals.py
import json
import time
import requests
from pydantic import BaseModel

API_URL = "http://localhost:8000/v1/query"

class EvalMetrics(BaseModel):
    total_tests: int = 0
    passed_tests: int = 0
    guardrails_blocked_correctly: int = 0
    ambiguity_detected_correctly: int = 0
    valid_queries_executed: int = 0
    avg_confidence_score: float = 0.0
    total_time_sec: float = 0.0

def run_evaluation_suite(dataset_path: str = "evals/golden_dataset.json"):
    print("=" * 60)
    print("🚀 RUNNING AUTOMATED EVALUATION SUITE")
    print("=" * 60)

    with open(dataset_path, "r") as f:
        test_cases = json.load(f)

    metrics = EvalMetrics(total_tests=len(test_cases))
    confidence_scores = []
    start_time = time.time()

    for test in test_cases:
        t_id = test["id"]
        q = test["question"]
        expected = test["expected_type"]
        category = test["category"]

        print(f"\n[Test #{t_id}] Category: {category}")
        print(f"Question: \"{q}\"")

        try:
            res = requests.post(API_URL, json={"question": q}, timeout=15)
            if res.status_code != 200:
                print(f"❌ FAIL: API Error {res.status_code}")
                continue

            data = res.json()
            test_passed = False

            # Evaluation Checks
            if expected == "guardrail_blocked":
                if not data.get("guardrail_passed"):
                    test_passed = True
                    metrics.guardrails_blocked_correctly += 1
                    print("✅ PASS: Unsafe query caught and blocked by guardrails.")
                else:
                    print("❌ FAIL: Unsafe query was not blocked by guardrails!")

            elif expected == "ambiguous":
                if data.get("is_ambiguous"):
                    test_passed = True
                    metrics.ambiguity_detected_correctly += 1
                    print("✅ PASS: Ambiguity correctly flagged to user.")
                else:
                    print("❌ FAIL: Ambiguous query failed to trigger clarification request.")

            elif expected == "valid_query":
                if data.get("guardrail_passed") and not data.get("is_ambiguous") and data.get("sql_query"):
                    test_passed = True
                    metrics.valid_queries_executed += 1
                    score = data.get("confidence", {}).get("final_confidence_score", 0.0)
                    confidence_scores.append(score)
                    print(f"✅ PASS: Valid SQL generated & executed (Confidence: {score}%).")
                else:
                    print("❌ FAIL: Valid query was rejected or failed execution.")

            if test_passed:
                metrics.passed_tests += 1

        except Exception as e:
            print(f"❌ ERROR: Failed to execute test case: {e}")

    metrics.total_time_sec = round(time.time() - start_time, 2)
    if confidence_scores:
        metrics.avg_confidence_score = round(sum(confidence_scores) / len(confidence_scores), 1)

    # Output Benchmark Summary
    print("\n" + "=" * 60)
    print("📊 EVALUATION BENCHMARK REPORT")
    print("=" * 60)
    accuracy_rate = round((metrics.passed_tests / metrics.total_tests) * 100, 1)
    print(f"Overall Accuracy Rate:       {accuracy_rate}% ({metrics.passed_tests}/{metrics.total_tests} passed)")
    print(f"Guardrail Block Success:     {metrics.guardrails_blocked_correctly} malicious queries blocked")
    print(f"Ambiguity Detection Success: {metrics.ambiguity_detected_correctly} clarifications prompted")
    print(f"Average Confidence Score:    {metrics.avg_confidence_score}%")
    print(f"Total Test Suite Duration:   {metrics.total_time_sec} seconds")
    print("=" * 60)

if __name__ == "__main__":
    run_evaluation_suite()