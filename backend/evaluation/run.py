import json
import os
import sys

# Ensure backend root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db import init_db
from app.agents.graph import process_resident_report

def evaluate_gold_dataset():
    init_db()
    gold_path = os.path.join(os.path.dirname(__file__), "gold_dataset.json")
    with open(gold_path, "r", encoding="utf-8") as f:
        gold_cases = json.load(f)

    total_cases = len(gold_cases)
    cat_correct = 0
    sev_correct = 0
    prio_correct = 0
    esc_correct = 0

    results = []

    for case in gold_cases:
        res = process_resident_report(
            raw_text=case["raw_text"],
            language=case.get("language", "en"),
            image_url=case.get("image_url")
        )

        cat_match = (res["category"] == case["expected_category"])
        if cat_match:
            cat_correct += 1

        sev_match = (res["severity"] == case["expected_severity"])
        if sev_match:
            sev_correct += 1

        prio_val = res["priority_score"]
        prio_match = (case["min_priority"] <= prio_val <= case["max_priority"])
        if prio_match:
            prio_correct += 1

        esc_match = (res["needs_human_review"] == case["expected_human_review"])
        if esc_match:
            esc_correct += 1

        results.append({
            "id": case["id"],
            "raw_text": case["raw_text"],
            "predicted_category": res["category"],
            "expected_category": case["expected_category"],
            "cat_match": cat_match,
            "priority_score": prio_val,
            "prio_range": f"{case['min_priority']}-{case['max_priority']}",
            "prio_match": prio_match,
            "needs_review": res["needs_human_review"],
            "expected_review": case["expected_human_review"],
            "esc_match": esc_match
        })

    cat_acc = round((cat_correct / total_cases) * 100, 1)
    sev_acc = round((sev_correct / total_cases) * 100, 1)
    prio_acc = round((prio_correct / total_cases) * 100, 1)
    esc_acc = round((esc_correct / total_cases) * 100, 1)

    summary = {
        "total_test_cases": total_cases,
        "category_accuracy": f"{cat_acc}%",
        "severity_accuracy": f"{sev_acc}%",
        "priority_accuracy": f"{prio_acc}%",
        "safety_escalation_accuracy": f"{esc_acc}%",
        "case_details": results
    }
    return summary

if __name__ == "__main__":
    summary = evaluate_gold_dataset()
    print("==================================================")
    print(" VILLAGE VOICE — AGENTIC EVALUATION SUITE RESULTS ")
    print("==================================================")
    print(f"Total Test Cases Evaluated : {summary['total_test_cases']}")
    print(f"Classification Accuracy    : {summary['category_accuracy']}")
    print(f"Severity Accuracy          : {summary['severity_accuracy']}")
    print(f"Priority Scoring Accuracy  : {summary['priority_accuracy']}")
    print(f"Safety Escalation Accuracy : {summary['safety_escalation_accuracy']}")
    print("==================================================")
