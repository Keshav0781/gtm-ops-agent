"""
GTM Ops Agent — Agent Evaluation Pipeline

Functional integration test suite that evaluates all 4 agents
by calling the live GCP API and comparing outputs against
golden datasets.

Why functional testing and not RAGAS:
GTM Ops Agent is an agentic reasoning system — not a RAG pipeline.
RAGAS metrics (faithfulness, context_recall) require retrieved
context chunks which agentic systems do not expose.
Functional testing is the correct evaluation approach for
agentic systems — used by teams at Siemens, Google, and other
enterprise AI teams to validate agent output quality.

What this evaluates:
- Lead Intelligence: score, qualification, draft email quality
- Email Triage: classification, priority, routing accuracy
- Meeting Intelligence: meeting type, action items, summary
- CRM Hygiene: deal detection, alert generation, notifications

Run with:
    source evaluation/venv/bin/activate
    python3 evaluation/evaluate_functional.py
"""

import json
import requests
import os
from datetime import datetime

API_BASE = "https://gtm-ops-agent-324111066236.europe-west3.run.app"

RESULTS = []


def log(msg):
    print(msg)


def evaluate_lead_intelligence():
    log("\n========================================")
    log("AGENT: Lead Intelligence")
    log("========================================")

    with open("evaluation/datasets/lead_intelligence.json") as f:
        dataset = json.load(f)

    passed = 0
    failed = 0

    for i, case in enumerate(dataset):
        inp = case["input"]
        expected = case["expected"]

        try:
            response = requests.post(
                f"{API_BASE}/leads/analyze",
                json=inp,
                timeout=60
            )
            result = response.json()

            errors = []

            # Check score
            if result.get("score") not in expected["score"]:
                errors.append(
                    f"score: got {result.get('score')}, "
                    f"expected one of {expected['score']}"
                )

            # Check is_qualified
            if result.get("is_qualified") not in expected["is_qualified"]:
                errors.append(
                    f"is_qualified: got {result.get('is_qualified')}, "
                    f"expected one of {expected['is_qualified']}"
                )

            # Check draft email subject contains keywords (only for HIGH/MEDIUM)
            if expected["draft_email_subject_contains"]:
                subject = result.get("draft_email_subject") or ""
                matched = any(
                    kw in subject
                    for kw in expected["draft_email_subject_contains"]
                )
                if not matched:
                    errors.append(
                        f"draft_email_subject: '{subject}' does not "
                        f"contain any of {expected['draft_email_subject_contains']}"
                    )

            if errors:
                log(f"  FAIL — Case {i+1} ({inp['company_name']})")
                for e in errors:
                    log(f"       → {e}")
                failed += 1
            else:
                log(f"  PASS — Case {i+1} ({inp['company_name']}) "
                    f"score={result.get('score')}")
                passed += 1

        except Exception as e:
            log(f"  ERROR — Case {i+1}: {str(e)}")
            failed += 1

    total = passed + failed
    accuracy = round((passed / total) * 100, 1) if total > 0 else 0
    log(f"\n  Result: {passed}/{total} passed — Accuracy: {accuracy}%")
    RESULTS.append({
        "agent": "Lead Intelligence",
        "passed": passed,
        "total": total,
        "accuracy": accuracy
    })


def evaluate_email_triage():
    log("\n========================================")
    log("AGENT: Email Triage")
    log("========================================")

    with open("evaluation/datasets/email_triage.json") as f:
        dataset = json.load(f)

    passed = 0
    failed = 0

    for i, case in enumerate(dataset):
        inp = case["input"]
        expected = case["expected"]

        try:
            response = requests.post(
                f"{API_BASE}/emails/triage",
                json=inp,
                timeout=60
            )
            result = response.json()

            errors = []

            # Check classification
            if result.get("classification") not in expected["classification"]:
                errors.append(
                    f"classification: got {result.get('classification')}, "
                    f"expected one of {expected['classification']}"
                )

            # Check priority
            if result.get("priority") not in expected["priority"]:
                errors.append(
                    f"priority: got {result.get('priority')}, "
                    f"expected one of {expected['priority']}"
                )

            # Check route_to
            route = (result.get("route_to") or "").lower()
            matched = any(r in route for r in expected["route_to"])
            if not matched:
                errors.append(
                    f"route_to: got '{route}', "
                    f"expected one of {expected['route_to']}"
                )

            if errors:
                log(f"  FAIL — Case {i+1} ({inp['sender_email']})")
                for e in errors:
                    log(f"       → {e}")
                failed += 1
            else:
                log(f"  PASS — Case {i+1} ({inp['sender_email']}) "
                    f"classification={result.get('classification')}")
                passed += 1

        except Exception as e:
            log(f"  ERROR — Case {i+1}: {str(e)}")
            failed += 1

    total = passed + failed
    accuracy = round((passed / total) * 100, 1) if total > 0 else 0
    log(f"\n  Result: {passed}/{total} passed — Accuracy: {accuracy}%")
    RESULTS.append({
        "agent": "Email Triage",
        "passed": passed,
        "total": total,
        "accuracy": accuracy
    })


