# OSINT Username Detection Accuracy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate false positives in GhostTrack username searches by implementing OSINT detection techniques (patterned after Sherlock and WhatsMyName): probe endpoints, response body missing/existence string verification, redirect detection, and username format regex validation.

**Architecture:**
Upgrade `username_tracker.py` site definitions from naive URL templates to OSINT detection schemas containing:
1. `url`: Target profile URL displayed to user.
2. `probe_url`: Specialized probe/API/feed endpoint if direct web page is an SPA or login-walled.
3. `regex`: Optional regex pattern to validate valid username syntax for that platform.
4. `error_type`: `'status_code'` or `'message'` or `'probe'`.
5. `error_msg` / `m_string`: List of strings indicating "Not Found" even when HTTP status is 200.
6. `e_string`: String indicating definitive existence in the response body.
7. `error_url`: URL prefix indicating a redirect to login / landing page.

Update `check_site()` to run this multi-tier verification pipeline, returning `FOUND` only when all criteria pass.

**Tech Stack:** Python 3, `requests`, standard library `re`, `unittest`.

---

### Task 1: Write Unit Tests for Advanced OSINT Verification (TDD Red)

**Files:**
- Modify: `tests/test_username_tracker.py`

**Interfaces:**
- Consumes: `check_site(site, username)`
- Produces: Correct `FOUND` vs `NOT_FOUND` on sites returning HTTP 200 with soft-404 strings or missing markers.

- [ ] **Step 1: Add unit tests for detection features**
  - `test_regex_check_rejection`: If username fails site's `regex`, return `NOT_FOUND` without network request.
  - `test_missing_string_detection`: When HTTP 200 is returned but response contains `error_msg`/`m_string` (e.g. Telegram "noindex, nofollow"), status is `NOT_FOUND`.
  - `test_existence_string_detection`: When HTTP 200 is returned, only set `FOUND` if `e_string` is present.
  - `test_redirect_to_error_url`: If redirected to `error_url` (e.g. login page), status is `NOT_FOUND`.
  - `test_probe_url_usage`: Verify site with `probe_url` uses probe endpoint for detection while preserving clean profile `url` for display.

- [ ] **Step 2: Run test suite to verify tests fail**
  Run: `./venv/bin/python3 -m unittest tests/test_username_tracker.py`

- [ ] **Step 3: Commit failing tests**
  ```bash
  git add tests/test_username_tracker.py
  git commit -m "test: add tests for OSINT false positive detection techniques"
  ```

---

### Task 2: Implement OSINT Multi-Tier Verification Engine (TDD Green)

**Files:**
- Modify: `username_tracker.py`

**Interfaces:**
- Produces:
  - Enhanced `DEFAULT_SITES` with OSINT rules (`regex`, `probe_url`, `error_type`, `error_msg`, `e_string`, `error_url`).
  - Upgraded `check_site()` executing regex check, probe requests, redirect inspection, and body analysis.

- [ ] **Step 1: Implement detection pipeline in `check_site`**
  1. Check `site.get('regex')`. If match fails, return `NOT_FOUND` with message `"Invalid username format for platform"`.
  2. Determine target URL (`probe_url` if defined, else `url`).
  3. Send request with proper headers.
  4. Check `error_url`: if `response.url` starts with or equals `error_url`, return `NOT_FOUND`.
  5. Check HTTP status code against `m_code` (default 404). If matches, return `NOT_FOUND`.
  6. Check `error_msg` / `m_string`. If any missing marker is found in `response.text`, return `NOT_FOUND`.
  7. Check `e_string`. If defined and not in `response.text`, return `NOT_FOUND`.
  8. If HTTP 200 and all negative checks pass (and `e_string` passes if specified), return `FOUND`.

- [ ] **Step 2: Update `DEFAULT_SITES` with rules for all supported platforms**
  Include verified rules for Telegram, TikTok, Pinterest, Twitch, GitHub, Reddit, Medium, Instagram, YouTube, SoundCloud, Snapchat, etc.

- [ ] **Step 3: Run unit tests to verify they pass**
  Run: `./venv/bin/python3 -m unittest discover tests -v`

- [ ] **Step 4: Commit engine implementation**
  ```bash
  git add username_tracker.py
  git commit -m "feat: implement OSINT multi-tier false-positive elimination engine"
  ```

---

### Task 3: Live Verification on Real Platforms (`verification-before-completion`)

**Files:**
- Create: `tests/test_live_accuracy.py` (marked as integration / live verification)

- [ ] **Step 1: Test non-existent username on live platforms**
  Verify `adnan_nonexistent_xyz_998877` returns 0 false positives across the updated platform list.

- [ ] **Step 2: Test known real username**
  Verify known accounts (e.g. `google` or `github`) are accurately found.

- [ ] **Step 3: Run full automated test suite**
  Run: `./venv/bin/python3 -m unittest discover tests -v`

- [ ] **Step 4: Commit live verification script**
  ```bash
  git add tests/
  git commit -m "test: add live accuracy verification test"
  ```
