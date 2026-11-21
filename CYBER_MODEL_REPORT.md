# Sentinel Cyber Model Report

## 1. Objective

The cyber component detects suspicious employee behaviour from enterprise
activity logs. It operates at the **user-day** level: one row represents one
user's activity on one calendar day.

The model is an investigative aid. A positive prediction means that a user-day
should be reviewed; it is not proof of malicious activity.

## 2. Dataset

The model uses the CERT Insider Threat Test Dataset release r4.2.

Source logs used:

- `logon.csv` — login/logoff activity
- `file.csv` — file access
- `device.csv` — removable-device activity
- `http.csv` — web activity
- `email.csv` — email activity

The raw dataset contains approximately 32 million events. The preprocessing
pipeline reads each CSV in chunks of 100,000 rows, groups events by user and
day, and produces 330,452 user-day rows.

Official labels came from the separate CERT `insiders.csv` answers archive.
A row is labeled malicious when its user and date fall within the official
scenario start/end window.

## 3. Features

The final supervised model uses six numerical features:

| Feature | Meaning |
|---|---|
| `login_count` | Number of logon/logoff events for the user that day |
| `file_reads` | Number of file activity records |
| `usb_events` | Number of removable-device events |
| `http_events` | Number of web activity records |
| `email_events` | Number of email records |
| `bytes_out` | Reserved byte-volume feature; currently zero because the first CERT baseline does not parse transfer sizes |

## 4. Models

### Isolation Forest baseline

Isolation Forest is an unsupervised anomaly detector. It does not need labels
for training and isolates observations that look rare compared with the rest
of the data.

Configuration:

- 200 trees
- contamination: 5%
- random seed: 42
- chronological 80/20 evaluation

Time-split result:

| Metric | Result |
|---|---:|
| ROC-AUC | 0.8360 |
| Precision | 0.30% |
| Recall | 3.76% |
| F1 | 0.56% |

The ranking is useful, but the default 5% alert threshold creates too many
false positives. It remains a baseline, not the final detector.

### Final supervised model

The final model is a `RandomForestClassifier` from scikit-learn.

Configuration:

- 200 decision trees
- maximum depth: 16
- minimum samples per leaf: 2
- `class_weight="balanced_subsample"` for severe class imbalance
- random seed: 42
- chronological 80/20 train/test split
- alert threshold: 0.80

The model learns from the official CERT labels in the training period and is
evaluated on later dates that were not used for fitting.

## 5. Final results

Test set:

- Training rows: 264,361
- Test rows: 66,091
- Known malicious test rows: 266
- Predicted alerts: 443

| Metric | Result |
|---|---:|
| Precision | 34.54% |
| Recall | 57.52% |
| F1-score | 43.16% |
| ROC-AUC | 97.65% |
| Average Precision | 47.19% |

Interpretation: at the selected threshold, the model catches approximately
58% of malicious user-days. Approximately 35% of its alerts are malicious
according to the CERT evaluation labels. The remaining alerts are false
positives and require human review.

ROC-AUC measures ranking quality across many thresholds; it is not the same as
the percentage of alerts that are correct at threshold 0.80.

## 6. Reproduction commands

```bash
cd /Users/apratim/Documents/ChatGPT/senitel
source .venv/bin/activate

python ai/cyber/preprocess_cert.py \
  --cert-dir ~/sentinel-data/cert/r4.2 \
  --output data/cert/cyber_features_v2.csv

python ai/cyber/label_cert.py \
  --features data/cert/cyber_features_v2.csv \
  --insiders ~/sentinel-data/cert/answers/answers/insiders.csv \
  --output data/cert/cyber_features_labeled.csv

python ai/cyber/train_supervised.py \
  --data data/cert/cyber_features_labeled.csv \
  --output artifacts/cyber-final \
  --threshold 0.8
```

The main implementation files are:

- `ai/cyber/preprocess_cert.py`
- `ai/cyber/label_cert.py`
- `ai/cyber/train.py`
- `ai/cyber/train_supervised.py`
- `scripts/threshold_report.py`

## 7. Limitations and future work

1. The first feature set uses event counts and does not yet include precise
   after-hours features, file sizes, external email recipients, URL categories,
   or session duration.
2. `bytes_out` is currently a placeholder and should not be presented as a
   measured network-volume feature.
