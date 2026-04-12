# Comprehensive Test Suite for Kenbu Auditing Tool

**Date:** 2026-04-12
**Goal:** Pre-release confidence — verify all shipped critical paths work as intended, with tests serving as a regression safety net going forward.

## Scope

Critical paths only (not exhaustive edge cases). Covers: authentication, browsing benchmarks/checks, audit sessions, hardening tasks, pentest assessments, Excel export, and YAML seeding. Admin and account management are out of scope for now.

## Tech Stack

- **Framework:** pytest + pytest-cov
- **Database:** SQLite in-memory (via existing `TestingConfig`)
- **HTTP:** Flask test client (no browser/Selenium)
- **CSRF:** Disabled in test config (already set: `WTF_CSRF_ENABLED = False`)

## Directory Structure

```
tests/
  conftest.py          # Shared fixtures
  test_auth.py         # Authentication flows
  test_benchmarks.py   # Browsing benchmarks and checks
  test_audits.py       # Audit session lifecycle
  test_hardening.py    # Hardening task lifecycle
  test_pentests.py     # Pentest assessment lifecycle
  test_export.py       # Excel export
  test_seed.py         # YAML data seeding
```

## Dependencies

Add to `requirements.txt`:

```
pytest
pytest-cov
```

## Fixtures (conftest.py)

### `app`
Creates a Flask app with `TestingConfig`. Yields the app instance. Scope: session.

### `_db` (internal)
Within the app context, calls `db.create_all()`, yields the `db` object, then calls `db.drop_all()`. Scope: session.

### `db_session`
For each test function, begins a nested transaction (savepoint), yields `db`, then rolls back. This isolates every test without recreating tables each time.

### `client`
Flask test client from the app. Scope: function (fresh per test via db_session rollback).

### `auth_client`
Creates an approved auditor user (`testauditor` / `password123`), logs them in via POST to `/auth/login`, returns the client. This is the default authenticated client for most tests.

### `admin_client`
Creates an approved admin user (`testadmin` / `password123`), logs them in, returns the client.

### `seed_data`
Seeds a minimal dataset for tests that need benchmark/check data:
- 1 Platform (name="Test Linux", slug="test-linux", os_family="linux")
- 1 Benchmark (name="Test CIS Benchmark", version="1.0", linked to platform)
- 1 BenchmarkSection (number="1", title="Test Section")
- 3 Checks (check_number="1.1", "1.2", "1.3" with level L1, L2, L1 — each with audit_command and expected_output)

Returns a dict with references to all created objects for easy access in tests.

## Test Cases

### test_auth.py — Authentication Flows (12 tests)

| # | Test | Action | Expected |
|---|------|--------|----------|
| 1 | Register valid user | POST `/auth/register` with valid data | Redirect to `/auth/login`, user exists in DB with `is_approved=False` |
| 2 | Register mismatched passwords | POST with password != confirm_password | Stays on register page, flash error |
| 3 | Register short password | POST with 5-char password | Flash "at least 8 characters" error |
| 4 | Register duplicate username | POST with existing username | Flash "already exists" error |
| 5 | Login approved user | POST `/auth/login` with valid creds | Redirect to dashboard |
| 6 | Login unapproved user | POST with unapproved user creds | Flash "pending admin approval" |
| 7 | Login wrong password | POST with wrong password | Flash "Invalid username or password" |
| 8 | Login MFA user | POST with MFA-enabled user | Redirect to `/auth/mfa-verify`, `mfa_user_id` in session |
| 9 | MFA verify valid token | POST `/auth/mfa-verify` with valid TOTP | Redirect to dashboard, user logged in |
| 10 | MFA verify invalid token | POST with wrong token | Flash error, stays on verify page |
| 11 | Logout | POST `/auth/logout` | Redirect to login |
| 12 | Protected route unauthenticated | GET `/audits/` without login | Redirect to login |

### test_benchmarks.py — Browsing (6 tests)

| # | Test | Action | Expected |
|---|------|--------|----------|
| 1 | List benchmarks | GET `/benchmarks/` | 200, page contains benchmark name |
| 2 | Benchmark detail | GET `/benchmarks/<id>` | 200, shows sections |
| 3 | Section detail | GET `/benchmarks/<id>/section/<id>` | 200, shows checks |
| 4 | Check detail | GET `/checks/<id>` | 200, shows audit_command and remediation |
| 5 | Search checks by keyword | GET `/checks/search?q=<keyword>` | 200, returns matching checks |
| 6 | Search checks by level | GET `/checks/search?level=L1` | 200, returns only L1 checks |

### test_audits.py — Audit Session Lifecycle (17 tests)

