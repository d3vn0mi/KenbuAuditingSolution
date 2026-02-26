# CIS Auditor - Product Design Document

## 1. Overview

**CIS Auditor** is a Python web application that serves as a reference and checklist
tool for security auditors performing CIS benchmark compliance audits. It is **not**
an automated scanner — it provides auditors with the knowledge of *what* to check,
*how* to verify it (commands or GUI steps), and *what the expected outcome* should be.

Auditors can browse checks by benchmark or by asset type, and export tailored Excel
checklists to carry during on-site audits.

---

## 2. Supported Assets (8 initial platforms)

| # | Asset Type       | OS Family | CIS Benchmark Reference                    |
|---|------------------|-----------|---------------------------------------------|
| 1 | Debian Linux     | Linux     | CIS Debian Linux 12 Benchmark              |
| 2 | Ubuntu Linux     | Linux     | CIS Ubuntu Linux 24.04 LTS Benchmark       |
| 3 | Windows Server   | Windows   | CIS Microsoft Windows Server 2022 Benchmark|
| 4 | RHEL             | Linux     | CIS Red Hat Enterprise Linux 9 Benchmark   |
| 5 | CentOS           | Linux     | CIS CentOS Linux 7 Benchmark               |
| 6 | Amazon Linux     | Linux     | CIS Amazon Linux 2023 Benchmark            |
| 7 | macOS            | macOS     | CIS Apple macOS 14 (Sonoma) Benchmark      |
| 8 | Cisco IOS        | Network   | CIS Cisco IOS 17 Benchmark                 |

---

## 3. Technology Stack

| Component        | Technology                       | Rationale                                    |
|------------------|----------------------------------|----------------------------------------------|
| Backend          | Flask 3.x                        | Lightweight, perfect for internal tools      |
| ORM              | Flask-SQLAlchemy (SQLAlchemy 2.0) | DB-agnostic, easy migration path             |
| Database         | SQLite                           | Zero config, portable, sufficient for scope  |
| Migrations       | Flask-Migrate (Alembic)          | Schema versioning                            |
| Excel Export     | xlsxwriter                       | Fast writes, excellent formatting            |
| Frontend         | Jinja2 + HTMX + TailwindCSS     | Modern, responsive, minimal JS              |
| Authentication   | Flask-Login + Werkzeug           | Simple username/password auth                |
| Password Hashing | Werkzeug security utils          | Secure bcrypt-based hashing                  |

---

## 4. Data Model

### 4.1 Entity Relationship

```
User (auth)
  |
  v
AuditSession ──────> Benchmark ──────> BenchmarkSection
  |                      |                    |
  v                      v                    v
AuditResult          Platform            Check
  |                                       │
  └───────────────────────────────────────┘
```

### 4.2 Models

#### `User`
```
id              INTEGER PRIMARY KEY
username        VARCHAR(80) UNIQUE NOT NULL
password_hash   VARCHAR(256) NOT NULL
display_name    VARCHAR(120)
created_at      DATETIME DEFAULT NOW
```

#### `Platform` (the asset type being audited)
```
id              INTEGER PRIMARY KEY
name            VARCHAR(100) NOT NULL        -- "Debian Linux 12"
slug            VARCHAR(50) UNIQUE NOT NULL   -- "debian-12"
os_family       VARCHAR(30) NOT NULL          -- "Linux" | "Windows" | "macOS" | "Network"
icon            VARCHAR(50)                   -- CSS class or emoji for UI
description     TEXT
```

#### `Benchmark`
```
id              INTEGER PRIMARY KEY
name            VARCHAR(200) NOT NULL        -- "CIS Debian Linux 12 Benchmark"
version         VARCHAR(20) NOT NULL          -- "1.1.0"
platform_id     INTEGER FK -> Platform
release_date    DATE
description     TEXT
url             VARCHAR(500)                  -- Link to official CIS PDF
```

