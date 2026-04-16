"""
upload.py — Login then upload a file to fm-agent.ai

Auth:   POST /api/login   → { token, nickname }
Upload: POST /api/upload  → { job_id }
Stream: GET  /api/stream/<job_id>?token=<token>  (EventSource, read-only)

Usage:
    python scripts/upload.py --account user1 --file test_files/sample_requests.zip
"""

import argparse
import yaml
import requests
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
CONFIG_FILE = ROOT / "config.yaml"
ACCOUNTS_FILE = ROOT / "accounts" / "accounts.yaml"


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
    """POST /api/login → returns Bearer token or None."""
    url = f"{base_url}/api/login"
    resp = requests.post(
        url,
        json={"email": account["email"], "password": account["password"]},
        timeout=15,
    )
    if resp.status_code == 200:
        token = resp.json().get("token")
        print(f"  Logged in as {account['email']} — token: {token[:20]}...")
        return token
    else:
        print(f"  Login FAILED — {resp.status_code}: {resp.text[:300]}")
        return None


def upload_file(archive_path: Path, account: dict, config: dict, base_url: str, token: str) -> Optional[str]:
    """POST /api/upload with multipart form → returns job_id or None."""
    url = f"{base_url}/api/upload"

    if not archive_path.exists():
        print(f"  File not found: {archive_path}")
        return None

    api_key = account.get("openrouter_api_key") or config.get("openrouter_api_key", "")
    model = config.get("model", "deepseek/deepseek-v3.2")

    print(f"  Uploading {archive_path.name} ({archive_path.stat().st_size // 1024} KB) ...")

    with open(archive_path, "rb") as f:
        files = {"file": (archive_path.name, f, "application/octet-stream")}
        data = {"api_key": api_key, "model": model}
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.post(url, files=files, data=data, headers=headers, timeout=60)

    if resp.status_code in (200, 201, 202):
        job_id = resp.json().get("job_id")
        print(f"  Upload OK — job_id: {job_id}")
        print(f"  Stream URL: {base_url}/api/stream/{job_id}?token=<token>")
        return job_id
    else:
        print(f"  Upload FAILED — {resp.status_code}: {resp.text[:300]}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Upload a test file to fm-agent.ai")
    parser.add_argument("--account", default="user1", help="Account ID from accounts.yaml")
    parser.add_argument("--file", default="test_files/sample_requests.zip", help="Path to archive file")
    args = parser.parse_args()

    config = load_config()
    accounts = load_accounts()

    if args.account not in accounts:
        sys.exit(f"Account '{args.account}' not found in accounts.yaml")

    account = accounts[args.account]
    base_url = config["target_url"].rstrip("/")
    archive_path = ROOT / args.file

    token = login(account, base_url)
    if not token:
        sys.exit(1)

    job_id = upload_file(archive_path, account, config, base_url, token)
    sys.exit(0 if job_id else 1)


if __name__ == "__main__":
    main()
