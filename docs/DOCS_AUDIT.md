# Docs audit (Jan 2026)

Scope: `docs/` top-level. Goal: identify what to archive, what to update, and what remains to reach P3 reporting/export parity.

## Current state

- `ARCHITECTURE.md` – up to date for P0–P2. Needs a P3 pass to document brief/export contracts and integration boundaries.
- `EXECUTION_PLAN.md` – P3 section lists workstreams but lacks concrete acceptance criteria for briefs v2/export bundles/Slack+Linear sinks.
- `P2_READINESS.md` – accurate for shipped P2 baseline; keep as-is for maintenance.
- `INTEGRATIONS.md` – guidance is current but P3 sinks (Slack/Linear payload shapes, export bundle schema) are undocumented.
- `specs/` – `canonicalization.md` and `run-record.schema.json` are current for P2; no brief/export schema yet.
- `archive/SPEC_HARDSTOP_V1.md` – archived legacy v1 spec (outdated fields: priority, stub brief, v0.4 notes).

## Archive
- `SPEC_HARDSTOP_V1.md` moved to `docs/archive/` as legacy reference; superseded by architecture/spec docs and current API surfaces.

## Updates needed to progress to P3
- Add a brief v2/export schema doc under `docs/specs/` (JSON/CSV bundle shape, evidence summary fields, suppression rollups).
- Update `ARCHITECTURE.md` + `EXECUTION_PLAN.md` with P3 acceptance criteria (brief v2 rendering, export API/CLI, CI signals).
- Extend `INTEGRATIONS.md` with canonical payload examples for Slack/Linear sinks and guidance to consume exported bundles (not DB).
- Add operational playbooks for P3 (runbooks for blocked sources, replay/export failure handling).

## Next steps (suggested order)
1) Author `docs/specs/brief-v2.md` (bundle schema + evidence/suppression fields) and reference it from `EXECUTION_PLAN.md` P3.
2) Update `ARCHITECTURE.md` to describe reporting/export boundary (read-only, artifact-driven) and trust-tier/suppression display rules.
3) Flesh out `INTEGRATIONS.md` with sample Slack/Linear payloads tied to `brief.v1/v2` fields and exported artifact hashes.
4) Add a short P3 runbook (`docs/runbooks/reporting.md`) covering failure budgets, stale sources, and export/replay troubleshooting.