#### `BenchmarkSection` (hierarchical categories)
```
id              INTEGER PRIMARY KEY
benchmark_id    INTEGER FK -> Benchmark
parent_id       INTEGER FK -> BenchmarkSection (nullable, self-referential)
number          VARCHAR(20) NOT NULL          -- "1", "1.1", "5.2"
title           VARCHAR(200) NOT NULL         -- "Initial Setup", "Filesystem Configuration"
description     TEXT
sort_order      INTEGER
```

#### `Check` (the core entity)
```
id              INTEGER PRIMARY KEY
section_id      INTEGER FK -> BenchmarkSection
check_number    VARCHAR(20) NOT NULL          -- "1.1.1.1"
title           VARCHAR(300) NOT NULL         -- "Ensure cramfs is disabled"
description     TEXT                          -- Why this matters
rationale       TEXT                          -- Security justification
level           INTEGER NOT NULL DEFAULT 1    -- CIS Level 1 or Level 2
scored          BOOLEAN NOT NULL DEFAULT TRUE -- Scored vs Not Scored
audit_command   TEXT                          -- Command to run for verification
audit_steps     TEXT                          -- GUI steps (for Windows/macOS)
expected_output TEXT NOT NULL                 -- What passing looks like
remediation     TEXT                          -- How to fix if failing
references      TEXT                          -- External references, CVEs
sort_order      INTEGER
```

#### `AuditSession` (tracks an auditor's work)
```
id              INTEGER PRIMARY KEY
user_id         INTEGER FK -> User
benchmark_id    INTEGER FK -> Benchmark
target_name     VARCHAR(200)                  -- "PROD-WEB-01"
target_ip       VARCHAR(45)                   -- Optional IP
started_at      DATETIME DEFAULT NOW
completed_at    DATETIME (nullable)
status          VARCHAR(20) DEFAULT 'in_progress'  -- in_progress | completed
notes           TEXT
```

#### `AuditResult` (per-check outcome during a session)
```
id              INTEGER PRIMARY KEY
session_id      INTEGER FK -> AuditSession
check_id        INTEGER FK -> Check
status          VARCHAR(20) DEFAULT 'not_checked'  -- pass | fail | not_applicable | not_checked
finding         TEXT                          -- Auditor's notes/evidence
checked_at      DATETIME
```

---

## 5. Project Structure

```
cis-auditor/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── config.py                # Configuration (dev/prod/test)
│   ├── extensions.py            # Flask extension instances
│   ├── models/
│   │   ├── __init__.py          # Import all models
│   │   ├── user.py              # User model
│   │   ├── platform.py          # Platform model
│   │   ├── benchmark.py         # Benchmark + Section models
│   │   ├── check.py             # Check model
│   │   └── audit.py             # AuditSession + AuditResult models
│   ├── routes/
│   │   ├── __init__.py          # Register all blueprints
│   │   ├── auth.py              # Login/logout/register
│   │   ├── main.py              # Dashboard, home
│   │   ├── benchmarks.py        # Browse benchmarks, sections, checks
│   │   ├── platforms.py         # Browse by platform/asset
│   │   ├── checks.py            # Check detail views
│   │   ├── audits.py            # Audit session management
│   │   └── export.py            # Excel export endpoints
│   ├── templates/
│   │   ├── base.html            # Base layout with nav, TailwindCSS, HTMX
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   └── register.html
│   │   ├── main/
│   │   │   └── dashboard.html   # Home page with stats + quick access
│   │   ├── benchmarks/
│   │   │   ├── list.html        # All benchmarks grid
│   │   │   ├── detail.html      # Single benchmark with sections tree
│   │   │   └── section.html     # Section with checks table
│   │   ├── platforms/
│   │   │   ├── list.html        # All platforms grid
│   │   │   └── detail.html      # Platform with its benchmarks
│   │   ├── checks/
│   │   │   ├── detail.html      # Full check view (command, expected, etc.)
│   │   │   ├── _check_row.html  # HTMX partial: single check table row
│   │   │   └── _search.html     # HTMX partial: search results
│   │   ├── audits/
│   │   │   ├── list.html        # Audit sessions list
│   │   │   ├── session.html     # Active audit session with checklist
│   │   │   └── _result_row.html # HTMX partial: check result update
│   │   └── export/
│   │       └── options.html     # Export configuration modal/page
│   ├── static/
│   │   ├── css/
│   │   │   └── app.css          # TailwindCSS compiled output
│   │   ├── js/
│   │   │   └── app.js           # Minimal JS (HTMX config, utilities)
│   │   └── img/                 # Platform icons, logos
│   └── utils/
│       ├── __init__.py
│       ├── excel_export.py      # xlsxwriter export logic
│       └── seed.py              # Database seeding from YAML
├── data/
│   ├── benchmarks/
│   │   ├── debian_12.yaml       # CIS Debian 12 checks
│   │   ├── ubuntu_2404.yaml     # CIS Ubuntu 24.04 checks
│   │   ├── windows_2022.yaml    # CIS Windows Server 2022 checks
│   │   ├── rhel_9.yaml          # CIS RHEL 9 checks
│   │   ├── centos_7.yaml        # CIS CentOS 7 checks
│   │   ├── amazon_linux_2023.yaml # CIS Amazon Linux 2023 checks
│   │   ├── macos_sonoma.yaml    # CIS macOS Sonoma checks
│   │   └── cisco_ios_17.yaml    # CIS Cisco IOS 17 checks
│   └── seed_users.yaml          # Default admin user
├── migrations/                  # Alembic migration files
├── tests/
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_routes.py
│   └── test_export.py
├── requirements.txt
├── tailwind.config.js           # TailwindCSS configuration
├── package.json                 # Node deps for TailwindCSS build
├── run.py                       # Entry point
├── seed.py                      # CLI command to seed database
├── DESIGN.md                    # This file
└── README.md
```

