import axios, { type AxiosError, type AxiosRequestConfig } from 'axios';
import type {
  AnalysisRun,
  AnomalyDetail,
  AnomalyResponse,
  AuditChainVerifyResponse,
  CaseListResponse,
  CaseSummaryResponse,
  EvidenceAuditRecord,
  EvidenceItem,
  EvidenceListResponse,
  EvidenceVerifyResponse,
  GraphResponse,
  HealthResponse,
  InvestigationCase,
  SourceTypeInfo,
  TimelineCluster,
  TimelineFilters,
  TimelineResponse,
} from '@/types/api';

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(/\/$/, '');
const API_ORIGIN = API_BASE_URL.replace(/\/api$/, '');

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
  headers: { Accept: 'application/json' },
});

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail: unknown = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map((item: { msg?: string }) => item.msg || JSON.stringify(item)).join(', ');
    }
    if (detail && typeof detail === 'object' && 'message' in detail) {
      return String((detail as { message: unknown }).message);
    }
    if (error.code === 'ECONNABORTED') return 'The request timed out. Check the API and try again.';
    if (!error.response) return 'Cannot reach the Sentinel API. Check that the backend is running.';
    return error.message || 'The request failed.';
  }
  return error instanceof Error ? error.message : 'An unexpected error occurred.';
}

export function getConflictRunId(error: unknown): string | null {
  if (!axios.isAxiosError(error)) return null;
  const detail = error.response?.data?.detail;
  return detail && typeof detail === 'object' && 'run_id' in detail
    ? String((detail as { run_id: unknown }).run_id)
    : null;
}

export const caseApi = {
  list: async (params: { page?: number; page_size?: number; status?: string } = {}) =>
    (await api.get<CaseListResponse>('/cases', { params: { page: 1, page_size: 100, ...params } })).data,
  create: async (payload: { title: string; description: string }) =>
    (await api.post<InvestigationCase>('/cases', payload)).data,
  getSummary: async (caseId: string) =>
    (await api.get<CaseSummaryResponse>(`/cases/${caseId}/summary`)).data,
  update: async (caseId: string, payload: Partial<Pick<InvestigationCase, 'title' | 'description' | 'status'>>) =>
    (await api.patch<InvestigationCase>(`/cases/${caseId}`, payload)).data,
};

export const evidenceApi = {
  list: async (caseId: string) =>
    (await api.get<EvidenceListResponse>('/evidence', { params: { case_id: caseId } })).data,
  sourceTypes: async () => (await api.get<SourceTypeInfo[]>('/evidence/source-types')).data,
  upload: async (caseId: string, sourceType: string, file: File, metadata: Record<string, string>) => {
    const body = new FormData();
    body.append('case_id', caseId);
    body.append('source_type', sourceType);
    body.append('file', file);
    if (Object.keys(metadata).length) body.append('metadata', JSON.stringify(metadata));
    return (await api.post<EvidenceItem>('/evidence', body, { timeout: 120_000 })).data;
  },
  verify: async (evidenceId: string) =>
    (await api.get<EvidenceVerifyResponse>(`/evidence/${evidenceId}/verify`)).data,
  audit: async (evidenceId: string) =>
    (await api.get<EvidenceAuditRecord[]>(`/evidence/${evidenceId}/audit`)).data,
  verifyAudit: async (evidenceId: string) =>
    (await api.get<AuditChainVerifyResponse>(`/evidence/${evidenceId}/audit/verify`)).data,
  download: async (evidenceId: string, config?: AxiosRequestConfig) =>
    api.get<Blob>(`/evidence/${evidenceId}/file`, { responseType: 'blob', ...config }),
};

export const analysisApi = {
  start: async (caseId: string, includeVideo: boolean) =>
    (await api.post<AnalysisRun>('/analysis/start', { case_id: caseId, include_video: includeVideo })).data,
  get: async (runId: string) => (await api.get<AnalysisRun>(`/analysis/${runId}`)).data,
  list: async (caseId: string) =>
    (await api.get<{ runs: AnalysisRun[]; total: number }>('/analysis', { params: { case_id: caseId } })).data,
};

export const investigationApi = {
  timeline: async (caseId: string, filters: TimelineFilters = {}) =>
    (await api.get<TimelineResponse>(`/timeline/${caseId}`, { params: filters })).data,
  clusters: async (caseId: string, crossModalOnly = true) =>
    (await api.get<{ case_id: string; clusters: TimelineCluster[]; total: number }>(`/timeline/${caseId}/clusters`, { params: { cross_modal_only: crossModalOnly } })).data,
  anomalies: async (caseId: string, filters: { page?: number; page_size?: number; severity?: string; type?: string; entity?: string } = {}) =>
    (await api.get<AnomalyResponse>(`/anomalies/${caseId}`, { params: filters })).data,
  anomaly: async (caseId: string, anomalyId: string) =>
    (await api.get<AnomalyDetail>(`/anomalies/${caseId}/${anomalyId}`)).data,
  graph: async (caseId: string) =>
    (await api.get<GraphResponse>(`/graph/${caseId}`, { params: { format: 'cytoscape' } })).data,
  suspects: async (caseId: string) =>
    (await api.get<{ case_id: string; suspects: CaseSummaryResponse['top_suspects']; total: number }>(`/cases/${caseId}/suspects`)).data,
};

export async function getHealth(): Promise<HealthResponse> {
  return (await axios.get<HealthResponse>(`${API_ORIGIN}/health`, { timeout: 5_000 })).data;
}

export async function downloadEvidence(evidenceId: string, fileName: string): Promise<void> {
  const response = await evidenceApi.download(evidenceId);
  const url = URL.createObjectURL(response.data);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function isAxiosError(error: unknown): error is AxiosError {
  return axios.isAxiosError(error);
}
