import os
import hashlib
import yaml
from datetime import date
from ..extensions import db
from ..models import User, Platform, Benchmark, BenchmarkSection, Check
from ..models.regulation import (
    Regulation, RegulationCheck, Obligation, Control,
    EvidenceRequirement, ControlReference,
)


def load_yaml(filepath):
    """Load and parse a YAML file."""
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


def seed_users(data_dir):
    """Create default users from seed_users.yaml."""
    filepath = os.path.join(data_dir, 'seed_users.yaml')
    if not os.path.exists(filepath):
        # Create default admin if no seed file
        if not User.query.filter_by(username='admin').first():
            user = User(
                username='admin',
                display_name='Administrator',
                role='admin',
                is_approved=True,
            )
            user.set_password('changeme')
            db.session.add(user)
            db.session.commit()
            print('  Created default admin user (admin/changeme)')
        return

    data = load_yaml(filepath)
    for user_data in data.get('users', []):
        if not User.query.filter_by(username=user_data['username']).first():
            user = User(
                username=user_data['username'],
                display_name=user_data.get('display_name', user_data['username']),
                role=user_data.get('role', 'user'),
                is_approved=user_data.get('is_approved', True),
            )
            user.set_password(user_data['password'])
            db.session.add(user)
            print(f'  Created user: {user_data["username"]} (role={user.role})')
    db.session.commit()


def seed_benchmark_file(filepath):
    """Load a single benchmark YAML file into the database."""
    data = load_yaml(filepath)
    bench_data = data['benchmark']
    filename = os.path.basename(filepath)

    # Find or create platform
    platform = Platform.query.filter_by(slug=bench_data['platform']).first()
    if not platform:
        print(f'  WARNING: Platform {bench_data["platform"]} not found, skipping {filename}')
        return

    # Check if benchmark already exists
    existing = Benchmark.query.filter_by(
        name=bench_data['name'],
        version=bench_data['version']
    ).first()
    if existing:
        print(f'  Benchmark already exists: {bench_data["name"]} v{bench_data["version"]}')
        return

    # Create benchmark
    release_date = bench_data.get('release_date')
    if isinstance(release_date, str):
        release_date = date.fromisoformat(release_date)

    benchmark = Benchmark(
        name=bench_data['name'],
        version=bench_data['version'],
        platform_id=platform.id,
        release_date=release_date,
        description=bench_data.get('description', ''),
        url=bench_data.get('url', '')
    )
    db.session.add(benchmark)
    db.session.flush()  # Get the ID

    # Create sections and checks recursively
    check_count = 0
    for section_data in data.get('sections', []):
        check_count += _create_section(benchmark.id, None, section_data, 0)

    db.session.commit()
    print(f'  Loaded: {bench_data["name"]} v{bench_data["version"]} ({check_count} checks)')


def _create_section(benchmark_id, parent_id, section_data, sort_order):
    """Recursively create sections and their checks."""
    section = BenchmarkSection(
        benchmark_id=benchmark_id,
        parent_id=parent_id,
        number=section_data['number'],
        title=section_data['title'],
        description=section_data.get('description', ''),
        sort_order=sort_order
    )
    db.session.add(section)
    db.session.flush()

    check_count = 0

    # Create checks in this section
    for i, check_data in enumerate(section_data.get('checks', [])):
        check = Check(
            section_id=section.id,
            check_number=check_data['number'],
            title=check_data['title'],
            description=check_data.get('description', ''),
            rationale=check_data.get('rationale', ''),
            level=check_data.get('level', 1),
            scored=check_data.get('scored', True),
            audit_command=check_data.get('audit_command', ''),
            audit_steps=check_data.get('audit_steps', ''),
            expected_output=check_data.get('expected_output', ''),
            remediation=check_data.get('remediation', ''),
            references=check_data.get('references', ''),
            sort_order=i
        )
        db.session.add(check)
        check_count += 1

    # Recursively create child sections
    for i, child_data in enumerate(section_data.get('children', [])):
        check_count += _create_section(benchmark_id, section.id, child_data, i)

    return check_count


