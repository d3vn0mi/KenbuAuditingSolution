import io
from datetime import datetime, timezone
import xlsxwriter
from ..models import Check, BenchmarkSection
from ..models.audit import AuditResult, AuditAsset
from ..models.hardening import HardeningCheckResult


def export_benchmark_to_excel(benchmark, level=None, scored_only=False):
    """Export a benchmark's checks to an Excel file for fieldwork."""
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    formats = _create_formats(workbook)

    _write_cover_sheet(workbook, formats, benchmark)

    checks_query = Check.query.join(BenchmarkSection).filter(
        BenchmarkSection.benchmark_id == benchmark.id
    )
    if level:
        checks_query = checks_query.filter(Check.level == level)
    if scored_only:
        checks_query = checks_query.filter(Check.scored.is_(True))

    checks = checks_query.order_by(Check.check_number).all()
    _write_checklist_sheet(workbook, formats, checks)

    workbook.close()
    output.seek(0)
    return output


def export_audit_to_excel(session):
    """Export an audit session with all assets and results to Excel."""
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    formats = _create_formats(workbook)

    # Cover sheet
    _write_audit_cover_sheet(workbook, formats, session)

    # Per-asset sheets
    assets = session.assets.all()
    for asset in assets:
        results = AuditResult.query.filter_by(
            asset_id=asset.id
        ).join(Check).order_by(Check.check_number).all()
        _write_audit_asset_sheet(workbook, formats, asset, results)

    # Summary sheet
    _write_audit_summary_sheet(workbook, formats, session, assets)

    workbook.close()
    output.seek(0)
    return output


def _create_formats(workbook):
    """Create reusable formats for the workbook."""
    return {
        'title': workbook.add_format({
            'bold': True, 'font_size': 18, 'font_color': '#1a1a2e',
            'bottom': 2, 'bottom_color': '#16213e'
        }),
        'subtitle': workbook.add_format({
            'bold': True, 'font_size': 12, 'font_color': '#16213e'
        }),
        'header': workbook.add_format({
            'bold': True, 'font_size': 11,
            'bg_color': '#1a1a2e', 'font_color': '#ffffff',
            'border': 1, 'text_wrap': True, 'valign': 'vcenter'
        }),
        'cell': workbook.add_format({
            'border': 1, 'text_wrap': True, 'valign': 'top', 'font_size': 10
        }),
        'cell_alt': workbook.add_format({
            'border': 1, 'text_wrap': True, 'valign': 'top', 'font_size': 10,
            'bg_color': '#f0f0f5'
        }),
        'cell_l2': workbook.add_format({
            'border': 1, 'text_wrap': True, 'valign': 'top', 'font_size': 10,
            'bg_color': '#fff8e1'
        }),
        'cell_l2_alt': workbook.add_format({
            'border': 1, 'text_wrap': True, 'valign': 'top', 'font_size': 10,
            'bg_color': '#fff3cd'
        }),
        'label': workbook.add_format({
            'bold': True, 'font_size': 11, 'font_color': '#16213e'
        }),
        'value': workbook.add_format({
            'font_size': 11
        }),
        'pass': workbook.add_format({
            'border': 1, 'text_wrap': True, 'valign': 'top', 'font_size': 10,
            'bg_color': '#d4edda', 'font_color': '#155724'
        }),
        'fail': workbook.add_format({
            'border': 1, 'text_wrap': True, 'valign': 'top', 'font_size': 10,
            'bg_color': '#f8d7da', 'font_color': '#721c24'
        }),
        'na': workbook.add_format({
            'border': 1, 'text_wrap': True, 'valign': 'top', 'font_size': 10,
            'bg_color': '#e2e3e5', 'font_color': '#383d41'
        }),
        'stat_label': workbook.add_format({
            'bold': True, 'font_size': 12, 'right': 1
        }),
        'stat_value': workbook.add_format({
            'font_size': 12, 'num_format': '0'
        }),
        'stat_pct': workbook.add_format({
            'font_size': 12, 'num_format': '0.0%'
        }),
    }


