# API Endpoint Discovery Guide

How to find the real API endpoints of a website before writing load test scripts — without access to the backend source code.

This document records the exact process used to discover the fm-agent.ai API, including what failed and why, so it can be reused for any target site.

---

## The Core Idea

Modern web apps are transparent. The browser must know which endpoints to call, which means the API structure is always reachable from the frontend — either in HTML, inline scripts, or loaded JS files. The job is to find where it's written.

---

## Step-by-Step Process

### Step 1 — Fetch the target page

Use any HTTP client to get the raw HTML. The goal is to find:
- `<script src="...">` tags (JS bundle references)
- Inline `<script>` blocks with `fetch(` or `axios.` calls
- Form `action` attributes and input `name` attributes
- References to framework-specific paths (`/_next/`, `/static/`, etc.)

```bash
curl -s https://example.com/demo | grep -oE '(src|href)="[^"]*\.(js|css)[^"]*"'
```

**What we found on fm-agent.ai:**
```
href="/static/style.css"
src="https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js"
src="/static/common.js"
```

Only one custom JS file: `/static/common.js`. No bundler, no framework hash — plain static files.

---

### Step 2 — Fetch each JS file and search for API calls

```bash
curl -s https://example.com/static/common.js | grep -E 'fetch\(|axios\.|/api/'
```

**What we found in `/static/common.js`:**
```javascript
// Logout
fetch('/api/logout', { method: 'DELETE', headers: { 'Authorization': 'Bearer ' + authToken } })

// Save completed job to history
fetch('/api/jobs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + authToken },
    body: JSON.stringify({ filename, model, correct_count, incorrect_count }),
})

// Auth stored in localStorage
let authToken = localStorage.getItem('auth_token')
```

This revealed: auth mechanism (JWT Bearer token), history endpoint, logout endpoint.

---

### Step 3 — Fetch page-specific inline scripts

Each page (demo, login, history) may have its own `<script>` blocks with page-specific API calls.

```bash
curl -s https://example.com/demo | grep -A200 'async function runModel'
curl -s https://example.com/login | grep -A100 'fetch\|api\|login\|register'
```

**What we found in `/demo` inline script:**
```javascript
// Upload endpoint
const res = await fetch('/api/upload', {
    method: 'POST',
    body: form,  // FormData with: file, api_key, model
    headers: { 'Authorization': 'Bearer ' + authToken }
});
const data = await res.json();  // → { job_id }

// Real-time results via EventSource
_es = new EventSource('/api/stream/' + jobId + '?token=' + encodeURIComponent(authToken));
```

**What we found in `/login` inline script:**
```javascript
// Register
fetch('/api/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, nickname, password }),
})

// Login
fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
})
// Response → { token, nickname }
```

---

### Step 4 — Try probing known API paths directly

Sometimes a quick probe confirms whether an endpoint exists and what it returns on a wrong method:

```bash
curl -s -I https://example.com/api/auth/register
# 404 → endpoint doesn't exist at this path
# 405 Method Not Allowed → endpoint exists but wrong HTTP method
# 200/401 → endpoint confirmed
```

**What we tried and got wrong (the mistakes):**

| Guessed Path | Result | Correct Path |
|---|---|---|
| `/api/auth/register` | 404 | `/api/register` |
| `/api/auth/login` | 404 | `/api/login` |
| `/api/history` | 404 | `/api/jobs` |
| `/api/results/<id>` | never tried | `/api/stream/<id>` (EventSource) |

**Lesson**: Don't guess path structure (e.g., `/api/auth/` prefix). Always read the actual JS before assuming RESTful conventions.

---

### Step 5 — Check response headers for tech stack hints

```bash
curl -s -I https://example.com
```

**What we saw:**
```
Server: nginx/1.24.0 (Ubuntu)
Content-Type: application/json
```

nginx serving JSON → likely a Python backend (FastAPI/Flask) behind nginx. FastAPI uses `detail` in error responses, which matched what the JS code checked: `data.detail || data.error`.

---

## What Didn't Work (and Why)

### WebFetch tool on the page HTML

The tool returned a high-level summary of the page instead of raw source, so inline `<script>` blocks were invisible. It was useful for getting the overall structure but not for extracting API calls.

**Fix**: Use `curl -s <url>` and grep for specific patterns directly.

### Guessing endpoints from REST conventions

Initial placeholders assumed `/api/auth/register`, `/api/upload` with field `file` (correct), `/api/history` — two out of three were wrong.

**Fix**: Always read the JS source before writing any script. Conventions differ per framework and developer preference.

### GitHub repo link was private/404

The site linked to a GitHub repo that returned 404 (private or removed). Reading the JS source was the correct fallback.

---

## Final Discovered API (fm-agent.ai)

| Endpoint | Method | Auth | Body / Params | Response |
|---|---|---|---|---|
| `/api/register` | POST | None | `{ email, nickname, password }` | `200` on success, `409` if duplicate |
| `/api/login` | POST | None | `{ email, password }` | `{ token, nickname }` |
| `/api/upload` | POST | Bearer | multipart: `file`, `api_key`, `model` | `{ job_id }` |
| `/api/stream/<job_id>` | GET (EventSource) | `?token=<token>` | — | SSE events: `correct`, `incorrect`, `done` |
| `/api/jobs` | POST | Bearer | `{ filename, model, correct_count, incorrect_count }` | Saves job to history |
| `/api/jobs` | GET | Bearer | — | List of saved jobs |
| `/api/logout` | DELETE | Bearer | — | Clears session |

**Auth**: JWT Bearer token. Obtained from `POST /api/login`. Sent as `Authorization: Bearer <token>` header. Also accepted as `?token=<token>` query param for EventSource (which can't set headers).

---

## Reusable Checklist for Any Target Site

```
[ ] curl -s <target_url> | grep -oE 'src="[^"]*\.js[^"]*"'
      → find all JS file references

[ ] for each JS file: curl -s <js_url> | grep -E 'fetch\(|axios\.|/api/'
      → extract API calls and auth patterns

[ ] for each page: curl -s <page_url> | grep -A100 'fetch\('
      → extract inline script API calls

[ ] check login/register page specifically for auth endpoint and payload shape

[ ] curl -s -I <target_url> to identify server/framework

[ ] document: endpoint, method, auth, body fields, response shape
      → then write the test scripts
```

---

## When to Use Browser DevTools Instead

This curl/grep approach works when:
- The site has accessible static JS files
- The site is server-rendered or uses plain JS (not heavy SPA with code splitting)

Use **Browser DevTools → Network tab** instead when:
- The site is a heavily bundled SPA (React/Next.js/Vue) where JS is minified and split across many chunks
- API calls only happen after user interaction (login, button click) — curl can't trigger those
- The site uses WebSockets or complex auth flows

In those cases: open DevTools, perform the action in browser, filter Network by `Fetch/XHR`, and read the actual requests.
