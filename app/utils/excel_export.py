import io
from datetime import datetime, timezone
import xlsxwriter
from ..models import Check, BenchmarkSection, AuditResult


def export_benchmark_to_excel(benchmark, level=None, scored_only=False):
    """Export a benchmark's checks to an Excel file for fieldwork.

    Returns a BytesIO object containing the Excel file.
    """
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})

    # Define formats
    formats = _create_formats(workbook)

    # Cover sheet
    _write_cover_sheet(workbook, formats, benchmark)

    # Checklist sheet
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
    """Export an audit session with results to an Excel file.

    Returns a BytesIO object containing the Excel file.
    """
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})

    formats = _create_formats(workbook)

    # Cover sheet with session info
    _write_audit_cover_sheet(workbook, formats, session)

    # Checklist with results
    results = AuditResult.query.filter_by(
        session_id=session.id
    ).join(Check).order_by(Check.check_number).all()
    _write_audit_checklist_sheet(workbook, formats, results)

    # Summary sheet
    _write_summary_sheet(workbook, formats, session, results)

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

    # Column widths
    widths = [12, 40, 8, 10, 55, 40, 14, 40, 45]
    headers = [
        'Check #', 'Title', 'Level', 'Scored',
        'Audit Command / Steps', 'Expected Output',
        'Status', 'Findings', 'Remediation'
    ]

    for i, (width, header) in enumerate(zip(widths, headers)):
        sheet.set_column(i, i, width)
        sheet.write(0, i, header, formats['header'])

    # Freeze top row
    sheet.freeze_panes(1, 0)

    # Add status dropdown validation
    sheet.data_validation(1, 6, len(checks) + 1, 6, {
        'validate': 'list',
        'source': ['Pass', 'Fail', 'N/A', 'Not Checked'],
    })

    # Write checks
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
        sheet.write(row_idx, 6, '', fmt)  # Status - to be filled by auditor
        sheet.write(row_idx, 7, '', fmt)  # Findings - to be filled by auditor
        sheet.write(row_idx, 8, (check.remediation or '').strip(), fmt)

    # Auto-filter
    if checks:
        sheet.autofilter(0, 0, len(checks), len(headers) - 1)


def _write_audit_cover_sheet(workbook, formats, session):
    """Write cover page for an audit session export."""
    sheet = workbook.add_worksheet('Cover')
    sheet.hide_gridlines(2)
    sheet.set_column('A:A', 25)
    sheet.set_column('B:B', 60)

    row = 1
    title = f'Audit Report: {session.target_name}'
    sheet.merge_range(row, 0, row, 1, title, formats['title'])
    row += 2

    fields = [
        ('Benchmark:', session.benchmark.name),
        ('Version:', session.benchmark.version),
        ('Platform:', session.benchmark.platform.name),
        ('', ''),
        ('Target System:', session.target_name or ''),
        ('Target IP:', session.target_ip or ''),
        ('Auditor:', session.auditor.display_name or session.auditor.username),
        ('Started:', session.started_at.strftime('%Y-%m-%d %H:%M UTC') if session.started_at else ''),
        ('Completed:', session.completed_at.strftime('%Y-%m-%d %H:%M UTC') if session.completed_at else 'In Progress'),
        ('Status:', session.status.replace('_', ' ').title()),
        ('', ''),
        ('Notes:', session.notes or ''),
    ]

    for label, value in fields:
        if label:
            sheet.write(row, 0, label, formats['label'])
            sheet.write(row, 1, value, formats['value'])
        row += 1


def _write_audit_checklist_sheet(workbook, formats, results):
    """Write checklist sheet with audit results filled in."""
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

    for row_idx, result in enumerate(results, start=1):
        check = result.check

        # Choose format based on status
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
            'pass': 'Pass',
            'fail': 'Fail',
            'not_applicable': 'N/A',
            'not_checked': 'Not Checked'
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


def _write_summary_sheet(workbook, formats, session, results):
    """Write summary statistics sheet."""
    sheet = workbook.add_worksheet('Summary')
    sheet.hide_gridlines(2)
    sheet.set_column('A:A', 25)
    sheet.set_column('B:B', 20)
    sheet.set_column('C:C', 15)

    row = 1
    sheet.merge_range(row, 0, row, 2, 'Audit Summary', formats['title'])
    row += 2

    total = len(results)
    pass_count = sum(1 for r in results if r.status == 'pass')
    fail_count = sum(1 for r in results if r.status == 'fail')
    na_count = sum(1 for r in results if r.status == 'not_applicable')
    not_checked = sum(1 for r in results if r.status == 'not_checked')
    checked = total - not_checked
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

    # Compliance by section breakdown
    sheet.write(row, 0, 'Compliance by Section', formats['subtitle'])
    row += 1
    sheet.write(row, 0, 'Section', formats['header'])
    sheet.write(row, 1, 'Pass / Checked', formats['header'])
    sheet.write(row, 2, 'Rate', formats['header'])
    row += 1

    # Group results by top-level section
    section_stats = {}
    for result in results:
        # Get top-level section number
        check_num = result.check.check_number
        top_section = check_num.split('.')[0]
        section_title = result.check.section.title

        # Walk up to find top-level section title
        sec = result.check.section
        while sec.parent:
            sec = sec.parent
        top_title = f'{sec.number}. {sec.title}'

        if top_title not in section_stats:
            section_stats[top_title] = {'pass': 0, 'checked': 0, 'total': 0}
        section_stats[top_title]['total'] += 1
        if result.status != 'not_checked':
            section_stats[top_title]['checked'] += 1
        if result.status == 'pass':
            section_stats[top_title]['pass'] += 1

    for section_name in sorted(section_stats.keys()):
        stats = section_stats[section_name]
        checked = stats['checked']
        passed = stats['pass']
        rate = passed / checked if checked > 0 else 0

        fmt = formats['cell_alt'] if row % 2 == 0 else formats['cell']
        sheet.write(row, 0, section_name, fmt)
        sheet.write(row, 1, f'{passed} / {checked}', fmt)
        sheet.write(row, 2, rate, formats['stat_pct'])
        row += 1

    # Add a pie chart
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
