# Datasets — Sentinel Research

> **Status**: Planned dataset strategy. No datasets have been downloaded or committed to this repository.

---

## Overview

Sentinel's development and evaluation will rely on publicly available research datasets. No single dataset perfectly captures Sentinel's complete multimodal insider-threat scenario — this is an acknowledged limitation of the research, discussed in the [Domain Gap](#domain-gap) section.

Datasets should be downloaded and processed locally by each team member as needed. Dataset files must never be committed to this repository.

---

## Dataset Inventory

---

### 1. CERT Insider Threat Test Dataset

**Maintained by**: Carnegie Mellon University Software Engineering Institute  
**URL**: https://resources.sei.cmu.edu/library/asset-view.cfm?assetid=508099  
**Access**: Requires registration and agreement to terms of use.

**What it contains**:
- Synthetic but realistic cyber log data simulating employee workstation activity
- Multiple releases (r4.2, r5.2, r6.2) with increasing complexity
- Log types: authentication, file access, HTTP, email, device/USB activity, psychometric profiles
- Labelled insider-threat scenarios embedded within a large background of normal user activity

**Sentinel component**: Cyber AI (log preprocessing, feature extraction, anomaly detection, behavioural modelling)

**Strengths**:
- Most widely used insider-threat evaluation benchmark
- Labelled ground truth
- Multiple log modalities in a single dataset
- Designed for reproducible evaluation

**Limitations**:
- Synthetic data — may not capture all real-world patterns
- No CCTV or video component
- No physical badge access data
- No real document or PDF evidence
- Psychometric data unlikely to be available in real investigations

**Modality**: Cyber (logs)

---

### 2. VAST 2009 Grand Challenge

**Maintained by**: IEEE VAST (Visual Analytics Science and Technology)  
**URL**: http://vacommunity.org/VAST+Challenge+2009  
**Access**: Publicly available.

**What it contains**:
- Multi-format scenario dataset designed for visual analytics investigation research
- Includes network activity, physical access logs, and contextual narrative information
- Designed around an investigation scenario with multiple evidence sources

**Sentinel component**: Cross-source correlation, timeline construction, investigation scenario demonstration

**Strengths**:
- One of the few datasets that spans multiple evidence modalities in a single scenario
- Designed for investigation use cases

**Limitations**:
- Older dataset (2009) — activity patterns may not reflect modern threats
- Limited video/CCTV component
- Small scale compared to modern needs
- Visual analytics focus rather than ML focus

**Modality**: Cyber + Physical (partial multimodal)

---

### 3. LANL Cybersecurity Dataset

**Maintained by**: Los Alamos National Laboratory  
**URL**: https://csr.lanl.gov/data/cyber1/  
**Access**: Publicly available.

**What it contains**:
- Anonymised enterprise network authentication event logs
- Approximately 1.6 billion network events over 58 days
- Process execution, network flows, DNS queries
- Includes a set of labelled red-team compromise events

**Sentinel component**: Cyber AI (network log analysis, authentication anomaly detection)

**Strengths**:
- Very large scale — realistic enterprise volume
- Real anonymised enterprise data (not synthetic)
- Labelled red-team events for evaluation

**Limitations**:
- Network/authentication focus only — no file access, USB, video, or document data
- No physical access data
- Red-team events may not perfectly model insider-threat patterns (vs. external intrusion)

**Modality**: Cyber (network/authentication logs)

---

### 4. SPEDIA / Similar Multimodal Datasets

**Note**: SPEDIA and related academic multimodal surveillance datasets vary in availability. The team should research current availability through academic channels at project start.

**What it may contain**:
- Person re-identification across cameras
- Multi-camera activity data
- Surveillance scenario data

**Sentinel component**: Video AI (person detection, cross-camera tracking), physical correlation

**Strengths**:
- Multi-camera perspective relevant to physical investigation
- Person-tracking useful for cross-zone movement reconstruction

**Limitations**:
- May require ethical review / institutional access
- Labelling may not correspond to insider-threat scenarios
- Does not include cyber log context

**Modality**: Video / Physical

---

### 5. UCF-Crime

**Maintained by**: University of Central Florida  
**URL**: https://www.crcv.ucf.edu/projects/real-world/  
**Access**: Publicly available for research.

**What it contains**:
- Real-world surveillance video clips
- 13 anomalous activity categories (assault, burglary, robbery, etc.)
- Weakly labelled at the video level (clip-level labels, not frame-level)
- ~1900 video clips

**Sentinel component**: Video AI (anomaly detection, unusual activity recognition — proxy task for insider-threat video analysis)

**Strengths**:
- Real CCTV footage (not synthetic)
- Established benchmark for video anomaly detection
- Widely used in academic literature

**Limitations**:
- Categories (assault, robbery) do not directly correspond to insider-threat activity
- Weak labels only
- Domain gap: insider-threat video scenarios (unusual after-hours access, device connection) differ significantly from crime scenarios
- No associated cyber log or document evidence

**Modality**: Video

---

### 6. DocVQA

**Maintained by**: IIT Hyderabad / Document Intelligence community  
**URL**: https://www.docvqa.org/  
**Access**: Publicly available for research.

**What it contains**:
- Document Visual Question Answering benchmark
- Scanned document images + natural language questions + answers
- Various document types: forms, tables, letters, reports

**Sentinel component**: Document AI (OCR, document understanding, information extraction)

**Strengths**:
- Widely used benchmark for document understanding
- Diverse document types
- Good for evaluating OCR and extraction pipeline quality

**Limitations**:
- Not insider-threat specific
- No associated cyber or video evidence
- Questions are answerable from single documents — no cross-document reasoning

**Modality**: Documents (OCR / visual question answering)

---

### 7. MITRE ATT&CK STIX Data

**Maintained by**: MITRE  
**URL**: https://github.com/mitre/cti  
**Access**: Publicly available.

**What it contains**:
- Structured threat-intelligence knowledge base
- Techniques, tactics, sub-techniques with detailed descriptions
- Relationships between threat actors, software, techniques
- Available in STIX 2.1 JSON format

**Sentinel component**: Cyber AI (threat intelligence enrichment), Correlation Engine (mapping observed events to known attack techniques)

**Strengths**:
- Comprehensive, well-maintained threat-intelligence resource
- Structured format suitable for graph construction
- Widely used in the security industry

**Limitations**:
- Knowledge base, not a dataset for training/evaluation
- Focuses on external threat actor tactics — insider-threat coverage is partial
- Does not include specific event-level data for model training

**Modality**: Threat Intelligence (structured knowledge)

---

## Domain Gap

> **No single public dataset perfectly represents Sentinel's complete multimodal insider-threat scenario.**

This is a fundamental limitation of the research and must be acknowledged in all evaluation and reporting.

| Dataset | Cyber | Physical | Video | Documents |
|---|---|---|---|---|
| CERT | ✅ | ❌ | ❌ | ❌ |
| VAST 2009 | ✅ | Partial | ❌ | ❌ |
| LANL | ✅ | ❌ | ❌ | ❌ |
| UCF-Crime | ❌ | ❌ | ✅ | ❌ |
| DocVQA | ❌ | ❌ | ❌ | ✅ |
| MITRE ATT&CK | Partial | ❌ | ❌ | ❌ |

**Implications**:
- Cross-modality correlation cannot be evaluated directly against a ground-truth multimodal dataset using current public data
- Per-modality evaluation (cyber only, video only, document only) is feasible using the datasets above
- Multimodal evaluation will require a purpose-built synthetic demonstration scenario
- The team should clearly distinguish between per-modality performance and end-to-end system demonstration

---

## Dataset Download Instructions

Datasets must be downloaded locally by each team member as required.

**Do not commit datasets to this repository.**

Suggested local layout (outside the repository):
```
~/sentinel-data/
    cert/           # CERT Insider Threat Dataset
    lanl/           # LANL Cybersecurity Dataset
    vast2009/       # VAST 2009
    ucf-crime/      # UCF-Crime
    docvqa/         # DocVQA
    mitre-attack/   # MITRE ATT&CK STIX
```

Dataset preprocessing scripts should be placed in `ai/<modality>/preprocessing/` and should accept configurable input paths via environment variable or argument.

---

*This document will be updated as dataset access and preprocessing decisions are finalised.*
