#!/usr/bin/env python3
"""generate_demo_data.py — Generate synthetic demo data for Sentinel multimodal investigation."""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import random
from pathlib import Path


def generate_cyber_data(output_file: Path, rows: int = 150) -> None:
    """Generate synthetic cyber endpoint and authentication logs."""
    users = [f"user_{i:03d}" for i in range(1, 11)]
    start_time = datetime.datetime(2026, 1, 15, 8, 0, 0, tzinfo=datetime.timezone.utc)

    records = []
    for i in range(rows):
        timestamp = (start_time + datetime.timedelta(minutes=i * 15)).isoformat()
        user = random.choice(users)
        is_anomaly = random.random() < 0.08  # 8% anomaly rate

        if is_anomaly:
            login_count = random.randint(5, 18)
            file_reads = random.randint(50, 200)
            usb_events = random.randint(1, 4)
            bytes_out = random.randint(500_000, 5_000_000)
            http_events = random.randint(20, 100)
            email_events = random.randint(10, 40)
            after_hours = 1 if (i % 24 < 6 or i % 24 > 19) else 0
            label = 1
        else:
            login_count = random.randint(1, 3)
            file_reads = random.randint(2, 25)
            usb_events = 0
            bytes_out = random.randint(1000, 50_000)
            http_events = random.randint(1, 15)
            email_events = random.randint(0, 5)
            after_hours = 0
            label = 0

        records.append({
            "timestamp": timestamp,
            "user_id": user,
            "login_count": login_count,
            "file_reads": file_reads,
            "usb_events": usb_events,
            "bytes_out": bytes_out,
            "http_events": http_events,
            "email_events": email_events,
            "after_hours_events": after_hours,
            "label": label,
        })

    output_file.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(records[0].keys())
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    print(f"Generated {len(records)} cyber records at {output_file}")


def generate_video_data(output_file: Path, rows: int = 150) -> None:
    """Generate synthetic video anomaly log records."""
    start_time = datetime.datetime(2026, 1, 15, 8, 0, 0, tzinfo=datetime.timezone.utc)

    records = []
    for i in range(rows):
        timestamp = (start_time + datetime.timedelta(minutes=i * 15)).isoformat()
        is_anomaly = random.random() < 0.08

        if is_anomaly:
            motion_score = round(random.uniform(0.65, 0.98), 4)
            person_count = random.randint(2, 6)
            restricted_zone = random.choice([0, 1])
            label = 1
        else:
            motion_score = round(random.uniform(0.01, 0.25), 4)
            person_count = random.randint(0, 2)
            restricted_zone = 0
            label = 0

        records.append({
            "timestamp": timestamp,
            "motion_score": motion_score,
            "person_count": person_count,
            "restricted_zone": restricted_zone,
            "label": label,
        })

    output_file.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(records[0].keys())
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    print(f"Generated {len(records)} video records at {output_file}")


def generate_documents_data(output_file: Path, count: int = 40) -> None:
    """Generate synthetic incident statements and reports in JSONL format."""
    users = [f"user_{i:03d}" for i in range(1, 11)]

    records = []
    for i in range(1, count + 1):
        doc_id = f"DOC-{i:03d}"
        user = random.choice(users)
        hour = random.randint(8, 20)
        time_str = f"{hour:02d}:30 UTC"

        if i % 4 == 0:
            # Suspicious document claim
            text = (
                f"Incident witness report: At {time_str}, {user} was observed accessing the restricted "
                f"server room. Removable media and a USB device were connected to the console, and "
                f"confidential source code directories were copied to external storage."
            )
            label = 1
        else:
            # Normal document
            text = (
                f"Routine shift handover memo: At {time_str}, {user} performed routine administrative "
                f"maintenance. System integrity check completed normally."
            )
            label = 0

        records.append({
            "document_id": doc_id,
            "text": text,
            "label": label,
        })

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    print(f"Generated {len(records)} document records at {output_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic demo data for Sentinel.")
    parser.add_argument("--output", default="data/generated", help="Output directory")
    parser.add_argument("--rows", type=int, default=150, help="Number of tabular rows per modality")
    args = parser.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating synthetic demonstration data in {out_dir}...")
    generate_cyber_data(out_dir / "cyber.csv", rows=args.rows)
    generate_video_data(out_dir / "video.csv", rows=args.rows)
    generate_documents_data(out_dir / "documents.jsonl", count=40)
    print("Demo data generation complete.")


if __name__ == "__main__":
    main()