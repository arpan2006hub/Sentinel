# ADR-003: Storage Architecture

**Status**: Accepted  
**Date**: 2026  
**Authors**: Sentinel Team  

---

## Context

Sentinel handles two fundamentally different categories of data:

1. **Structured data** — metadata, events, entities, anomalies, relationships, audit records. Small records, highly queryable, require relational integrity and consistency.

2. **Evidence files** — CCTV video, PDFs, scanned documents, raw log archives, images. Can be very large (video files may be gigabytes each). Require integrity verification, not relational querying.

The team needed to decide how to store and manage both categories.

---

## Decision

**Sentinel uses a split storage architecture:**

| Data Type | Storage System | Rationale |
|---|---|---|
| Structured metadata, events, anomalies, audit | **PostgreSQL** | Relational integrity, SQL queries, JSONB flexibility |
| Raw evidence files (video, PDFs, logs, images) | **Local filesystem / Object Storage** | Suitable for large binary files |

---

## PostgreSQL — Structured Metadata

### What PostgreSQL stores

- Cases
- Evidence metadata (filename, hash, size, source type, status)
- Normalised events (from all AI pipelines)
- Entities and entity aliases
- Entity relationships
- Anomaly records
- Analysis runs
- Audit logs

### What PostgreSQL does NOT store

- Raw evidence file contents
- Video frames or binary video data
- Raw PDF binary data
- Large log archive files
- Model weights

### Rationale for PostgreSQL

- Provides ACID guarantees for evidence metadata and audit records
- SQL enables flexible querying (filter events by time, actor, source, confidence)
- JSONB columns allow modality-specific metadata without rigid schema extension
- Alembic migrations ensure reproducible schema evolution
- PostgreSQL is self-hostable and widely supported

---

## Local / Object Storage — Evidence Files

### What file storage stores

- CCTV video files (`.mp4`, `.avi`, `.mkv`, etc.)
- PDF evidence files
- Scanned document images
- Raw log files and archives
- Any other large binary evidence

### Storage layout (planned)

```
/evidence-store/
    ├── <case_id>/
    │       ├── <evidence_id>/
    │       │       ├── original_filename.mp4
    │       │       └── manifest.json   (optional, may store hash + metadata)
    │       └── ...
    └── ...
```

The `evidence-store` root path is configurable via the `STORAGE_PATH` environment variable. It must reside **outside** the Git repository.

### Future object storage

If an organisation prefers to use S3-compatible object storage (for example, MinIO running locally, or an organisation-controlled S3 bucket), the storage layer should be designed to support this as an alternative backend.

This must remain opt-in and organisation-controlled. Evidence files must not be sent to any Sentinel-operated service. See ADR-002 (Local-First).

### Rationale for separate file storage

- Video files and raw logs can be gigabytes to hundreds of gigabytes in size
- Storing large binary data in PostgreSQL degrades query performance and bloats the database
- Filesystem storage is simple, well-understood, and does not introduce additional dependencies
- Separation makes it easy to back up structured data (PostgreSQL dump) independently of raw files
- Large files can be stored on separate high-capacity volumes without affecting database sizing

---

## Evidence Integrity via SHA-256

The integrity of evidence files is maintained through a cryptographic hash mechanism.

### How it works (planned)

```
1. Investigator uploads evidence file
           │
           ▼
2. Backend computes SHA-256 hash of the file
           │
           ▼
3. PostgreSQL record created:
   evidence.file_hash = "sha256:<hex_digest>"
   evidence.file_path = "/evidence-store/<case>/<evidence>/filename"
           │
           ▼
4. File written to evidence store

5. On any subsequent access or analysis run:
   - Re-compute SHA-256 of the stored file
   - Compare with evidence.file_hash
   - If mismatch: raise integrity alert, create audit record
```

### Why SHA-256

- SHA-256 is a widely accepted cryptographic hash function
- Collisions are computationally infeasible with current hardware
- Widely supported in Python (`hashlib`) without additional dependencies
- Produces a compact, storable 64-character hex digest

### Limitations

SHA-256 hashing detects **unexpected modification** of evidence files. It does not:
- Prevent deliberate tampering by a system administrator with access to both the hash database and the file store
- Provide legal chain-of-custody guarantees equivalent to formal forensic procedures
- Replace proper access control and physical security

These limitations should be documented in any investigation report that cites Sentinel evidence-integrity checks.

---

## Audit Records

All significant evidence and analysis operations should produce an audit record in the `audit_logs` table:

| Operation | Audit event |
|---|---|
| Evidence uploaded | `evidence_ingested` |
| Evidence hash verified (pass) | `integrity_check_passed` |
| Evidence hash mismatch | `integrity_check_failed` |
| Analysis job started | `analysis_started` |
| Analysis job completed | `analysis_completed` |
| Case created | `case_created` |
| Case status changed | `case_status_changed` |

Audit records should never be deleted or updated. They represent an append-only history of operations on the evidence.

---

## Consequences

### Positive

- Clean separation between structured metadata (queryable) and raw files (large, binary)
- SHA-256 integrity provides evidence-tampering detection
- Storage scales independently: grow the database and file storage independently
- PostgreSQL dump + file store backup provides a complete evidence backup
- Local filesystem path is simple to configure for different deployment environments

### Negative / Trade-offs

- Two storage systems to maintain and backup
- File path management must be consistent between PostgreSQL records and the filesystem
- If files are manually moved or deleted outside Sentinel, integrity checks will fail

### Mitigations

- Evidence files should only be managed through the Sentinel API, not directly via the filesystem
- Regular integrity checks should be scheduled as part of the audit workflow
- Backup procedures should cover both PostgreSQL and the evidence store path

---

## Review Triggers

This ADR should be revisited if:
- The team decides to support S3-compatible object storage as a primary option
- Evidence file sizes exceed filesystem capacity on target deployments
- PostgreSQL performance degrades significantly under the expected event volume

---

*Storage decisions are foundational. Changes to this architecture require careful migration planning.*