def seed_platforms():
    """Create the 8 supported platforms."""
    platforms = [
        {
            'name': 'Debian Linux 12',
            'slug': 'debian-12',
            'os_family': 'Linux',
            'icon': 'debian',
            'description': 'Debian GNU/Linux 12 (Bookworm)'
        },
        {
            'name': 'Ubuntu 24.04 LTS',
            'slug': 'ubuntu-2404',
            'os_family': 'Linux',
            'icon': 'ubuntu',
            'description': 'Ubuntu 24.04 LTS (Noble Numbat)'
        },
        {
            'name': 'Windows Server 2022',
            'slug': 'windows-2022',
            'os_family': 'Windows',
            'icon': 'windows',
            'description': 'Microsoft Windows Server 2022'
        },
        {
            'name': 'Windows 10',
            'slug': 'windows-10',
            'os_family': 'Windows',
            'icon': 'windows',
            'description': 'Microsoft Windows 10'
        },
        {
            'name': 'Windows 11',
            'slug': 'windows-11',
            'os_family': 'Windows',
            'icon': 'windows',
            'description': 'Microsoft Windows 11'
        },
        {
            'name': 'RHEL 7',
            'slug': 'rhel-7',
            'os_family': 'Linux',
            'icon': 'redhat',
            'description': 'Red Hat Enterprise Linux 7'
        },
        {
            'name': 'RHEL 8',
            'slug': 'rhel-8',
            'os_family': 'Linux',
            'icon': 'redhat',
            'description': 'Red Hat Enterprise Linux 8'
        },
        {
            'name': 'RHEL 9',
            'slug': 'rhel-9',
            'os_family': 'Linux',
            'icon': 'redhat',
            'description': 'Red Hat Enterprise Linux 9'
        },
        {
            'name': 'CentOS 7',
            'slug': 'centos-7',
            'os_family': 'Linux',
            'icon': 'centos',
            'description': 'CentOS Linux 7'
        },
        {
            'name': 'Amazon Linux 2023',
            'slug': 'amazon-linux-2023',
            'os_family': 'Linux',
            'icon': 'amazon',
            'description': 'Amazon Linux 2023'
        },
        {
            'name': 'macOS Sonoma',
            'slug': 'macos-sonoma',
            'os_family': 'macOS',
            'icon': 'apple',
            'description': 'Apple macOS 14 (Sonoma)'
        },
        {
            'name': 'Cisco IOS 17',
            'slug': 'cisco-ios-17',
            'os_family': 'Network',
            'icon': 'cisco',
            'description': 'Cisco IOS XE 17'
        },
        {
            'name': 'Sophos Firewall',
            'slug': 'sophos-firewall',
            'os_family': 'Network',
            'icon': 'sophos',
            'description': 'Sophos Firewall (SFOS)'
        },
        {
            'name': 'SUSE Linux Enterprise 15',
            'slug': 'sles-15',
            'os_family': 'Linux',
            'icon': 'suse',
            'description': 'SUSE Linux Enterprise Server 15'
        },
        {
            'name': 'HP iLO 5',
            'slug': 'hp-ilo-5',
            'os_family': 'Firmware',
            'icon': 'hp',
            'description': 'HP Integrated Lights-Out 5 (iLO 5)'
        },
    ]

    for p_data in platforms:
        if not Platform.query.filter_by(slug=p_data['slug']).first():
            platform = Platform(**p_data)
            db.session.add(platform)
            print(f'  Created platform: {p_data["name"]}')
    db.session.commit()


def seed_regulations(data_dir):
    """Seed compliance regulations (GDPR, NIS2) from YAML files or defaults."""
    standards_dir = os.path.join(data_dir, 'standards')

    defaults = [
        {
            'name': 'GDPR',
            'short_code': 'GDPR',
            'slug': 'gdpr',
            'description': 'General Data Protection Regulation (EU) 2016/679',
            'version': '2016/679',
            'status': 'in_force',
            'source_url': 'https://eur-lex.europa.eu/eli/reg/2016/679',
        },
        {
            'name': 'NIS2',
            'short_code': 'NIS2',
            'slug': 'nis2',
            'description': 'Network and Information Security Directive (EU) 2022/2555',
            'version': '2022/2555',
            'status': 'in_force',
            'source_url': 'https://eur-lex.europa.eu/eli/dir/2022/2555',
        },
    ]

    for reg_data in defaults:
        if not Regulation.query.filter_by(slug=reg_data['slug']).first():
            regulation = Regulation(**reg_data)
            db.session.add(regulation)
            print(f'  Created regulation: {reg_data["name"]}')

    db.session.commit()

    # Load regulation-check mappings from YAML if available
    if os.path.exists(standards_dir):
        for filename in sorted(os.listdir(standards_dir)):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                filepath = os.path.join(standards_dir, filename)
                _seed_regulation_checks(filepath)


