"""Case analysis orchestration: process every evidence item of a case into
canonical events, then run the multimodal correlation engine and store the
results under ``artifacts/cases/<case_id>/correlation/``.

Runs are executed as FastAPI background tasks (in-process thread). This keeps
the local-first demo free of Redis/Celery; the run record in SQLite gives the
frontend something to poll (``GET /api/analysis/{run_id}``).
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any, Optional

from ai.correlation.correlator import OUTPUT_FILES, MultimodalCorrelator
from ai.processing.processors import process_canonical_jsonl
from ai.processing.router import detect_processor, process_evidence_file
from app.config import get_settings
from app.db import connect, new_id, utcnow
from app.schemas.analysis import AnalysisRunListResponse, AnalysisRunResponse, AnalysisStartRequest
from app.services.evidence_service import EvidenceService

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = ("queued", "running")


class AnalysisAlreadyRunningError(RuntimeError):
    def __init__(self, run_id: str) -> None:
        super().__init__(f"An analysis run ({run_id}) is already queued or running for this case")
        self.run_id = run_id


class AnalysisService:
    _instance: Optional[AnalysisService] = None

    def __init__(self, db_path: Optional[str | Path] = None, artifacts_dir: Optional[str | Path] = None) -> None:
        settings = get_settings()
        self.db_path = Path(db_path) if db_path else settings.db_path
        self.artifacts_dir = Path(artifacts_dir) if artifacts_dir else settings.artifacts_dir
        self._recover_stale_runs()

    @classmethod
    def get_instance(cls) -> AnalysisService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ---------------------------------------------------------------- paths
    def case_output_dir(self, case_id: str) -> Path:
        return self.artifacts_dir / "cases" / case_id / "correlation"

    def read_output(self, case_id: str, name: str) -> Any:
        """Read one correlation output (see ``OUTPUT_FILES``) for a case, or None."""
        path = self.case_output_dir(case_id) / OUTPUT_FILES[name]
        if not path.is_file():
            return None
        if path.suffix == ".jsonl":
            return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return json.loads(path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------ runs
    def _recover_stale_runs(self) -> None:
        """Runs left 'running' by a previous process can never finish; mark them failed."""
        with connect(self.db_path) as conn:
            conn.execute(
                "UPDATE analysis_runs SET status = 'failed', finished_at = ?, "
                "error = 'Server restarted while the run was in progress' WHERE status IN ('queued', 'running')",
                (utcnow(),),
            )

    def start_run(self, request: AnalysisStartRequest) -> AnalysisRunResponse:
        with connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")  # check-then-insert must be atomic (double-clicked "Analyse")
            active = conn.execute(
                "SELECT run_id FROM analysis_runs WHERE case_id = ? AND status IN ('queued', 'running')",
                (request.case_id,),
            ).fetchone()
            if active:
                raise AnalysisAlreadyRunningError(active["run_id"])
            run_id = new_id()
            conn.execute(
                "INSERT INTO analysis_runs (run_id, case_id, status, created_at, options) VALUES (?, ?, 'queued', ?, ?)",
                (run_id, request.case_id, utcnow(), request.model_dump_json()),
            )
        run = self.get_run(run_id)
        assert run is not None
        return run

    def get_run(self, run_id: str) -> Optional[AnalysisRunResponse]:
        with connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM analysis_runs WHERE run_id = ?", (run_id,)).fetchone()
        return self._row_to_run(row) if row else None

    def list_runs(self, case_id: Optional[str] = None) -> AnalysisRunListResponse:
        with connect(self.db_path) as conn:
            if case_id:
                rows = conn.execute(
                    "SELECT * FROM analysis_runs WHERE case_id = ? ORDER BY created_at DESC", (case_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM analysis_runs ORDER BY created_at DESC").fetchall()
        runs = [self._row_to_run(r) for r in rows]
        return AnalysisRunListResponse(runs=runs, total=len(runs))

    def _update(self, run_id: str, **fields: Any) -> None:
        assignments = ", ".join(f"{k} = ?" for k in fields)
        values = [json.dumps(v, default=str) if isinstance(v, (dict, list)) else v for v in fields.values()]
        with connect(self.db_path) as conn:
            conn.execute(f"UPDATE analysis_runs SET {assignments} WHERE run_id = ?", (*values, run_id))

    # ------------------------------------------------------------- execution
    def execute_run(self, run_id: str) -> Optional[AnalysisRunResponse]:
        """Process all evidence for the run's case and correlate. Never raises."""
        run = self.get_run(run_id)
        if not run:
            return None
        options = AnalysisStartRequest(**run.options)
        self._update(run_id, status="running", started_at=utcnow())
        try:
            events, results = self._process_case_evidence(run.case_id, options)
            summary = self._correlate(run.case_id, events, options)
            summary["evidence_processed"] = sum(1 for r in results if r["status"] == "processed")
            summary["evidence_skipped"] = sum(1 for r in results if r["status"] == "skipped")
            summary["evidence_errors"] = sum(1 for r in results if r["status"] == "error")
            self._update(run_id, status="completed", finished_at=utcnow(), summary=summary, evidence_results=results)
        except Exception as err:  # pragma: no cover - defensive
            logger.exception("Analysis run %s failed", run_id)
            self._update(run_id, status="failed", finished_at=utcnow(), error=str(err))
        return self.get_run(run_id)

    def _process_case_evidence(
        self, case_id: str, options: AnalysisStartRequest
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        settings = get_settings()
        evidence_svc = EvidenceService.get_instance()
        events: list[dict[str, Any]] = []
        results: list[dict[str, Any]] = []
        for item in evidence_svc.list_evidence(case_id=case_id).evidence:
            path = evidence_svc.get_evidence_file_path(item.evidence_id)
            result = {"evidence_id": item.evidence_id, "file_name": item.file_name,
                      "source_type": item.source_type, "processor": "none", "status": "error", "events": 0,
                      "message": None}
            if path is None:
                result["message"] = "Evidence file missing from storage"
                results.append(result)
                evidence_svc.set_processing_status(item.evidence_id, "error", {"message": result["message"]})
                continue
            processor = detect_processor(item.source_type, path)
            result["processor"] = processor
            evidence_svc.set_processing_status(item.evidence_id, "processing")
            try:
                if processor == "video":
                    if not options.include_video:
                        result.update(status="skipped", message="Video analysis disabled for this run (include_video=false)")
                        new_events: list[dict[str, Any]] = []
                    else:
                        new_events, message = self._process_video(case_id, item, path, options)
                        result.update(status="processed", message=message)
                elif processor == "unsupported":
                    new_events = []
                    result.update(status="skipped", message=f"No processor for source_type '{item.source_type}' "
                                                          f"({path.suffix}); file is stored and hashed only")
                else:
                    new_events = process_evidence_file(
                        path, item.source_type, source_id=item.evidence_id, case_id=case_id,
                        metadata=item.metadata,
                        cyber_model_path=settings.cyber_model_path,
                        document_model_path=settings.document_model_path,
                        video_features_model_path=settings.video_features_model_path,
                    )
                    result["status"] = "processed"
                result["events"] = len(new_events)
                events.extend(new_events)
            except Exception as err:
                logger.warning("Processing evidence %s failed: %s", item.evidence_id, err)
                result.update(status="error", message=str(err))
            evidence_svc.set_processing_status(
                item.evidence_id, result["status"], {"events": result["events"], "message": result["message"]}
            )
            results.append(result)
        return events, results

    def _process_video(
        self, case_id: str, item: Any, path: Path, options: AnalysisStartRequest
    ) -> tuple[list[dict[str, Any]], Optional[str]]:
        from app.services.video_service import VideoAnalysisService

        service = VideoAnalysisService.get_instance()
        analysis = service.analyze_file(
            path, case_id=case_id,
            location_id=item.metadata.get("location_id"),
            evidence_id=item.evidence_id,
            threshold=options.video_threshold,
            window_seconds=options.video_window_seconds,
            stride_seconds=options.video_stride_seconds,
            start_time=item.metadata.get("recorded_at"),
            max_seconds=options.video_max_seconds,
        )
        out_dir = self.artifacts_dir / "cases" / case_id / "video"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{item.evidence_id}.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
        events_file = out_dir / f"{item.evidence_id}.events.jsonl"
        events_file.write_text("".join(json.dumps(e) + "\n" for e in analysis["canonical_events"]), encoding="utf-8")
        if analysis.get("timestamp_is_estimated"):
            # Without recorded_at the detector can only stamp "now"; correlating invented
            # times would create false after-hours / travel / badge contradictions.
            return [], ("Video analysed, but its events were left out of correlation: set evidence metadata "
                        "'recorded_at' (time of the first frame) to align it with other evidence")
        return process_canonical_jsonl(events_file, source_id=item.evidence_id, case_id=case_id), None

    def _correlate(self, case_id: str, events: list[dict[str, Any]], options: AnalysisStartRequest) -> dict[str, Any]:
        # Write into a staging directory and swap it in only on success, so the previous
        # results stay readable while a re-run is in progress and survive a failed run.
        final_dir = self.case_output_dir(case_id)
        out_dir = final_dir.with_name("correlation.staging")
        shutil.rmtree(out_dir, ignore_errors=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        summary = self._write_correlation(case_id, events, options, out_dir)
        old_dir = final_dir.with_name("correlation.old")
        shutil.rmtree(old_dir, ignore_errors=True)
        if final_dir.exists():
            final_dir.rename(old_dir)
        out_dir.rename(final_dir)
        shutil.rmtree(old_dir, ignore_errors=True)
        return summary

    def _write_correlation(
        self, case_id: str, events: list[dict[str, Any]], options: AnalysisStartRequest, out_dir: Path
    ) -> dict[str, Any]:
        if not events:
            summary = {"case_id": case_id, "total_events": 0, "skipped_events": 0, "incident_clusters": 0,
                       "cross_modal_clusters": 0, "contradictions_detected": 0, "graph_nodes": 0, "graph_edges": 0,
                       "ranked_suspects": 0, "top_suspect": None, "sources_represented": []}
            empty = {
                "timeline": {"events": [], "clusters": [], "contradictions": [], "skipped_events": [], "summary": summary},
                "graph": {"nodes": [], "edges": [], "metrics": {"total_nodes": 0, "total_edges": 0}},
                "cytoscape": {"elements": {"nodes": [], "edges": []}},
                "contradictions": [], "suspects": [], "summary": summary,
            }
            for name, payload in empty.items():
                (out_dir / OUTPUT_FILES[name]).write_text(json.dumps(payload, indent=2), encoding="utf-8")
            (out_dir / OUTPUT_FILES["events"]).write_text("", encoding="utf-8")
            return summary
        correlator = MultimodalCorrelator(window_minutes=options.window_minutes)
        return correlator.run_correlation(events, output_dir=out_dir, case_id=case_id)["summary"]

    @staticmethod
    def _row_to_run(row: Any) -> AnalysisRunResponse:
        return AnalysisRunResponse(
            run_id=row["run_id"], case_id=row["case_id"], status=row["status"], created_at=row["created_at"],
            started_at=row["started_at"], finished_at=row["finished_at"],
            options=json.loads(row["options"] or "{}"), summary=json.loads(row["summary"] or "{}"),
            evidence_results=json.loads(row["evidence_results"] or "[]"), error=row["error"],
        )
