# ADR-002: Local-First / Self-Hosted Architecture

**Status**: Accepted  
**Date**: 2026  
**Authors**: Sentinel Team  

---

## Context

Sentinel is designed to assist in insider-threat investigations. The evidence it processes may include:

- Authentication and system logs
- CCTV footage and physical access records
- Internal documents, incident reports, and employee statements
- File-access histories and device activity

This evidence is fundamentally sensitive. Organisations conducting insider-threat investigations have legitimate expectations that their investigation data will not leave their control.

The team needed to decide whether Sentinel should operate as:

1. **A hosted/centralised SaaS platform** — where organisations upload evidence to a shared Sentinel-operated service
2. **A local-first, self-hosted application** — where each organisation runs its own Sentinel instance on infrastructure it controls

---

## Decision

**Sentinel will be designed as a local-first, self-hosted application.**

Each organisation or user that wishes to use Sentinel:
1. Clones or downloads the Sentinel repository from GitHub
2. Deploys Sentinel on infrastructure they control (local server, private cloud, air-gapped system, etc.)
3. Operates their own independent instance with no dependency on a centralised Sentinel-operated service

```
GitHub (code distribution only)
            │
            │  clone
            ▼
Organisation's Own Infrastructure
            │
            ├── Sentinel Frontend
            ├── Sentinel Backend
            ├── PostgreSQL
            ├── Local Evidence Storage
            ├── AI Processing
            └── Audit / Integrity Records
```

Investigation data never leaves the organisation's infrastructure as part of the Sentinel application architecture.

---

## Rationale

### 1. Sensitivity of Investigation Data

Insider-threat investigations involve personnel data, behavioural records, and evidence that organisations are legally and ethically obligated to protect. Uploading this evidence to a third-party service introduces significant legal, ethical, and practical risk.

### 2. Organisational Control

Organisations should retain full control over:
- What evidence is stored
- Where it is stored
- Who can access it
- How long it is retained
- Whether to delete it

A centralised SaaS model requires placing trust in the service operator. A local-first model eliminates this dependency.

### 3. Suitability for Security-Sensitive Environments

Security-oriented organisations (government, defence, finance, critical infrastructure) frequently operate in environments where:
- External data transfers are restricted
- Air-gapped or isolated networks are required
- Third-party data processors require extensive legal agreement

A local-first design accommodates these environments without special configuration.

### 4. Privacy Story

When all investigation data stays on the organisation's infrastructure, the privacy story is simple:

> *Your investigation data never leaves your system.*

A centralised SaaS model requires a complex privacy policy, data processing agreements, and ongoing trust.

### 5. Dependency Reduction

A local-first architecture is resilient to:
- Service outages of a centralised provider
- Pricing changes
- API deprecation
- Changes in the service operator's terms or ownership

### 6. No Hidden Telemetry

Sentinel will not include any telemetry, analytics, or usage-tracking code that transmits data to the Sentinel project team or any third party.

---

## Scope of This Decision

### What local-first means for Sentinel

| Requirement | Status |
|---|---|
| No mandatory centralised Sentinel server | ✅ Required |
| No mandatory cloud database | ✅ Required |
| No mandatory cloud evidence storage | ✅ Required |
| No user account on a Sentinel-operated service | ✅ Required |
| No hidden telemetry | ✅ Required |
| Evidence files stay on local/org infrastructure | ✅ Required |

### What local-first does NOT prohibit

> **Local-first does not mean the system can never support optional external services.**

Future optional integrations could include:
- Optional integration with a local LLM API (e.g., Ollama, local Llama instance)
- Optional integration with a threat-intelligence feed (e.g., MITRE ATT&CK API)
- Optional S3-compatible object storage for large evidence files (organisation-controlled bucket)

**Any future external service integration must be:**
- Explicitly opt-in (not on by default)
- Documented clearly in configuration
- Under the organisation's control (not a Sentinel-operated service)

---

## Consequences

### Positive

- Simple, honest privacy story
- No centralised infrastructure to maintain
- Suitable for security-sensitive and isolated deployments
- No compliance burden from processing third-party data
- Resilient to Sentinel project decisions (users own their deployment)

### Negative / Trade-offs

- No automatic updates — organisations must pull new versions from GitHub and redeploy
- No centralised usage analytics that might help the project team understand how Sentinel is used
- More operational responsibility on the deploying organisation
- No shared authentication / identity management across organisations

### Mitigations

- Clear deployment documentation in Docker Compose and the README
- Makefile targets for common operations (setup, update, restart)
- Future CI-based release packaging (Docker images, tagged releases)

---

## Review Triggers

This ADR should be revisited if:

- The team explicitly decides to offer an optional hosted offering for research demonstration purposes
- An external AI API integration is required and it involves sending evidence data externally

Any such change must be documented as an amendment to this ADR and reflected in all user-facing documentation.

---

*Local-first is a core design principle of Sentinel, not a temporary implementation choice.*
