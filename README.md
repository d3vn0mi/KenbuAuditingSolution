# CIS Auditor

A web-based security audit reference tool for CIS benchmark compliance. Provides auditors with a browsable catalog of CIS checks organized by benchmark and platform, with audit commands, expected outputs, and Excel export for fieldwork.

## Features

- **8 Platforms**: Debian 12, Ubuntu 24.04, Windows Server 2022, RHEL 9, CentOS 7, Amazon Linux 2023, macOS Sonoma, Cisco IOS 17
- **635+ CIS Checks** with real audit commands, expected outputs, and remediation steps
- **Browse by Benchmark or Platform** with hierarchical section navigation
- **Search & Filter** across all checks by keyword, platform, level, and scored status
- **Excel Export** with formatted checklists, status dropdowns, and color-coded levels
- **Audit Sessions** to track pass/fail results per check during on-site audits
- **Audit Reports** with summary statistics, compliance rates, and pie charts
- **Basic Authentication** with username/password login

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Seed the database (creates tables, platforms, benchmarks, checks, and default admin user)
python seed.py

# Run the application
python run.py
```

Open http://localhost:5000 and log in with:
- **Username:** `admin`
- **Password:** `changeme`

## Usage

### Browsing Checks
- **Dashboard** shows stats and quick access to all platforms
- **Benchmarks** page lists all CIS benchmarks with section navigation
- **Platforms** page groups assets by OS family (Linux, Windows, macOS, Network)
- **Search** page allows filtering by keyword, platform, level (L1/L2), and scored status
- Each check shows: audit command (with copy button), expected output, GUI steps (where applicable), and remediation

### Exporting Checklists
- Click "Export to Excel" on any benchmark or audit session
- Exported Excel files include: cover sheet, formatted checklist with status dropdowns, and (for audits) a summary sheet with compliance statistics and charts

### Running Audits
1. Go to **Audits > New Audit**
2. Select a benchmark and enter the target system details
3. Work through the checklist, marking each check as Pass/Fail/N/A
4. Add findings notes per check
5. Export the completed audit to Excel

## Tech Stack

- **Backend:** Flask 3.x, Flask-SQLAlchemy, Flask-Login, Flask-Migrate
- **Database:** SQLite
- **Frontend:** Jinja2, HTMX, TailwindCSS (CDN)
- **Excel Export:** xlsxwriter
- **Seed Data:** YAML files in `data/benchmarks/`

## Project Structure

```
cis-auditor/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration
│   ├── extensions.py        # Flask extensions
│   ├── models/              # SQLAlchemy models
│   ├── routes/              # Flask blueprints
│   ├── templates/           # Jinja2 templates
│   └── utils/               # Excel export, seed logic
├── data/
│   └── benchmarks/          # YAML benchmark data (8 platforms)
├── instance/                # SQLite database (auto-created)
├── requirements.txt
├── run.py                   # Entry point
└── seed.py                  # Database seeder
```

## Adding More Checks

Checks are defined in YAML files under `data/benchmarks/`. To add checks:

1. Edit the relevant YAML file (e.g., `data/benchmarks/debian_12.yaml`)
2. Follow the existing structure for sections and checks
3. Re-run `python seed.py` to load new data

Each check requires: `number`, `title`, `description`, `rationale`, `level`, `scored`, `audit_command`, `expected_output`, and `remediation`.

## Roadmap

### v1.0 — MVP (Current)

The foundation is live with a fully functional audit reference tool.

| Feature | Status |
|---------|--------|
| 8 platforms (Debian, Ubuntu, Windows Server, RHEL, CentOS, Amazon Linux, macOS, Cisco IOS) | Done |
| 635+ CIS checks with audit commands, expected outputs, and remediation | Done |
| Browse by benchmark or platform with hierarchical section navigation | Done |
| HTMX-powered search and filtering (keyword, platform, level, scored) | Done |
| Excel export with formatted checklists, status dropdowns, color coding | Done |
| Audit session management (create, track pass/fail/N/A, complete) | Done |
| Audit report export with summary statistics and pie charts | Done |
| Basic authentication (username/password, Flask-Login) | Done |
| YAML-based seed data system for extensible benchmark definitions | Done |

---

### v1.1 — Audit Experience

Improve the day-to-day audit workflow for field auditors.

- **Evidence attachments** — Upload screenshots, logs, or files as proof per check during audits
- **Bulk status updates** — Select multiple checks and mark them pass/fail/N/A in one action
- **Audit comparison** — Diff two audit sessions against the same benchmark to track remediation progress
- **Print-friendly views** — CSS print styles for check details and full audit reports
- **Section-level notes** — Add auditor notes per section, not just per individual check
- **Audit templates** — Save and reuse custom check subsets (e.g., "Quick L1 Scan", "Network-only")
- **Dark mode** — Toggle for late-night audit work

---

### v1.2 — Expanded CIS Coverage

Scale from 635 to 2,000+ checks with full Level 1 Scored coverage.

- **Full L1 Scored coverage** for all 8 platforms (~150-250 checks per platform)
- **Modular YAML files** — Split each platform into per-section files for maintainability:
  ```
  data/benchmarks/debian_12/
  ├── 01_initial_setup.yaml
  ├── 02_services.yaml
  ├── 03_network.yaml
  ├── 04_logging.yaml
  ├── 05_access_auth.yaml
  └── 06_maintenance.yaml
  ```
- **YAML schema validation** — Automated script to enforce required fields and structure
- **CIS version tracking** — Map each check to its specific CIS benchmark version
- **Delta detection** — When CIS releases a new benchmark version, flag added/removed/changed checks
- **L2 Scored checks** — Second wave expansion after L1 coverage is complete
- **Expansion priority**: L1 Scored > L2 Scored > L1 Not Scored > L2 Not Scored

---

### v2.0 — Multi-Framework & Collaboration

Extend beyond CIS with team-based auditing capabilities.

**Additional Benchmark Frameworks:**
- NIST SP 800-53 (federal/government compliance)
- DISA STIG (Department of Defense hardening)
- ISO 27001 (information security management)
- PCI DSS (payment card industry)

**Additional Platforms:**
- PostgreSQL, MySQL (database servers)
- Apache HTTP Server, Nginx (web servers)
- Docker, Kubernetes (container infrastructure)
- AWS (IAM, S3, VPC, CloudTrail)

**Collaboration Features:**
- **Role-based access control** — Admin, Lead Auditor, Auditor, Viewer roles with granular permissions
- **Shared audit sessions** — Multiple auditors work on the same audit simultaneously
- **Audit assignment** — Lead auditor assigns specific sections or checks to team members
- **Activity log** — Track who changed what and when during an audit

**Analytics & API:**
- **Dashboard analytics** — Compliance trends over time, heatmaps by section, pass/fail ratios
- **REST API** — Programmatic access to benchmarks, checks, and audit results for CI/CD and SIEM integration
- **Webhook notifications** — Trigger alerts on audit events (session created, check failed, audit completed)

---

### v2.1 — Reporting & Compliance

Professional reporting for stakeholders and regulators.

- **PDF report generation** — Executive summary + detailed findings in branded PDF format
- **Custom report templates** — Upload company logo, set branding colors, configure report sections
- **Compliance scoring** — Weighted scoring per check based on risk impact and business criticality
- **Remediation priority matrix** — Rank findings by impact vs. effort to fix
- **Historical audit trail** — Full version history of every audit session and result change
- **Compliance drift detection** — Compare current state against previous audits to spot regressions
- **Scheduled audits** — Set recurring audit reminders with pre-configured benchmark and target
- **Export formats** — PDF, Excel, CSV, JSON for integration with GRC platforms

---

### v3.0 — Enterprise & Automation

Enterprise-grade features for large organizations and MSSPs.

- **SSO integration** — SAML 2.0 and OpenID Connect for enterprise identity providers
- **PostgreSQL support** — Production-grade database for multi-user deployments
- **Evidence vault** — Cryptographically signed evidence storage with integrity verification
- **Automated check execution** — Optional agent-based scanning via SSH (Linux), WinRM (Windows), and API (cloud/network) to auto-populate audit results
- **Remediation playbooks** — One-click fix scripts with approval workflow and rollback capability
- **Offline mode (PWA)** — Progressive Web App for audits in air-gapped or low-connectivity environments
- **Multi-tenancy** — Isolated tenant environments for managed security service providers (MSSPs)
- **LDAP/Active Directory sync** — Auto-provision users and groups from corporate directory
- **Compliance mapping** — Cross-reference checks across frameworks (e.g., CIS 5.2.1 maps to NIST AC-7)

---

## Contributing

### Adding New Checks

1. Edit the relevant YAML file in `data/benchmarks/`
2. Follow the existing section/check structure
3. Ensure every check has: `number`, `title`, `description`, `rationale`, `level`, `scored`, `audit_command`, `expected_output`, `remediation`
4. Run `python seed.py` to load changes

### Adding a New Platform

1. Create a new YAML file: `data/benchmarks/<platform_slug>.yaml`
2. Add the platform definition to `app/utils/seed.py` in the `seed_platforms()` function
3. Follow the benchmark YAML format used by existing platforms
4. Run `python seed.py`

### Adding a New Benchmark Framework

1. Create YAML files following the same structure (sections with numbered checks)
2. The `benchmark.name` field should reflect the framework (e.g., "NIST SP 800-53 Rev 5")
3. Map checks to the framework's control numbering system
4. The existing data model supports any hierarchical check framework
