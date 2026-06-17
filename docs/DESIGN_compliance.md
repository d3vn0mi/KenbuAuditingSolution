# Kenbu — Space Compliance Readiness & Evidence Layer (Design)

**Status:** Phase 0 — design for review. No code written yet beyond this document set.
**Date:** 2026-06-17
**Scope:** Extend Kenbu (existing CIS audit tool) into a space-sector compliance
readiness & evidence platform (EU Space Act resilience chapter, NIS2, CER, CSA2),
while keeping the proven technical-check model untouched.

This document is the deliverable for **Phase 0** of the kickoff. It ends with a
list of open questions. **Implementation is paused pending review of this doc.**

---

## 1. Orientation — the existing system (real names)

Read from `app/models/`, `app/routes/`, `app/utils/`, `data/`, `migrations/`.

### 1.1 Technical-check core (the moat — DO NOT disturb)

```
Platform ──< Benchmark ──< BenchmarkSection ──< (self) ──< Check
                                                            │
                          AuditAsset ──< AuditResult ───────┘  (status, finding)
                          HardeningAsset ──< HardeningCheckResult
```

| Model | File | Key fields |
|-------|------|-----------|
| `Platform` | `app/models/platform.py` | name, slug, os_family, icon |
| `Benchmark` | `app/models/benchmark.py` | name, version, platform_id, release_date, url |
| `BenchmarkSection` | `app/models/benchmark.py` | benchmark_id, parent_id (self-ref), number, title, sort_order |
| `Check` | `app/models/check.py` | section_id, check_number, title, description, rationale, **level**, **scored**, **audit_command**, audit_steps, **expected_output**, remediation, references |

`Check.audit_command` / `expected_output` are the real audit-command IP. **Nothing
in the regulatory layer writes to or reshapes `Check`.**

### 1.2 Audit / hardening / pentest workflows

| Model | File | Notes |
|-------|------|-------|
| `AuditSession` | `app/models/audit.py` | user_id, title, **standard_id (nullable FK→standards)**, status (draft/in_progress/completed) |
| `AuditAsset`, `AuditAssetBenchmark`, `AuditResult` | `app/models/audit.py` | per-asset, per-check results: status ∈ pass/fail/not_applicable/not_checked, `finding` text |
| `HardeningTask` / `HardeningAsset` / `HardeningCheckResult` | `app/models/hardening.py` | status ∈ pending/done/skipped |
| `PentestAssessment` → `PentestPhase` → `PentestChecklistItem` | `app/models/pentest.py` | engagement workflow |
| **`PentestFinding`** | `app/models/pentest.py` | title, **severity** (critical/high/medium/low/informational), cvss_score, steps_to_reproduce, evidence, remediation, retest_status — **bound to a PentestAssessment, NOT to any control** |
| `PentestDocument`, `PentestTeamMember` | `app/models/pentest.py` | |

### 1.3 A regulatory layer already exists (thin)

This is the critical orientation finding and the kickoff did **not** mention it.

| Model | File | Fields |
|-------|------|--------|
| `Standard` | `app/models/standard.py` | name, slug, description, version |
| `StandardCheck` | `app/models/standard.py` | standard_id, check_id, **article**, **requirement** |

- Seeded with **GDPR** and **NIS2** (`app/utils/seed.py::seed_standards`).
- `data/standards/nis2.yaml` already **directly maps NIS2 Article 21 sub-points
  (a–j) and Art 23 to specific CIS `check_number`s** (~200 mappings). This is
  exactly the "passing a CIS check evidences a regulatory obligation" idea, in
  prototype form — **valuable seed content to reuse, not throw away.**
- `Standard` is consumed by: `AuditSession.standard_id`, `app/routes/audits.py`,
  `app/templates/audits/{new,detail,list}.html`, `app/utils/excel_export.py`
  (cover sheet). Surface to change = ~6 `.py` files + 3 templates.

### 1.4 Auth, config, seed, export, tests, migrations

- **`User`** (`app/models/user.py`): roles `admin / auditor / security_engineer /
  user`, `ROLE_PERMISSIONS` feature-gate sets, `is_approved`, MFA (pyotp), GitHub OAuth.
