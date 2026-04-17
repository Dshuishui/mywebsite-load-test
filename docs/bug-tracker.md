# Bug Tracker — fm-agent.ai

Bugs and issues found during load testing and manual testing.
Update this file whenever a new bug is discovered.

Format:
- **ID**: BUG-XXX
- **Severity**: Critical / High / Medium / Low
- **Status**: Open / Fixed / Won't Fix
- **Found**: date discovered
- **Description**: what the bug is
- **Steps to reproduce**
- **Expected / Actual behavior**

---

## BUG-001 — No email validation on registration

- **Severity**: Medium
- **Status**: Open
- **Found**: 2026-04-16
- **Description**: The `/api/register` endpoint accepts any string as email with no format validation and no verification email sent. Completely fake addresses (e.g. `fmtest.user1.loadtest@gmail.com`) register successfully.
- **Steps to reproduce**:
  1. POST `/api/register` with `{ "email": "notanemail", "nickname": "test", "password": "123456" }`
  2. Observe: registration succeeds
- **Expected**: Reject invalid email format, or send verification email before activating account
- **Actual**: Account created immediately with no checks

---

## BUG-002 — History page shows "Network error" when job list is empty

- **Severity**: High
- **Status**: Open
- **Found**: 2026-04-16
- **Description**: `/history` page JS crashes with a TypeError when the user has no jobs, causing the catch block to display "Network error loading history." instead of the intended "No runs yet" message.
- **Root cause**: `loadHistory()` calls `document.getElementById('history-stats').style.display = 'none'` when `jobs.length === 0`, but the element `#history-stats` does not exist in the HTML DOM — `getElementById` returns `null`, accessing `.style` throws TypeError, catch fires.
- **Steps to reproduce**:
  1. Register a new account
  2. Navigate to `/history` without having submitted any analysis jobs
  3. Observe: "Network error loading history." is displayed
- **Expected**: "No runs yet. Run your first analysis →"
- **Actual**: "Network error loading history." (misleading — no network error occurred)
- **Fix**: Add null check before accessing the element: `const statsEl = document.getElementById('history-stats'); if (statsEl) statsEl.style.display = 'none';`

---

## BUG-003 — Task lifecycle managed by frontend, not backend (design issue)

- **Severity**: High
- **Status**: Open
- **Found**: 2026-04-16
- **Description**: The demo page stores the active job ID in `sessionStorage` and is responsible for saving completed jobs to history via `POST /api/jobs`. This means task state is tied to a single browser tab session, not the user's account on the server.
- **Impact**:
  - Refreshing the page during analysis loses all progress display
  - Closing the tab before analysis completes means the job is never saved to history
  - Jobs submitted via API/script never appear in history (no browser to call `saveJobToGateway`)
  - Users cannot resume or view running jobs from another device or browser
- **Root cause**: `sessionStorage.setItem('active_job_id', job_id)` is frontend-only state. History is written by browser JS (`saveJobToGateway`) at stream end, not by the backend worker.
- **Recommended fixes** (by priority):
  1. **P0** — Backend writes job record to DB immediately on upload (`status=pending`), updates to `done` when analysis completes. Frontend never responsible for writing history.
  2. **P1** — `/history` page shows `pending`/`running` jobs with a live progress indicator
  3. **P2** — Demo page checks for any running job on load and auto-reconnects to its SSE stream
  4. **P3** — Limit one active job per user, queue additional submissions

---

## BUG-004 — GET /api/my-running-job returns api_key in plaintext (security)

- **Severity**: Critical
- **Status**: Open
- **Found**: 2026-04-17
- **Description**: The `/api/my-running-job` endpoint returns the user's OpenRouter API key in plaintext in the response body. This key was submitted by the user for analysis but should never be returned to the client after submission.
- **Evidence** (seen in browser DevTools):
  ```json
  {
    "job_id": "3cd02913...",
    "filename": "sample_tqdm.zip",
    "model": "deepseek/deepseek-v3.2",
    "api_key": "sk-or-v1-57263712fc40ecb25...",
    "initial_usage": 13.018,
    "session_cost": 1.640
  }
  ```
- **Impact**: Any attacker who can obtain a valid session cookie can retrieve the victim's OpenRouter API key via this endpoint. The key can then be used to make unauthorized LLM requests at the victim's expense.
- **Note**: `/api/jobs` (history) does NOT return `api_key` — only this specific endpoint leaks it.
- **Fix**: Remove `api_key` from the `/api/my-running-job` response. Never return credentials after they have been received.

---

## BUG-005 — Job status not cleared after completion (frontend shows running forever)

- **Severity**: High
- **Status**: Open
- **Found**: 2026-04-17
- **Description**: After a job finishes (or fails), the backend does not update the job status from `running` to `done`/`failed`. The `/api/my-running-job` endpoint continues to return the completed job, causing the frontend to permanently display the job as still running.
- **Observed symptoms**:
  - Frontend spinner never stops even after analysis is complete
  - Subsequent upload attempts return `409 "A job is already running"` indefinitely
  - User is permanently blocked from submitting new jobs
- **Root cause**: Job completion/failure handler does not update job status in DB. Likely the error path (e.g. invalid API key causing OpenRouter failure) exits without setting `status=done` or `status=failed`.
- **Steps to reproduce**:
  1. Submit a job with an invalid/fake OpenRouter API key
  2. Wait for analysis to fail
  3. Try to submit another job → 409 forever
  4. Check `/api/my-running-job` → still returns the failed job
- **Fix**: Wrap the analysis worker in try/finally — always update job status to `done` or `failed` regardless of how the analysis exits.

---

*Add new bugs below this line*
