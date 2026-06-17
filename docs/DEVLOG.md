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
