"""NIS2 incident statutory-clock helpers (Phase 4 m8)."""
from datetime import datetime, timezone


def _naive(dt):
    """Drop tzinfo so naive (DB) and aware datetimes compare safely."""
    if dt is not None and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def incident_clock(incident, now=None):
    """Return the three statutory stages with due / sent / overdue state."""
    if now is None:
        now = datetime.now(timezone.utc)
    now_n = _naive(now)

    stages_def = [
        ('early_warning', 'Early warning (24h)', incident.early_warning_due,
         incident.early_warning_sent_at),
        ('notification', 'Incident notification (72h)', incident.notification_due,
         incident.notification_sent_at),
        ('final_report', 'Final report (1 month)', incident.final_report_due,
         incident.final_report_sent_at),
    ]

    stages = []
    for key, label, due, sent_at in stages_def:
        due_n = _naive(due)
        sent = sent_at is not None
        overdue = (not sent) and due_n is not None and now_n > due_n
        stages.append({
            'key': key,
            'label': label,
            'due': due,
            'sent_at': sent_at,
            'sent': sent,
            'overdue': overdue,
        })
    return stages


def overdue_stage_count(incident, now=None):
    return sum(1 for s in incident_clock(incident, now=now) if s['overdue'])
