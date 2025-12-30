# Hardstop Execution Plan

This document translates the Hardstop runtime architecture into a concrete,
prioritized execution plan. The goal is to ensure every change furthers the
deterministic, local-first design while sequencing work from the most
foundational dependencies to user-facing integrations.

---

## Guiding Principles

1. **Determinism before features** – every new surface must emit fingerprints,
   RunRecords, and bounded execution hooks before we consider UX polish.
2. **Single source of truth for contracts** – schemas, configs, and operator
   boundaries live in `docs/ARCHITECTURE.md` + `docs/specs`. Implementation and
   documentation changes ship together.
3. **Ship measurable increments** – each priority band ends with artifacts we
   can demo (`hardstop run`, `hardstop brief`) plus regression tests that lock
   in behavior.
4. **Protect local-first defaults** – no network writes, no hidden services, and
   strict mode is always the default path.

---

## Priority Bands at a Glance

| Priority | Focus Area | Why it is first | Representative Deliverables | Exit Criteria |
| --- | --- | --- | --- | --- |
| **P0** | Deterministic kernel hardening | Without trustworthy RunRecords and bounded operators, no downstream plan is replayable. | Complete RunRecord schema, config fingerprinting, CLI exit-code matrix, deterministic fixtures | Golden-run fixture reproduces hashes; `hardstop doctor` reports RunRecord coverage gaps <= 5% |
| **P1** | Source health + ingestion reliability | The pipeline depends on timely, bounded signals. | Tier-aware source registry, health scoring, suppression auditing, adapter conformance tests | `hardstop sources health` surfaces stale/failing sources with actionable codes; adapters emit standardized `SourceRun` rows |
| **P2** | Decision core + artifact quality | Alerts must be correct before we broadcast them. | Canonicalization refactor, impact scoring rationale, correlation evidence graph, incident replay CLI | Regression suite validates impact scoring deltas <= 5%; incidents carry full provenance |
| **P3** | Reporting + integrations | Only after artifacts are correct do we expand surfaces. | Markdown/JSON briefs v2, export API, Slack/Linear sinks, CI-ready exit signals | Daily brief + export flows align with new artifact schema; integration hooks stay read-only |

---

## Detailed Execution Steps

### P0 – Deterministic Kernel Hardening

- **RunRecord coverage**: extend `tests/test_run_status.py` and `hardstop/ops/*`
  to ensure every operator writes `input_refs`, `output_refs`, config hashes,
  and mode metadata. Add `docs/specs/run-record.schema.json` acceptance tests.
- **Config fingerprinting**: formalize a merged config view (`runtime.yaml`,
  operator defaults, env overrides) and persist the stable hash alongside every
  RunRecord.
- **Strict/best-effort enforcement**: gate operators behind explicit modes,
  fail fast when an operator attempts nondeterministic IO without switching to
  best-effort.
- **Golden-run fixture**: refresh the fixture dataset under `tests/fixtures/`
  and assert SHA-256 outputs for alerts, incidents, and briefs. This guards all
  downstream work.
- **Operational ergonomics**: align CLI exit codes, `hardstop doctor`, and
  run-status footer so we can rely on them in CI/CD integrations later.

#### P0 Verification (Dec 2025)

- `python3 -m pytest` passes (103 tests as of Dec 2025). `tests/test_run_record.py`,
  `tests/test_run_status.py`, and `tests/test_golden_run.py` lock the RunRecord schema,
  the resolved merged-config fingerprint hash (canonical JSON serialization of the
  post-default snapshot), the strict vs best-effort exit-code matrix, and the golden
  fixture digests (with nondeterministic fields such as timestamps/paths normalized
  out of the hashed payloads) that guard determinism.
- `hardstop run` emits RunRecords with merged config fingerprints and mode metadata
  through the `hardstop.ops.run_record` helpers, and the CLI footer mirrors the exit-code
  decisions validated in the tests above.
- `hardstop doctor` exercises the same schema- and config-validation paths that drive
  RunRecord diagnostics, so CI or local operators get identical guidance before
  progressing to P1 workstreams.
- Given identical inputs, resolved configs, and strict mode, rerunning `hardstop run`
  produces identical RunRecord hashes plus unchanged golden artifact digests.
