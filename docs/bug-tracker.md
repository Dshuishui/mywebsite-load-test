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

*Add new bugs below this line*
