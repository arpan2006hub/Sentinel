# Evaluation Plan — Sentinel

> **Status**: Planned evaluation process. No evaluation has been conducted yet.

---

## Overview

This document describes the planned evaluation process for Sentinel. Evaluation covers four distinct dimensions:

| Dimension | What is being measured |
|---|---|
| **Model performance** | How well individual AI models detect anomalies within a single modality |
| **System performance** | How efficiently the full Sentinel system ingests and processes evidence |
| **Evidence-correlation performance** | How well the correlation engine links events across modalities |
| **Demonstration performance** | How effectively a complete investigation scenario is reconstructed |

These dimensions must be clearly distinguished in all reports and presentations. Conflating them leads to misleading conclusions.

---

## Evaluation Phases

---

### Phase 1 — Dataset Preprocessing and Verification

**Goal**: Ensure datasets are correctly downloaded, preprocessed, and split before any model is trained or evaluated.

**Tasks**:
- [ ] Download required datasets (CERT, LANL, UCF-Crime, DocVQA)
- [ ] Implement preprocessing scripts for each modality
- [ ] Define reproducible train / validation / test splits
- [ ] Verify that no test-set data leaks into training
- [ ] Document all preprocessing decisions in code comments and this document

**Acceptance criteria**:
- Preprocessing scripts run end-to-end without manual intervention
- Split sizes and random seeds are documented and reproducible
- Data statistics (event counts, label distributions) are recorded

---

### Phase 2 — Baseline Models

**Goal**: Establish a simple baseline for each modality to compare against learned models.

**Planned baselines**:

| Modality | Baseline approach |
|---|---|
| Cyber | Statistical z-score anomaly detection on event frequency features |
| Video | Frame difference magnitude thresholding |
| Document | Exact keyword matching for claim extraction |

**Metrics to record**: Precision, Recall, F1 on the held-out test set for each modality.

**Acceptance criteria**:
- Baseline results are logged to MLflow
- Results are documented in a results table

---

### Phase 3 — Per-Modality AI Evaluation

**Goal**: Evaluate each modality-specific AI model independently (no cross-source correlation).

**Tasks**:
- [ ] Train / fine-tune Cyber AI model on CERT dataset
- [ ] Evaluate Cyber AI on CERT test split
- [ ] Train / evaluate Video AI on UCF-Crime (proxy task)
- [ ] Train / evaluate Document AI on DocVQA (proxy task)

**Metrics**:
- Precision, Recall, F1, PR-AUC per modality
- False-positive rate per modality
- Inference latency per evidence unit

**Acceptance criteria**:
- Each modality AI pipeline produces structured event outputs in canonical event format
- Performance metrics are logged to MLflow and documented here

---

### Phase 4 — Multimodal Correlation Evaluation

**Goal**: Evaluate the correlation engine's ability to link events across evidence sources.

Because no single public dataset spans all modalities, this phase uses a **purpose-built synthetic scenario** (see `scripts/generate_demo_data.py` and `data/sample/`).

**Tasks**:
- [ ] Define a synthetic multimodal scenario with known ground-truth event sequences
- [ ] Run each modality AI pipeline over the synthetic evidence
- [ ] Run the correlation engine
- [ ] Evaluate against the ground-truth sequence

**Metrics**:
- Cross-source entity resolution accuracy (are the same real-world entities correctly linked?)
- Timeline reconstruction accuracy (are events ordered and timestamped correctly?)
- Evidence graph edge precision / recall (are the correct entity relationships established?)

**Acceptance criteria**:
- Correlation produces at least one correctly linked cross-source anomaly in the demonstration scenario
- Results are documented with specific evidence references

---

### Phase 5 — Ablation Study

**Goal**: Isolate the contribution of each evidence modality and the correlation engine.

**Variants**:

| Variant | Components | Expected outcome |
|---|---|---|
| Model A | Cyber only | Baseline detection on cyber evidence |
| Model B | Cyber + temporal correlation | Temporal clustering improves precision |
| Model C | Cyber + physical + correlation | Physical evidence resolves ambiguous cyber events |
| Model D | Cyber + physical + document + correlation | Document evidence adds explanation and contradiction signals |

