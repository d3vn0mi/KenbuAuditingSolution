"""Evidence / readiness pack: shared context builder + PDF renderer (Phase 3).

The same context feeds the Excel exporter and the WeasyPrint PDF, so both packs
report identical numbers. The pack is regulator/supervisor/prime-ready: scorecard,
control register, evidence index (with integrity hashes), gap plan, and a
regulation-version + assessment-date stamp.
"""
from flask import render_template
from ..models import Control
from . import readiness as scoring


def build_context(assessment, generated_at):
    sevs = scoring.open_finding_severities(assessment)
    statuses = assessment.control_statuses.join(Control).order_by(
        Control.domain, Control.code).all()

    evidence_index = []
    for cs in statuses:
        ev = list(cs.control.evidence)
        if ev:
            evidence_index.append({'control': cs.control, 'evidence': ev})

    return {
        'assessment': assessment,
        'regulation': assessment.regulation,
        'generated_at': generated_at,
        'overall': scoring.assessment_score(assessment, finding_severities=sevs),
        'domains': scoring.domain_scores(assessment, finding_severities=sevs),
        'coverage': (scoring.obligation_coverage(assessment, assessment.regulation,
                                                 finding_severities=sevs)
                     if assessment.regulation else None),
        'roadmap': scoring.remediation_roadmap(assessment, finding_severities=sevs),
        'statuses': statuses,
        'evidence_index': evidence_index,
    }


def render_pdf(assessment, generated_at):
    """Render the branded readiness pack to PDF bytes via WeasyPrint."""
    from weasyprint import HTML  # imported lazily (native deps)
    ctx = build_context(assessment, generated_at)
    html = render_template('pack/readiness_pack.html', **ctx)
    return HTML(string=html).write_pdf()
