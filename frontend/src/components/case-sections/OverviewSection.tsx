import { Activity, AlertTriangle, GitBranch, Play, ShieldCheck } from 'lucide-react';
import { StatusBadge } from '@/components/StatusBadge';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import type { AnalysisRun, CaseSummaryResponse } from '@/types/api';

export function OverviewSection({
  caseId,
  data,
  run,
  isRunActive,
  includeVideo,
  onIncludeVideoChange,
  onStartAnalysis,
  starting,
  runError,
  runQueryError,
}: {
  caseId: string;
  data: CaseSummaryResponse | undefined;
  run: AnalysisRun | null;
  isRunActive: boolean;
  includeVideo: boolean;
  onIncludeVideoChange: (value: boolean) => void;
  onStartAnalysis: () => void;
  starting: boolean;
  runError: string | null;
  runQueryError: string | null;
}) {
  const summary = data?.summary ?? {};
  const hasAnalysis = typeof summary.total_events === 'number';
  const evidenceResults = run?.evidence_results?.length
    ? run.evidence_results
    : data?.analysis?.evidence_results ?? [];
  const hasEvidenceResults = evidenceResults.length > 0;
  const evidenceProcessed = hasEvidenceResults
    ? evidenceResults.filter((item) => item.status.toLowerCase() === 'processed').length
    : summary.evidence_processed ?? 0;
  const evidenceSkipped = hasEvidenceResults
    ? evidenceResults.filter((item) => item.status.toLowerCase().includes('skip')).length
    : summary.evidence_skipped ?? 0;
  const evidenceErrors = hasEvidenceResults
    ? evidenceResults.filter((item) => ['error', 'failed'].includes(item.status.toLowerCase())).length
    : summary.evidence_errors ?? 0;
  const metrics = [
    { label: 'Events', value: summary.total_events ?? 0, icon: Activity },
    { label: 'Incident clusters', value: summary.incident_clusters ?? 0, icon: GitBranch },
    { label: 'Contradictions', value: summary.contradictions_detected ?? 0, icon: AlertTriangle },
    { label: 'Cross-modal clusters', value: summary.cross_modal_clusters ?? 0, icon: ShieldCheck },
  ];

  return (
    <div className="section-stack">
      <Card>
        <CardContent className="flex flex-col gap-4 py-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle>Analysis</CardTitle>
              {run && <StatusBadge status={run.status} />}
            </div>
            <CardDescription>
              {isRunActive ? 'Sentinel is processing the evidence for this case.' : hasAnalysis ? `Latest run ${run?.run_id ?? data?.case.last_analysis_run_id ?? ''}` : 'Run an analysis to process evidence and generate the timeline, anomalies, graph and entity leads.'}
            </CardDescription>
            {run?.error && <p className="text-xs text-destructive">{run.error}</p>}
            {runQueryError && <p className="text-xs text-destructive">{runQueryError}</p>}
            {runError && <p className="text-xs text-destructive">{runError}</p>}
          </div>
          <div className="flex flex-col gap-2 md:items-end">
            <Button onClick={onStartAnalysis} disabled={starting || isRunActive || !data?.case.evidence_count}>
              {isRunActive ? <><span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-r-transparent" /> Analysis running</> : <><Play className="h-3.5 w-3.5" /> Run analysis</>}
            </Button>
            <label className="flex cursor-pointer items-center gap-2 text-[11px] text-muted-foreground">
              <Checkbox checked={includeVideo} onCheckedChange={(checked) => onIncludeVideoChange(checked === true)} />
              Include raw CCTV video (CPU-intensive)
            </label>
          </div>
        </CardContent>
      </Card>

      {!data?.case.evidence_count && (
        <Alert variant="warning">Upload evidence before starting an analysis.</Alert>
      )}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(({ label, value, icon: Icon }) => (
          <Card key={label}>
            <CardContent className="flex items-center justify-between gap-3 p-4">
              <div><p className="text-xs text-muted-foreground">{label}</p><p className="mt-2 text-2xl font-semibold tracking-tight tabular-nums">{value}</p></div>
              <span className="rounded-lg border bg-muted/40 p-2.5 text-muted-foreground"><Icon className="h-4 w-4" /></span>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(280px,.75fr)]">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Processing summary</CardTitle>
            <CardDescription>Counts reported by the latest completed analysis.</CardDescription>
          </CardHeader>
          <CardContent>
            {hasAnalysis ? (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                <SummaryValue label="Validated events" value={summary.validated_events ?? summary.total_events ?? 0} />
                <SummaryValue label="Invalid events" value={summary.invalid_event_count ?? 0} />
                <SummaryValue label="Skipped events" value={summary.skipped_events ?? 0} />
                <SummaryValue label="Evidence processed" value={evidenceProcessed} />
                <SummaryValue label="Evidence skipped" value={evidenceSkipped} />
                <SummaryValue label="Evidence errors" value={evidenceErrors} />
              </div>
            ) : (
              <div className="py-5 text-sm text-muted-foreground">No completed analysis is available for this case.</div>
            )}
            {summary.sources_represented && summary.sources_represented.length > 0 && (
              <div className="mt-5 flex flex-wrap items-center gap-2 border-t pt-4">
                <span className="mr-1 text-[11px] text-muted-foreground">Sources</span>
                {summary.sources_represented.map((source) => <Badge key={source} variant="secondary" className="capitalize">{source}</Badge>)}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Leading entities</CardTitle>
            <CardDescription>Ranked leads from the latest correlation run.</CardDescription>
          </CardHeader>
          <CardContent>
            {data?.top_suspects?.length ? (
              <div className="space-y-3">
                {data.top_suspects.slice(0, 4).map((suspect) => (
                  <div key={suspect.entity} className="flex items-start justify-between gap-3 border-b pb-3 last:border-0 last:pb-0">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2"><span className="text-xs font-semibold">#{suspect.rank}</span><span className="truncate text-sm font-medium">{suspect.entity}</span></div>
                      <p className="mt-1 text-[11px] text-muted-foreground">{suspect.event_count} flagged events · {suspect.distinct_sources} sources</p>
                    </div>
                    <span className="whitespace-nowrap text-xs font-semibold tabular-nums">{suspect.aggregate_risk_score.toFixed(3)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-5 text-sm text-muted-foreground">Entity leads will appear after analysis.</div>
            )}
          </CardContent>
        </Card>
      </div>

      {run?.evidence_results && run.evidence_results.length > 0 && (
        <Card>
          <CardHeader className="pb-3"><CardTitle>Evidence processing</CardTitle><CardDescription>Per-file results from the latest analysis run.</CardDescription></CardHeader>
          <CardContent className="space-y-2">
            {run.evidence_results.map((item) => (
              <div key={item.evidence_id} className="flex flex-wrap items-center justify-between gap-3 border-b pb-2 last:border-0 last:pb-0">
                <div className="min-w-0"><p className="truncate text-xs font-medium">{item.file_name}</p><p className="text-[11px] text-muted-foreground">{item.processor} · {item.events} events</p>{item.message && <p className="mt-1 text-[11px] text-muted-foreground">{item.message}</p>}</div>
                <StatusBadge status={item.status} />
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <p className="text-[11px] text-muted-foreground">Case reference: <span className="font-mono">{caseId}</span>. Risk scores are investigative leads and are not findings of wrongdoing.</p>
    </div>
  );
}

function SummaryValue({ label, value }: { label: string; value: number }) {
  return <div className="rounded-lg border bg-muted/20 p-3"><p className="text-[11px] text-muted-foreground">{label}</p><p className="mt-1 text-lg font-semibold tabular-nums">{value}</p></div>;
}
