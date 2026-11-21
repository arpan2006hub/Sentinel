import { lazy, Suspense, useEffect, useState } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, FileText, Network, ShieldAlert, Users, Clock3, FolderOpen, LoaderCircle } from 'lucide-react';
import { StatusBadge } from '@/components/StatusBadge';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { analysisApi, caseApi, getConflictRunId, getErrorMessage } from '@/services/api';
import type { AnalysisRun, CaseStatus } from '@/types/api';


const OverviewSection = lazy(() =>
  import('@/components/case-sections/OverviewSection').then((module) => ({ default: module.OverviewSection })),
);
const EvidenceSection = lazy(() =>
  import('@/components/case-sections/EvidenceSection').then((module) => ({ default: module.EvidenceSection })),
);
const TimelineSection = lazy(() =>
  import('@/components/case-sections/TimelineSection').then((module) => ({ default: module.TimelineSection })),
);
const AnomaliesSection = lazy(() =>
  import('@/components/case-sections/AnomaliesSection').then((module) => ({ default: module.AnomaliesSection })),
);
const GraphSection = lazy(() =>
  import('@/components/case-sections/GraphSection').then((module) => ({ default: module.GraphSection })),
);
const LeadsSection = lazy(() =>
  import('@/components/case-sections/LeadsSection').then((module) => ({ default: module.LeadsSection })),
);
const sections = [
  { id: 'overview', label: 'Overview', icon: FolderOpen },
  { id: 'evidence', label: 'Evidence', icon: FileText },
  { id: 'timeline', label: 'Timeline', icon: Clock3 },
  { id: 'anomalies', label: 'Anomalies', icon: ShieldAlert },
  { id: 'graph', label: 'Graph', icon: Network },
  { id: 'leads', label: 'Entity leads', icon: Users },
] as const;