3. CERT is synthetic enterprise activity, not live production data.
4. The threshold was selected from a small threshold comparison and should be
   validated on a separate validation period before deployment.
5. The model produces investigative leads, not automated disciplinary or
   employment decisions.

## 8. Viva / presentation questions and answers

### Q1. What is the objective of the cyber model?

It detects suspicious user behaviour from authentication, file, device, web,
and email logs. Its output is a risk signal for an investigator.

### Q2. Which dataset did you use?

The CERT Insider Threat Test Dataset r4.2, together with its separate answers
archive for official insider-scenario labels.

### Q3. Why did you aggregate events by user and day?

Individual events are too granular and produce a very large, noisy dataset.
User-day aggregation creates a manageable behavioural unit for anomaly
detection and matches common insider-threat evaluation practice.

### Q4. What preprocessing was performed?

The raw CSV files were read in chunks, timestamps were parsed, events were
grouped by user and calendar day, and counts were created for each log source.
Missing source counts were filled with zero.

### Q5. What features were used?

Daily counts of logon, file, USB/device, HTTP, and email events. A byte-volume
field exists in the schema but is currently a placeholder in this baseline.

### Q6. Which final algorithm was used?

A scikit-learn Random Forest classifier with 200 trees, maximum depth 16, and
balanced class weights.

### Q7. Why use Random Forest?

It works well on tabular behavioural features, handles nonlinear relationships,
requires little feature scaling, is relatively interpretable, and runs on a
MacBook without a GPU.

### Q8. Did you also try an unsupervised model?

Yes. Isolation Forest was used as a baseline because real deployments may not
have reliable labels. It achieved ROC-AUC 0.836 on the time-based test, but its
alert precision was poor at the default threshold.

### Q9. Why is the dataset split chronologically?

Randomly mixing dates can leak future behaviour into training. A chronological
split better represents deployment: train on the past and evaluate on later
activity.

### Q10. What does the 0.80 threshold mean?

The Random Forest outputs a probability-like risk score. A user-day is flagged
when its score is at least 0.80. This threshold trades some recall for fewer
false alerts.

### Q11. What is precision?

Precision is the proportion of generated alerts that are actually labeled
malicious. Here it is 34.54% at threshold 0.80.

### Q12. What is recall?

Recall is the proportion of all malicious user-days that the model catches.
Here it is 57.52%.

### Q13. What is F1-score?

F1 is the harmonic mean of precision and recall. It summarizes the balance
between catching threats and limiting false alerts. Here it is 43.16%.

### Q14. What does ROC-AUC 0.9765 mean?

It means the model ranks a randomly selected malicious user-day above a
randomly selected normal user-day with high probability across thresholds. It
does not mean 97.65% of alerts are correct.

### Q15. Why is Average Precision also reported?

Insider threats are rare. Average Precision summarizes the precision-recall
curve and is more informative than accuracy or ROC-AUC alone for imbalanced
data. It is 47.19% here.

### Q16. Why not report accuracy?

Accuracy can be misleading. If malicious rows are extremely rare, a model that
always predicts normal can have very high accuracy while detecting no threats.

### Q17. Is a predicted user definitely malicious?

No. It is only an investigative lead. A human investigator must review the
underlying evidence and context.

### Q18. Why are there false positives?

Busy employees, administrators, backup processes, incident responders, and
unusual but legitimate work can resemble malicious activity.

### Q19. Why did the first Isolation Forest perform poorly?

It flagged rare high-volume patterns without knowing which behaviours were
officially malicious. It also used a fixed 5% contamination assumption.

### Q20. What would you improve next?

Add session duration, after-hours indicators, file sizes, external email
features, URL categories, per-user rolling baselines, and a separate validation
period for threshold selection. Then compare Random Forest with gradient
boosting, One-Class SVM, and sequence models.

### Q21. Can this run on a MacBook Air M4?

Yes. The current tabular pipeline runs on CPU and has already run successfully.
Large deep-learning video models would be better on a GPU machine, but the
cyber Random Forest and Isolation Forest are feasible locally.

### Q22. How does this fit Sentinel’s larger architecture?

The cyber model converts raw logs into risk-scored canonical events. Those
events can later be correlated with video, physical-access, and document
events to build an investigation timeline and evidence graph.