- **Config** (`app/config.py`): dev + prod default to **PostgreSQL**
  (`postgresql://kenbu:kenbu@db:5432/kenbu`); testing = SQLite in-memory. **Build is
  already PostgreSQL-ready.** `.env.example` ships PG vars.
- **Seed** (`app/utils/seed.py`): `seed_all(data_dir)` → platforms, users,
  standards (+ `data/standards/*.yaml` mappings), benchmarks (recursive
  section/check loader). CLI entry `seed.py`.
- **Excel** (`app/utils/excel_export.py`): `xlsxwriter`, reusable `_create_formats`,
  cover/checklist/summary sheets + pie charts. Three exporters (benchmark, audit, hardening).
- **Tests** (`tests/`, `conftest.py`): pytest; session-scoped `app`, function-scoped
  `db_session` (truncates tables between tests), `auth_client`/`admin_client`,
  `seed_data` fixture. SQLite in-memory.
- **Migrations**: Flask-Migrate/Alembic, hand-written data migrations exist.
  **Current head = `c3d4e5f6a7b8`** (pentest models). New migrations chain from it.
  Note: SQLite needs Alembic **batch mode** (`render_as_batch=True`) for
  ALTER/rename — relevant to the `Standard→Regulation` rename on dev SQLite.

---

## 2. Design principles applied

1. **Extend, don't rewrite.** New layer sits *alongside* `Check`; every schema
   change is a Flask-Migrate migration.
2. **Technical-check model untouched.** Regulatory controls link to checks via a
   join table; `Check` schema is not modified.
3. **Mappings are versioned DATA** (`data/regulations/`, `data/controls/`), not code.
4. **Narrow:** space operators + suppliers + defence/dual-use only.
5. **Expert-assisted:** structured readiness + maintained evidence + packs;
   no fleet of automated evidence integrations.
6. **EU residency + single-tenant-per-deployment MVP**, multi-tenancy designed-for.

---

## 3. The central decision — reconcile `Standard` vs the new `Regulation`

The kickoff specifies a *rich* regulatory layer (`Regulation` → `Obligation` →
`Control` ↔ `Check`). A *thin* one (`Standard`/`StandardCheck`) already exists.
Having both means "NIS2" exists as two entities — confusing and duplicative,
which principle #1 forbids ("reconcile, do not duplicate").

**Recommendation (Option A — promote):** treat `Regulation` as the evolution of
`Standard`.

- Migration **renames `standards`→`regulations`** and adds `short_code`,
  `status`, `effective_date`, `source_url` (keep name/slug/description/version).
- **`Standard` model class → `Regulation`**; repoint `AuditSession.standard_id`
  → `regulation_id` (FK→regulations). Update the ~6 files + 3 templates.
- The thin direct map `StandardCheck` is **superseded** by the new `Control↔Check`
  path. We do **not** auto-convert its rows (lossy); instead the curated
  `data/standards/nis2.yaml` content is **re-authored into the new
  `data/regulations/nis2/` + `data/controls/` YAML** during Phase 1 — reusing the
  intellectual content, dropping the redundant table after NIS2 controls seed.

**Alternative (Option B — coexist + bridge):** leave `Standard`/`StandardCheck`
and `AuditSession.standard_id` untouched; add `Regulation` etc. beside them;
`Regulation.legacy_standard_slug` bridges the two; import `nis2.yaml` mappings as
`control_checks`. Zero risk to the audit flow, but two parallel regulatory
concepts persist.

> **This is the #1 review question (see §11).** The rest of this doc assumes
> **Option A**. Under Option B the only deltas are: keep `Standard`, no FK rename,
> add a bridge column.

---

## 4. New entity-relationship model