---

## 6. Benchmark Data Format (YAML)

Each benchmark YAML file follows this structure:

```yaml
benchmark:
  name: "CIS Debian Linux 12 Benchmark"
  version: "1.1.0"
  platform: "debian-12"
  release_date: "2024-01-15"
  description: "CIS benchmark for Debian GNU/Linux 12"
  url: "https://www.cisecurity.org/benchmark/debian_linux"

sections:
  - number: "1"
    title: "Initial Setup"
    children:
      - number: "1.1"
        title: "Filesystem Configuration"
        children:
          - number: "1.1.1"
            title: "Disable unused filesystems"
            checks:
              - number: "1.1.1.1"
                title: "Ensure cramfs kernel module is not available"
                description: "The cramfs filesystem type is a compressed..."
                rationale: "Removing support for unneeded filesystem types..."
                level: 1
                scored: true
                audit_command: |
                  modprobe -n -v cramfs
                  lsmod | grep cramfs
                expected_output: |
                  install /bin/false
                  (no output from lsmod, meaning module is not loaded)
                remediation: |
                  Create a file ending in .conf in /etc/modprobe.d/:
                  echo "install cramfs /bin/false" >> /etc/modprobe.d/cramfs.conf
                  echo "blacklist cramfs" >> /etc/modprobe.d/cramfs.conf
```

---

## 7. CIS Check Categories per Asset (30+ checks each)

### 7.1 Debian Linux 12 / Ubuntu 24.04 / RHEL 9 / CentOS 7 / Amazon Linux 2023
(Linux family — similar categories, platform-specific commands)

