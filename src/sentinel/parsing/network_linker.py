from __future__ import annotations

import re
from typing import Dict, Optional, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session

from sentinel.database.schema import Facility, Lane, Shipment


US_STATE_TO_ABBR = {
    "indiana": "IN",
    "illinois": "IL",
    "ohio": "OH",
    "michigan": "MI",
    "kentucky": "KY",
    # expand as needed
}


def _normalize_state(s: str) -> str:
    s = s.strip()
    if len(s) == 2:
        return s.upper()
    return US_STATE_TO_ABBR.get(s.lower(), s.upper())


def _extract_city_state(text: str) -> Optional[Tuple[str, str]]:
    # matches "Avon, IN" or "Avon, Indiana"
    m = re.search(r"\b([A-Z][a-zA-Z.\- ]+?),\s*([A-Za-z]{2}|[A-Za-z ]{3,})\b", text)
    if not m:
        return None
    city = m.group(1).strip().strip(".")
    state = _normalize_state(m.group(2).strip().strip("."))
    return city, state


def link_event_to_network(event: Dict, session: Session, max_shipments: int = 50) -> Dict:
    """
    Attach facilities/lanes/shipments to the event using SQLite context.
    Adds event["linking_notes"], event["link_confidence"], and event["link_provenance"]
    so you can see why matches happened and how confident we are.
    """
    text = f"{event.get('title','')} {event.get('raw_text','')}".strip()

    event.setdefault("facilities", [])
    event.setdefault("lanes", [])
    event.setdefault("shipments", [])
    event.setdefault("linking_notes", [])
    event.setdefault("link_confidence", {})
    event.setdefault("link_provenance", {})

    facility_confidence = 0.0
    facility_provenance = None

    # 1) Try exact facility_id match in text (highest confidence)
    all_facility_ids = [r[0] for r in session.query(Facility.facility_id).all()]
    matched_ids = [fid for fid in all_facility_ids if fid and fid in text]
    if matched_ids:
        event["facilities"] = sorted(set(event["facilities"] + matched_ids))
        facility_confidence = 0.95
        facility_provenance = "FACILITY_ID_EXACT"
        event["linking_notes"].append(f"Facility match by exact ID in text: {matched_ids}")

    # 2) Try facility name substring match (medium-high confidence)
    if not event["facilities"]:
        facilities = session.query(Facility).all()
        name_hits = []
        text_l = text.lower()
        for f in facilities:
            if f.name and f.name.lower() in text_l:
                name_hits.append(f.facility_id)
        if name_hits:
            event["facilities"] = sorted(set(event["facilities"] + name_hits))
            facility_confidence = 0.85
            facility_provenance = "FACILITY_NAME_SUBSTRING"
            event["linking_notes"].append(f"Facility match by name substring: {name_hits}")

    # 3) Try city/state match from text (medium confidence)
    if not event["facilities"]:
        cs = _extract_city_state(text)
        if cs:
            city, state = cs
            # Check both normalized abbreviation and original state name
            # (database might have "Indiana" while we normalized to "IN")
            state_conditions = [
                Facility.state == state,
                Facility.state.ilike(state),
            ]
            # If state is an abbreviation, also check for full name
            if len(state) == 2:
                # Find full state name from abbreviation (reverse lookup)
                for full_name, abbr in US_STATE_TO_ABBR.items():
                    if abbr == state:
                        state_conditions.append(Facility.state.ilike(full_name))
                        break
            
            hits = (
                session.query(Facility)
                .filter(Facility.city.isnot(None))
                .filter(Facility.city.ilike(city))
                .filter(or_(*state_conditions))
                .all()
            )
            if hits:
                ids = [h.facility_id for h in hits]
                event["facilities"] = sorted(set(event["facilities"] + ids))
                facility_confidence = 0.70
                facility_provenance = "CITY_STATE"
                event["linking_notes"].append(f"Facility match by city/state: {city}, {state} -> {ids}")
            else:
                event["linking_notes"].append(f"No facility match for city/state: {city}, {state}")

    # Store facility confidence and provenance
    if event["facilities"]:
        event["link_confidence"]["facility"] = facility_confidence
        event["link_provenance"]["facility"] = facility_provenance

    # 2) If facilities found, link lanes
    if event["facilities"]:
        fac_ids = event["facilities"]
        lanes = (
            session.query(Lane)
            .filter(or_(Lane.origin_facility_id.in_(fac_ids), Lane.dest_facility_id.in_(fac_ids)))
            .all()
        )
        lane_ids = [l.lane_id for l in lanes]
        if lane_ids:
            event["lanes"] = sorted(set(event["lanes"] + lane_ids))
            # Lane confidence is 0.70 (inherited from facility relationship)
            event["link_confidence"]["lanes"] = 0.70
            event["link_provenance"]["lanes"] = "FACILITY_RELATION"
            event["linking_notes"].append(f"Linked lanes via facility match: {lane_ids}")

        # 3) If lanes found, link shipments
        if lane_ids:
            shipments = (
                session.query(Shipment)
                .filter(Shipment.lane_id.in_(lane_ids))
                .limit(max_shipments)
                .all()
            )
            shipment_ids = [s.shipment_id for s in shipments]
            if shipment_ids:
                event["shipments"] = sorted(set(event["shipments"] + shipment_ids))
                # Shipment confidence is 0.60 (lower confidence for indirect relationship)
                event["link_confidence"]["shipments"] = 0.60
                event["link_provenance"]["shipments"] = "LANE_RELATION"
                event["linking_notes"].append(f"Linked shipments via lanes: {shipment_ids}")

    return event