```
                         ┌──────────────────────────────────────────┐
Regulation ──< Obligation │ (article/sub-article, self-ref hierarchy) │
   │  (versioned,         └──────────────────────────────────────────┘
   │   status)                          │
   │                                    │ control_obligations (M:N)
   │                                    ▼
   │                                 Control ──< EvidenceRequirement
   │                                 │  │ │
   │            control_checks (M:N) │  │ └──< ControlReference  (ISO/NIST IR/ECSS/CCSDS xref)
   │                                 ▼  │
   │                              Check  │ (EXISTING — unchanged)
   │                                     │
   ▼                                     ▼
ReadinessAssessment ──< ControlStatus ──┘   (status, maturity, owner, target_date)
   │                        │  │
   │                        │  └──< (links) Evidence   via evidence_controls (M:N)
   │                        └──< (links) Finding       via finding_controls (M:N)
   │
   └── (rolls up to) readiness score per regulation / domain

Evidence ──< EvidenceVersion        (content_hash, valid_until, version history)
Finding   (severity; imported from RAVEN TLPT / pentest / internal)
   └── (optional) promoted_from → PentestFinding
Organization (tenant anchor; single default row for MVP)
```

### 4.1 Regulatory model (Phase 1)

| Model | Table | Key fields |
|-------|-------|-----------|
| `Regulation` | `regulations` | name, short_code (`EUSA`,`NIS2`,`CER`,`CSA2`), slug, version, **status** (proposal/in_trilogue/adopted/in_force), effective_date, source_url, description |
| `Obligation` | `obligations` | regulation_id, parent_id (self-ref), **ref** (e.g. `Art.21(2)(d)`), title, text, sort_order, **content_hash** (delta detection) |
| `Control` | `controls` | code (`AC-01`), title, description, **domain** (e.g. IAM, Crypto, SupplyChain, TLPT, IncidentMgmt, BCDR), guidance |
| `EvidenceRequirement` | `evidence_requirements` | control_id, title, description, type (document/config/test_result/attestation), cadence_days |
| `ControlReference` | `control_references` | control_id, framework (`ISO27001`,`NIST_IR_8270`,`NIST_IR_8401`,`ECSS`,`CCSDS`,`ENISA_SPACE`), ref_code (`A.5.23`), title |
| `control_obligations` | assoc table | control_id, obligation_id (cross-regulation M:N) |
| `control_checks` | assoc table | control_id, check_id (control evidenced by a technical check) |

Design notes:
- **`Control` is the cross-framework hub.** One control can satisfy Space Act
  Art X *and* NIS2 Art 21(g) *and* ISO 27001 A.x — that synthesis is the product.
- **In-scope regulations** (EUSA/NIS2/CER/CSA2) get full `Obligation` trees.
  **Reference standards** (ISO/NIST IR/ECSS/CCSDS/ENISA) are modelled as lighter
  `ControlReference` rows, not full obligation hierarchies — they are cross-map
  anchors, not assessable regulations. (ISO 27001 may later be promoted to a full
  `Regulation` so an existing ISMS cert becomes a mapping anchor.)

### 4.2 Readiness & evidence model (Phase 2)

| Model | Table | Key fields |
|-------|-------|-----------|
| `ReadinessAssessment` | `readiness_assessments` | organization_id, regulation_id (nullable = cross-reg), title, status, owner_id, created_at |
| `ControlStatus` | `control_statuses` | assessment_id, control_id, **status** (not_started/planned/partial/implemented/not_applicable), maturity (0–5), owner_id, target_date, notes |
| `Evidence` | `evidence` | organization_id, title, owner_id, collected_at, **valid_until**, review_date, **content_hash** (sha256), storage_path, mime, size, current_version |
| `EvidenceVersion` | `evidence_versions` | evidence_id, version, content_hash, storage_path, collected_at, note |
| `Finding` | `findings` | organization_id, title, **severity**, source (tlpt/pentest/internal/scan), description, remediation, status (open/remediated/accepted), discovered_at, promoted_from_pentest_finding_id (nullable) |
| `evidence_controls` | assoc | evidence_id, control_id |
| `evidence_checks` | assoc | evidence_id, check_id (reuse audit results as evidence) |
| `finding_controls` | assoc | finding_id, control_id |
| `Organization` | `organizations` | name, slug (single default row for MVP) |

`AuditResult.finding` (existing per-check note) stays; `evidence_checks` lets an
audit result double as control evidence without schema change to `AuditResult`.

---

## 5. YAML data schema (`data/regulations/`, `data/controls/`)