| Section | Category                              | Sample Checks                                          |
|---------|---------------------------------------|--------------------------------------------------------|
| 1       | Initial Setup                         | Filesystem config, software updates, boot settings     |
| 1.1     | Filesystem Configuration              | Disable cramfs/squashfs, /tmp partition, mount options  |
| 1.2     | Configure Software Updates            | Ensure GPG keys configured, repo configured             |
| 1.3     | Filesystem Integrity Checking         | AIDE installed, cron job for integrity check            |
| 1.4     | Secure Boot Settings                  | Bootloader password, permissions on boot config         |
| 2       | Services                              | Time sync, X Window, mail transfer agent                |
| 2.1     | Special Purpose Services              | Disable avahi, CUPS, DHCP, LDAP, NFS, DNS, FTP, SNMP   |
| 3       | Network Configuration                 | IP forwarding, ICMP redirects, source routing           |
| 3.1     | Network Parameters (Host)             | IP forwarding disabled, packet redirect                 |
| 3.2     | Network Parameters (Host and Router)  | Suspicious packets logged, TCP SYN cookies              |
| 3.3     | Firewall Configuration                | iptables/nftables installed, default deny               |
| 4       | Logging and Auditing                  | rsyslog/journald, auditd configuration                  |
| 4.1     | Configure System Accounting (auditd)  | Audit log storage, rules for privileged commands        |
| 4.2     | Configure Logging                     | rsyslog installed, remote log host, file permissions    |
| 5       | Access, Authentication, Authorization | SSH config, PAM, password policy, sudo                  |
| 5.1     | Configure time-based job schedulers   | cron permissions, at daemon                             |
| 5.2     | SSH Server Configuration              | SSH protocol, log level, X11 forwarding, MaxAuthTries   |
| 5.3     | Configure PAM                         | Password length, complexity, lockout                    |
| 5.4     | User Accounts and Environment         | Password expiration, inactive lockout, default umask    |
| 6       | System Maintenance                    | File permissions, user/group settings                   |
| 6.1     | System File Permissions               | Passwd, shadow, group file permissions                  |
| 6.2     | User and Group Settings               | No duplicate UIDs/GIDs, root is only UID 0              |

### 7.2 Windows Server 2022

| Section | Category                              | Sample Checks                                          |
|---------|---------------------------------------|--------------------------------------------------------|
| 1       | Account Policies                      | Password policy, account lockout                        |
| 1.1     | Password Policy                       | Min length, complexity, history, max age                |
| 1.2     | Account Lockout Policy                | Lockout threshold, duration, reset counter              |
| 2       | Local Policies                        | Audit policy, user rights, security options             |
| 2.2     | Audit Policy                          | Logon events, object access, policy changes             |
| 2.3     | Security Options                      | Admin/Guest account rename, LAN Manager auth            |
| 5       | System Services                       | Disable unnecessary services                            |
| 9       | Windows Firewall                      | Domain/Private/Public profile settings                  |
| 17      | Advanced Audit Policy                 | Detailed audit subcategories                            |
| 18      | Administrative Templates              | Various Group Policy settings                           |
| 19      | Administrative Templates (User)       | User-level policy settings                              |

### 7.3 macOS Sonoma

| Section | Category                              | Sample Checks                                          |
|---------|---------------------------------------|--------------------------------------------------------|
| 1       | Install Updates                       | Auto-update, app update settings                        |
| 2       | System Preferences                    | Bluetooth, date/time, sharing, screen saver             |
| 2.1     | Bluetooth                             | Disable if not needed, show status in menu              |
| 2.3     | General                               | Show filename extensions                                |
| 2.4     | Date & Time                           | Time source, time zone auto                             |
| 2.5     | Sharing                               | Screen sharing, file sharing, remote login              |
| 2.6     | Security & Privacy                    | Gatekeeper, FileVault, Firewall                         |
| 3       | Logging and Auditing                  | Security auditing, install.log retention                |
| 4       | Network Configurations                | Bonjour advertising, Wi-Fi status, HTTP server          |
| 5       | System Access, Authentication         | Login window, password hints, guest access              |
| 6       | User Accounts                         | Automatic login, root account disabled                  |

### 7.4 Cisco IOS 17

