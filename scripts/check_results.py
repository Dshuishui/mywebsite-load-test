"""
check_results.py — Fetch and validate analysis results from fm-agent.ai

Auth:    POST /api/login           → { token, nickname }
History: GET  /api/jobs            → list of jobs
Stream:  GET  /api/stream/<job_id>?token=<token>  (EventSource — not polled here)

Usage:
    python scripts/check_results.py --account user1
"""

import argparse
import yaml
import requests
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List

ROOT = Path(__file__).parent.parent
CONFIG_FILE = ROOT / "config.yaml"
ACCOUNTS_FILE = ROOT / "accounts" / "accounts.yaml"
REPORTS_DIR = ROOT / "reports"


def load_config():
    if not CONFIG_FILE.exists():
        sys.exit("config.yaml not found.")
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


def load_accounts():
    if not ACCOUNTS_FILE.exists():
        sys.exit("accounts/accounts.yaml not found.")
    with open(ACCOUNTS_FILE) as f:
        data = yaml.safe_load(f)
    return {a["id"]: a for a in data["accounts"]}


def login(account: dict, base_url: str) -> Optional[str]:
    resp = requests.post(
        f"{base_url}/api/login",
        json={"email": account["email"], "password": account["password"]},
        timeout=15,
    )
    if resp.status_code == 200:
        return resp.json().get("token")
    print(f"  Login FAILED — {resp.status_code}: {resp.text[:200]}")
    return None


def fetch_jobs(base_url: str, token: str) -> list:
    """GET /api/jobs — history of completed jobs for this user."""
    resp = requests.get(
        f"{base_url}/api/jobs",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    if resp.status_code == 200:
        return resp.json() if isinstance(resp.json(), list) else resp.json().get("jobs", [])
    print(f"  Jobs fetch FAILED — {resp.status_code}: {resp.text[:200]}")
    return []


def validate_job(job: dict) -> List[str]:
    """Check that a job record has expected fields with valid values."""
    issues = []
    for field in ["filename", "model", "correct_count", "incorrect_count"]:
        if field not in job:
            issues.append(f"Missing field: {field}")

    if "correct_count" in job and "incorrect_count" in job:
        correct = int(job["correct_count"])
        incorrect = int(job["incorrect_count"])
        total = correct + incorrect
        if total == 0:
            issues.append("Both counts are 0 — analysis may not have run")

    return issues


def save_report(account_id: str, data: list):
    REPORTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"jobs_{account_id}_{timestamp}.json"
    with open(report_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Report saved: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Check job history and validate results on fm-agent.ai")
    parser.add_argument("--account", default="user1", help="Account ID from accounts.yaml")
    args = parser.parse_args()

    config = load_config()
    accounts = load_accounts()

    if args.account not in accounts:
        sys.exit(f"Account '{args.account}' not found in accounts.yaml")

    account = accounts[args.account]
    base_url = config["target_url"].rstrip("/")

    print(f"Checking jobs for {account['email']} ...")
    token = login(account, base_url)
    if not token:
        sys.exit(1)

    jobs = fetch_jobs(base_url, token)
    print(f"  Found {len(jobs)} job(s)")

    all_ok = True
    for job in jobs:
        job_id = job.get("id") or job.get("job_id") or "?"
        issues = validate_job(job)
        if issues:
            print(f"  Job {job_id} — issues: {issues}")
            all_ok = False
        else:
            correct = job.get("correct_count", 0)
            incorrect = job.get("incorrect_count", 0)
            total = correct + incorrect
            pct = round(correct / total * 100, 1) if total else 0
            print(f"  Job {job_id} — OK ({correct}/{total} = {pct}% pass rate)")

    if jobs:
        save_report(args.account, jobs)

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