Mirrors `data/benchmarks/` spirit; loaded by extending `app/utils/seed.py`;
validated by `scripts/validate_regulations.py` (add `jsonschema`).

### 5.1 Layout
```
data/
  regulations/
    nis2/regulation.yaml          # meta + obligation tree
    eu_space_act/regulation.yaml
    cer/regulation.yaml
    csa2/regulation.yaml
  controls/
    controls.yaml                 # the cross-framework control library
  mappings/
    nis2.yaml                     # control_code → [obligation refs]
    eu_space_act.yaml
    ...
```

### 5.2 `regulations/<reg>/regulation.yaml`
```yaml
regulation:
  short_code: NIS2
  name: "Network and Information Security Directive (EU) 2022/2555"
  slug: nis2
  version: "2022/2555"
  status: in_force            # proposal | in_trilogue | adopted | in_force
  effective_date: "2024-10-17"
  source_url: "https://eur-lex.europa.eu/eli/dir/2022/2555"
obligations:
  - ref: "Art.21"
    title: "Cybersecurity risk-management measures"
    children:
      - ref: "Art.21(2)(d)"
        title: "Supply chain security"
        text: "Security related to the acquisition, development and maintenance..."
```

### 5.3 `controls/controls.yaml`
```yaml
controls:
  - code: SC-01
    title: "Supply-chain risk management programme"
    domain: SupplyChain
    description: "..."
    checks: ["1.2.1", "1.4.2", "1.6.2"]      # existing CIS check_numbers
    evidence_requirements:
      - title: "Approved supplier register"
        type: document
        cadence_days: 365
    references:
      - {framework: ISO27001, ref_code: "A.5.19", title: "Supplier relationships"}
      - {framework: NIST_IR_8401, ref_code: "GS-SC", title: "Ground-segment supply chain"}
```

### 5.4 `mappings/<reg>.yaml`
```yaml
regulation_slug: nis2
mappings:
  - control: SC-01
    obligations: ["Art.21(2)(d)"]
```

Resolution order at seed: regulations (obligations) → controls (+ check links by
`check_number`, + references, + evidence requirements) → mappings
(control↔obligation). Unknown check_numbers/refs are logged, not fatal.

---

## 6. Versioning & delta detection

The EU Space Act is a **proposal in trilogue** (Council vs Parliament divergence)
— volatility is a product feature.

- `Regulation.status` + `version` express maturity.
- Each `Obligation` carries a `content_hash` (sha256 of `ref|title|text`).
- A `flask regs diff <slug>` command (and the validator) compares YAML vs DB and
  reports **added / removed / changed** obligations and any controls whose mapped
  obligations changed — reusing the spirit of CIS version tracking.
- When the trilogue text settles, update the YAML + bump `version`; the diff report
  shows reviewers exactly what moved. No code change required.

---

## 7. Readiness scoring

Two complementary numbers, computed in a `app/utils/readiness.py` service:

1. **Control implementation score** (per assessment, per domain):
   `not_started=0, planned=0.25, partial=0.5, implemented=1.0`,
   `not_applicable` excluded from denominator. Domain score = mean of its controls.
2. **Obligation coverage** (per regulation): an obligation is *covered* if ≥1
   mapped control is `implemented` (partial → "partially covered"). Regulation
   readiness = covered / total in-scope obligations.

**Finding impact (the offensive-led differentiator):** an `open` `Finding` of
severity ≥ high linked to a control caps that control's effective status at
`partial` (configurable), feeding straight into the score. This is what pure-GRC
tools cannot do — the readiness number reflects *tested* reality.

**Remediation roadmap** = gap list of controls not `implemented`, ranked by
`impact (obligation count × max linked finding severity) × effort (inverse of
maturity)`; exportable.

---

## 8. Evidence lifecycle

1. **Capture:** upload artifact (or link an `AuditResult`/`Check` via
   `evidence_checks`). Store `content_hash` (sha256), `collected_at`.
2. **Validate:** `valid_until` / `review_date`; a `flask evidence expiring`
   command + dashboard "freshness" view flag items past/near expiry.
