# Research Methodology — Sentinel

> **Status**: Planned methodology. No experiments have been conducted yet.

---

## Research Question

> **Can multimodal evidence correlation improve the detection and explanation of insider-threat activity compared with analysing individual evidence sources independently?**

This question drives the technical design of Sentinel. The system is structured to make a direct comparison between single-modality AI pipelines and a multimodal correlation system feasible.

---

## Hypothesis

We hypothesise that combining and correlating evidence from multiple modalities (cyber logs, physical access events, video, and documents) will:

1. Reduce false-positive rates compared with single-modality approaches
2. Improve detection of suspicious patterns that span multiple evidence sources
3. Provide richer, more explainable investigative leads that a human investigator can act on
4. Surface contradictions and corroborating evidence that would be invisible to a single-modality system

We make no claim about a specific detection accuracy or performance level. These hypotheses will be tested through the ablation study described below.

---

## Ablation Study Design

The core evaluation strategy is an ablation study comparing models with increasing numbers of evidence modalities.

| Model | Evidence Sources | AI Components |
|---|---|---|
| **Model A** | Cyber logs only | Cyber AI |
| **Model B** | Cyber + temporal correlation | Cyber AI + temporal correlation |
| **Model C** | Cyber + physical access evidence | Cyber AI + Physical logs + correlation |
| **Model D** | Cyber + physical + document evidence | Cyber AI + Physical + Document AI + correlation |

Each model variant processes the same underlying scenario. Performance is measured on each variant to isolate the contribution of each evidence modality and the correlation engine.

If video AI is sufficiently developed, a Model E (all modalities) variant may be added.

---

## Evaluation Metrics

### Detection Performance

| Metric | Description |
|---|---|
| **Precision** | Of all flagged anomalies, what fraction were genuine? |
| **Recall** | Of all genuine suspicious events, what fraction were detected? |
| **F1 Score** | Harmonic mean of precision and recall |
| **PR-AUC** | Area under the precision-recall curve |
| **False-Positive Rate** | Rate of flagged anomalies that are not genuinely suspicious |
| **Detection Latency** | Time from evidence ingestion to surfacing a relevant anomaly |

### Explanation / Evidence Coverage

Where measurable:

| Metric | Description |
|---|---|
| **Evidence coverage** | Fraction of relevant evidence events included in an anomaly explanation |
| **Cross-source coverage** | Whether anomaly explanations reference evidence from multiple modalities |

### System Performance

| Metric | Description |
|---|---|
| **Ingestion throughput** | Evidence records processed per second |
| **Analysis latency** | Wall-clock time from job submission to results |

---

## Evaluation Data

### Per-Modality Evaluation

- **Cyber AI**: Evaluated on CERT Insider Threat Test Dataset and/or LANL dataset
- **Video AI**: Evaluated on UCF-Crime (as a proxy task for activity anomaly detection)
- **Document AI**: Evaluated on DocVQA (as a proxy for extraction quality)

### Multimodal / Correlation Evaluation

No single public dataset covers the complete multimodal scenario. The team will:

1. Use VAST 2009 to the extent that its multi-source format is applicable
2. Construct a **purpose-built synthetic scenario** combining synthetic events from multiple modalities to form a ground-truth multimodal test case

The synthetic scenario should be documented and made reproducible using the scripts in `scripts/generate_demo_data.py`.

---

## Evaluation Process

### Phase 1 — Dataset Preprocessing

- Download relevant datasets locally (see `docs/research/datasets.md`)
- Implement preprocessing pipelines in `ai/<modality>/preprocessing/`
- Define train / validation / test splits
- Document all preprocessing decisions

### Phase 2 — Baseline Models

- Implement and evaluate simple statistical baselines for each modality
- Establish baseline precision, recall, F1 for comparison

### Phase 3 — Per-Modality AI

- Implement and evaluate each modality AI pipeline independently (Model A variant)
- Record per-modality metrics

### Phase 4 — Multimodal Correlation

- Implement the correlation engine
- Evaluate Model B, C, D variants with increasing modality coverage
- Compare against per-modality baselines

### Phase 5 — Ablation Study

- Systematically compare all model variants
- Document which evidence sources contribute most to detection quality
- Document the cost of each additional modality (processing time, complexity)

### Phase 6 — False-Positive Analysis

- Examine cases where the system raised anomalies that were not genuinely suspicious
- Identify patterns in false positives
- Document strategies to reduce false-positive rate

### Phase 7 — Error Analysis

- Examine missed detections (false negatives)
- Examine incorrect anomaly descriptions
- Identify failure modes

### Phase 8 — Domain Gap Discussion

- Document the gap between available public datasets and a real insider-threat investigation scenario
- Discuss how this gap affects the validity and generalisability of results

### Phase 9 — Demonstration Scenario

- Construct a realistic end-to-end demonstration scenario
- Run the full Sentinel system (ingestion → AI → correlation → dashboard)
- Document the demonstration for reproducibility

### Phase 10 — Reproducibility

- Ensure all code, configuration, and preprocessing steps are documented
- Ensure the synthetic scenario and its ground truth are reproducible
- Ensure MLflow experiment logs are preserved

---

## Performance Claims

> ⚠️ **No performance claims should be made before evaluation is complete.**

The team should not claim specific accuracy figures, detection rates, or comparison to state-of-the-art results until:

1. Evaluation experiments have been completed
2. Results have been verified
3. Limitations and confounding factors have been documented

All performance numbers presented in reports should be accompanied by:
- The exact dataset and split used
- The model variant being evaluated
- Known limitations and caveats

---

## Ethical Considerations

- Sentinel is designed to **assist** human investigation, not replace human judgment
- AI outputs must never be presented as verdicts
- Evaluation metrics do not tell an investigator that a person is guilty
- Domain-gap limitations must be communicated clearly in all reporting
- Any future use of real data requires appropriate ethical approval and data governance

---

*This methodology document will be updated as evaluation progresses.*
