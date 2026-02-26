# CIS Auditor

A web-based security audit reference tool for CIS benchmark compliance. Provides auditors with a browsable catalog of CIS checks organized by benchmark and platform, with audit commands, expected outputs, and Excel export for fieldwork.

## Features

- **8 Platforms**: Debian 12, Ubuntu 24.04, Windows Server 2022, RHEL 9, CentOS 7, Amazon Linux 2023, macOS Sonoma, Cisco IOS 17
- **460+ CIS Checks** with real audit commands, expected outputs, and remediation steps
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
