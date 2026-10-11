# Username Search Resilience & Error Flagging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the username lookup feature in GhostTrack so that when a website errors, times out, or fails to respond, it flags the issue with specific diagnostics instead of aborting the entire search, ensuring all responding sites are displayed.

**Architecture:** 
Decompose username search into an isolated lookup module (`check_site`) and an aggregator (`search_username`). The lookup handles request timeouts, network connection drops, and HTTP status codes (200 Found, 404 Not Found, 403/429 Rate limited/Blocked, 5xx Server error, Timeout, Connection failure). In `GhostTR.py`, `TrackLu` consumes this modular engine, streams or aggregates results, and displays formatted status indicators (Green `+` for found, Yellow `-` for not found, Red `!` for errors/timeouts) without cancelling the search on external network faults.

**Tech Stack:** Python 3 (standard library `unittest`, `requests`).

**Spec:** Root cause analysis and user requirements: single-site failure currently triggers an unhandled outer exception in `TrackLu` that immediately executes `return` before results are displayed. Required fix: isolate site requests with timeouts and headers, flag non-responding/erroring sites, and output all results.

## Global Constraints
- Target python version: Python 3.12+ (existing project environment).
- Keep external dependencies minimal: use existing `requests` dependency and Python standard library (`unittest`).
- Preserve existing CLI aesthetic and color schemes (`Wh`, `Gr`, `Re`, `Ye`).
- No infinite recursion or silent crashes.

---

### Task 1: Create Unit Tests for Username Lookup Engine (TDD Red)

**Files:**
- Create: `tests/test_username_tracker.py`

**Interfaces:**
- Consumes: `check_site(site_info, username, timeout=5, user_agent=...) -> dict`
- Consumes: `search_username(username, sites=None) -> list[dict]`
- Produces: Result dictionaries with keys:
  - `name`: str (Platform name)
  - `status`: str ('FOUND', 'NOT_FOUND', 'TIMEOUT', 'ERROR', 'BLOCKED')
  - `url`: str (Target profile URL)
  - `message`: str (Human-readable outcome)

- [ ] **Step 1: Write the failing unit tests for site checking and search aggregation**

Create `tests/test_username_tracker.py` testing:
1. `test_check_site_found`: When HTTP 200, status is 'FOUND'.
2. `test_check_site_not_found`: When HTTP 404, status is 'NOT_FOUND'.
3. `test_check_site_timeout`: When `requests.exceptions.Timeout` occurs, status is 'TIMEOUT' and does not raise exception.
4. `test_check_site_connection_error`: When `requests.exceptions.ConnectionError` occurs, status is 'ERROR' and does not raise exception.
5. `test_check_site_rate_limited`: When HTTP 403 or 429, status is 'BLOCKED' or 'ERROR'.
6. `test_search_username_resilience`: When one site in list raises Timeout and another returns 200, both are recorded and the search completes.

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python3 -m unittest tests/test_username_tracker.py`
Expected: FAIL (ModuleNotFoundError or ImportError: cannot import `check_site`, `search_username`).

- [ ] **Step 3: Commit test suite**

```bash
git add tests/test_username_tracker.py
git commit -m "test: add failing tests for resilient username lookup"
```

---

### Task 2: Implement Resilient Username Lookup Module

**Files:**
- Create: `username_tracker.py`
- Modify: `tests/test_username_tracker.py`

**Interfaces:**
- Produces:
  - `check_site(site: dict, username: str, timeout: float = 5.0) -> dict`
  - `search_username(username: str, sites: list[dict] = None) -> list[dict]`
  - `DEFAULT_SITES: list[dict]`

- [ ] **Step 1: Implement `username_tracker.py`**

Write `username_tracker.py` with:
1. Standard browser `DEFAULT_USER_AGENT` header to avoid bot-rejection.
2. Cleaned list of `DEFAULT_SITES` (removing duplicates like duplicate Snapchat, removing dead platforms like Periscope).
3. `check_site(site, username, timeout=5.0)` wrapping `requests.get` with per-request timeout and individual `try...except` handling for:
   - `requests.exceptions.Timeout` -> `{'name': site['name'], 'status': 'TIMEOUT', 'url': url, 'message': 'Request timed out'}`
   - `requests.exceptions.ConnectionError` -> `{'name': site['name'], 'status': 'ERROR', 'url': url, 'message': 'Connection failed'}`
   - `requests.exceptions.RequestException` -> `{'name': site['name'], 'status': 'ERROR', 'url': url, 'message': str(e)}`
   - Status code inspection:
     - 200 -> `FOUND`
     - 404 -> `NOT_FOUND`
     - 403/429 -> `BLOCKED` (HTTP status code)
     - Other -> `ERROR` (HTTP status code)
4. `search_username(username, sites=None)` iterating across sites and returning list of results without ever raising.

- [ ] **Step 2: Run unit tests to verify they pass**

Run: `./venv/bin/python3 -m unittest tests/test_username_tracker.py`
Expected: PASS (All tests passing).

- [ ] **Step 3: Commit implementation**

```bash
git add username_tracker.py
git commit -m "feat: implement resilient username lookup engine"
```

---

### Task 3: Integrate Resilient Lookup into GhostTR.py

**Files:**
- Modify: `GhostTR.py`

**Interfaces:**
- Consumes: `username_tracker.search_username`, `username_tracker.DEFAULT_SITES`
- Produces: Updated `TrackLu()` function in `GhostTR.py` with categorized, colored output for found, not found, and error/timeout sites.

- [ ] **Step 1: Write integration test**

Create `tests/test_integration.py` to verify `TrackLu` handles site errors without throwing unhandled exceptions or returning empty results.

- [ ] **Step 2: Run test to verify failure before change**

Run: `./venv/bin/python3 -m unittest tests/test_integration.py`

- [ ] **Step 3: Refactor `TrackLu()` in `GhostTR.py`**

Update `TrackLu()` to:
1. Call `search_username(username)`.
2. Format output cleanly:
   - Green `[ + ] Site : URL` for `FOUND`
   - Yellow `[ - ] Site : Username not found` for `NOT_FOUND`
   - Red `[ ! ] Site : Connection timed out / Error [Details]` for `TIMEOUT`, `ERROR`, `BLOCKED`
3. Print summary count (Found: X, Not Found: Y, Errors/Unreachable: Z).
4. Never cancel or exit early when a site fails.

- [ ] **Step 4: Run integration and unit tests**

Run: `./venv/bin/python3 -m unittest discover tests`
Expected: PASS (All tests passing).

- [ ] **Step 5: Commit changes**

```bash
git add GhostTR.py tests/test_integration.py
git commit -m "fix: integrate resilient username lookup into GhostTR"
```
