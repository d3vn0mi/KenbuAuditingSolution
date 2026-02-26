import os
import yaml
from datetime import date
from ..extensions import db
from ..models import User, Platform, Benchmark, BenchmarkSection, Check


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
            user = User(username='admin', display_name='Administrator')
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
                display_name=user_data.get('display_name', user_data['username'])
            )
            user.set_password(user_data['password'])
            db.session.add(user)
            print(f'  Created user: {user_data["username"]}')
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
    ]

    for p_data in platforms:
        if not Platform.query.filter_by(slug=p_data['slug']).first():
            platform = Platform(**p_data)
            db.session.add(platform)
            print(f'  Created platform: {p_data["name"]}')
    db.session.commit()


def seed_all(data_dir):
    """Run all seed operations."""
    print('Seeding platforms...')
    seed_platforms()

    print('Seeding users...')
    seed_users(data_dir)

    print('Seeding benchmarks...')
    benchmarks_dir = os.path.join(data_dir, 'benchmarks')
    if os.path.exists(benchmarks_dir):
        for filename in sorted(os.listdir(benchmarks_dir)):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                filepath = os.path.join(benchmarks_dir, filename)
                seed_benchmark_file(filepath)
    else:
        print('  No benchmarks directory found')

    # Print summary
    print('\n--- Seed Summary ---')
    print(f'  Platforms: {Platform.query.count()}')
    print(f'  Benchmarks: {Benchmark.query.count()}')
    print(f'  Sections: {BenchmarkSection.query.count()}')
    print(f'  Checks: {Check.query.count()}')
    print(f'  Users: {User.query.count()}')
