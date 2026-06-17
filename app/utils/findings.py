"""Finding ingestion + promotion helpers.

Findings come from RAVEN TLPT/pentest engagements, internal review, or scans.
import_findings accepts structured rows (parsed from JSON or CSV); promote_pentest_finding
turns an engagement-scoped PentestFinding into a control-linked Finding.
"""
from datetime import date
from ..extensions import db
from ..models import Control, Finding
from ..models.finding import FINDING_SOURCES, FINDING_STATUSES
from ..models.pentest import SEVERITY_LEVELS


def _norm_severity(value):
    v = (value or '').strip().lower()
    return v if v in SEVERITY_LEVELS else 'informational'


def _parse_date(value):
    value = (value or '').strip() if isinstance(value, str) else value
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def import_findings(rows):
    """Create Finding rows from an iterable of dicts. Each row may carry a
    `controls` list of control codes to link. Returns the created findings."""
    created = []
    for row in rows:
        title = (row.get('title') or '').strip()
        if not title:
            continue
        source = (row.get('source') or 'internal').strip().lower()
        status = (row.get('status') or 'open').strip().lower()
        finding = Finding(
            title=title,
            severity=_norm_severity(row.get('severity')),
            source=source if source in FINDING_SOURCES else 'other',
            status=status if status in FINDING_STATUSES else 'open',
            description=(row.get('description') or '').strip() or None,
            remediation=(row.get('remediation') or '').strip() or None,
            discovered_at=_parse_date(row.get('discovered_at')),
        )
        codes = row.get('controls') or []
        if codes:
            finding.controls = Control.query.filter(Control.code.in_(codes)).all()
        db.session.add(finding)
        created.append(finding)
    db.session.commit()
    return created


def promote_pentest_finding(pentest_finding, control_ids=None):
    """Create a control-linked Finding from a PentestFinding (the offensive moat)."""
    finding = Finding(
        title=pentest_finding.title,
        severity=_norm_severity(pentest_finding.severity),
        source='pentest',
        status='open',
        description=pentest_finding.description,
        remediation=pentest_finding.remediation,
        promoted_from_pentest_finding_id=pentest_finding.id,
    )
    if control_ids:
        finding.controls = Control.query.filter(Control.id.in_(control_ids)).all()
    db.session.add(finding)
    db.session.commit()
    return finding
