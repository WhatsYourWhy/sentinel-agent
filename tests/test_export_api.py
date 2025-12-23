"""Tests for export API contracts."""

import json
from pathlib import Path

import pytest

from sentinel.api.brief_api import get_brief
from sentinel.api.export import export_alerts, export_brief, export_sources


def test_export_brief_matches_api_brief_invariants(session):
    """Test that export brief matches API brief invariants."""
    # Get brief from API
    brief_data = get_brief(session, since="24h", include_class0=False, limit=20)
    
    # Export brief
    export_json = export_brief(session, since="24h", include_class0=False, limit=20, format="json")
    export_dict = json.loads(export_json)
    
    # Assert export schema
    assert export_dict["export_schema_version"] == "1"
    assert "exported_at_utc" in export_dict
    assert "data" in export_dict
    
    # Assert data matches API brief
    exported_brief = export_dict["data"]
    assert exported_brief["read_model_version"] == "brief.v1"
    assert exported_brief["counts"] == brief_data["counts"]
    assert exported_brief["tier_counts"] == brief_data["tier_counts"]
    
    # Assert required keys exist
    required_keys = [
        "read_model_version",
        "generated_at_utc",
        "window",
        "counts",
        "tier_counts",
        "top",
        "updated",
        "created",
        "suppressed",
        "suppressed_legacy",
    ]
    for key in required_keys:
        assert key in exported_brief, f"Missing required key: {key}"


def test_export_alerts_csv_has_required_columns_and_row_count(session):
    """Test that export alerts CSV has required columns and correct row count."""
    # Get alerts from API
    from sentinel.api.alerts_api import list_alerts
    
    alerts = list_alerts(session, since="24h", limit=50)
    
    # Export alerts as CSV
    csv_output = export_alerts(session, since="24h", limit=50, format="csv")
    csv_lines = csv_output.strip().split("\n")
    
    # Check header
    header = csv_lines[0]
    required_columns = [
        "alert_id",
        "classification",
        "impact_score",
        "tier",
        "trust_tier",
        "source_id",
        "correlation_action",
        "update_count",
        "first_seen_utc",
        "last_seen_utc",
        "summary",
    ]
    
    header_cols = [col.strip() for col in header.split(",")]
    assert header_cols == required_columns, f"CSV header mismatch: expected {required_columns}, got {header_cols}"
    
    # Check row count (header + data rows)
    assert len(csv_lines) == len(alerts) + 1, f"CSV row count mismatch: expected {len(alerts) + 1} (header + {len(alerts)} rows), got {len(csv_lines)}"


def test_get_brief_is_stable_sort_order(session):
    """Test that get_brief returns alerts in stable sort order."""
    # Get brief twice
    brief1 = get_brief(session, since="24h", include_class0=False, limit=20)
    brief2 = get_brief(session, since="24h", include_class0=False, limit=20)
    
    # Assert ordering is stable (same alerts in same order)
    assert brief1["top"] == brief2["top"], "Top alerts ordering should be stable"
    assert brief1["updated"] == brief2["updated"], "Updated alerts ordering should be stable"
    assert brief1["created"] == brief2["created"], "Created alerts ordering should be stable"


def test_alert_reconstruction_round_trip(session):
    """Test that alert reconstruction from DB preserves all required fields."""
    from sentinel.api.alerts_api import list_alerts
    from sentinel.database.alert_repo import upsert_new_alert_row
    import json
    
    # Create alert row via repo
    alert_id = "ALERT-TEST-ROUNDTRIP"
    root_event_id = "EVT-TEST-001"
    correlation_key = "test:correlation:key"
    
    scope_json = json.dumps({
        "facilities": ["FAC-001", "FAC-002"],
        "lanes": ["LANE-001"],
        "shipments": ["SHIP-001"],
        "shipments_total_linked": 1,
        "shipments_truncated": False,
    })
    
    alert_row = upsert_new_alert_row(
            session,
            alert_id=alert_id,
            summary="Test alert for round-trip reconstruction",
            risk_type="TEST",
            classification=2,
            status="OPEN",
            reasoning="Test reasoning",
            recommended_actions=json.dumps([{
                "id": "ACT-001",
                "description": "Test action",
                "owner_role": "Operations",
                "due_within_hours": 4
            }]),
            root_event_id=root_event_id,
            correlation_key=correlation_key,
            correlation_action="CREATED",
            impact_score=8,
            scope_json=scope_json,
            tier="global",
            source_id="test_source",
            trust_tier=2,
        )
    session.commit()
    
    # Call api.list_alerts()
    alerts = list_alerts(session, since=None, limit=100)
    
    # Find our test alert
    test_alert = None
    for alert in alerts:
        if alert.alert_id == alert_id:
            test_alert = alert
            break
    
    assert test_alert is not None, "Test alert should be found in list_alerts()"
    
    # Assert required fields exist
    assert test_alert.alert_id == alert_id
    assert test_alert.classification == 2
    assert test_alert.summary == "Test alert for round-trip reconstruction"
    assert test_alert.risk_type == "TEST"
    assert test_alert.root_event_id == root_event_id
    assert test_alert.scope is not None
    assert len(test_alert.scope.facilities) == 2
    assert len(test_alert.scope.lanes) == 1
    assert len(test_alert.scope.shipments) == 1
    
    # Assert new fields are present (via evidence.correlation)
    assert test_alert.evidence is not None
    assert test_alert.evidence.correlation is not None
    assert test_alert.evidence.correlation["key"] == correlation_key
    assert test_alert.evidence.correlation["action"] == "CREATED"
    assert test_alert.evidence.correlation["alert_id"] == alert_id
    
    # Assert impact_score is in diagnostics
    assert test_alert.evidence.diagnostics is not None
    assert test_alert.evidence.diagnostics.impact_score == 8
    
    # Note: tier, trust_tier, source_id, update_count, first_seen_utc, last_seen_utc
    # are stored in Alert ORM row but not yet in SentinelAlert model.
    # They are accessible via get_alert_detail() which queries the row directly.
    # This test verifies the core reconstruction works.

