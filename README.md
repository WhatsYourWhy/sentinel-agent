# Sentinel Agent

**Sentinel** is a local-first, domain-agnostic event → risk → alert engine.

The initial domain pack focuses on **supply chain risk** (facilities, lanes, shipments), but the architecture is designed to work for other domains (security, finance, operations) by swapping out domain rules.

## Status

- **v0.8** — Current implementation
  - External source retrieval (RSS, NWS, FDA, USCG)
  - Source tiers (Global, Regional, Local) with trust weighting
  - Suppression rules (global and per-source)
  - Tier-aware briefing with trust tier indicators
  - Event normalization and entity linking
  - Deterministic alert generation with network impact scoring
  - Alert correlation (deduplication over 7-day window)
  - Daily brief generation (markdown/JSON)
  - Local SQLite storage with additive migrations

## Features

### Core Capabilities

- **External Source Retrieval**: Fetch events from RSS/Atom feeds, NWS Alerts API, FDA, USCG, and other public sources
- **Source Tiers**: Classify sources as Global, Regional, or Local for tier-aware processing
- **Trust Tier Weighting**: Prioritize sources based on reliability (tier 1-3) with configurable bias
- **Suppression Rules**: Filter noisy events using keyword, regex, or exact match patterns (global and per-source)
- **Event Processing**: Normalize raw events into canonical format
- **Network Linking**: Automatically link events to facilities, lanes, and shipments
- **Alert Generation**: Deterministic risk assessment using network impact scoring with trust tier modifiers
- **Alert Correlation**: Deduplicate and update alerts based on correlation keys
- **Tier-Aware Briefing**: Generate summaries with tier counts, badges, and grouping (markdown or JSON)

### Database Requirements

**Requires Database:**
- `sentinel demo` — Needs DB for network linking and alert correlation
- `sentinel brief` — Needs DB to query stored alerts
- `sentinel ingest` — Needs DB to store network data
- `sentinel fetch` — Needs DB to store raw items
- `sentinel ingest-external` — Needs DB to store events and alerts
- `sentinel run` — Needs DB for full pipeline
- `sentinel doctor` — Needs DB to check schema health

**Works Without Database:**
- Alert generation can fall back to `severity_guess` if no session provided
- Event normalization (pure transformation, no DB needed)
- `sentinel sources list` — Reads config only

## Project Structure

```
sentinel-agent/
├── README.md
├── pyproject.toml
├── requirements.txt
├── sentinel.config.yaml
├── .gitignore
├── config/
│   ├── sources.yaml          # External source definitions
│   └── suppression.yaml       # Global suppression rules
├── docs/
│   ├── SPEC_SENTINEL_V1.md
│   └── ARCHITECTURE.md
├── src/
│   └── sentinel/
│       ├── __init__.py
│       ├── config/
│       │   ├── __init__.py
│       │   └── loader.py      # Config and source loading
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── file_ingestor.py
│       │   ├── json_ingestor.py
│       │   └── rss_ingestor.py
│       ├── retrieval/         # External source retrieval (v0.6+)
│       │   ├── __init__.py
│       │   ├── adapters.py    # RSS, NWS, FEMA adapters
│       │   └── fetcher.py     # Rate-limited fetching
│       ├── suppression/       # Suppression engine (v0.8)
│       │   ├── __init__.py
│       │   ├── models.py      # SuppressionRule, SuppressionResult
│       │   └── engine.py      # Rule evaluation logic
│       ├── parsing/
│       │   ├── __init__.py
│       │   ├── normalizer.py
│       │   ├── entity_extractor.py
│       │   └── network_linker.py
│       ├── database/
│       │   ├── __init__.py
│       │   ├── schema.py      # RawItem, Event, Alert models
│       │   ├── sqlite_client.py
│       │   ├── alert_repo.py
│       │   ├── event_repo.py  # Event persistence
│       │   ├── raw_item_repo.py  # Raw item storage
│       │   └── migrate.py
│       ├── alerts/
│       │   ├── __init__.py
│       │   ├── alert_models.py
│       │   ├── alert_builder.py
│       │   ├── impact_scorer.py
│       │   └── correlation.py
│       ├── output/
│       │   ├── __init__.py
│       │   └── daily_brief.py
│       ├── runners/
│       │   ├── __init__.py
│       │   ├── run_demo.py
│       │   ├── load_network.py
│       │   └── ingest_external.py  # External ingestion pipeline
│       └── utils/
│           ├── __init__.py
│           ├── id_generator.py
│           └── logging.py
└── tests/
    ├── __init__.py
    ├── test_demo_pipeline.py
    ├── test_suppression_engine.py
    ├── test_suppression_integration.py
    ├── conftest.py
    └── fixtures/
        ├── facilities.csv
        ├── lanes.csv
        ├── shipments_snapshot.csv
        └── event_spill.json
```

## Quickstart

