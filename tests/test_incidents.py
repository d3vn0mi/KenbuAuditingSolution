"""Tests for the NIS2 incident workflow + statutory clock (Phase 4 m8)."""
from datetime import datetime, timezone, timedelta

from app.models import Incident
from app.utils import incidents as inc_service


DETECTED = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)


def _incident(db_session, **kw):
    i = Incident(title='Relay outage', severity='high', detected_at=DETECTED, **kw)
    db_session.session.add(i)
    db_session.session.commit()
    return i


def test_statutory_deadlines(db_session):
    i = _incident(db_session)
    # SQLite/PG return naive datetimes; compare on the naive value.
    base = i.detected_at
    assert i.early_warning_due == base + timedelta(hours=24)
    assert i.notification_due == base + timedelta(hours=72)
    assert i.final_report_due == base + timedelta(days=30)


def test_clock_stage_overdue_when_unsent_and_past_due(db_session):
    i = _incident(db_session)
    now = DETECTED + timedelta(hours=30)  # past 24h early warning, before 72h
    clock = inc_service.incident_clock(i, now=now)
    stages = {s['key']: s for s in clock}
    assert stages['early_warning']['overdue'] is True
    assert stages['early_warning']['sent'] is False
    assert stages['notification']['overdue'] is False  # 72h not yet passed


def test_clock_stage_sent_not_overdue(db_session):
    i = _incident(db_session)
    i.early_warning_sent_at = DETECTED + timedelta(hours=2)
    db_session.session.commit()
    now = DETECTED + timedelta(hours=30)
    stages = {s['key']: s for s in inc_service.incident_clock(i, now=now)}
    assert stages['early_warning']['sent'] is True
    assert stages['early_warning']['overdue'] is False


def test_overdue_incidents_helper(db_session):
    i = _incident(db_session)
    now = DETECTED + timedelta(hours=100)  # past 24h and 72h, both unsent
    overdue = inc_service.overdue_stage_count(i, now=now)
    assert overdue == 2  # early warning + notification overdue; final report not yet