def _write_cover_sheet(workbook, formats, benchmark):
    """Write the cover page with benchmark information."""
    sheet = workbook.add_worksheet('Cover')
    sheet.hide_gridlines(2)
    sheet.set_column('A:A', 25)
    sheet.set_column('B:B', 60)

    row = 1
    sheet.write(row, 0, benchmark.name, formats['title'])
    sheet.merge_range(row, 0, row, 1, benchmark.name, formats['title'])
    row += 2

    fields = [
        ('Benchmark:', benchmark.name),
        ('Version:', benchmark.version),
        ('Platform:', benchmark.platform.name),
        ('Release Date:', str(benchmark.release_date) if benchmark.release_date else 'N/A'),
        ('Description:', benchmark.description or ''),
        ('Reference URL:', benchmark.url or ''),
        ('', ''),
        ('Export Date:', datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')),
        ('Total Checks:', str(benchmark.total_checks)),
        ('', ''),
        ('Target System:', ''),
        ('Target IP:', ''),
        ('Auditor Name:', ''),
        ('Audit Date:', ''),
    ]

    for label, value in fields:
        if label:
            sheet.write(row, 0, label, formats['label'])
            sheet.write(row, 1, value, formats['value'])
        row += 1


def _write_checklist_sheet(workbook, formats, checks):
    """Write the main checklist sheet."""
    sheet = workbook.add_worksheet('Checklist')

    widths = [12, 40, 8, 10, 55, 40, 14, 40, 45]
    headers = [
        'Check #', 'Title', 'Level', 'Scored',
        'Audit Command / Steps', 'Expected Output',
        'Status', 'Findings', 'Remediation'
    ]

    for i, (width, header) in enumerate(zip(widths, headers)):
        sheet.set_column(i, i, width)
        sheet.write(0, i, header, formats['header'])

    sheet.freeze_panes(1, 0)

    sheet.data_validation(1, 6, len(checks) + 1, 6, {
        'validate': 'list',
        'source': ['Pass', 'Fail', 'N/A', 'Not Checked'],
    })

    for row_idx, check in enumerate(checks, start=1):
        is_l2 = check.level == 2
        if is_l2:
            fmt = formats['cell_l2_alt'] if row_idx % 2 == 0 else formats['cell_l2']
        else:
            fmt = formats['cell_alt'] if row_idx % 2 == 0 else formats['cell']

        audit_text = check.audit_command or check.audit_steps or ''
        sheet.write(row_idx, 0, check.check_number, fmt)
        sheet.write(row_idx, 1, check.title, fmt)
        sheet.write(row_idx, 2, f'L{check.level}', fmt)
        sheet.write(row_idx, 3, 'Yes' if check.scored else 'No', fmt)
        sheet.write(row_idx, 4, audit_text.strip(), fmt)
        sheet.write(row_idx, 5, (check.expected_output or '').strip(), fmt)
        sheet.write(row_idx, 6, '', fmt)
        sheet.write(row_idx, 7, '', fmt)
        sheet.write(row_idx, 8, (check.remediation or '').strip(), fmt)

    if checks:
        sheet.autofilter(0, 0, len(checks), len(headers) - 1)


def _write_audit_cover_sheet(workbook, formats, session):
    """Write cover page for an audit session export."""
    sheet = workbook.add_worksheet('Cover')
    sheet.hide_gridlines(2)
    sheet.set_column('A:A', 25)
    sheet.set_column('B:B', 60)

    row = 1
    title = f'Audit Report: {session.title}'
    sheet.merge_range(row, 0, row, 1, title, formats['title'])
    row += 2

    fields = [
        ('Title:', session.title),
        ('Description:', session.description or ''),
        ('Standard:', session.standard.name if session.standard else 'All Checks'),
        ('', ''),
        ('Auditor:', session.user.display_name or session.user.username),
        ('Created:', session.created_at.strftime('%Y-%m-%d %H:%M UTC') if session.created_at else ''),
        ('Started:', session.started_at.strftime('%Y-%m-%d %H:%M UTC') if session.started_at else ''),
        ('Completed:', session.completed_at.strftime('%Y-%m-%d %H:%M UTC') if session.completed_at else 'In Progress'),
        ('Status:', session.status.replace('_', ' ').title()),
        ('', ''),
        ('Total Assets:', str(session.assets.count())),
        ('Total Checks:', str(session.total_checks)),
        ('', ''),
        ('Notes:', session.notes or ''),
    ]

    # List assets
    row_start = row
    for label, value in fields:
        if label:
            sheet.write(row, 0, label, formats['label'])
            sheet.write(row, 1, value, formats['value'])
        row += 1

    # Asset summary
    row += 1
    sheet.write(row, 0, 'Assets:', formats['subtitle'])
    row += 1
    for asset in session.assets.all():
        benchmarks_str = ', '.join(
            f'{ab.benchmark.platform.name} v{ab.benchmark.version}'
            for ab in asset.benchmarks
        )
        sheet.write(row, 0, f'  {asset.name}', formats['label'])
        sheet.write(row, 1, f'{asset.asset_type} | {benchmarks_str}', formats['value'])
        row += 1


def _write_audit_asset_sheet(workbook, formats, asset, results):
    """Write a sheet for a single audit asset."""
    sheet_name = asset.name[:31]
    sheet = workbook.add_worksheet(sheet_name)

    widths = [12, 40, 8, 10, 55, 40, 14, 40, 45]
    headers = [
        'Check #', 'Title', 'Level', 'Scored',
        'Audit Command / Steps', 'Expected Output',
        'Status', 'Findings', 'Remediation'
    ]

    for i, (width, header) in enumerate(zip(widths, headers)):
        sheet.set_column(i, i, width)
        sheet.write(0, i, header, formats['header'])

    sheet.freeze_panes(1, 0)

    for row_idx, result in enumerate(results, start=1):
        check = result.check

        if result.status == 'pass':
            fmt = formats['pass']
        elif result.status == 'fail':
            fmt = formats['fail']
        elif result.status == 'not_applicable':
            fmt = formats['na']
        else:
            fmt = formats['cell_alt'] if row_idx % 2 == 0 else formats['cell']

        audit_text = check.audit_command or check.audit_steps or ''
        status_display = {
            'pass': 'Pass', 'fail': 'Fail',
            'not_applicable': 'N/A', 'not_checked': 'Not Checked'
        }.get(result.status, result.status)

        sheet.write(row_idx, 0, check.check_number, fmt)
        sheet.write(row_idx, 1, check.title, fmt)
        sheet.write(row_idx, 2, f'L{check.level}', fmt)
        sheet.write(row_idx, 3, 'Yes' if check.scored else 'No', fmt)
        sheet.write(row_idx, 4, audit_text.strip(), fmt)
        sheet.write(row_idx, 5, (check.expected_output or '').strip(), fmt)
        sheet.write(row_idx, 6, status_display, fmt)
        sheet.write(row_idx, 7, result.finding or '', fmt)
        sheet.write(row_idx, 8, (check.remediation or '').strip(), fmt)

    if results:
        sheet.autofilter(0, 0, len(results), len(headers) - 1)


def _write_audit_summary_sheet(workbook, formats, session, assets):
    """Write summary statistics sheet for audit."""
    sheet = workbook.add_worksheet('Summary')
    sheet.hide_gridlines(2)
    sheet.set_column('A:A', 30)
    sheet.set_column('B:B', 20)
    sheet.set_column('C:C', 15)

    row = 1
    sheet.merge_range(row, 0, row, 2, 'Audit Summary', formats['title'])
    row += 2

    total = session.total_checks
    pass_count = session.pass_count
    fail_count = session.fail_count
    na_count = session.na_count
    checked = session.checked_count
    not_checked = total - checked
    compliance = pass_count / checked if checked > 0 else 0

    stats = [
        ('Total Checks:', total),
        ('Checked:', checked),
        ('Not Checked:', not_checked),
        ('', ''),
        ('Pass:', pass_count),
        ('Fail:', fail_count),
        ('Not Applicable:', na_count),
        ('', ''),
    ]

    for label, value in stats:
        if label:
            sheet.write(row, 0, label, formats['stat_label'])
            sheet.write(row, 1, value, formats['stat_value'])
        row += 1

    sheet.write(row, 0, 'Compliance Rate:', formats['stat_label'])
    sheet.write(row, 1, compliance, formats['stat_pct'])
    row += 2

    # Per-asset breakdown
    sheet.write(row, 0, 'Per-Asset Results', formats['subtitle'])
    row += 1
    sheet.write(row, 0, 'Asset', formats['header'])
    sheet.write(row, 1, 'Pass / Checked', formats['header'])
    sheet.write(row, 2, 'Rate', formats['header'])
    row += 1

    for asset in assets:
        fmt = formats['cell_alt'] if row % 2 == 0 else formats['cell']
        asset_checked = asset.checked_count
        asset_pass = asset.pass_count
        rate = asset_pass / asset_checked if asset_checked > 0 else 0

        sheet.write(row, 0, asset.name, fmt)
        sheet.write(row, 1, f'{asset_pass} / {asset_checked}', fmt)
        sheet.write(row, 2, rate, formats['stat_pct'])
        row += 1

    # Pie chart
    if total > 0:
        row += 2
        chart = workbook.add_chart({'type': 'pie'})
        chart_sheet = workbook.add_worksheet('_chart_data')
        chart_sheet.hide()

        chart_data = [
            ['Pass', pass_count],
            ['Fail', fail_count],
            ['N/A', na_count],
            ['Not Checked', not_checked],
        ]
        for i, (label, val) in enumerate(chart_data):
            chart_sheet.write(i, 0, label)
            chart_sheet.write(i, 1, val)

        chart.add_series({
            'name': 'Audit Results',
            'categories': ['_chart_data', 0, 0, 3, 0],
            'values': ['_chart_data', 0, 1, 3, 1],
            'points': [
                {'fill': {'color': '#28a745'}},
                {'fill': {'color': '#dc3545'}},
                {'fill': {'color': '#6c757d'}},
                {'fill': {'color': '#ffc107'}},
            ],
        })
        chart.set_title({'name': 'Results Distribution'})
        chart.set_size({'width': 480, 'height': 360})
        sheet.insert_chart(row, 0, chart)


def export_hardening_to_excel(task):
    """Export a hardening task with all assets and results to Excel."""
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    formats = _create_formats(workbook)

    formats['done'] = workbook.add_format({
        'border': 1, 'text_wrap': True, 'valign': 'top', 'font_size': 10,
        'bg_color': '#d4edda', 'font_color': '#155724'
    })
    formats['skipped'] = workbook.add_format({
        'border': 1, 'text_wrap': True, 'valign': 'top', 'font_size': 10,
        'bg_color': '#e2e3e5', 'font_color': '#383d41'
    })

    _write_hardening_cover_sheet(workbook, formats, task)

    assets = task.assets.all()
    for asset in assets:
        results = HardeningCheckResult.query.filter_by(
            asset_id=asset.id
        ).join(Check).order_by(Check.check_number).all()
        _write_hardening_asset_sheet(workbook, formats, asset, results)

    _write_hardening_summary_sheet(workbook, formats, task, assets)

    workbook.close()
    output.seek(0)
    return output


def _write_hardening_cover_sheet(workbook, formats, task):
    """Write cover page for a hardening task export."""
    sheet = workbook.add_worksheet('Cover')
    sheet.hide_gridlines(2)
    sheet.set_column('A:A', 25)
    sheet.set_column('B:B', 60)

    row = 1
    title = f'Hardening Report: {task.title}'
    sheet.merge_range(row, 0, row, 1, title, formats['title'])
    row += 2

    fields = [
        ('Title:', task.title),
        ('Description:', task.description or ''),
        ('Status:', task.status.replace('_', ' ').title()),
        ('', ''),
        ('Created:', task.created_at.strftime('%Y-%m-%d %H:%M UTC') if task.created_at else ''),
        ('Started:', task.started_at.strftime('%Y-%m-%d %H:%M UTC') if task.started_at else ''),
        ('Completed:', task.completed_at.strftime('%Y-%m-%d %H:%M UTC') if task.completed_at else 'In Progress'),
        ('', ''),
        ('Total Assets:', str(task.assets.count())),
        ('Total Checks:', str(task.total_items)),
        ('Completed:', str(task.completed_items)),
        ('Progress:', f'{task.progress}%'),
    ]

    for label, value in fields:
        if label:
            sheet.write(row, 0, label, formats['label'])
            sheet.write(row, 1, value, formats['value'])
        row += 1


def _write_hardening_asset_sheet(workbook, formats, asset, results):
    """Write a sheet for a single hardening asset."""
    sheet_name = asset.name[:31]
    sheet = workbook.add_worksheet(sheet_name)

    widths = [12, 40, 8, 45, 14, 40, 20]
    headers = [
        'Check #', 'Title', 'Level', 'Remediation',
        'Status', 'Notes', 'Completed At'
    ]

    for i, (width, header) in enumerate(zip(widths, headers)):
        sheet.set_column(i, i, width)
        sheet.write(0, i, header, formats['header'])

    sheet.freeze_panes(1, 0)

    for row_idx, result in enumerate(results, start=1):
        check = result.check

        if result.status == 'done':
            fmt = formats['done']
        elif result.status == 'skipped':
            fmt = formats['skipped']
        else:
            fmt = formats['cell_alt'] if row_idx % 2 == 0 else formats['cell']

        status_display = result.status.title()
        completed = result.completed_at.strftime('%Y-%m-%d %H:%M') if result.completed_at else ''

        sheet.write(row_idx, 0, check.check_number, fmt)
        sheet.write(row_idx, 1, check.title, fmt)
        sheet.write(row_idx, 2, f'L{check.level}', fmt)
        sheet.write(row_idx, 3, (check.remediation or '').strip(), fmt)
        sheet.write(row_idx, 4, status_display, fmt)
        sheet.write(row_idx, 5, result.notes or '', fmt)
        sheet.write(row_idx, 6, completed, fmt)

    if results:
        sheet.autofilter(0, 0, len(results), len(headers) - 1)


def _write_hardening_summary_sheet(workbook, formats, task, assets):
    """Write summary sheet for a hardening task."""
    sheet = workbook.add_worksheet('Summary')
    sheet.hide_gridlines(2)
    sheet.set_column('A:A', 30)
    sheet.set_column('B:B', 15)
    sheet.set_column('C:C', 15)
    sheet.set_column('D:D', 15)

    row = 1
    sheet.merge_range(row, 0, row, 3, 'Hardening Summary', formats['title'])
    row += 2

    total = task.total_items
    completed = task.completed_items
    done_count = sum(
        a.check_results.filter(HardeningCheckResult.status == 'done').count()
        for a in assets
    )
    skipped_count = sum(
        a.check_results.filter(HardeningCheckResult.status == 'skipped').count()
        for a in assets
    )
    pending_count = total - completed

    stats = [
        ('Total Checks:', total),
        ('Done:', done_count),
        ('Skipped:', skipped_count),
        ('Pending:', pending_count),
    ]

    for label, value in stats:
        sheet.write(row, 0, label, formats['stat_label'])
        sheet.write(row, 1, value, formats['stat_value'])
        row += 1

    row += 1
    sheet.write(row, 0, 'Completion Rate:', formats['stat_label'])
    sheet.write(row, 1, completed / total if total > 0 else 0, formats['stat_pct'])
    row += 2

    sheet.write(row, 0, 'Per-Asset Progress', formats['subtitle'])
    row += 1
    sheet.write(row, 0, 'Asset', formats['header'])
    sheet.write(row, 1, 'Type', formats['header'])
    sheet.write(row, 2, 'Done / Total', formats['header'])
    sheet.write(row, 3, 'Progress', formats['header'])
    row += 1

    for asset in assets:
        fmt = formats['cell_alt'] if row % 2 == 0 else formats['cell']
        asset_total = asset.total_checks
        asset_completed = asset.completed_checks
        progress = asset.progress / 100.0 if asset_total > 0 else 0

        sheet.write(row, 0, asset.name, fmt)
        sheet.write(row, 1, asset.asset_type, fmt)
        sheet.write(row, 2, f'{asset_completed} / {asset_total}', fmt)
        sheet.write(row, 3, progress, formats['stat_pct'])
        row += 1

    if total > 0:
        row += 2
        chart = workbook.add_chart({'type': 'pie'})
        chart_sheet = workbook.add_worksheet('_hardening_chart_data')
        chart_sheet.hide()

        chart_data = [
            ['Done', done_count],
            ['Skipped', skipped_count],
            ['Pending', pending_count],
        ]
        for i, (label, val) in enumerate(chart_data):
            chart_sheet.write(i, 0, label)
            chart_sheet.write(i, 1, val)

        chart.add_series({
            'name': 'Hardening Progress',
            'categories': ['_hardening_chart_data', 0, 0, 2, 0],
            'values': ['_hardening_chart_data', 0, 1, 2, 1],
            'points': [
                {'fill': {'color': '#28a745'}},
                {'fill': {'color': '#6c757d'}},
                {'fill': {'color': '#ffc107'}},
            ],
        })
        chart.set_title({'name': 'Hardening Progress'})
        chart.set_size({'width': 480, 'height': 360})
        sheet.insert_chart(row, 0, chart)
