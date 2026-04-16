# Website Security & Quality Checklist

Full inspection checklist for a web application. Covers security, performance, reliability, and UX.
Intended as a reference for fm-agent.ai testing, but applicable to any web app.

---

## 1. Authentication & Authorization

### What to check
- [ ] Password strength requirements enforced
- [ ] Brute force protection (rate limit on `/api/login`)
- [ ] JWT token expiry — does it expire? what happens after?
- [ ] JWT token invalidated on logout (or just discarded client-side?)
- [ ] Can user A access user B's data by guessing IDs?
- [ ] Sensitive endpoints require auth — what happens if Bearer token is missing/invalid?

### How to test
```bash
# Brute force login — does it get rate limited?
for i in $(seq 1 20); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST https://fm-agent.ai/api/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@test.com","password":"wrongpass"}'
done

# Access another user's job
curl https://fm-agent.ai/api/jobs/1 \
  -H "Authorization: Bearer <user2_token>"

# Call protected endpoint without token
curl https://fm-agent.ai/api/jobs
```

---

## 2. Input Validation & Injection

### What to check
- [ ] Email format validated on registration
- [ ] File upload — only allowed formats accepted (.zip, .tar.gz, .tar)?
- [ ] File upload — size limit enforced?
- [ ] File upload — malicious filenames handled? (e.g. `../../etc/passwd.zip`)
- [ ] File upload — zip bomb handled? (tiny zip that expands to GB)
- [ ] SQL injection in login/register fields
- [ ] XSS in nickname/filename fields — does the site escape output?

### How to test
```bash
# Upload wrong format
curl -X POST https://fm-agent.ai/api/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@malware.exe" -F "api_key=x" -F "model=x"

# XSS in nickname
curl -X POST https://fm-agent.ai/api/register \
  -H "Content-Type: application/json" \
  -d '{"email":"xss@test.com","nickname":"<script>alert(1)</script>","password":"test123"}'

# Oversized file — check if server rejects it
dd if=/dev/zero bs=1M count=500 | zip - > big.zip
curl -X POST https://fm-agent.ai/api/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@big.zip" -F "api_key=x" -F "model=x"
```

---

## 3. API Security

### What to check
- [ ] Rate limiting on all endpoints (register, login, upload)
- [ ] CORS policy — which origins are allowed?
- [ ] Sensitive data in responses — do error messages leak stack traces?
- [ ] HTTP methods restricted — does DELETE /api/register work?
- [ ] API versioning — are old/undocumented endpoints accessible?

### How to test
```bash
# Check CORS headers
curl -I -H "Origin: https://evil.com" https://fm-agent.ai/api/jobs

# Check what methods are allowed
curl -X OPTIONS https://fm-agent.ai/api/upload -v

# Probe for stack traces in errors
curl -X POST https://fm-agent.ai/api/login \
  -H "Content-Type: application/json" \
  -d '{"email": null, "password": null}'

# Try undocumented endpoints
curl https://fm-agent.ai/api/admin
curl https://fm-agent.ai/api/users
curl https://fm-agent.ai/api/debug
```

---

## 4. Data Isolation (Multi-user)

### What to check
- [ ] User A cannot see User B's job history
- [ ] User A cannot download User B's results
- [ ] User A cannot delete User B's jobs
- [ ] Job IDs are not sequential integers (guessable)

### How to test
```python
# Login as user1, get job list → record job IDs
# Login as user2, try to access user1's job IDs
import requests

r1 = requests.post("https://fm-agent.ai/api/login",
    json={"email": "fmtest.user1.loadtest@gmail.com", "password": "..."})
token1 = r1.json()["token"]

r2 = requests.post("https://fm-agent.ai/api/login",
    json={"email": "fmtest.user2.loadtest@gmail.com", "password": "..."})
token2 = r2.json()["token"]

# Get user1's jobs
jobs1 = requests.get("https://fm-agent.ai/api/jobs",
    headers={"Authorization": f"Bearer {token1}"}).json()

# Try to access user1's job with user2's token
for job in jobs1:
    r = requests.get(f"https://fm-agent.ai/api/jobs/{job['id']}",
        headers={"Authorization": f"Bearer {token2}"})
    print(f"Job {job['id']}: {r.status_code}")  # Should be 403, not 200
```

---

## 5. File Upload Security

### What to check
- [ ] Zip slip attack — filenames with `../` path traversal inside zip
- [ ] Symlinks inside zip
- [ ] Zip bomb (compressed ratio too high)
- [ ] Executable files inside zip — are they run or just read?
- [ ] Archive with no Python files — graceful error?

