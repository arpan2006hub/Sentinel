export type CaseStatus = 'open' | 'investigating' | 'closed' | 'archived';
export type RunStatus = 'queued' | 'running' | 'completed' | 'failed';

export interface InvestigationCase {
  case_id: string;
  title: string;
  description: string;
  status: CaseStatus | string;
  evidence_count: number;
  event_count: number;
  anomaly_count: number;
  last_analysis_run_id?: string | null;
  last_analysis_status?: string | null;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
}

export interface CaseListResponse {
  cases: InvestigationCase[];
  total: number;
  page: number;
  page_size: number;
}

export interface AnalysisSummary {
  total_events?: number;
  input_events?: number;
  validated_events?: number;
  invalid_event_count?: number;
  skipped_events?: number;
  incident_clusters?: number;
  cross_modal_clusters?: number;
  contradictions_detected?: number;
  graph_nodes?: number;
  graph_edges?: number;
  ranked_suspects?: number;
  top_suspect?: string | null;
  sources_represented?: string[];
  evidence_processed?: number;
  evidence_skipped?: number;
  evidence_errors?: number;
}

export interface AnalysisEvidenceResult {
  evidence_id: string;
  file_name: string;
  source_type: string;
  processor: string;
  status: string;
  events: number;
  message?: string | null;
}

export interface AnalysisRun {
  run_id: string;
  case_id: string;
  status: RunStatus | string;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  options: Record<string, unknown>;
  summary: AnalysisSummary;
  evidence_results: AnalysisEvidenceResult[];
  error?: string | null;
}

export interface Suspect {
  entity: string;
  rank: number;
  event_count: number;
  distinct_sources: number;
  sources: string[];
  max_score: number;
  contradiction_count: number;
  aggregate_risk_score: number;
  event_ids: string[];
  evidence_ids: string[];
  anomaly_ids: string[];
  reasons: string[];
}

export interface CaseSummaryResponse {
  case: InvestigationCase;
  analysis: AnalysisRun | null;
  summary: AnalysisSummary;
  top_suspects: Suspect[];
  anomalies_by_severity: Record<string, number>;
  evidence_by_status: Record<string, number>;
}

export interface EvidenceItem {
  evidence_id: string;
  case_id: string;
  file_name: string;
  file_hash: string;
  file_size_bytes: number;
  source_type: string;
  processing_status: string;
  ingested_at: string;
  metadata: Record<string, unknown>;
}

export interface EvidenceListResponse {
  evidence: EvidenceItem[];
  total: number;
}

export interface SourceTypeInfo {
  source_type: string;
  processor: string;
  description: string;
}

export interface EvidenceVerifyResponse {
  evidence_id: string;
  file_name: string;
  stored_hash: string;
  computed_hash: string;
  integrity: string;
  checked_at: string;
  message?: string | null;
}

export interface EvidenceAuditRecord {
  audit_id: string;
  evidence_id: string;
  case_id: string;
  action: string;
  actor: string;
  timestamp: string;
  details: Record<string, unknown>;
  prev_hash?: string | null;
  record_hash?: string | null;
}

export interface AuditChainVerifyResponse {
  evidence_id: string;
  valid: boolean;
  records: number;
  legacy_unverifiable: number;
  broken_at_index?: number | null;
  broken_audit_id?: string | null;
  reason?: string | null;
}

export interface TimelineEvent {
  event_id: string;
  case_id: string;
  timestamp: string;
  timestamp_end?: string | null;
  source: string;
  source_type: string;
  source_id?: string | null;
  actor_id?: string | null;
  canonical_entity?: string | null;
  entity_resolution_confidence?: number;
  action?: string | null;
  kind?: string | null;
  location_id?: string | null;
  object_id?: string | null;
  score?: number;
  confidence?: number;
  prediction?: number;
  details?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface TimelineResponse {
  case_id: string;
  analyzed: boolean;
  events: TimelineEvent[];
  total: number;
  page: number;
  page_size: number;
  summary: Record<string, unknown>;
  skipped_events: unknown[];
}

export interface TimelineCluster {
  cluster_id: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  entities: string[];
  known_entities: string[];
  sources: string[];
  is_cross_modal: boolean;
  max_score: number;
  event_count: number;
  event_ids: string[];
}

export interface Anomaly {
  anomaly_id: string;
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical' | string;
  entity?: string | null;
  description: string;
  event_ids: string[];
  time_window_seconds?: number;
}

export interface AnomalyDetail extends Anomaly {
  case_id: string;
  events: TimelineEvent[];
  evidence_ids: string[];
}

export interface AnomalyResponse {
  anomalies: Anomaly[];
  total: number;
  page: number;
  page_size: number;
  case_id: string;
}

export interface GraphNode {
  data: {
    id: string;
    label?: string;
    type?: string;
    resolved_id?: string;
    [key: string]: unknown;
  };
}

export interface GraphEdge {
  data: {
    id: string;
    source: string;
    target: string;
    label?: string;
    weight?: number;
    [key: string]: unknown;
  };
}

export interface GraphResponse {
  case_id: string;
  analyzed: boolean;
  elements: { nodes: GraphNode[]; edges: GraphEdge[] };
}

export interface HealthResponse {
  status: string;
  api: string;
  database: string;
  storage: string;
  video_model?: string;
  storage_path?: string;
  artifacts_dir?: string;
}

export interface TimelineFilters {
  page?: number;
  page_size?: number;
  actor_id?: string;
  source?: string;
  source_type?: string;
  flagged_only?: boolean;
  from?: string;
  to?: string;
}
