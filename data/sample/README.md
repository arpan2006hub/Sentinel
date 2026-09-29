# Sample Data — Sentinel

> **Status**: Empty. No sample data has been added yet.

---

## Purpose

This directory may eventually contain:

- Tiny synthetic event examples that validate against `../schemas/event.schema.json`
- Minimal test fixtures for unit/integration tests
- Legally redistributable toy datasets (if any suitable ones exist)

---

## Rules

### No Real Data

- No real CCTV footage
- No real employee information
- No real authentication logs
- No real file-access logs
- No real USB/device logs
- No real network/DNS/HTTP logs
- No real badge/door-access logs
- No real incident reports
- No real PDF documents
- No real statements

### Synthetic Only

Any sample data must be:
- Clearly fabricated
- Small (< 100 KB per file)
- Free of any identifiable personal or organisational information
- Clearly labelled as synthetic in filenames and content

### File Naming

Use descriptive names:
```
synthetic-events-sample.json
synthetic-case-fixture.json
```

### Schema Validation

All JSON sample files representing events **must validate** against `../schemas/event.schema.json`.

---

## Dataset Downloads

Public research datasets are **not** placed in this directory.

See `docs/research/datasets.md` for the list of planned datasets and where to download them.

Each developer downloads datasets to a local path outside the repository (e.g., `~/sentinel-datasets/`).

---

*This directory exists as a placeholder for future synthetic test fixtures.*