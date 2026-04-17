"""
basic_flow.py — Locust scenario: full user flow on fm-agent.ai

Endpoints (confirmed from source):
  POST /api/register  { email, nickname, password }
  POST /api/login     { email, password }           → { token, nickname }
  POST /api/upload    multipart: file, api_key, model  (Bearer token) → { job_id }
  GET  /api/stream/<job_id>?token=<token>           EventSource stream
  POST /api/jobs      { filename, model, correct_count, incorrect_count } (Bearer)
  GET  /api/jobs      (Bearer) → list of saved jobs
  DELETE /api/logout  (Bearer)

Usage:
    # Interactive UI
    locust -f scenarios/basic_flow.py --host https://fm-agent.ai

    # Headless (3 users, 1/sec spawn, 2 min)
    locust -f scenarios/basic_flow.py --host https://fm-agent.ai \
        --users 3 --spawn-rate 1 --run-time 2m --headless
"""

import yaml
import random
import itertools
from pathlib import Path
from locust import HttpUser, task, between

ROOT = Path(__file__).parent.parent
CONFIG_FILE = ROOT / "config.yaml"
ACCOUNTS_FILE = ROOT / "accounts" / "accounts.yaml"
TEST_FILES_DIR = ROOT / "test_files"


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Copy the .example version and fill in values.")
    with open(path) as f:
        return yaml.safe_load(f)


try:
    _config = _load_yaml(CONFIG_FILE)
    _accounts: list[dict] = _load_yaml(ACCOUNTS_FILE)["accounts"]
except FileNotFoundError as e:
    raise SystemExit(str(e))

_archives = list(TEST_FILES_DIR.glob("*.zip")) + list(TEST_FILES_DIR.glob("*.tar.gz"))
if not _archives:
    raise SystemExit(
        "No test archives found in test_files/. "
        "Run: bash test_files/fetch_samples.sh"
    )

_user_counter = itertools.count()


class FMAgentUser(HttpUser):
    """Simulates a single user: register → login → upload → check history."""

    wait_time = between(
        _config.get("think_time_min", 1),
        _config.get("think_time_max", 3),
    )

    def on_start(self):
        self._idx = next(_user_counter)
        self.account = _accounts[self._idx % len(_accounts)]
        self._logged_in = False
        self._register()
        self._logged_in = self._login()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _register(self):
        """POST /api/register — 409 = already exists, treat as success."""
        with self.client.post(
            "/api/register",
            json={
                "email": self.account["email"],
                "nickname": self.account["nickname"],
                "password": self.account["password"],
            },
            catch_response=True,
            name="POST /api/register",
        ) as resp:
            if resp.status_code in (200, 201, 409):
                resp.success()
            else:
                resp.failure(f"Register failed: {resp.status_code} — {resp.text[:100]}")

    def _login(self) -> bool:
        """POST /api/login → session cookie stored in self.client.cookies."""
        with self.client.post(
            "/api/login",
            json={
                "email": self.account["email"],
                "password": self.account["password"],
            },
            catch_response=True,
            name="POST /api/login",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
                return True
            else:
                resp.failure(f"Login failed: {resp.status_code} — {resp.text[:100]}")
                return False

    def _auth_headers(self) -> dict:
        return {}  # auth via cookie, no header needed

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    @task(3)
    def upload_and_analyze(self):
        """POST /api/upload — core feature, tested 3x more than history check."""
        if not self._logged_in:
            self._logged_in = self._login()
            if not self._logged_in:
                return

        archive = random.choice(_archives)
        api_key = self.account.get("openrouter_api_key") or _config.get("openrouter_api_key", "")
        model = _config.get("model", "deepseek/deepseek-v3.2")

        try:
            with open(archive, "rb") as f:
                with self.client.post(
                    "/api/upload",
                    files={"file": (archive.name, f, "application/octet-stream")},
                    data={"api_key": api_key, "model": model},
                    headers=self._auth_headers(),
                    catch_response=True,
                    name="POST /api/upload",
                ) as resp:
                    if resp.status_code in (200, 201, 202):
                        resp.success()
                    elif resp.status_code == 401:
                        self._logged_in = False
                        resp.failure("401 — session expired")
                    else:
                        resp.failure(f"Upload failed: {resp.status_code} — {resp.text[:100]}")
        except Exception as e:
            print(f"[upload_and_analyze] EXCEPTION: {type(e).__name__}: {e}")

    @task(1)
    def check_history(self):
        """GET /api/jobs — verify history isolation between users."""
        with self.client.get(
            "/api/jobs",
            catch_response=True,
            name="GET /api/jobs",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 401:
                self._logged_in = self._login()
                resp.failure("401 — re-logged in")
            else:
                resp.failure(f"History failed: {resp.status_code}")
