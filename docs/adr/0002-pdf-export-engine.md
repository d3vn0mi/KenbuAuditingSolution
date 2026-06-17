# ADR 0002 — PDF export engine

- **Status:** Proposed (Phase 0 — pending review)
- **Date:** 2026-06-17

## Context

Phase 3 needs a branded **evidence/readiness pack** PDF for a national competent
authority, a NIS2 supervisor, or a prime's supplier onboarding — alongside the
existing `xlsxwriter` Excel export. Two viable Python engines: WeasyPrint
(HTML/CSS → PDF) and ReportLab (programmatic layout).

## Decision

Use **WeasyPrint**.

- Reuses Jinja2 templates, so the PDF pack matches the existing web UI styling and
  branding with little duplicated layout code.
- HTML/CSS is far easier to author and iterate for multi-section documents
  (scorecard, control register, evidence index, gap plan) than ReportLab's
  imperative API.
- Excel (xlsxwriter) and PDF stay as separate renderers sharing the same data
  service; xlsxwriter is unchanged.

## Consequences

- Docker image gains native dependencies (cairo, pango, gdk-pixbuf, libffi); add
  them to the `Dockerfile`.
- A print-oriented CSS stylesheet is maintained for the pack templates.
- If the native deps prove problematic in the deploy environment, ReportLab is the
  fallback (more code, no system libs).