def evaluate_meeting_intelligence():
    log("\n========================================")
    log("AGENT: Meeting Intelligence")
    log("========================================")

    with open("evaluation/datasets/meeting_intelligence.json") as f:
        dataset = json.load(f)

    passed = 0
    failed = 0

    for i, case in enumerate(dataset):
        inp = case["input"]
        expected = case["expected"]

        try:
            response = requests.post(
                f"{API_BASE}/meetings/analyze",
                json=inp,
                timeout=60
            )
            result = response.json()

            errors = []

            # Check meeting type contains expected keywords
            meeting_type = (result.get("meeting_type") or "").lower()
            matched = any(t in meeting_type for t in expected["meeting_type"])
            if not matched:
                errors.append(
                    f"meeting_type: got '{meeting_type}', "
                    f"expected one of {expected['meeting_type']}"
                )

            # Check action items count
            count = result.get("action_items_count") or 0
            if count < expected["action_items_count_min"]:
                errors.append(
                    f"action_items_count: got {count}, "
                    f"expected >= {expected['action_items_count_min']}"
                )

            # Check summary exists
            if expected["has_summary"] and not result.get("summary"):
                errors.append("summary: missing")

            # Check slack message exists
            if expected["has_slack_message"] and not result.get("slack_message"):
                errors.append("slack_message: missing")

            if errors:
                log(f"  FAIL — Case {i+1} ({inp['meeting_title']})")
                for e in errors:
                    log(f"       → {e}")
                failed += 1
            else:
                log(f"  PASS — Case {i+1} ({inp['meeting_title']}) "
                    f"actions={result.get('action_items_count')}")
                passed += 1

        except Exception as e:
            log(f"  ERROR — Case {i+1}: {str(e)}")
            failed += 1

    total = passed + failed
    accuracy = round((passed / total) * 100, 1) if total > 0 else 0
    log(f"\n  Result: {passed}/{total} passed — Accuracy: {accuracy}%")
    RESULTS.append({
        "agent": "Meeting Intelligence",
        "passed": passed,
        "total": total,
        "accuracy": accuracy
    })


def evaluate_crm_hygiene():
    log("\n========================================")
    log("AGENT: CRM Hygiene")
    log("========================================")

    with open("evaluation/datasets/crm_hygiene.json") as f:
        dataset = json.load(f)

    passed = 0
    failed = 0

    for i, case in enumerate(dataset):
        inp = case["input"]
        expected = case["expected"]

        try:
            response = requests.post(
                f"{API_BASE}/crm/analyze",
                json=inp,
                timeout=60
            )
            result = response.json()

            errors = []

            # Check total deals count
            if result.get("total_deals_count") != expected["total_deals_count"]:
                errors.append(
                    f"total_deals_count: got {result.get('total_deals_count')}, "
                    f"expected {expected['total_deals_count']}"
                )

            # Check problematic deals
            problematic = result.get("problematic_deals_count") or 0
            if problematic < expected["problematic_deals_min"]:
                errors.append(
                    f"problematic_deals_count: got {problematic}, "
                    f"expected >= {expected['problematic_deals_min']}"
                )

            # Check owner notifications exist
            if expected["has_owner_notifications"] and not result.get("owner_notifications"):
                errors.append("owner_notifications: missing")

            # Check scan summary exists
            if expected["has_scan_summary"] and not result.get("scan_summary"):
                errors.append("scan_summary: missing")

            if errors:
                log(f"  FAIL — Case {i+1}")
                for e in errors:
                    log(f"       → {e}")
                failed += 1
            else:
                log(f"  PASS — Case {i+1} "
                    f"problematic={result.get('problematic_deals_count')} "
                    f"alerts={result.get('total_alerts_count')}")
                passed += 1

        except Exception as e:
            log(f"  ERROR — Case {i+1}: {str(e)}")
            failed += 1

    total = passed + failed
    accuracy = round((passed / total) * 100, 1) if total > 0 else 0
    log(f"\n  Result: {passed}/{total} passed — Accuracy: {accuracy}%")
    RESULTS.append({
        "agent": "CRM Hygiene",
        "passed": passed,
        "total": total,
        "accuracy": accuracy
    })


def print_final_report():
    log("\n========================================")
    log("FINAL EVALUATION REPORT")
    log(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("========================================")

    total_passed = sum(r["passed"] for r in RESULTS)
    total_cases = sum(r["total"] for r in RESULTS)
    overall = round((total_passed / total_cases) * 100, 1) if total_cases > 0 else 0

    for r in RESULTS:
        status = "✅" if r["accuracy"] >= 80 else "⚠️"
        log(f"  {status} {r['agent']}: {r['passed']}/{r['total']} — {r['accuracy']}%")

    log(f"\n  Overall Accuracy: {total_passed}/{total_cases} — {overall}%")
    log("========================================\n")

    # Save report to file
    report = {
        "run_at": datetime.now().isoformat(),
        "results": RESULTS,
        "overall_accuracy": overall,
        "total_passed": total_passed,
        "total_cases": total_cases
    }
    with open("evaluation/report.json", "w") as f:
        json.dump(report, f, indent=2)
    log("Report saved to evaluation/report.json")


if __name__ == "__main__":
    log("GTM Ops Agent — Evaluation Starting...")
    log(f"API: {API_BASE}")

    evaluate_lead_intelligence()
    evaluate_email_triage()
    evaluate_meeting_intelligence()
    evaluate_crm_hygiene()

    print_final_report()