**Tasks**:
- [ ] Evaluate each variant on the same scenario / test set
- [ ] Record all metrics per variant
- [ ] Compute improvement of each modality addition over the previous variant

**Acceptance criteria**:
- All variants use the same evaluation scenario
- Comparison is fair: same random seeds, same test data
- Results are presented in a comparison table

---

### Phase 6 — False-Positive Analysis

**Goal**: Understand when and why the system raises anomalies that are not genuine.

**Tasks**:
- [ ] Collect all false-positive anomalies across all variants
- [ ] Categorise false positives by type (temporal, behavioural, cross-source, etc.)
- [ ] Identify systematic patterns in false positives
- [ ] Document potential mitigation strategies

**Acceptance criteria**:
- False-positive cases are documented with specific evidence references
- Patterns are identified and discussed in the final report

---

### Phase 7 — Error Analysis

**Goal**: Understand missed detections and incorrect anomaly descriptions.

**Tasks**:
- [ ] Identify all false negatives (genuine suspicious events that were not flagged)
- [ ] Categorise by cause: missing evidence, model failure, schema gap, etc.
- [ ] Identify incorrect anomaly descriptions / wrong actor attributions
- [ ] Document failure modes

**Acceptance criteria**:
- Error cases are catalogued
- Root causes are discussed

---

### Phase 8 — Domain Gap Discussion

**Goal**: Honestly characterise the limitations of evaluating on public datasets.

**Key points to address**:
- No single dataset covers all Sentinel modalities
- Synthetic scenarios may not reflect real investigation complexity
- UCF-Crime anomaly categories (crime) do not directly correspond to insider-threat activity
- CERT data is synthetic
- Results may not generalise to real-world deployments

**Acceptance criteria**:
- Domain gap is explicitly acknowledged in the evaluation report
- Generalisability claims are appropriately qualified

---

### Phase 9 — Demonstration Scenario

**Goal**: Produce a convincing end-to-end demonstration of the full Sentinel system for presentation.

**Tasks**:
- [ ] Design a self-contained multi-step demonstration scenario
- [ ] Generate synthetic evidence for each modality
- [ ] Run full Sentinel pipeline: ingest → AI → correlate → dashboard
- [ ] Record a walkthrough of the investigator dashboard
- [ ] Document the scenario ground truth so reviewers can verify correctness

**Acceptance criteria**:
- Demonstration runs end-to-end without manual intervention
- The investigator dashboard surfaces at least two meaningful investigative leads
- The scenario ground truth is documented

---

### Phase 10 — Reproducibility

**Goal**: Ensure all results can be reproduced by the team and external reviewers.

**Tasks**:
- [ ] All preprocessing scripts are committed and documented
- [ ] All random seeds are fixed and documented
- [ ] MLflow experiment logs are exported and archived
- [ ] Model weights for submitted models are stored (outside Git) with documented access instructions
- [ ] A reproducibility checklist is included in the final report

**Acceptance criteria**:
- A fresh clone of the repository + dataset download + script execution reproduces the evaluation results

---

## Results Table Template

*(To be filled in as evaluation is completed.)*

| Metric | Model A | Model B | Model C | Model D |
|---|---|---|---|---|
| Precision | — | — | — | — |
| Recall | — | — | — | — |
| F1 | — | — | — | — |
| PR-AUC | — | — | — | — |
| False-Positive Rate | — | — | — | — |

> **Do not fill in placeholder or fabricated numbers.** Leave cells blank until real evaluation results are available.

---

## MLflow Integration

All evaluation runs should be logged to MLflow:

- Run parameters (model variant, dataset, split)
- All metrics
- Artefact paths (model weights, predictions)
- Run notes

MLflow tracking server: `http://localhost:5000` (see `docker-compose.yml`)

---

*This evaluation plan will be updated as evaluation progresses and decisions are finalised.*
