#!/usr/bin/env python3
"""generate_demo_data.py — Synthetic multimodal evidence with a planted insider scenario.

Unlike independent random tables, every modality here shares one company
(10 employees, 3 working days, the same zones/cameras/badges), and one planted
insider-threat scenario spans all modalities so that the correlation engine
has something real to find and evaluate against ``scenario_ground_truth.json``.

Scenario "Night Copy" (2026-01-16, all times UTC):
  15 Jan 16:10  HR note: user_007 resigned and is joining a competitor
  16 Jan 21:00  user_007 logs in after hours on WS-007 (ZONE-OFFICE-3F)
  16 Jan 21:40  BADGE-007 enters the building (ZONE-LOBBY)
  16 Jan 21:52  BADGE-007 is DENIED at the server room door
  16 Jan 21:58  CCTV: two people enter the server room (tailgating), high motion
  16 Jan 22:05  WS-007: mass file reads, 4 USB events, ~4.8 MB out
  16 Jan 22:06  BADGE-007 swiped at ZONE-DATA-CENTER-B (1 minute after the
                workstation activity on another floor -> credential sharing?)
  16 Jan 22:30  Night guard note describing the tailgating and a USB drive

Background activity is generated with a fixed seed and includes benign
"hard negatives" (an admin who visits the server room daily with a valid
badge, a busy engineer with many file reads).

Outputs (default ``data/generated/``): cyber.csv, badge.csv, video.csv,
documents.jsonl, scenario_ground_truth.json
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import random
from pathlib import Path

UTC = dt.timezone.utc
DAYS = [dt.date(2026, 1, 14), dt.date(2026, 1, 15), dt.date(2026, 1, 16)]
USERS = [f"user_{i:03d}" for i in range(1, 11)]
INSIDER = "user_007"
ADMIN = "user_003"
BUSY_ENGINEER = "user_005"

ZONE_LOBBY = "ZONE-LOBBY"
ZONE_SERVER = "ZONE-RESTRICTED-SERVER-ROOM"
ZONE_DC = "ZONE-DATA-CENTER-B"
CAMERAS = [
    ("CAM-LOBBY-01", ZONE_LOBBY, 0),
    ("CAM-SERVER-01", ZONE_SERVER, 1),
    ("CAM-OFFICE-3F", "ZONE-OFFICE-3F", 0),
]


def office_zone(user: str) -> str:
    return "ZONE-OFFICE-2F" if int(user.split("_")[1]) <= 5 else "ZONE-OFFICE-3F"


def badge_id(user: str) -> str:
    return f"BADGE-{user.split('_')[1]}"


def ts(day: dt.date, hour: int, minute: int = 0) -> str:
    return dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC).isoformat()


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {len(rows):4d} rows -> {path}")


# ---------------------------------------------------------------------------
def generate_cyber(rng: random.Random) -> list[dict]:
    rows = []
    for day in DAYS:
        for hour in range(8, 18):
            for user in USERS:
                busy = user == BUSY_ENGINEER and hour in (11, 15)
                rows.append({
                    "timestamp": ts(day, hour, rng.randint(35, 45)),
                    "user_id": user,
                    "host": f"WS-{user.split('_')[1]}",
                    "location_id": office_zone(user),
                    "login_count": rng.randint(0, 2),
                    "file_reads": rng.randint(60, 110) if busy else rng.randint(2, 25),
                    "usb_events": 0,
                    "bytes_out": rng.randint(5_000, 60_000),
                    "http_events": rng.randint(3, 20),
                    "email_events": rng.randint(0, 6),
                    "after_hours_events": 0,
                    "label": 0,
                })
    scenario_day = DAYS[-1]
    rows += [
        {"timestamp": ts(scenario_day, 21, 0), "user_id": INSIDER, "host": "WS-007", "location_id": "ZONE-OFFICE-3F",
         "login_count": 3, "file_reads": 70, "usb_events": 0, "bytes_out": 250_000, "http_events": 4,
         "email_events": 0, "after_hours_events": 1, "label": 1},
        {"timestamp": ts(scenario_day, 22, 5), "user_id": INSIDER, "host": "WS-007", "location_id": "ZONE-OFFICE-3F",
         "login_count": 2, "file_reads": 240, "usb_events": 4, "bytes_out": 4_800_000, "http_events": 2,
         "email_events": 12, "after_hours_events": 1, "label": 1},
    ]
    rows.sort(key=lambda r: r["timestamp"])
    return rows


def generate_badges(rng: random.Random) -> list[dict]:
    rows = []
    for day in DAYS:
        for user in USERS:
            arrive = rng.randint(0, 25)
            rows.append({"timestamp": ts(day, 8, arrive), "badge_id": badge_id(user), "location_id": ZONE_LOBBY,
                         "door_id": "DOOR-MAIN", "result": "granted"})
            rows.append({"timestamp": ts(day, 8, arrive + rng.randint(2, 6)), "badge_id": badge_id(user),
                         "location_id": office_zone(user), "door_id": f"DOOR-{office_zone(user)[5:]}", "result": "granted"})
            rows.append({"timestamp": ts(day, 12, rng.randint(0, 20)), "badge_id": badge_id(user),
                         "location_id": ZONE_LOBBY, "door_id": "DOOR-MAIN", "result": "granted"})
        # Authorised admin visits the server room every day (benign hard negative).
        rows.append({"timestamp": ts(day, 10, 30), "badge_id": badge_id(ADMIN), "location_id": ZONE_SERVER,
                     "door_id": "DOOR-SERVER", "result": "granted"})
    scenario_day = DAYS[-1]
    rows += [
        {"timestamp": ts(scenario_day, 21, 40), "badge_id": badge_id(INSIDER), "location_id": ZONE_LOBBY,
         "door_id": "DOOR-MAIN", "result": "granted"},
        {"timestamp": ts(scenario_day, 21, 52), "badge_id": badge_id(INSIDER), "location_id": ZONE_SERVER,
         "door_id": "DOOR-SERVER", "result": "denied"},
        {"timestamp": ts(scenario_day, 22, 6), "badge_id": badge_id(INSIDER), "location_id": ZONE_DC,
         "door_id": "DOOR-DC-B", "result": "granted"},
    ]
    rows.sort(key=lambda r: r["timestamp"])
    return rows


def generate_video_features(rng: random.Random) -> list[dict]:
    rows = []
    for day in DAYS:
        for hour in range(7, 24):
            for minute in (0, 15, 30, 45):
                for camera, zone, restricted in CAMERAS:
                    business = 8 <= hour < 18
                    if restricted:
                        admin_visit = hour == 10 and minute == 30
                        motion = rng.uniform(0.25, 0.35) if admin_visit else rng.uniform(0.0, 0.03)
                        persons = 1 if admin_visit else 0
                    elif business:
                        motion, persons = rng.uniform(0.08, 0.3), rng.randint(1, 4)
                    else:
                        motion, persons = rng.uniform(0.0, 0.05), 0
                    rows.append({"timestamp": ts(day, hour, minute), "camera_id": camera, "location_id": zone,
                                 "motion_score": round(motion, 4), "person_count": persons,
                                 "restricted_zone": restricted, "label": 0})
    scenario_day = DAYS[-1]
    rows += [
        {"timestamp": ts(scenario_day, 21, 58), "camera_id": "CAM-SERVER-01", "location_id": ZONE_SERVER,
         "motion_score": 0.86, "person_count": 2, "restricted_zone": 1, "label": 1},
        {"timestamp": ts(scenario_day, 22, 2), "camera_id": "CAM-SERVER-01", "location_id": ZONE_SERVER,
         "motion_score": 0.74, "person_count": 2, "restricted_zone": 1, "label": 1},
    ]
    rows.sort(key=lambda r: (r["timestamp"], r["camera_id"]))
    return rows


def generate_documents(rng: random.Random) -> list[dict]:
    routine = [
        "Routine shift handover memo: {user} completed scheduled maintenance on {zone}. No issues found.",
        "IT ticket closed: {user} requested a monitor replacement. Resolved by service desk.",
        "Meeting minutes: {user} presented the quarterly roadmap to the team. Action items assigned.",
        "Facilities note: {user} reported the coffee machine on {zone} is out of order.",
        "Training record: {user} completed annual security awareness training.",
    ]
    docs = []
    for i, day in enumerate(DAYS):
        for j in range(5):
            user = rng.choice([u for u in USERS if u != INSIDER])
            docs.append({
                "document_id": f"DOC-{i + 1}{j + 1:02d}",
                "timestamp": ts(day, rng.randint(9, 17), rng.randint(0, 59)),
                "text": routine[j].format(user=user, zone=office_zone(user)),
                "label": 0,
            })
    docs += [
        {"document_id": "DOC-IT-USB", "timestamp": ts(DAYS[0], 14, 20),
         "text": f"IT ticket: {BUSY_ENGINEER} asked for a USB exception for a hardware test rig. "
                 "Approved by manager, scoped to lab devices only.", "label": 0},
        {"document_id": "DOC-HR-007", "timestamp": ts(DAYS[1], 16, 10),
         "text": f"HR note: {INSIDER} submitted a resignation letter and will join a competitor next month. "
                 f"Manager reports {INSIDER} recently asked for access to the confidential source code repository.",
         "label": 1},
        {"document_id": "DOC-TIP-01", "timestamp": ts(DAYS[2], 9, 5),
         "text": "Anonymous tip: someone has been copying confidential files to removable media after hours.",
         "label": 1},
        {"document_id": "DOC-GUARD-0116", "timestamp": ts(DAYS[2], 22, 30),
         "text": f"Night guard incident note: badge {badge_id(INSIDER)} was denied at the {ZONE_SERVER} door at 21:52. "
                 f"Minutes later two people entered {ZONE_SERVER} (possible tailgating). {INSIDER} was later seen "
                 "leaving the building with a USB drive. Unauthorized after hours access suspected.",
         "label": 1},
    ]
    docs.sort(key=lambda d: d["timestamp"])
    return docs


def ground_truth() -> dict:
    day = DAYS[-1]
    return {
        "scenario": "Night Copy",
        "malicious_entity": INSIDER,
        "aliases": [badge_id(INSIDER), "WS-007"],
        "window": {"start": ts(day, 21, 0), "end": ts(day, 22, 30)},
        "expected_contradictions": [
            "denied_access_then_activity", "uncredentialed_presence", "impossible_travel", "after_hours_activity",
        ],
        "benign_hard_negatives": {
            ADMIN: "daily authorised server-room visit at 10:30 with a valid badge",
            BUSY_ENGINEER: "high file-read volume at 11:00 and 15:00, approved USB exception",
        },
        "suggested_video_start_time": ts(day, 21, 58),
        "suggested_video_location_id": ZONE_SERVER,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Sentinel synthetic multimodal demo data.")
    parser.add_argument("--output", default="data/generated", help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (deterministic output)")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    out = Path(args.output)
    print(f"Generating synthetic scenario data in {out} (seed={args.seed})...")
    write_csv(out / "cyber.csv", generate_cyber(rng))
    write_csv(out / "badge.csv", generate_badges(rng))
    write_csv(out / "video.csv", generate_video_features(rng))
    docs = generate_documents(rng)
    with (out / "documents.jsonl").open("w", encoding="utf-8") as handle:
        for doc in docs:
            handle.write(json.dumps(doc) + "\n")
    print(f"  wrote {len(docs):4d} rows -> {out / 'documents.jsonl'}")
    (out / "scenario_ground_truth.json").write_text(json.dumps(ground_truth(), indent=2), encoding="utf-8")
    print(f"  wrote ground truth -> {out / 'scenario_ground_truth.json'}")


if __name__ == "__main__":
    main()
