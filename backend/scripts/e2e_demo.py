"""End-to-end scenario against a running Mlution backend.

Usage:  python scripts/e2e_demo.py            (expects server on E2E_BASE_URL, default http://127.0.0.1:8000)

Covers: create project (demo dataset) -> data profile -> run pipeline ->
wait for completion -> experiments -> report -> downloads -> prediction -> chat.
"""
import os
import sys
import time

import httpx

BASE = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8000")
FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}" + (f" — {detail}" if detail else ""))
    if not condition:
        FAILURES.append(label)


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=30.0)

    r = client.get("/api/health")
    check("health endpoint", r.status_code == 200 and r.json().get("status") == "ok")

    # 1. create project with demo dataset
    r = client.post("/api/projects", json={
        "name": "E2E Churn Demo",
        "description": "Predict customer churn (end-to-end test).",
        "use_demo_dataset": True,
    })
    check("create project", r.status_code == 201, r.text[:200])
    project = r.json()
    pid = project["id"]

    # 2. data profile
    r = client.get(f"/api/projects/{pid}/profile")
    profile = r.json()
    check("profile available", r.status_code == 200)
    check("profile row count", profile["n_rows"] >= 1500, f"n_rows={profile['n_rows']}")
    check("id column detected", "customer_id" in profile["id_columns"], str(profile["id_columns"]))
    check("target suggested", profile["target_column"] == "churn", str(profile["target_column"]))
    check("task hint is binary", profile["task_hint"] == "binary_classification", str(profile["task_hint"]))

    # 3. run pipeline
    r = client.post(f"/api/projects/{pid}/run", json={"time_budget_seconds": 180, "max_experiments": 4})
    check("run started", r.status_code == 200 and r.json()["status"] == "running", r.text[:200])

    deadline = time.time() + 300
    status = {}
    while time.time() < deadline:
        time.sleep(2)
        status = client.get(f"/api/projects/{pid}/status").json()
        if status["status"] in ("completed", "failed"):
            break
    check("pipeline completed", status.get("status") == "completed", f"status={status.get('status')} error={status.get('error')}")
    stage_names = [s["name"] for s in status.get("stages", [])]
    check("all 7 stages present", stage_names == ["analyze", "plan", "build_baseline", "evaluate", "critique", "improve", "finalize"])

    # 4. agent events
    events = client.get(f"/api/projects/{pid}/events").json()
    check("agent events recorded", len(events) >= 10, f"events={len(events)}")

    # 5. experiments
    r = client.get(f"/api/projects/{pid}/experiments")
    experiments = r.json()
    completed = [e for e in experiments if e["status"] == "completed"]
    check(">=3 completed experiments", len(completed) >= 3, f"completed={len(completed)}")
    check("validation f1 present", all(
        any(m["name"] == "f1" and m["split"] == "validation" for m in e["metrics"]) for e in completed))
    best = completed[0]
    check("leaderboard sorted best-first", all(
        (e["primary_metric_value"] or 0) <= (completed[0]["primary_metric_value"] or 0) + 1e-9 for e in completed))
    check("feature importance present", len(best["feature_importance"]) > 0)
    check("confusion matrix present", best["confusion_matrix"] is not None)
    improvement = [e for e in experiments if e["stage"] == "improvement"]
    check("improvement experiment ran", len(improvement) == 1, f"improvement={len(improvement)}")

    # 6. report
    r = client.get(f"/api/projects/{pid}/report")
    check("report available", r.status_code == 200)
    report = r.json()
    check("report summary", len(report["summary"]) > 20)
    check("report usage_code", "joblib.load" in report["usage_code"])
    check("report leaderboard", len(report["leaderboard"]) == len(completed))
    check("report improvements recorded", len(report["improvements"]) == 1
          and report["improvements"][0]["decision"] in ("accept_improvement", "reject_improvement"))
    check("report task type", report["task"]["task_type"] == "binary_classification")

    # 7. downloads
    r = client.get(f"/api/projects/{pid}/model")
    check("model download", r.status_code == 200 and len(r.content) > 1_000, f"bytes={len(r.content)}")
    r = client.get(f"/api/projects/{pid}/code")
    check("code download", r.status_code == 200 and "joblib" in r.text)

    # 8. prediction
    sample = {
        "customer_id": "CUST-999999",
        "tenure_months": 3,
        "monthly_charges": 105.5,
        "total_charges": 310.2,
        "contract_type": "Month-to-month",
        "payment_method": "Electronic check",
        "num_support_calls": 4,
        "is_premium": "No",
        "avg_monthly_gb": 52.3,
        "has_streaming": "Yes",
    }
    r = client.post(f"/api/projects/{pid}/predict", json={"features": sample})
    check("predict endpoint", r.status_code == 200, r.text[:200])
    pred = r.json()
    check("prediction label valid", str(pred["prediction"]) in ("0", "1"), str(pred["prediction"]))
    check("probability in [0,1]", pred["probability"] is not None and 0.0 <= pred["probability"] <= 1.0)
    check("explanation non-empty", len(pred["explanation"]) > 10)

    # 9. chat
    r = client.post(f"/api/projects/{pid}/chat", json={"message": "Which model won and why?"})
    check("chat reply", r.status_code == 200 and len(r.json()["reply"]) > 10)

    print()
    if FAILURES:
        print(f"E2E FAILED: {len(FAILURES)} check(s): {FAILURES}")
        return 1
    print(f"E2E PASSED: full scenario green. Best model: {best['name']} "
          f"(f1={best['primary_metric_value']:.4f}), prediction={pred['prediction']} p={pred['probability']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