3. **Version:** re-upload creates an `EvidenceVersion`; hash chain proves integrity.
4. **Link:** to controls (`evidence_controls`) and/or checks (`evidence_checks`).
5. **At rest:** files stored under an instance evidence dir, **encrypted with
   Fernet** (key from env); never logged. (Security requirement, not afterthought.)

---

## 9. Export (Phase 3)

- **Excel:** extend `app/utils/excel_export.py` with `export_readiness_to_excel`
  reusing `_create_formats`: cover (regulation + version stamp + assessment date),
  readiness scorecard, control register (status/owner/mapped obligations),
  evidence index (control → evidence, dates, hash), gap/remediation sheet.
- **PDF:** add **WeasyPrint** (HTML/CSS→PDF) — reuse Jinja2 templates so the
  branded pack matches the web UI; produces a regulator/supervisor/prime-ready
  document. (Docker needs cairo/pango libs — see ADR-0002.)

---

## 10. Migration, tenancy, security, deployment

- **Migrations** chain from head `c3d4e5f6a7b8`, one per logical group:
  `m1` rename standards→regulations (+columns, repoint audit FK; batch mode for
  SQLite); `m2` regulatory layer (obligations/controls/joins/refs/evidence_reqs);
  `m3` readiness (assessments/control_statuses); `m4` evidence + findings + orgs.
- **PostgreSQL** confirmed default (dev/prod); SQLite kept for dev/tests.
- **Tenancy:** `Organization` table + nullable `organization_id` on top-level new
  entities; MVP runs a single default org per deployment. Enabling multi-tenancy
  later = add tenant scoping/filters, no destructive migration.
- **RBAC:** for MVP extend `ROLE_PERMISSIONS` with a `compliance` feature gate
  reusing existing roles. Full Admin/Lead Auditor/Auditor/Viewer + activity log is
  Phase 4 (per kickoff sequencing).
- **Security:** access control on every route, Fernet evidence encryption at rest,
  activity log (Phase 4), tenant isolation, EU self-hosting (Caddy/Docker unchanged).
  Never log secrets or evidence contents.
- **Tests:** pytest alongside each model/seed/scoring/evidence/export change; add
  `data/regulations` fixtures; CI workflow `.github/workflows/ci.yml` (pytest + the
  YAML validator). Existing CIS tests must stay green.

---

## 11. Open questions (resolve before Phase 1)

1. **§3 Standard↔Regulation:** Option A (promote/rename — recommended) or Option B
   (coexist + bridge, zero risk to audit flow)?
2. **EU Space Act article numbers:** kickoff says "~75–95"; the proposal is in
   flux. Seed against the latest Commission/Council text now and version it, or
   wait for the trilogue settle? (Recommend: seed now, `status: in_trilogue`.)
3. **Evidence storage:** filesystem (instance dir, Fernet) for MVP, or object
   storage (S3-compatible, EU region) from the start? (Recommend filesystem MVP.)
4. **Organization granularity:** single default org for MVP confirmed? Any need
   for sub-org / business-unit scoping in the readiness assessment now?
5. **PDF engine:** WeasyPrint (HTML/CSS, recommended) vs ReportLab (programmatic)?
   WeasyPrint adds native Docker deps.
6. **`Finding` vs `PentestFinding`:** new general `Finding` with optional
   `promoted_from` link (recommended), confirmed? Auto-import format for external
   RAVEN TLPT findings — CSV, JSON, or both?
7. **Control library authorship:** who supplies the canonical EUSA/CER/CSA2
   control text and the control↔check expert mappings (RAVEN), and at what
   coverage for MVP (e.g. NIS2 + EUSA full; CER/CSA2 skeleton)?

---

## 12. Deliverables status (Phase 0)

- [x] Repo orientation with real model/field names (§1)
- [x] New ER model (§4)
- [x] YAML schema for regulations/controls/mappings (§5)
- [x] Regulatory→technical-check linkage (`control_checks`, §4.1)
- [x] Readiness scoring method (§7)
- [x] Evidence lifecycle (§8)
- [x] Migration + tenancy + PostgreSQL plan (§10)
- [x] ADRs: `docs/adr/0001`, `0002`, `0003`
- [ ] **Review & approval — STOP here.**
