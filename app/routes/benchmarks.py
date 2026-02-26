from flask import Blueprint, render_template, abort
from flask_login import login_required
from ..models import Benchmark, BenchmarkSection, Check

benchmarks_bp = Blueprint('benchmarks', __name__, url_prefix='/benchmarks')


@benchmarks_bp.route('/')
@login_required
def list_benchmarks():
    benchmarks = Benchmark.query.join(Benchmark.platform).order_by(Benchmark.name).all()
    return render_template('benchmarks/list.html', benchmarks=benchmarks)


@benchmarks_bp.route('/<int:benchmark_id>')
@login_required
def detail(benchmark_id):
    benchmark = Benchmark.query.get_or_404(benchmark_id)
    # Get top-level sections
    sections = BenchmarkSection.query.filter_by(
        benchmark_id=benchmark_id,
        parent_id=None
    ).order_by(BenchmarkSection.sort_order).all()
    return render_template('benchmarks/detail.html',
                           benchmark=benchmark,
                           sections=sections)


@benchmarks_bp.route('/<int:benchmark_id>/section/<int:section_id>')
@login_required
def section(benchmark_id, section_id):
    benchmark = Benchmark.query.get_or_404(benchmark_id)
    section = BenchmarkSection.query.get_or_404(section_id)
    if section.benchmark_id != benchmark_id:
        abort(404)

    # Get all checks in this section and subsections
    checks = _get_section_checks(section)

    # Build breadcrumb
    breadcrumb = _build_breadcrumb(section)

    return render_template('benchmarks/section.html',
                           benchmark=benchmark,
                           section=section,
                           checks=checks,
                           breadcrumb=breadcrumb)


def _get_section_checks(section):
    """Get all checks in a section and its children, maintaining order."""
    checks = list(section.checks.order_by(Check.sort_order).all())
    for child in section.children.order_by(BenchmarkSection.sort_order):
        checks.extend(_get_section_checks(child))
    return checks


def _build_breadcrumb(section):
    """Build breadcrumb path from root to current section."""
    crumbs = []
    current = section
    while current:
        crumbs.insert(0, current)
        current = current.parent
    return crumbs
