import json
from datetime import UTC
from pathlib import Path

from hardstop.alerts.alert_builder import build_basic_alert
from hardstop.ingestion.file_ingestor import ingest_all_csvs
from hardstop.parsing.entity_extractor import attach_dummy_entities
from hardstop.parsing.network_linker import link_event_to_network
from hardstop.parsing.normalizer import normalize_event
from hardstop.runners.run_demo import (
    DEFAULT_PINNED_RUN_ID,
    DEFAULT_PINNED_SEED,
    DEFAULT_PINNED_TIMESTAMP,
)
from hardstop.utils.id_generator import deterministic_id_context


def test_demo_pipeline():
    event_path = Path("tests/fixtures/event_spill.json")
    raw = json.loads(event_path.read_text(encoding="utf-8"))
    raw["event_id"] = "EVT-TEST-0001"

    event = normalize_event(raw)
    event = attach_dummy_entities(event)

    alert = build_basic_alert(event)
    assert alert.alert_id.startswith("ALERT-")
    assert alert.root_event_id == "EVT-TEST-0001"
    assert alert.classification in (0, 1, 2)
    assert alert.scope.facilities


def test_pinned_demo_output_is_stable(tmp_path, session):
    facilities = Path("tests/fixtures/facilities.csv")
    lanes = Path("tests/fixtures/lanes.csv")
    shipments = Path("tests/fixtures/shipments_snapshot.csv")
    ingest_all_csvs(facilities, lanes, shipments, session)

    event_path = Path("tests/fixtures/event_spill.json")
    raw = json.loads(event_path.read_text(encoding="utf-8"))
    raw["event_id"] = "EVT-DEMO-0001"

    event = normalize_event(raw)
    event = link_event_to_network(event, session=session)

    pinned_dt = DEFAULT_PINNED_TIMESTAMP
    pinned_iso = pinned_dt.astimezone(UTC).isoformat().replace("+00:00", "Z")
    event["event_time_utc"] = pinned_iso
    event["published_at_utc"] = pinned_iso
    event["scoring_now"] = pinned_dt

    determinism_context = {
        "seed": DEFAULT_PINNED_SEED,
        "timestamp_utc": pinned_iso,
        "run_id": DEFAULT_PINNED_RUN_ID,
    }

    incidents_dir = tmp_path / "incidents"
    with deterministic_id_context(now=pinned_dt, seed=DEFAULT_PINNED_SEED):
        alert = build_basic_alert(
            event,
            session=session,
            determinism_mode="pinned",
            determinism_context=determinism_context,
            incident_dest_dir=incidents_dir,
        )

    assert alert.alert_id == "ALERT-20251229-d31a370b"

    incident_summary = alert.evidence.incident_evidence
    artifact_path = Path(incident_summary.artifact_path)
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert payload["determinism_mode"] == "pinned"
    assert payload["determinism_context"] == determinism_context
    expected_hash = "e36dbe8cf992b8a2e49fb2eb3d867fe9a728517fcbe6bcc19d46e66875eaa2d6"
    assert incident_summary.artifact_hash == expected_hash
    assert payload["artifact_hash"] == expected_hash

