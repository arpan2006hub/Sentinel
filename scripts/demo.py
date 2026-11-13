#!/usr/bin/env python3
"""demo.py — Build a fully analysed demo case in one command (CPU, ~15 s without video).

Steps:
  1. Generate the synthetic "Night Copy" insider scenario (data/generated/).
  2. Fit the lightweight baselines on it (scripts/run_all.py; seconds).
  3. Create a case, ingest every evidence file through the evidence service
     (SHA-256 + hash-chained audit), and run the same analysis the API runs.
  4. Print the case ID and the API URLs to open in Swagger / the frontend.

Optional CCTV clip (TimeSformer, CPU-heavy: roughly 7 s of CPU per second of
video on a laptop i5 — keep clips short or use --video-max-seconds):

    python scripts/demo.py --video path/to/clip.mp4 --video-max-seconds 20

The clip is aligned to the scenario (first frame = 2026-01-16T21:58:00Z in
ZONE-RESTRICTED-SERVER-ROOM) unless --video-start / --video-location are given.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (PROJECT_ROOT, PROJECT_ROOT / "backend"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.schemas.analysis import AnalysisStartRequest  # noqa: E402
from app.schemas.cases import CaseCreate  # noqa: E402
from app.services.analysis_service import AnalysisService  # noqa: E402
from app.services.case_service import CaseService  # noqa: E402
from app.services.evidence_service import EvidenceService  # noqa: E402

DATA_DIR = PROJECT_ROOT / "data" / "generated"

EVIDENCE = [
    ("cyber.csv", "endpoint_log", {"description": "Endpoint activity per user-hour (WS-001..WS-010)"}),
    ("badge.csv", "badge_log", {"description": "Physical access control export"}),
    ("video.csv", "video_features", {"description": "CCTV motion features (3 cameras)"}),
    ("documents.jsonl", "text_document", {"description": "HR notes, IT tickets, guard reports"}),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an analysed Sentinel demo case.")
    parser.add_argument("--skip-train", action="store_true", help="Reuse existing data/generated and artifacts/")
    parser.add_argument("--video", help="Optional CCTV clip to analyse with TimeSformer (CPU-heavy)")
    parser.add_argument("--video-start", default=None, help="ISO time of the clip's first frame")
    parser.add_argument("--video-location", default=None, help="Zone of the camera")
    parser.add_argument("--video-max-seconds", type=float, default=20.0, help="Analyse at most N seconds of the clip")
    parser.add_argument("--title", default="Night Copy — suspected data exfiltration (demo)")
    args = parser.parse_args()

    if not args.skip_train:
        subprocess.run([sys.executable, "scripts/run_all.py", "--regenerate"], check=True, cwd=PROJECT_ROOT)

    truth = json.loads((DATA_DIR / "scenario_ground_truth.json").read_text(encoding="utf-8"))
    cases, evidence, analysis = CaseService.get_instance(), EvidenceService.get_instance(), AnalysisService.get_instance()

    case = cases.create_case(CaseCreate(
        title=args.title,
        description="Synthetic multimodal scenario: after-hours access, denied badge, tailgating, USB exfiltration.",
        metadata={"demo": True, "scenario": truth["scenario"], "ground_truth_entity": truth["malicious_entity"]},
    ))
    print(f"\n[demo] Case created: {case.case_id}")

    for file_name, source_type, meta in EVIDENCE:
        item = evidence.ingest_local_file(case.case_id, DATA_DIR / file_name, source_type=source_type,
                                          metadata=meta, actor="demo-script")
        print(f"[demo] Ingested {file_name:16s} as {source_type:15s} {item.file_hash[:23]}...")

    if args.video:
        meta = {
            "description": "CCTV clip analysed with TimeSformer",
            "recorded_at": args.video_start or truth["suggested_video_start_time"],
            "location_id": args.video_location or truth["suggested_video_location_id"],
        }
        evidence.ingest_local_file(case.case_id, Path(args.video), source_type="cctv_video", metadata=meta,
                                   actor="demo-script")
        print(f"[demo] Ingested video {args.video} (start {meta['recorded_at']}, {meta['location_id']})")

    run = analysis.start_run(AnalysisStartRequest(
        case_id=case.case_id, include_video=bool(args.video), video_max_seconds=args.video_max_seconds,
    ))
    print(f"[demo] Running analysis {run.run_id} ...")
    run = analysis.execute_run(run.run_id)
    assert run is not None
    print(f"[demo] Analysis {run.status}: {json.dumps(run.summary, indent=2)}")
    for result in run.evidence_results:
        print(f"         - {result.file_name}: {result.status} ({result.events} events) {result.message or ''}")

    suspects = analysis.read_output(case.case_id, "suspects") or []
    if suspects:
        top = suspects[0]
        print(f"\n[demo] Top suspect: {top['entity']} (score {top['aggregate_risk_score']}, "
              f"ground truth: {truth['malicious_entity']})")
    base = "http://localhost:8000/api"
    print("\n[demo] Start the API:  uvicorn app.main:app --app-dir backend --port 8000")
    print("[demo] Then open:      http://localhost:8000/docs")
    for path in (f"/cases/{case.case_id}/summary", f"/timeline/{case.case_id}", f"/anomalies/{case.case_id}",
                 f"/graph/{case.case_id}?format=cytoscape", f"/cases/{case.case_id}/suspects"):
        print(f"                     {base}{path}")


if __name__ == "__main__":
    main()
