# Data — Sentinel

> **Status**: No datasets are stored in this repository.

---

## Directory Structure

```
data/
├── schemas/          # JSON schemas for data validation
│   └── event.schema.json
├── sample/           # Tiny synthetic examples only
│   └── README.md
└── README.md         # This file
```

---

## Principles

### 1. No Real Data in Git

**Real investigation data, private evidence, and real CCTV footage must never be committed to this repository.**

The `.gitignore` explicitly excludes:
- `data/raw/`
- `data/private/`
- `data/processed/`
- `evidence/`
- `uploads/`
- `videos/`
- `cctv/`
- `documents/private/`
- All common video, document, and archive file extensions

### 2. Datasets Are Downloaded Separately

Public research datasets (CERT, LANL, VAST, UCF-Crime, DocVQA, etc.) are **not** bundled with the repository.

Each developer or CI job should download required datasets to a local path outside the repository (e.g., `~/sentinel-datasets/` or a mounted volume).

See `docs/research/datasets.md` for the list of planned datasets and download instructions.

### 3. Sample Data Is Synthetic

The `data/sample/` directory may contain:
- Tiny synthetic JSON event examples that conform to `schemas/event.schema.json`
- Minimal test fixtures for unit tests
- Legally redistributable toy examples (if any exist)

Sample data must:
- Be clearly synthetic (no real names, IPs, organisations)
- Be small (< 100 KB per file)
- Not resemble any real investigation

### 4. Schemas Are Versioned

The canonical event schema (`schemas/event.schema.json`) is the source of truth for the event format.

- All AI pipelines must emit events that validate against this schema.
- The backend validates incoming events against this schema.
- The frontend TypeScript types should be generated from or aligned with this schema.

Schema versioning will be added as the project evolves.

---

## Evidence Storage

Raw evidence files (video, PDFs, logs) are stored in the **local evidence store** configured via the `STORAGE_PATH` environment variable.

```
STORAGE_PATH=/path/to/evidence-store
```

This path must be **outside the Git repository**.

The backend records only metadata and SHA-256 hashes in PostgreSQL. The actual files live in the evidence store.

See `docs/decisions/ADR-003-storage.md` for the full storage architecture.

---

## Large File Handling

- Video files: can be gigabytes each — never commit
- PDFs: can be tens of megabytes — never commit
- Model weights: can be hundreds of megabytes — never commit
- Log archives: can be large — never commit

Use the evidence store, not Git.

---

*Data management is a shared responsibility. Every team member must ensure no private or sensitive data enters the repository.*