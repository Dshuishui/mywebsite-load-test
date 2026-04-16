# mywebsite-load-test

A load and stress testing toolkit for [fm-agent.ai](https://fm-agent.ai/demo), designed to simulate real user workflows and surface potential bugs.

> **Target**: fm-agent.ai demo — a code analysis platform that accepts uploaded archives and returns function-level correctness reports.

---

## Project Structure

```
mywebsite-load-test/
├── accounts/                   # Test account config (no real passwords committed)
│   └── accounts.example.yaml   # Template — copy to accounts.yaml and fill in
├── test_files/                  # Sample code archives for upload testing
│   └── fetch_samples.sh        # Script to download sample repos from GitHub
├── scripts/
│   ├── register.py             # Simulate user registration
│   ├── upload.py               # Simulate file upload and analysis trigger
│   └── check_results.py        # Validate and fetch analysis results
├── scenarios/
│   └── basic_flow.py           # Locust scenario: register → upload → check results
├── config.example.yaml         # Configuration template
├── reports/                    # Test output (gitignored for real data)
└── requirements.txt
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure

```bash
cp config.example.yaml config.yaml
cp accounts/accounts.example.yaml accounts/accounts.yaml
# Edit config.yaml and accounts/accounts.yaml with your test settings
```

### 3. Download test files

```bash
bash test_files/fetch_samples.sh
```

### 4. Run basic flow test (single user)

```bash
python scenarios/basic_flow.py
```

### 5. Run load test with Locust (multi-user)

```bash
locust -f scenarios/basic_flow.py --host https://fm-agent.ai
```

Then open http://localhost:8089 to configure and start the test.

---

## Test Accounts

This project uses **clearly fake test accounts** for simulation. All test emails follow the pattern:

```
fmtest.userN.loadtest@gmail.com
```

These accounts are created solely for testing and will be deleted after go-live cleanup.

---

## Test Files

Sample code archives are downloaded from public GitHub repositories. See `test_files/fetch_samples.sh` for sources.

---

## Configuration

| Key | Description |
|-----|-------------|
| `target_url` | Base URL of the site under test |
| `openrouter_api_key` | API key for analysis (per test account) |
| `model` | Model name to use for analysis |
| `think_time_min/max` | Simulated user think time (seconds) |

---

## What This Tests

| Scenario | Bug Surface |
|----------|------------|
| Registration flow | Email validation, duplicate handling |
| File upload | Format support, size limits, error messages |
| Analysis trigger | Task queue isolation between users |
| Result retrieval | Data isolation, correct statistics |
| Concurrent users | Race conditions, resource contention |

---

## Extending to Other Sites

This toolkit is designed to be reusable. To adapt it for a different target:

1. Update `config.yaml` with the new `target_url`
2. Modify `scripts/register.py` and `scripts/upload.py` to match the new site's API
3. Update `accounts/accounts.yaml` with new test accounts
4. Run the same Locust scenarios

---

## Notes

- Never commit real API keys or passwords — use `config.yaml` (gitignored)
- All test data in `reports/` is gitignored
- Test accounts are intentionally named to be identifiable for post-test cleanup