def _seed_regulation_checks(filepath):
    """Load regulation-to-check mappings from a YAML file."""
    data = load_yaml(filepath)
    if not data:
        return

    slug = data.get('regulation_slug') or data.get('standard_slug')
    if not slug:
        return

    regulation = Regulation.query.filter_by(slug=slug).first()
    if not regulation:
        print(f'  WARNING: Regulation {slug} not found, skipping {os.path.basename(filepath)}')
        return

    mappings = data.get('mappings', [])
    added = 0
    for mapping in mappings:
        check_number = mapping.get('check_number')
        if not check_number:
            continue

        checks = Check.query.filter_by(check_number=check_number).all()
        if not checks:
            continue

        for check in checks:
            existing = RegulationCheck.query.filter_by(
                regulation_id=regulation.id, check_id=check.id
            ).first()
            if not existing:
                rc = RegulationCheck(
                    regulation_id=regulation.id,
                    check_id=check.id,
                    article=mapping.get('article', ''),
                    requirement=mapping.get('requirement', ''),
                )
                db.session.add(rc)
                added += 1

    db.session.commit()
    if added:
        print(f'  Loaded {added} check mappings for {regulation.name}')


# ---------------------------------------------------------------------------
# Regulatory layer (Control hub) — versioned YAML under data/regulations,
# data/controls, data/mappings. Loading is idempotent so reseeding only applies
# deltas. See DESIGN_compliance §5.
# ---------------------------------------------------------------------------

def _obligation_content_hash(ref, title, text):
    """sha256 of the obligation's identifying text — used for delta detection."""
    raw = f"{ref}|{title}|{text or ''}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _upsert_obligation(regulation_id, parent_id, ob_data, sort_order):
    ref = ob_data['ref']
    title = ob_data['title']
    text = ob_data.get('text')

    ob = Obligation.query.filter_by(regulation_id=regulation_id, ref=ref).first()
    if not ob:
        ob = Obligation(regulation_id=regulation_id, ref=ref)
        db.session.add(ob)
    ob.parent_id = parent_id
    ob.title = title
    ob.text = text
    ob.sort_order = sort_order
    ob.content_hash = _obligation_content_hash(ref, title, text)
    db.session.flush()

    for i, child in enumerate(ob_data.get('children', [])):
        _upsert_obligation(regulation_id, ob.id, child, i)


def seed_regulation_file(filepath):
    """Upsert a regulation and its obligation tree from a regulation.yaml file."""
    data = load_yaml(filepath)
    if not data:
        return

    reg_data = data['regulation']
    slug = reg_data['slug']

    effective_date = reg_data.get('effective_date')
    if isinstance(effective_date, str):
        effective_date = date.fromisoformat(effective_date)

    fields = dict(
        name=reg_data['name'],
        short_code=reg_data.get('short_code'),
        description=reg_data.get('description'),
        version=reg_data.get('version'),
        status=reg_data.get('status', 'in_force'),
        effective_date=effective_date,
        source_url=reg_data.get('source_url'),
    )

    reg = Regulation.query.filter_by(slug=slug).first()
    if not reg:
        reg = Regulation(slug=slug, **fields)
        db.session.add(reg)
    else:
        for key, value in fields.items():
            setattr(reg, key, value)
    db.session.flush()

    for i, ob_data in enumerate(data.get('obligations', [])):
        _upsert_obligation(reg.id, None, ob_data, i)

    db.session.commit()