```bash
# create venv and install
python -m venv .venv

# Activate virtual environment
# On Linux/Mac:
source .venv/bin/activate

# On Windows (PowerShell):
# If you get an execution policy error, run this first:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

pip install -e .

# For contributors (includes pytest and other dev tools):
pip install -e ".[dev]"

# Load network data (required for demo and brief)
sentinel ingest

# Run demo pipeline
sentinel demo

# Generate daily brief
sentinel brief --today
```

## Usage

### CLI Commands

Sentinel provides a comprehensive CLI interface:

```bash
# External Source Management
sentinel sources list                    # List all configured sources
sentinel fetch                           # Fetch items from all enabled sources
sentinel fetch --tier global             # Fetch only global tier sources
sentinel fetch --since 24h               # Fetch items from last 24 hours
sentinel fetch --max-items-per-source 10  # Limit items per source

# Ingestion Pipeline
sentinel ingest-external                 # Normalize and ingest fetched raw items
sentinel ingest-external --since 24h    # Process items from last 24 hours
sentinel ingest-external --no-suppress   # Bypass suppression rules
sentinel ingest-external --explain-suppress  # Log suppression decisions

# Convenience Commands
sentinel run                             # Fetch + ingest-external in one command
sentinel run --since 24h                 # With time window
sentinel run --no-suppress               # Bypass suppression

# Network Data
sentinel ingest                          # Load network data from CSV files

# Demo Pipeline
sentinel demo                            # Run demo pipeline (requires DB with network data)

# Daily Brief
sentinel brief --today                   # Generate brief for today
sentinel brief --today --since 72h       # Custom time window
sentinel brief --today --format json     # JSON output
sentinel brief --today --limit 50        # Custom limit
sentinel brief --today --include-class0  # Include classification 0 alerts

# Health Checks
sentinel doctor                          # Check database schema and config health
```

### External Source Retrieval

Sentinel can fetch events from external public sources:

1. **Configure Sources**: Edit `config/sources.yaml` to define RSS feeds, NWS alerts, FDA recalls, etc.
2. **Fetch Items**: `sentinel fetch` retrieves raw items from enabled sources
3. **Ingest Events**: `sentinel ingest-external` normalizes items into events and generates alerts
4. **View Results**: `sentinel brief --today` shows alerts from external sources

**Source Configuration:**
- **Tiers**: Global, Regional, Local (for tier-aware briefing)
- **Trust Tier**: 1-3 (affects impact scoring: tier 3 gets +1, tier 1 gets -1)
- **Classification Floor**: Minimum alert classification (0-2)
- **Weighting Bias**: Adjust impact score (-2 to +2)
- **Suppression Rules**: Per-source patterns to filter noise

**Example Workflow:**
```bash
# Fetch from all sources
sentinel fetch --since 24h

# Ingest and generate alerts
sentinel ingest-external --since 24h

# Or do both in one command
sentinel run --since 24h

# View results
sentinel brief --today --since 24h
```

### Running the Demo Pipeline

The demo pipeline (`sentinel demo`) demonstrates the core Sentinel workflow:

1. Loads a sample JSON event from `tests/fixtures/event_spill.json`
2. Normalizes the event into a canonical format
3. Links the event to network data (facilities, lanes, shipments) from the database
4. Builds a risk alert using network impact scoring
5. Correlates with existing alerts (if any) or creates new alert
6. Outputs the alert as formatted JSON

**Prerequisites:** Run `sentinel ingest` first to load network data.

### Loading Network Data

Before running the demo or generating briefs, load your network data:

```bash
sentinel ingest
```

This reads CSV files from `tests/fixtures/` (or paths specified in `sentinel.config.yaml`) and loads them into SQLite. The demo will then use this real network data to link events to facilities and shipments.

### Daily Brief

Generate a summary of recent alerts:

```bash
# Basic usage (last 24 hours, markdown)
sentinel brief --today

# Custom time window
sentinel brief --today --since 72h

# JSON output
sentinel brief --today --format json

# Include classification 0 alerts
sentinel brief --today --include-class0

# Custom limit
sentinel brief --today --limit 50
```

The brief shows:
- **Tier Summary**: Counts by Global, Regional, Local tiers
- **Top Impactful Alerts**: Classification 2 alerts with tier badges `[G]`, `[R]`, `[L]`
- **Updated Alerts**: Correlated alerts with update counts
- **New Alerts**: Newly created alerts
- **Suppressed Count**: Number of items suppressed by rules (v0.8)
- **Summary Counts**: By classification and tier

**Tier-Aware Features:**
- Tier badges on each alert (`[G]`, `[R]`, `[L]`)
- Trust tier indicators `(T3)`, `(T2)`, `(T1)`
- Grouping by tier within sections
- Tier counts in header

**Note:** Brief requires alerts to be persisted (created via `sentinel demo`, `sentinel run`, or alert builder with session).
