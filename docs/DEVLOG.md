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

## 2026-06-17 — Phase 1 complete

- **m3** data pipeline: idempotent YAML loader (regulations/controls/mappings) with
  obligation content_hash; `scripts/validate_regulations.py` (jsonschema +
  referential integrity). Starter data: NIS2 (in_force), EU Space Act
  (in_trilogue, provisional Art. numbers), CER + CSA2 skeletons; 12-control
  starter library linked to real CIS checks + ISO/NIST IR refs. Smoke: 5 regs,
  30 obligations, 12 controls, 213 control↔check links; SC-01 spans NIS2+EUSA+CSA2.
- **m4** browse UI: regulations blueprint + templates (list, regulation detail with
  recursive obligation tree + mapped controls, control detail with cross-framework
  mapping + linked checks + references + evidence requirements); nav links.
- **CI**: `.github/workflows/ci.yml` (deps, validate YAML, pytest).
- Test suite: **89 passed**. All four migrations PG-validated; existing CIS audit
  functionality unaffected.
- **Content is starter-level — flagged for RAVEN expert review/expansion** (esp.
  EUSA/CSA2 article numbers, CER/CSA2 obligations, full control coverage).
- **Phase 1 done. Awaiting review before Phase 2** (readiness assessment, scoring,
  evidence repository, finding→control linkage).

## 2026-06-17 — Phase 2 complete

- **m5** readiness: Organization, ReadinessAssessment, ControlStatus + scoring
  service (overall/domain score, obligation coverage, remediation roadmap;
  `effective_status` hook for finding impact). `compliance` permission feature.
  UI: dashboard (score, domain heatmap, coverage, gaps) + control register with
  inline HTMX status editing.
- **m6** evidence repository: Evidence + EvidenceVersion (+ link tables),
  Fernet-encrypted at rest via `app/utils/crypto.py` (MultiFernet) +
  `evidence_store.py` (hash plaintext before encrypt, UUID storage names,
  integrity-verify on download, fail-closed prod key). UI: list w/ freshness,
  upload, versions, download. Advisor crypto checklist applied; ADR 0003 updated
  with honest threat model.
- **m7** findings (offensive moat): Finding + finding_controls +
  promoted_from_pentest_finding; open high/critical finding caps linked control
  readiness. findings service (import JSON/CSV, promote pentest finding). UI:
  list/new/detail/import + promote; control detail shows findings + evidence.
- Migrations m5–m7 all validated upgrade+downgrade on throwaway Postgres.
- Test suite: **111 passed**. Existing CIS functionality unaffected.
- **Phase 2 done.** Remaining: Phase 3 (Excel + PDF evidence/readiness pack),
  Phase 4 (NIS2 incident workflow, CSA2 supplier/SBOM, RBAC + activity log).

## 2026-06-17 — Phase 3 complete (evidence/readiness pack export)

- `app/utils/pack.py` `build_context()` is the single source for both exporters
  (scorecard, domain readiness, coverage, control register, evidence index w/
  integrity hashes, remediation plan, regulation-version + date stamp).
- Excel: `export_readiness_to_excel` (5 sheets) reusing the xlsxwriter palette.
- PDF: WeasyPrint renders `app/templates/pack/readiness_pack.html`. Confirmed
  WeasyPrint works in this env (pango/cairo/harfbuzz present) — emits real PDFs.
- Routes `/readiness/<id>/export.xlsx` + `export.pdf` + dashboard buttons.
- weasyprint==63.1 dep; Dockerfile + CI install native libs.
- No new migration. Test suite: **117 passed**.
- **Phase 3 done.** Remaining: Phase 4 (NIS2 incident workflow, CSA2
  supplier/SBOM, RBAC + activity log + tenant hardening).

## 2026-06-17 — Phase 4 complete (operational extensions)

- **m8** NIS2 incident workflow: Incident model + statutory clock (24h/72h/1-month
  due dates, per-stage sent timestamps), incident_clock service, UI (log, clock
  timeline, mark-sent, printable per-stage report templates citing Art.23(4)).
- **m9** CSA2 supply chain: Supplier + SBOM + SBOMComponent (+ supplier_controls);
  SBOM parser for CycloneDX + SPDX JSON; UI (supplier register, SBOM upload →
  component table).
- **m10** RBAC + audit trail + tenancy: roles lead_auditor + viewer; split
  compliance into write (`compliance`) vs read (`compliance_view`) — viewer is
  read-only across the compliance layer; ActivityLog via after_request hook +
  admin activity view; default Organization seeded (single-tenant anchor).
- Migrations m8–m10 validated upgrade+downgrade on Postgres.
- Test suite: **135 passed**. App boots: 18 blueprints, 117 routes. Validator green.

## Summary — Phases 0–4 delivered

Branch `feat/compliance-layer`. Full loop: browse regulations → readiness
assessment + scoring → encrypted evidence + offensive findings (cap readiness) →
Excel/PDF pack → NIS2 incidents, CSA2 suppliers/SBOM, RBAC + activity log.
10 migrations (m1–m10), all PG-validated; existing CIS audit functionality intact.
Regulatory content is starter-level — flagged for RAVEN expert review.
