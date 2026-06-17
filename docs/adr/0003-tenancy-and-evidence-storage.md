# ADR 0003 — Tenancy model and evidence storage

- **Status:** Proposed (Phase 0 — pending review)
- **Date:** 2026-06-17

## Context

The product stores sensitive customer compliance evidence for European space
operators, NewSpace SMEs, ground-segment/GSaaS providers, and defence/dual-use
suppliers. EU data residency and tenant isolation are selling points. The kickoff
defaults to **single-tenant-per-deployment** for the MVP (cleaner and safer for
sensitive/defence customers) while keeping a path to full multi-tenancy.

## Decision

1. **Single-tenant-per-deployment for MVP**, multi-tenancy designed-for. Introduce
   an `Organization` table with one default row per deployment. Top-level new
   entities (`ReadinessAssessment`, `Evidence`, `Finding`) carry a nullable
   `organization_id`. Enabling multi-tenancy later = add scoping filters and make
   the column required — no destructive migration.

2. **Evidence at rest:** store uploaded artifacts on the filesystem under the Flask
   `instance/` evidence directory, **encrypted with Fernet** (key from environment).
   Persist `content_hash` (sha256) and version history (`EvidenceVersion`) for
   integrity. Never log evidence contents or secrets. Object storage
   (S3-compatible, EU region) is a post-MVP option.

3. **EU residency:** keep self-hosting (Caddy + Docker) unchanged; no third-party
   data processors introduced by this layer.

## Consequences

- Minimal tenancy overhead now; clean upgrade path.
- A Fernet key becomes a required production secret (add to `.env.example`,
  document key-rotation as a follow-up).
- Filesystem evidence must be on a persistent, backed-up volume in the deploy.
