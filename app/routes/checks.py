from flask import Blueprint, render_template, request
from flask_login import login_required
from ..models import Check, BenchmarkSection, Benchmark, Platform

checks_bp = Blueprint('checks', __name__, url_prefix='/checks')


@checks_bp.route('/<int:check_id>')
@login_required
def detail(check_id):
    check = Check.query.get_or_404(check_id)
    section = check.section
    benchmark = section.benchmark

    # Build breadcrumb
    breadcrumb = []
    current = section
    while current:
        breadcrumb.insert(0, current)
        current = current.parent

    return render_template('checks/detail.html',
                           check=check,
                           section=section,
                           benchmark=benchmark,
                           breadcrumb=breadcrumb)


@checks_bp.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()
    platform_slug = request.args.get('platform', '')
    level = request.args.get('level', '')
    scored = request.args.get('scored', '')

    checks_query = Check.query.join(BenchmarkSection).join(Benchmark)

    if query:
        search_term = f'%{query}%'
        checks_query = checks_query.filter(
            (Check.title.ilike(search_term)) |
            (Check.check_number.ilike(search_term)) |
            (Check.description.ilike(search_term)) |
            (Check.audit_command.ilike(search_term))
        )

    if platform_slug:
        checks_query = checks_query.join(Platform).filter(
            Platform.slug == platform_slug
        )

    if level in ('1', '2'):
        checks_query = checks_query.filter(Check.level == int(level))

    if scored in ('true', 'false'):
        checks_query = checks_query.filter(Check.scored == (scored == 'true'))

    checks = checks_query.order_by(Check.check_number).limit(50).all()

    # If HTMX request, return partial
    if request.headers.get('HX-Request'):
        return render_template('checks/_search.html', checks=checks, query=query)

    # Full page search
    platforms = Platform.query.order_by(Platform.name).all()
    return render_template('checks/search.html',
                           checks=checks,
                           query=query,
                           platforms=platforms,
                           selected_platform=platform_slug,
                           selected_level=level,
                           selected_scored=scored)