| Section | Category                              | Sample Checks                                          |
|---------|---------------------------------------|--------------------------------------------------------|
| 1       | Management Plane                      | AAA, access rules, banner, passwords                   |
| 1.1     | Local Authentication                  | Enable secret, service password-encryption              |
| 1.2     | AAA Rules                             | AAA new model, authentication/authorization             |
| 1.3     | Access Rules                          | VTY transport, exec-timeout, ACL for VTY               |
| 1.4     | Banner Rules                          | Login/MOTD banner configured                           |
| 2       | Control Plane                         | SSH, NTP, logging                                       |
| 2.1     | Global Service Rules                  | CDP disabled, bootp server disabled, DHCP snooping     |
| 2.2     | Logging Rules                         | Logging enabled, timestamps, buffered logging          |
| 2.3     | NTP Rules                             | NTP authentication, trusted key                         |
| 2.4     | Loopback Rules                        | Source interface for NTP/SNMP/logging                   |
| 3       | Data Plane                            | Routing, interfaces, ACLs                               |
| 3.1     | Routing Rules                         | No IP source routing, uRPF                              |
| 3.2     | Border Router Filtering               | IP directed broadcast disabled, proxy-arp               |
| 3.3     | Neighbor Authentication               | OSPF/EIGRP authentication                              |

---

## 8. URL Routes

### Authentication
| Method | URL                    | Description                |
|--------|------------------------|----------------------------|
| GET    | `/auth/login`          | Login page                 |
| POST   | `/auth/login`          | Process login              |
| GET    | `/auth/register`       | Registration page          |
| POST   | `/auth/register`       | Process registration       |
| GET    | `/auth/logout`         | Logout                     |

### Main
| Method | URL                    | Description                |
|--------|------------------------|----------------------------|
| GET    | `/`                    | Dashboard with stats       |

### Benchmarks (browse by benchmark)
| Method | URL                              | Description                    |
|--------|----------------------------------|--------------------------------|
| GET    | `/benchmarks`                    | All benchmarks grid            |
| GET    | `/benchmarks/<id>`               | Benchmark detail with sections |
| GET    | `/benchmarks/<id>/section/<sid>` | Section with checks            |

### Platforms (browse by asset)
| Method | URL                              | Description                    |
|--------|----------------------------------|--------------------------------|
| GET    | `/platforms`                     | All platforms grid             |
| GET    | `/platforms/<slug>`              | Platform detail + benchmarks   |

### Checks
| Method | URL                              | Description                    |
|--------|----------------------------------|--------------------------------|
| GET    | `/checks/<id>`                   | Full check detail view         |
| GET    | `/checks/search`                 | HTMX: search checks            |

### Audits
| Method | URL                              | Description                    |
|--------|----------------------------------|--------------------------------|
| GET    | `/audits`                        | List audit sessions            |
| POST   | `/audits/new`                    | Create new audit session       |
| GET    | `/audits/<id>`                   | Audit session detail           |
| POST   | `/audits/<id>/check/<check_id>`  | HTMX: update check result      |
| POST   | `/audits/<id>/complete`          | Mark session as complete       |

### Export
| Method | URL                              | Description                    |
|--------|----------------------------------|--------------------------------|
| GET    | `/export/benchmark/<id>`         | Export benchmark checks to Excel|
| GET    | `/export/audit/<id>`             | Export audit session to Excel  |
| GET    | `/export/options`                | Export configuration page      |

---

## 9. Excel Export Format

### Benchmark Export (empty checklist for fieldwork)

**Sheet 1: "Cover"**
- Benchmark name, version, release date
- Export date, auditor name
- Target system placeholder fields

**Sheet 2: "Checklist"**
| Column          | Width | Description                                      |
|-----------------|-------|--------------------------------------------------|
| Section         | 10    | Check number (1.1.1.1)                           |
| Title           | 40    | Check title                                      |
| Level           | 8     | L1 or L2                                         |
| Scored          | 8     | Yes/No                                           |
| Audit Command   | 50    | Command to run or GUI steps                      |
| Expected Output | 40    | What passing looks like                          |
| Status          | 12    | Empty (Pass/Fail/N/A — auditor fills in)         |
| Findings        | 40    | Empty (auditor fills in during audit)            |
| Remediation     | 40    | How to fix if failing                            |

