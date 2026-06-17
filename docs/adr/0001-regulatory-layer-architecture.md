# ADR 0001 — Regulatory layer architecture

- **Status:** Proposed (Phase 0 — pending review)
- **Date:** 2026-06-17

## Context

Kenbu owns a proven technical-check model (`Platform → Benchmark →
BenchmarkSection → Check` with real `audit_command` / `expected_output`). The
product is being extended into a space-sector compliance readiness & evidence
platform (EU Space Act, NIS2, CER, CSA2). The kickoff specifies a rich regulatory
layer (`Regulation → Obligation → Control ↔ Check`).

A thin regulatory layer **already exists** and was not mentioned in the kickoff:
`Standard` + `StandardCheck` (`app/models/standard.py`), seeded with GDPR and
NIS2, with `data/standards/nis2.yaml` directly mapping NIS2 Article 21 sub-points
to CIS `check_number`s. `AuditSession.standard_id` references it.

## Decision

1. **Add the regulatory layer alongside `Check`, never inside it.** Controls link
   to checks through a `control_checks` join table. The `Check` schema is not
   modified. This preserves the moat (technical checks with real audit commands).

2. **`Control` is the cross-framework hub.** Obligations (per regulation) and
   external standard references (ISO 27001, NIST IR 8270/8401, ECSS, CCSDS, ENISA)
   attach to controls, so one control can evidence many obligations across
   frameworks. This synthesis is the product differentiator.

3. **In-scope regulations get full `Obligation` trees; reference standards get
   lightweight `ControlReference` rows** (not full hierarchies), because they are
   cross-map anchors, not assessable regulations.

4. **Mappings are versioned YAML data** under `data/regulations/`,
   `data/controls/`, `data/mappings/` — loaded by extending `app/utils/seed.py`,
   validated by `scripts/validate_regulations.py`. No code change to update a mapping.

5. **Reconcile `Standard` → `Regulation` (Option A, recommended).** Rename
   `standards`→`regulations`, add `short_code/status/effective_date/source_url`,
   repoint `AuditSession.standard_id`→`regulation_id`. The thin `StandardCheck`
   direct map is superseded by `control_checks`; the curated `nis2.yaml` content is
   re-authored into the new YAML (reuse the IP, drop the redundant table).
   Option B (coexist + `Regulation.legacy_standard_slug` bridge) is the
   lower-risk fallback if review prefers leaving the audit flow untouched.

## Consequences

- One canonical regulatory entity (no "NIS2 exists twice"); existing curated NIS2
  mappings are reused, not duplicated.
- Option A touches ~6 `.py` files + 3 templates and needs Alembic batch mode for
  the SQLite rename; Option B avoids that at the cost of two parallel concepts.
- Final choice between A and B is the #1 review question (see DESIGN_compliance §11).
