# Changelog

## [0.3.0] - 2024-XX-XX

### Added
- `classification` field (canonical) for alert risk tier (0=Interesting, 1=Relevant, 2=Impactful)
- `evidence` field to separate non-decisional evidence from decisions
- `AlertEvidence` model to contain diagnostics and linking notes
- Robust ETA parsing with timezone handling and bad date tolerance
- Database schema now includes `classification` column

### Changed
- Network impact scoring now uses 1-10 scale (normalized from previous approach)
- ETA "within 48h" check now uses actual 48-hour window (not calendar days)
- Date-only ETA values treated as end-of-day UTC consistently
- Alert model structure: `diagnostics` moved to `evidence.diagnostics`

### Deprecated
- `priority` field: Use `classification` instead. Will be removed in v0.4.
- `diagnostics` field: Use `evidence.diagnostics` instead. Will be removed in v0.4.

### Fixed
- ETA parsing no longer crashes on invalid/missing dates
- Timezone drift issues in ETA comparisons resolved
- Parsing failures gracefully skip subscores without breaking pipeline

### Technical
- Database schema: Added `classification` column, `priority` kept for backward compatibility (nullable)
- Clear separation between decisions (what system asserts) and evidence (what system believes)
- Backward compatibility maintained via computed properties for deprecated fields

## [0.1.0] - Initial release

- Basic event ingestion and normalization
- Network entity linking (facilities, lanes, shipments)
- Alert generation with heuristic-based scoring
- Local SQLite storage
- Demo pipeline

