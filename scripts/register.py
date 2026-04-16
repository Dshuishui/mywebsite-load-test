"""
register.py — Simulate user registration on fm-agent.ai

API: POST /api/register
Body: { email, nickname, password }

Usage:
    python scripts/register.py --account user1
"""

import argparse
import yaml
import requests
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONFIG_FILE = ROOT / "config.yaml"
ACCOUNTS_FILE = ROOT / "accounts" / "accounts.yaml"


def load_config():
    if not CONFIG_FILE.exists():
        sys.exit("config.yaml not found. Copy config.example.yaml and fill in values.")
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


def load_accounts():
    if not ACCOUNTS_FILE.exists():
        sys.exit("accounts/accounts.yaml not found. Copy accounts.example.yaml and fill in values.")
    with open(ACCOUNTS_FILE) as f:
        data = yaml.safe_load(f)
    return {a["id"]: a for a in data["accounts"]}


def register(account: dict, base_url: str) -> bool:
    url = f"{base_url}/api/register"
    payload = {
        "email": account["email"],
        "nickname": account["nickname"],
        "password": account["password"],
    }

    print(f"Registering {account['email']} (nickname: {account['nickname']}) ...")
    resp = requests.post(url, json=payload, timeout=15)

    if resp.status_code in (200, 201):
        print(f"  OK — registered successfully")
        return True
    elif resp.status_code == 409:
        print(f"  Already registered (409) — continuing")
        return True
    else:
        print(f"  FAILED — status {resp.status_code}: {resp.text[:300]}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Register a test account on fm-agent.ai")
    parser.add_argument("--account", default="user1", help="Account ID from accounts.yaml")
    args = parser.parse_args()

    config = load_config()
    accounts = load_accounts()

    if args.account not in accounts:
        sys.exit(f"Account '{args.account}' not found in accounts.yaml")

    account = accounts[args.account]
    success = register(account, config["target_url"].rstrip("/"))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