**Formatting:**
- Header row: bold, dark background, white text, frozen panes
- Alternating row colors for readability
- Section grouping with indentation
- Level 1 checks: white background
- Level 2 checks: light yellow background
- Column auto-width with wrapping
- Data validation dropdown for Status column (Pass/Fail/N/A/Not Checked)

### Audit Session Export (completed checklist)

Same as above but with Status and Findings columns pre-filled from AuditResult records.

**Sheet 3: "Summary"**
- Total checks, pass count, fail count, N/A count
- Compliance percentage by section
- Pie chart of results distribution

---

## 10. UI Design

### Dashboard (`/`)
- Welcome message with user name
- Stats cards: total benchmarks, total checks, active audits
- Quick access: grid of platform cards with icons
- Recent audit sessions list

### Benchmark List (`/benchmarks`)
- Card grid showing each benchmark
- Each card: platform icon, benchmark name, version, check count
- Click to drill into sections

### Benchmark Detail (`/benchmarks/<id>`)
- Collapsible section tree (accordion style)
- Each section shows: number, title, check count
- Expand to see checks as a table
- "Export to Excel" button in top-right

### Platform List (`/platforms`)
- Card grid with platform icons
- Each card: platform name, OS family badge, benchmark count
- Click to see available benchmarks for that platform

### Check Detail (`/checks/<id>`)
- Full page with all check information
- Code blocks for audit commands (with copy button)
- Expected output in highlighted box
- Remediation steps
- Breadcrumb navigation: Benchmark > Section > Check

### Search (HTMX-powered)
- Global search bar in navigation
- Filters: platform, level, scored/not-scored
- Live results via HTMX as user types
- Results show check number, title, platform, level

---

## 11. Authentication

### Simple auth flow:
- First run creates a default admin user (admin/changeme)
- Login required for all pages except login page
- Registration can be open or admin-only (config toggle)
- Password hashing via Werkzeug `generate_password_hash`/`check_password_hash`
- Session-based auth via Flask-Login
- No roles in v1 — all authenticated users have equal access

---

## 12. Implementation Phases

### Phase 1: Foundation (MVP)
1. Project scaffolding (Flask app factory, config, requirements)
2. Database models + migrations
3. Seed data system (YAML parser + loader)
4. Basic auth (login/logout/register)
5. Dashboard page
6. Benchmark listing and detail views
7. Platform listing and detail views
8. Check detail view
9. Basic TailwindCSS layout

### Phase 2: Core Features
10. YAML seed data for all 8 platforms (30+ checks each)
11. Excel export for benchmarks
12. HTMX search and filtering
13. Audit session management (create, track, complete)
14. Audit result tracking per check
15. Excel export for audit sessions

### Phase 3: Enhancement
16. Summary statistics and charts
17. Advanced search with filters
18. Bulk operations (mark multiple checks)
19. Print-friendly CSS for checks

### Future: Complete CIS Coverage
- Expand each platform from 30+ to full CIS benchmark (200-400 checks)
- Add YAML files incrementally per section
- Community contribution workflow for adding checks
- Version tracking when CIS releases updated benchmarks
- Additional benchmarks beyond CIS (NIST, DISA STIG, etc.)
- Additional platforms as needed

---

## 13. Expanding to Full CIS Coverage (Roadmap)

### Strategy for scaling from 30 to 400+ checks per asset:

1. **Modular YAML files**: Split each platform into per-section YAML files:
   ```
   data/benchmarks/debian_12/
   ├── 01_initial_setup.yaml
   ├── 02_services.yaml
   ├── 03_network.yaml
   ├── 04_logging.yaml
   ├── 05_access_auth.yaml
   └── 06_maintenance.yaml
   ```

2. **Priority order for expansion**:
   - Phase A: L1 Scored checks (highest priority, most impactful)
   - Phase B: L2 Scored checks
   - Phase C: L1 Not Scored checks
   - Phase D: L2 Not Scored checks

3. **Automated validation**: Script to validate YAML structure and required fields

4. **Version control**: Track which CIS benchmark version each check maps to

5. **Delta tracking**: When CIS releases new benchmark version, flag added/removed/changed checks