### How to test
```python
import zipfile, io

# Zip slip — path traversal filename
buf = io.BytesIO()
with zipfile.ZipFile(buf, 'w') as z:
    z.writestr("../../etc/crontab", "malicious content")
buf.seek(0)
# Upload buf as a zip file

# Zip bomb — lots of zeros compressed
import zlib
bomb_content = b'\x00' * (10 * 1024 * 1024)  # 10MB of zeros
buf2 = io.BytesIO()
with zipfile.ZipFile(buf2, 'w', compression=zipfile.ZIP_DEFLATED) as z:
    z.writestr("bomb.py", bomb_content)
```

---

## 6. Performance & Load

### What to check
- [ ] Response time under normal load (single user)
- [ ] Response time under concurrent load (10+ users)
- [ ] Does upload endpoint queue requests or process all simultaneously?
- [ ] Memory/CPU behavior under many concurrent analysis jobs
- [ ] Does the server recover after load spike?

### How to test
```bash
# Single endpoint latency
curl -w "\nTime: %{time_total}s\n" -s -o /dev/null \
  -X POST https://fm-agent.ai/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"fmtest.user1.loadtest@gmail.com","password":"..."}'

# Locust concurrent load test
locust -f scenarios/basic_flow.py --host https://fm-agent.ai \
  --users 10 --spawn-rate 2 --run-time 3m --headless
```

---

## 7. HTTPS & Transport Security

### What to check
- [ ] HTTPS enforced — does HTTP redirect to HTTPS?
- [ ] TLS version — TLS 1.2 minimum, TLS 1.3 preferred
- [ ] HSTS header present
- [ ] Secure/HttpOnly flags on cookies (if used)
- [ ] Sensitive data not in URL query params (tokens, keys)

### How to test
```bash
# Check TLS and security headers
curl -I https://fm-agent.ai

# Check if HTTP redirects to HTTPS
curl -I http://fm-agent.ai

# Check TLS version
openssl s_client -connect fm-agent.ai:443 -tls1 2>&1 | grep "Cipher"
```

---

## 8. Error Handling & Information Leakage

### What to check
- [ ] 404 page doesn't reveal server/framework info
- [ ] Error responses don't include stack traces
- [ ] Server headers don't expose version info (`Server: nginx/1.24.0` — already seen this)
- [ ] `/robots.txt`, `/.env`, `/.git` not publicly accessible

### How to test
```bash
# Check for exposed sensitive files
curl https://fm-agent.ai/.env
curl https://fm-agent.ai/.git/config
curl https://fm-agent.ai/robots.txt
curl https://fm-agent.ai/api/../../../etc/passwd

# Check server headers for info leakage
curl -I https://fm-agent.ai
```

---

## 9. Frontend / UX Issues

### What to check
- [ ] Meaningful error messages (not "Network error" for logic errors — BUG-002)
- [ ] Loading states on all async actions
- [ ] Page refresh during async operation — graceful recovery?
- [ ] Mobile responsive layout
- [ ] Form validation feedback before submit
- [ ] Broken links / missing assets (404 on JS/CSS files)

---

## 10. Business Logic

### What to check
- [ ] Can user submit multiple jobs simultaneously? Any limit?
- [ ] What happens if OpenRouter API key is invalid/exhausted?
- [ ] What happens if analysis job crashes midway?
- [ ] Job results persisted correctly (BUG-003 — currently front-end writes history)
- [ ] Can user delete a job that's currently running?

### How to test
```bash
# Submit multiple jobs simultaneously
for i in 1 2 3; do
  python3 scripts/upload.py --account user1 --file test_files/sample_simple.zip &
done
wait

# Use invalid API key
curl -X POST https://fm-agent.ai/api/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@test_files/sample_simple.zip" \
  -F "api_key=invalid-key" \
  -F "model=deepseek/deepseek-v3.2"
```

---

## Priority Matrix

| Area | Severity | Effort | Do First? |
|------|----------|--------|-----------|
| Data isolation (user A/B) | Critical | Low | Yes |
| Rate limiting on login | High | Low | Yes |
| Zip slip / path traversal | High | Medium | Yes |
| JWT invalidation on logout | High | Low | Yes |
| XSS in nickname display | Medium | Low | Yes |
| Zip bomb | Medium | Medium | Later |
| TLS/HTTPS headers | Medium | Low | Yes |
| Concurrent job limits | Low | Medium | Later |

---

## Known Bugs (fm-agent.ai)

See [bug-tracker.md](bug-tracker.md) for full details.

| ID | Issue |
|----|-------|
| BUG-001 | No email validation on registration |
| BUG-002 | History page JS crash on empty job list |
| BUG-003 | Task lifecycle managed by frontend, not backend |