def seed_controls_file(filepath):
    """Upsert controls (+ check links, evidence requirements, references)."""
    data = load_yaml(filepath)
    if not data:
        return

    for c_data in data.get('controls', []):
        code = c_data['code']
        control = Control.query.filter_by(code=code).first()
        if not control:
            control = Control(code=code)
            db.session.add(control)
        control.title = c_data['title']
        control.domain = c_data.get('domain')
        control.description = c_data.get('description')
        control.guidance = c_data.get('guidance')
        db.session.flush()

        # Link to existing technical checks by check_number.
        for number in c_data.get('checks', []):
            for check in Check.query.filter_by(check_number=number).all():
                if check not in control.checks:
                    control.checks.append(check)

        # Evidence requirements (idempotent by title).
        existing_titles = {er.title for er in control.evidence_requirements}
        for er in c_data.get('evidence_requirements', []):
            if er['title'] not in existing_titles:
                control.evidence_requirements.append(EvidenceRequirement(
                    title=er['title'],
                    description=er.get('description'),
                    type=er.get('type'),
                    cadence_days=er.get('cadence_days'),
                ))

        # Cross-framework references (idempotent by framework + ref_code).
        existing_refs = {(r.framework, r.ref_code) for r in control.references}
        for r in c_data.get('references', []):
            key = (r['framework'], r.get('ref_code'))
            if key not in existing_refs:
                control.references.append(ControlReference(
                    framework=r['framework'],
                    ref_code=r.get('ref_code'),
                    title=r.get('title'),
                ))
        db.session.flush()

    db.session.commit()


def seed_mappings_file(filepath):
    """Link controls to obligations from a mappings.yaml file."""
    data = load_yaml(filepath)
    if not data:
        return

    slug = data.get('regulation_slug')
    reg = Regulation.query.filter_by(slug=slug).first()
    if not reg:
        print(f'  WARNING: Regulation {slug} not found, skipping {os.path.basename(filepath)}')
        return

    linked = 0
    for mapping in data.get('mappings', []):
        control = Control.query.filter_by(code=mapping['control']).first()
        if not control:
            continue
        for ref in mapping.get('obligations', []):
            ob = Obligation.query.filter_by(regulation_id=reg.id, ref=ref).first()
            if ob and ob not in control.obligations:
                control.obligations.append(ob)
                linked += 1

    db.session.commit()
    if linked:
        print(f'  Linked {linked} control->obligation mappings for {reg.short_code or reg.name}')


def seed_regulatory_layer(data_dir):
    """Load regulations, controls and mappings (in dependency order)."""
    reg_dir = os.path.join(data_dir, 'regulations')
    if os.path.isdir(reg_dir):
        for slug in sorted(os.listdir(reg_dir)):
            filepath = os.path.join(reg_dir, slug, 'regulation.yaml')
            if os.path.exists(filepath):
                seed_regulation_file(filepath)

    controls_dir = os.path.join(data_dir, 'controls')
    if os.path.isdir(controls_dir):
        for filename in sorted(os.listdir(controls_dir)):
            if filename.endswith(('.yaml', '.yml')):
                seed_controls_file(os.path.join(controls_dir, filename))

    mappings_dir = os.path.join(data_dir, 'mappings')
    if os.path.isdir(mappings_dir):
        for filename in sorted(os.listdir(mappings_dir)):
            if filename.endswith(('.yaml', '.yml')):
                seed_mappings_file(os.path.join(mappings_dir, filename))


def seed_all(data_dir):
    """Run all seed operations."""
    print('Seeding platforms...')
    seed_platforms()

    print('Seeding users...')
    seed_users(data_dir)

    print('Seeding regulations...')
    seed_regulations(data_dir)

    print('Seeding benchmarks...')
    benchmarks_dir = os.path.join(data_dir, 'benchmarks')
    if os.path.exists(benchmarks_dir):
        for filename in sorted(os.listdir(benchmarks_dir)):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                filepath = os.path.join(benchmarks_dir, filename)
                seed_benchmark_file(filepath)
    else:
        print('  No benchmarks directory found')

    # Regulatory layer depends on checks existing (control->check links).
    print('Seeding regulatory layer (obligations, controls, mappings)...')
    seed_regulatory_layer(data_dir)

    # Print summary
    print('\n--- Seed Summary ---')
    print(f'  Platforms: {Platform.query.count()}')
    print(f'  Benchmarks: {Benchmark.query.count()}')
    print(f'  Sections: {BenchmarkSection.query.count()}')
    print(f'  Checks: {Check.query.count()}')
    print(f'  Users: {User.query.count()}')
    print(f'  Regulations: {Regulation.query.count()}')
    print(f'  Obligations: {Obligation.query.count()}')
    print(f'  Controls: {Control.query.count()}')
