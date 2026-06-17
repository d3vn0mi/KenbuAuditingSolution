# DEVLOG — Space Compliance Readiness & Evidence layer

Running log of significant decisions. ADRs in `docs/adr/`.

## 2026-06-17 — Phase 0: orientation & design

- Read existing codebase: `app/models/` (platform, benchmark, check, audit,
  hardening, pentest, standard, user), `app/utils/` (seed, excel_export),
  `app/config.py`, `app/routes/`, `data/`, `migrations/`.
- **Key finding:** a thin regulatory layer already exists — `Standard` /
  `StandardCheck` with GDPR + NIS2 seeded, and `data/standards/nis2.yaml` already
  mapping NIS2 Art 21 sub-points to CIS `check_number`s (~200 mappings). Kickoff
  did not mention it; reconciliation is the central design decision.
- Confirmed build is **PostgreSQL-ready** (dev/prod default to PG; tests SQLite
  in-memory). Migration head = `c3d4e5f6a7b8`.
- Wrote `docs/DESIGN_compliance.md` (ER model, YAML schema, scoring, evidence
  lifecycle, migration/tenancy plan, open questions).
- ADRs: 0001 regulatory layer architecture (promote `Standard`→`Regulation`,
  recommended), 0002 PDF engine (WeasyPrint), 0003 tenancy + evidence storage
  (single-tenant MVP, Fernet-encrypted filesystem evidence).
- **Status: PAUSED for review** (Phase 0 gate). Open questions in DESIGN §11 —
  the Standard↔Regulation reconciliation (Option A vs B) is the #1 item.

## 2026-06-17 — Phase 0 review: decisions locked

- **#1 Reconciliation: Option A** — promote `Standard`→`Regulation` (rename table,
  add columns, repoint `AuditSession.standard_id`→`regulation_id`).
- **#2 EU Space Act:** seed now, `status: in_trilogue`, versioned.
- **#3 Evidence storage:** filesystem (`instance/`) + Fernet encryption at rest.
- **#4 PDF:** WeasyPrint.
- **#5 Finding:** new general `Finding` model + `promoted_from` link.
- **#6 Control library:** authored best-effort from public regulatory text + the
  existing `nis2.yaml`; NIS2 + EUSA fuller, CER/CSA2 skeleton; flagged for RAVEN
  expert review.
- **Phase 1 started.** Sequence: m1 promote Standard→Regulation → m2 regulatory
  layer (Obligation/Control/joins) → YAML + validator + seed → browse UI.

## 2026-06-17 — Phase 1: m1 + m2 implemented (TDD)

- Branch `feat/compliance-layer`.
- **m1** (`d4e5f6a7b8c9`): promoted `Standard`→`Regulation` (+ short_code, status,
  effective_date, source_url), `StandardCheck`→`RegulationCheck`, repointed
  `AuditSession.regulation_id`. Updated routes/templates/seed/export. Migration
  validated upgrade+downgrade on a throwaway Postgres 16 (data preserved,
  constraints renamed, fully reversible).
- **m2** (`e5f6a7b8c9d0`): Control hub — `Obligation` (hierarchical, content_hash),
  `Control` (M:N to obligations across regs + M:N to existing `Check`),
  `EvidenceRequirement`, `ControlReference`. 6 new tables; up+down validated on PG.
- Test suite green: **77 passed** (added test_regulations, test_controls).
- Note: project migrations are PG-targeted deltas on a `create_all` base (the base
  Alembic revision already ALTERs `users`); dev/test SQLite uses create_all+seed.
- Note: local pytest needs `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` (broken global
  `anchorpy` plugin in this env); CI will use a clean venv.
- **Next:** YAML schema (`data/regulations/`, `data/controls/`, `data/mappings/`)
  + `scripts/validate_regulations.py` + seed loader + starter content (NIS2 from
  existing mappings, EUSA in_trilogue skeleton), then browse UI.