- Deterministic runs rely on caller-supplied IDs/timestamps (or replay-pinned values),
  stable hashing of normalized inputs with canonical key ordering, and deterministic
  ordering of diagnostics/messages prior to hashing/serialization. Operators that must
  tolerate nondeterminism switch to best-effort, declare their entropy sources
  (wall-clock reads, random jitter, network ordering), and record seeds/metadata under
  `best_effort` so replays know which fields may drift. Strict mode scrubs or pins
  nondeterministic fields when possible and will fail fast if an operator attempts to
  emit untracked entropy.

**P0 invariants**
- Every operator emits/finalizes a RunRecord for each execution.
- Config fingerprint hashes remain stable for identical resolved (post-default) snapshots.
- Strict vs best-effort exit codes and CLI footer messaging remain stable across runs.
- Golden fixture digests remain stable because nondeterministic fields are normalized.

### P1 – Source Reliability & Health (Completed)

Deterministic source health scoring, suppression explainability, and failure-budget gating are shipped and regression-tested.

- **Delivered scope:** canonical source schema and tier defaults, persisted health telemetry, adapter diagnostics contracts, and CLI/API gating paths.
- **Validation:** deterministic scoring and gating pinned in `tests/test_source_health.py`, `tests/test_source_health_integration.py`, `tests/test_cli_sources.py`, and `tests/test_run_status.py`. Suppression explainability coverage lives in `tests/test_suppression_engine.py` and `tests/test_suppression_integration.py`.
- **Operational notes:** strict mode promotes budget warnings to blocking exit codes; `hardstop sources health --explain-suppress <source>` remains the supported tuning path.

### P2 – Decision Core & Artifact Quality (Completed)

- **Canonicalization v2:** explicit operators now emit RunRecords and deterministic hashes; partial entity linking fallbacks are codified and covered by fixtures in `tests/test_correlation.py` and `tests/test_golden_run.py`.
- **Impact scoring transparency:** rationale (trust-tier modifiers, network criticality, suppression context) is persisted and documented; regressions live in `tests/test_impact_scorer.py` with fixtures under `tests/fixtures/`.
- **Correlation evidence graph:** merge evidence artifacts are persisted and surfaced in briefs/exports; evidence regressions live in `tests/test_correlation.py` and `tests/test_output_renderer_only.py`.
- **Incident replay CLI:** `hardstop incidents replay <incident_id>` re-materializes inputs using RunRecords, artifacts, and config fingerprints; strict mode fails deterministically on missing inputs, best-effort warns and proceeds. Replay coverage sits in `tests/test_run_record.py`, `tests/test_golden_run.py`, and replay-specific tests.
- **Artifact schema updates:** `docs/specs/run-record.schema.json` and SQLite migrations are refreshed to include the richer incident and decision artifacts exercised by the suites above.

### P3 – Reporting, Export, and Integrations

- **Brief v2**: restructure Markdown/JSON briefs to consume the new artifacts,
  add badges for trust tiers, and expose suppression rationale for each alert.
- **Export API / bundles**: deliver read-only exports (JSON bundle + CSV) so
  downstream tools can ingest Hardstop outputs without touching the DB.
- **Chat & work tracker sinks**: document Slack webhook + Linear issue mirroring
  flows with deterministic retry logic; integrations should read from exported
  artifacts instead of live DB queries.
- **CI/CD hooks**: publish a reference GitHub Actions workflow that runs
  `hardstop run`, `hardstop doctor`, and surfaces exit codes/status summaries.
- **Operational playbooks**: document runbooks for remediation when sources or
  operators fail, tying back to health metrics emitted in earlier phases.

---

## Cross-Cutting Deliverables

- **Documentation cadence**: every phase requires README + `docs/ARCHITECTURE.md`
  updates plus changelog entries so contributors can follow along.
- **Testing + automation**: expand pytest suites, add benchmarking hooks, and
  gate releases on golden-run plus health test success.
- **Release packaging**: ensure `pyproject.toml` extras stay current and the
  `hardstop init` path provisions config compatible with the new plan.

---

## Current Status Snapshot (Jan 2026)

- **P0 complete:** RunRecord schema + config fingerprints, strict/best-effort exit codes, and golden-run fixtures are locked by regression tests.
- **P1 complete:** health scoring, suppression explainability, and failure-budget gating are live and validated by deterministic tests.
- **P2 complete:** canonicalization v2, impact scoring rationale persistence, correlation evidence graph, and incident replay CLI are implemented and regression-tested.
- **P3 pending:** integrations still rely on ad-hoc scripts; export bundle spec remains open.

This plan should be revisited at the end of every release cycle to confirm
assumptions, retire completed work, and reprioritize based on new risks.
