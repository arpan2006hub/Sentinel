import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/EmptyState';
import { getErrorMessage, investigationApi } from '@/services/api';

export function LeadsSection({ caseId }: { caseId: string }) {
  const [expandedEntity, setExpandedEntity] = useState<string | null>(null);
  const suspectsQuery = useQuery({ queryKey: ['suspects', caseId], queryFn: () => investigationApi.suspects(caseId) });

  return (
    <Card>
      <CardHeader className="border-b px-5 py-4">
        <CardTitle>Ranked entity leads</CardTitle>
        <CardDescription className="mt-1">Risk scores help prioritise review. They are investigative leads, not findings of wrongdoing.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2 p-3 sm:p-4">
        {suspectsQuery.isLoading ? (
          <div className="space-y-3"><Skeleton className="h-20 w-full" /><Skeleton className="h-20 w-full" /></div>
        ) : suspectsQuery.isError ? (
          <Alert variant="destructive">{getErrorMessage(suspectsQuery.error)}</Alert>
        ) : suspectsQuery.data?.suspects.length ? (
          suspectsQuery.data.suspects.map((suspect) => {
            const expanded = expandedEntity === suspect.entity;
            return (
              <section key={suspect.entity} className="overflow-hidden rounded-lg border bg-card">
                <Button
                  type="button"
                  variant="ghost"
                  className="h-auto w-full justify-between rounded-none px-3 py-3 text-left hover:bg-muted/40 sm:px-4"
                  aria-expanded={expanded}
                  onClick={() => setExpandedEntity(expanded ? null : suspect.entity)}
                >
                  <span className="flex min-w-0 items-center gap-3">
                    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-muted text-xs font-semibold tabular-nums">{suspect.rank}</span>
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-semibold text-foreground">{suspect.entity}</span>
                      <span className="mt-0.5 block text-[11px] text-muted-foreground">
                        {suspect.event_count} flagged events · {suspect.distinct_sources} {suspect.distinct_sources === 1 ? 'source' : 'sources'}
                      </span>
                    </span>
                  </span>
                  <span className="flex shrink-0 items-center gap-3 sm:gap-5">
                    <span className="text-right">
                      <span className="block text-base font-semibold tabular-nums text-foreground">{suspect.aggregate_risk_score.toFixed(3)}</span>
                      <span className="block text-[10px] text-muted-foreground">Aggregate risk score</span>
                    </span>
                    {expanded ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
                  </span>
                </Button>

                <div className="flex flex-wrap items-center gap-1.5 border-t bg-muted/10 px-3 py-2 sm:px-4">
                  {suspect.sources.map((source) => <Badge key={source} variant="secondary" className="capitalize">{source}</Badge>)}
                  <Badge variant="outline">{suspect.contradiction_count} contradictions</Badge>
                  <Badge variant="outline">Max signal {(suspect.max_score * 100).toFixed(0)}%</Badge>
                  <span className="ml-auto text-[10px] text-muted-foreground">
                    {suspect.event_ids.length} events · {suspect.evidence_ids.length} evidence · {suspect.anomaly_ids.length} anomalies
                  </span>
                </div>

                {expanded && (
                  <div className="space-y-4 border-t px-3 py-4 sm:px-4">
                    <div className="space-y-2">
                      <h4 className="text-xs font-semibold">Why this entity was ranked</h4>
                      {suspect.reasons.length ? (
                        <ul className="space-y-2">
                          {suspect.reasons.map((reason, index) => (
                            <li key={`${suspect.entity}-${index}`} className="border-l-2 border-muted pl-3 text-xs leading-5 text-muted-foreground">{reason}</li>
                          ))}
                        </ul>
                      ) : <p className="text-xs text-muted-foreground">No explanation was returned for this entity.</p>}
                    </div>
                    <div className="grid gap-3 border-t pt-3 md:grid-cols-3">
                      <ReferenceBlock title="Event IDs" ids={suspect.event_ids} />
                      <ReferenceBlock title="Evidence IDs" ids={suspect.evidence_ids} />
                      <ReferenceBlock title="Anomaly IDs" ids={suspect.anomaly_ids} />
                    </div>
                  </div>
                )}
              </section>
            );
          })
        ) : <EmptyState title="No entity leads available" description="Ranked entity leads will appear after a completed analysis." />}
      </CardContent>
    </Card>
  );
}

function ReferenceBlock({ title, ids }: { title: string; ids: string[] }) {
  return (
    <div className="min-w-0">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{title} · {ids.length}</p>
      {ids.length ? (
        <div className="max-h-28 space-y-1.5 overflow-auto rounded-md bg-muted/30 p-2">
          {ids.map((id) => <p key={id} className="break-all font-mono text-[10px] leading-4 text-muted-foreground">{id}</p>)}
        </div>
      ) : <p className="text-xs text-muted-foreground">No linked records</p>}
    </div>
  );
}
