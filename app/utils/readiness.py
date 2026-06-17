"""Readiness scoring and remediation roadmap (DESIGN_compliance §7).

Two complementary numbers:
  - control implementation score: mean of per-control status scores
    (not_applicable excluded), overall and per domain;
  - obligation coverage: share of a regulation's mapped obligations that have at
    least one implemented control.

`effective_status` is the hook through which findings cap readiness (Phase 2 m7):
an open high/critical finding linked to a control caps its effective status at
'partial'. Until findings exist the effective status equals the stored status.
"""
from ..models.readiness import STATUS_SCORE
from ..models import ControlStatus


# Statuses at or above which an obligation counts as "covered".
_COVERED_STATUSES = {'implemented'}
_CAP_FOR_OPEN_FINDING = 'partial'


def effective_status(control_status, open_finding_severities=None):
    """Return the status used for scoring, applying finding impact.

    open_finding_severities: optional iterable of severities of OPEN findings
    linked to this control. A high/critical open finding caps an otherwise
    'implemented' control at 'partial'.
    """
    status = control_status.status
    sevs = set(open_finding_severities or [])
    if status == 'implemented' and ({'high', 'critical'} & sevs):
        return _CAP_FOR_OPEN_FINDING
    return status


def _statuses(assessment):
    return assessment.control_statuses.all()


def _score_for(status):
    return STATUS_SCORE.get(status)


def assessment_score(assessment, finding_severities=None):
    """Overall implementation score in [0, 1]; not_applicable excluded."""
    finding_severities = finding_severities or {}
    total, count = 0.0, 0
    for cs in _statuses(assessment):
        eff = effective_status(cs, finding_severities.get(cs.control_id))
        score = _score_for(eff)
        if score is None:  # not_applicable
            continue
        total += score
        count += 1
    return (total / count) if count else 0.0


def domain_scores(assessment, finding_severities=None):
    """Mean implementation score per control domain."""
    finding_severities = finding_severities or {}
    buckets = {}
    for cs in _statuses(assessment):
        eff = effective_status(cs, finding_severities.get(cs.control_id))
        score = _score_for(eff)
        if score is None:
            continue
        domain = cs.control.domain or 'Uncategorised'
        buckets.setdefault(domain, []).append(score)
    return {d: (sum(v) / len(v)) for d, v in buckets.items()}


def _implemented_control_ids(assessment, finding_severities=None):
    finding_severities = finding_severities or {}
    ids = set()
    for cs in _statuses(assessment):
        if effective_status(cs, finding_severities.get(cs.control_id)) in _COVERED_STATUSES:
            ids.add(cs.control_id)
    return ids


def obligation_coverage(assessment, regulation, finding_severities=None):
    """Coverage of a regulation's mapped obligations by implemented controls.

    Only obligations that have at least one mapped control are considered
    in-scope (others cannot yet be evidenced).
    """
    implemented = _implemented_control_ids(assessment, finding_severities)
    total = 0
    covered = 0
    for ob in regulation.obligations:
        control_ids = {c.id for c in ob.controls}
        if not control_ids:
            continue
        total += 1
        if control_ids & implemented:
            covered += 1
    ratio = (covered / total) if total else 0.0
    return {'total': total, 'covered': covered, 'ratio': ratio}


def remediation_roadmap(assessment, finding_severities=None):
    """Ranked gap list: controls not implemented/not_applicable, highest priority
    first. Priority = impact (number of mapped obligations) x effort
    (inverse maturity, so less-mature controls rank higher)."""
    finding_severities = finding_severities or {}
    items = []
    for cs in _statuses(assessment):
        eff = effective_status(cs, finding_severities.get(cs.control_id))
        if eff in ('implemented', 'not_applicable'):
            continue
        control = cs.control
        impact = len(control.obligations)
        maturity = cs.maturity if cs.maturity is not None else 0
        effort = 6 - min(max(maturity, 0), 5)  # 1..6, lower maturity => higher effort
        priority = impact * effort
        items.append({
            'control': control,
            'status': cs.status,
            'effective_status': eff,
            'impact': impact,
            'effort': effort,
            'priority': priority,
            'target_date': cs.target_date,
        })
    items.sort(key=lambda i: (i['priority'], i['impact']), reverse=True)
    return items