export function CasePage() {
  const { caseId, section = 'overview' } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [includeVideo, setIncludeVideo] = useState(false);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  const summaryQuery = useQuery({
    queryKey: ['case-summary', caseId],
    queryFn: () => caseApi.getSummary(caseId!),
    enabled: Boolean(caseId),
    refetchInterval: 20_000,
  });

  const currentCase = summaryQuery.data?.case;
  const inferredActiveRunId = summaryQuery.data?.analysis && ['queued', 'running'].includes(summaryQuery.data.analysis.status)
    ? summaryQuery.data.analysis.run_id
    : null;
  const runId = activeRunId ?? inferredActiveRunId;

  const runQuery = useQuery({
    queryKey: ['analysis-run', runId],
    queryFn: () => analysisApi.get(runId!),
    enabled: Boolean(runId),
    refetchInterval: (query) => ['completed', 'failed'].includes(query.state.data?.status ?? '') ? false : 1_500,
  });

  const startMutation = useMutation({
    mutationFn: () => analysisApi.start(caseId!, includeVideo),
    onSuccess: (run) => {
      setActiveRunId(run.run_id);
      setRunError(null);
    },
    onError: (error: unknown) => {
      const conflictRunId = getConflictRunId(error);
      if (conflictRunId) {
        setActiveRunId(conflictRunId);
        setRunError('An analysis is already active. Its status is shown below.');
      } else {
        setRunError(getErrorMessage(error));
      }
    },
  });

  const statusMutation = useMutation({
    mutationFn: (status: CaseStatus) => caseApi.update(caseId!, { status }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['case-summary', caseId] });
      await queryClient.invalidateQueries({ queryKey: ['cases'] });
    },
  });

  const runStatus = runQuery.data?.status;
  useEffect(() => {
    if (runStatus === 'completed' || runStatus === 'failed') {
      void queryClient.invalidateQueries({ queryKey: ['case-summary', caseId] });
      void queryClient.invalidateQueries({ queryKey: ['evidence', caseId] });
      void queryClient.invalidateQueries({ queryKey: ['timeline', caseId] });
      void queryClient.invalidateQueries({ queryKey: ['anomalies', caseId] });
      void queryClient.invalidateQueries({ queryKey: ['graph', caseId] });
      void queryClient.invalidateQueries({ queryKey: ['suspects', caseId] });
    }
  }, [runStatus, queryClient, caseId]);

  if (!caseId) return <Navigate to="/" replace />;
  if (!sections.some((item) => item.id === section)) return <Navigate to={`/cases/${caseId}/overview`} replace />;

  const displayedRun: AnalysisRun | null = runQuery.data ?? summaryQuery.data?.analysis ?? null;
  const isRunActive = Boolean(displayedRun && ['queued', 'running'].includes(displayedRun.status));

  return (
    <div className="page-stack">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Link to="/" className="inline-flex items-center gap-1.5 hover:text-foreground"><ArrowLeft className="h-3.5 w-3.5" /> Cases</Link>
        <span>/</span>
        <span>Investigation</span>
      </div>

      {summaryQuery.isLoading ? (
        <div className="space-y-3"><Skeleton className="h-8 w-1/2" /><Skeleton className="h-4 w-2/3" /></div>
      ) : summaryQuery.isError ? (
        <Alert variant="destructive" className="flex items-center justify-between gap-4">
          <span>{getErrorMessage(summaryQuery.error)}</span>
          <Button size="sm" variant="outline" onClick={() => summaryQuery.refetch()}>Retry</Button>
        </Alert>
      ) : currentCase ? (
        <>
          <section className="flex flex-col justify-between gap-4 border-b pb-5 md:flex-row md:items-start">
            <div className="min-w-0 space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="break-words text-2xl font-semibold tracking-tight">{currentCase.title}</h1>
                <StatusBadge status={currentCase.status} />
              </div>
              <p className="max-w-3xl text-sm leading-6 text-muted-foreground">{currentCase.description || 'No case description provided.'}</p>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
                <span className="font-mono">{currentCase.case_id}</span>
                <span>Updated {formatDate(currentCase.updated_at)}</span>
                <span>{currentCase.evidence_count} evidence items</span>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <Select value={currentCase.status} disabled={statusMutation.isPending} onValueChange={(value) => statusMutation.mutate(value as CaseStatus)}>
                <SelectTrigger className="w-[150px]" aria-label="Update case status"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="open">Open</SelectItem>
                  <SelectItem value="investigating">Investigating</SelectItem>
                  <SelectItem value="closed">Closed</SelectItem>
                  <SelectItem value="archived">Archived</SelectItem>
                </SelectContent>
              </Select>
              {statusMutation.isPending && <LoaderCircle className="h-4 w-4 animate-spin text-muted-foreground" />}
            </div>
          </section>
          {statusMutation.isError && <Alert variant="destructive">{getErrorMessage(statusMutation.error)}</Alert>}

          <Tabs value={section} onValueChange={(value) => navigate(`/cases/${caseId}/${value}`)}>
            <TabsList className="case-tabs">
              {sections.map(({ id, label, icon: Icon }) => (
                <TabsTrigger key={id} value={id} className="case-tab"><Icon className="h-3.5 w-3.5" />{label}</TabsTrigger>
              ))}
            </TabsList>
            <TabsContent value="overview">
              <Suspense fallback={<SectionFallback />}>
                <OverviewSection
                  caseId={caseId}
                  data={summaryQuery.data}
                  run={displayedRun}
                  isRunActive={isRunActive}
                  includeVideo={includeVideo}
                  onIncludeVideoChange={setIncludeVideo}
                  onStartAnalysis={() => { setRunError(null); startMutation.mutate(); }}
                  starting={startMutation.isPending}
                  runError={runError}
                  runQueryError={runQuery.isError ? getErrorMessage(runQuery.error) : null}
                />
              </Suspense>
            </TabsContent>
            <TabsContent value="evidence"><Suspense fallback={<SectionFallback />}><EvidenceSection caseId={caseId} /></Suspense></TabsContent>
            <TabsContent value="timeline"><Suspense fallback={<SectionFallback />}><TimelineSection caseId={caseId} /></Suspense></TabsContent>
            <TabsContent value="anomalies"><Suspense fallback={<SectionFallback />}><AnomaliesSection caseId={caseId} /></Suspense></TabsContent>
            <TabsContent value="graph"><Suspense fallback={<SectionFallback />}><GraphSection caseId={caseId} /></Suspense></TabsContent>
            <TabsContent value="leads"><Suspense fallback={<SectionFallback />}><LeadsSection caseId={caseId} /></Suspense></TabsContent>
          </Tabs>
        </>
      ) : null}
    </div>
  );
}

function SectionFallback() {
  return (
    <div className="space-y-3" role="status" aria-label="Loading section">
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-40 w-full" />
    </div>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}