| # | Test | Action | Expected |
|---|------|--------|----------|
| 1 | List audits empty | GET `/audits/` | 200, no sessions listed |
| 2 | Create audit session | POST `/audits/new` with title | Redirect to session detail, session in DB |
| 3 | Create without title | POST `/audits/new` without title | Flash error |
| 4 | View session detail | GET `/audits/<id>` | 200, shows title and draft status |
| 5 | Edit draft session | POST `/audits/<id>/edit` with new title | Title updated in DB |
| 6 | Edit non-draft session | Start session, then POST edit | Flash error, no change |
| 7 | Add asset | POST `/audits/<id>/assets/new` with name and type | Asset created, redirect to benchmark selection |
| 8 | Assign benchmarks to asset | POST `/audits/<id>/assets/<id>/benchmarks` with benchmark_ids | Benchmarks linked to asset |
| 9 | Start session | POST `/audits/<id>/start` with asset+benchmark ready | Status = `in_progress`, AuditResult records created |
| 10 | Start without assets | POST `/audits/<id>/start` on empty session | Flash error |
| 11 | Start with unassigned benchmarks | POST start, asset has no benchmarks | Flash error |
| 12 | Update single result | POST update_result with status=pass | Result status updated, checked_at set |
| 13 | Bulk update results | POST bulk_update with check_ids and status | All selected results updated |
| 14 | Complete session | POST `/audits/<id>/complete` | Status = `completed`, completed_at set |
| 15 | Delete draft session | POST `/audits/<id>/delete` on draft | Session removed from DB |
| 16 | Delete non-draft session | POST delete on in_progress session | Flash error, session still exists |
| 17 | Access other user's session | GET another user's session | 403 |

### test_hardening.py — Hardening Task Lifecycle (13 tests)

Mirrors the audit pattern with hardening-specific models:

| # | Test | Action | Expected |
|---|------|--------|----------|
| 1 | List tasks empty | GET `/hardening/` | 200 |
| 2 | Create task | POST `/hardening/new` with title | Redirect to task detail |
| 3 | Create without title | POST without title | Flash error |
| 4 | View task detail | GET `/hardening/<id>` | 200 |
| 5 | Add asset | POST `/hardening/<id>/assets/new` | Asset created |
| 6 | Assign benchmarks | POST benchmarks for asset | Benchmarks linked |
| 7 | Start task | POST `/hardening/<id>/start` | Status = `in_progress`, check results generated |
| 8 | Start without assets | POST start on empty task | Flash error |
| 9 | Update single check | POST update_check with status | Check result updated |
| 10 | Bulk update checks | POST bulk_update with check_ids | All selected updated |
| 11 | Complete task | POST `/hardening/<id>/complete` | Status = `completed` |
| 12 | Delete draft task | POST delete on draft | Task removed |
| 13 | Access other user's task | GET another user's task | 403 |

### test_pentests.py — Pentest Assessment Lifecycle (15 tests)

| # | Test | Action | Expected |
|---|------|--------|----------|
| 1 | List assessments empty | GET `/pentests/` | 200 |
| 2 | Create assessment | POST `/pentests/new` with title, type, scope | Redirect to detail, phases auto-created |
| 3 | View assessment detail | GET `/pentests/<id>` | 200, shows phases |
| 4 | Start assessment | POST `/pentests/<id>/start` | Status = `in_progress` |
| 5 | View phase detail | GET `/pentests/<id>/phases/<id>` | 200, shows checklist items |
| 6 | Start phase | POST phase start | Phase status updated |
| 7 | Complete phase | POST phase complete | Phase marked completed |
| 8 | Skip phase | POST phase skip | Phase marked skipped |
| 9 | Toggle checklist item | POST toggle_checklist_item | `is_completed` flipped |
| 10 | Add custom checklist item | POST add_checklist_item | New item in phase |
| 11 | Create finding | POST `/pentests/<id>/findings/new` with severity | Finding in DB |
| 12 | Edit finding | POST edit with updated fields | Finding updated |
| 13 | Delete finding | POST delete | Finding removed |
| 14 | Add team member | POST add_team_member with user_id and role | Member linked |
| 15 | Remove team member | POST remove | Member removed |

### test_export.py — Excel Export (3 tests)

| # | Test | Action | Expected |
|---|------|--------|----------|
| 1 | Export benchmark checklist | GET `/export/benchmark/<id>` | 200, content-type = xlsx, response body is non-empty |
| 2 | Export audit results | GET `/export/audit/<id>` on completed session | 200, xlsx returned |
| 3 | Export hardening checklist | GET `/export/hardening/<id>` | 200, xlsx returned |

### test_seed.py — Data Seeding (3 tests)

| # | Test | Action | Expected |
|---|------|--------|----------|
| 1 | Seed platforms | Call `seed_platforms()` | Platform count matches expected (15) |
| 2 | Seed single benchmark | Call `seed_benchmark_file()` with one YAML | Benchmark, sections, checks created with correct parent-child hierarchy |
| 3 | Seed all | Call `seed_all()` with data dir | All platforms, benchmarks, checks populated; counts > 0 |

## Total: ~67 test cases across 7 files

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=term-missing

# Run a specific module
pytest tests/test_auth.py -v
```

## Design Decisions

1. **SQLite in-memory only** — Fast, zero setup. Production Postgres-specific issues are out of scope for now.
2. **Session-scoped app/db, function-scoped rollback** — Tables created once per test run, each test gets a clean slate via savepoint rollback. Fast.
3. **Minimal seed data** — Tests create only what they need. The `seed_data` fixture provides a small reusable dataset for tests that need benchmarks/checks. `test_seed.py` tests the full seeding against real YAML files.
4. **No browser tests** — All HTMX endpoints are standard HTTP that the test client can exercise. We verify response status and content, not JavaScript behavior.
5. **No mocking** — Tests hit the real app stack (routes, models, database). The only thing disabled is CSRF (already handled by TestingConfig).
