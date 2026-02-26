from flask import Blueprint, render_template
from flask_login import login_required
from ..models import Platform, Benchmark

platforms_bp = Blueprint('platforms', __name__, url_prefix='/platforms')


@platforms_bp.route('/')
@login_required
def list_platforms():
    platforms = Platform.query.order_by(Platform.os_family, Platform.name).all()
    return render_template('platforms/list.html', platforms=platforms)


@platforms_bp.route('/<slug>')
@login_required
def detail(slug):
    platform = Platform.query.filter_by(slug=slug).first_or_404()
    benchmarks = Benchmark.query.filter_by(platform_id=platform.id).all()
    return render_template('platforms/detail.html',
                           platform=platform,
                           benchmarks=benchmarks)
