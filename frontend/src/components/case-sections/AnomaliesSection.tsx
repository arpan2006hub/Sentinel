import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { EmptyState } from '@/components/EmptyState';
import { StatusBadge } from '@/components/StatusBadge';
import { getErrorMessage, investigationApi } from '@/services/api';

export function AnomaliesSection({ caseId }: { caseId: string }) {
  const [severity, setSeverity] = useState('all');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const anomaliesQuery = useQuery({
    queryKey: ['anomalies', caseId, severity],
    queryFn: () => investigationApi.anomalies(caseId, { page: 1, page_size: 100, severity: severity === 'all' ? undefined : severity }),
  });
  const detailQuery = useQuery({
    queryKey: ['anomaly-detail', caseId, selectedId],
    queryFn: () => investigationApi.anomaly(caseId, selectedId!),
    enabled: Boolean(selectedId),
  });

  return (
    <div className="section-stack">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 border-b px-5 py-4">
          <div><CardTitle>Anomalies and contradictions</CardTitle><CardDescription className="mt-1">Signals detected by the correlation engine. Review the supporting context before drawing conclusions.</CardDescription></div>
          <Select value={severity} onValueChange={setSeverity}><SelectTrigger className="w-[145px]" aria-label="Filter anomaly severity"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">All severity</SelectItem><SelectItem value="critical">Critical</SelectItem><SelectItem value="high">High</SelectItem><SelectItem value="medium">Medium</SelectItem><SelectItem value="low">Low</SelectItem></SelectContent></Select>
        </CardHeader>
        {anomaliesQuery.isLoading ? <div className="space-y-3 p-5"><Skeleton className="h-10 w-full" /><Skeleton className="h-10 w-full" /></div> : anomaliesQuery.isError ? <div className="p-5"><Alert variant="destructive">{getErrorMessage(anomaliesQuery.error)}</Alert></div> : anomaliesQuery.data?.anomalies.length ? (
          <Table>
            <TableHeader><TableRow><TableHead>Severity</TableHead><TableHead>Type</TableHead><TableHead>Entity</TableHead><TableHead>Description</TableHead><TableHead /></TableRow></TableHeader>
            <TableBody>{anomaliesQuery.data.anomalies.map((item) => <TableRow key={item.anomaly_id}>
              <TableCell><StatusBadge status={item.severity} /></TableCell>
              <TableCell><span className="text-xs font-medium">{titleCase(item.type)}</span></TableCell>
              <TableCell className="text-xs">{item.entity || '—'}</TableCell>
              <TableCell><p className="max-w-[440px] text-xs leading-5 text-muted-foreground">{item.description}</p></TableCell>
              <TableCell><Button size="sm" variant="outline" onClick={() => setSelectedId(item.anomaly_id)}>Details</Button></TableCell>
            </TableRow>)}</TableBody>
          </Table>
        ) : <EmptyState title="No anomalies found" description="No anomalies were returned for this case and severity filter." />}
        <div className="border-t px-5 py-3 text-[11px] text-muted-foreground">{anomaliesQuery.data?.total ?? 0} anomalies</div>
      </Card>

      <Dialog open={Boolean(selectedId)} onOpenChange={(open) => { if (!open) setSelectedId(null); }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>Anomaly details</DialogTitle><DialogDescription>Supporting events and evidence references returned by Sentinel.</DialogDescription></DialogHeader>
          {detailQuery.isLoading ? <Skeleton className="h-24 w-full" /> : detailQuery.isError ? <Alert variant="destructive">{getErrorMessage(detailQuery.error)}</Alert> : detailQuery.data ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2"><StatusBadge status={detailQuery.data.severity} /><Badge variant="outline">{titleCase(detailQuery.data.type)}</Badge><span className="text-xs text-muted-foreground">{detailQuery.data.entity || 'Unknown entity'}</span></div>
              <p className="text-sm leading-6">{detailQuery.data.description}</p>
              <div className="grid gap-3 sm:grid-cols-2">
                <ReferenceList title="Event IDs" values={detailQuery.data.event_ids} />
                <ReferenceList title="Evidence IDs" values={detailQuery.data.evidence_ids} />
              </div>
              <div className="space-y-2"><h3 className="text-xs font-semibold">Supporting events</h3>{detailQuery.data.events.length ? detailQuery.data.events.map((event) => <div key={event.event_id} className="rounded-lg border p-3"><div className="flex flex-wrap justify-between gap-2"><span className="text-xs font-medium">{event.canonical_entity || event.actor_id || 'Unknown'}</span><span className="text-[11px] text-muted-foreground">{formatDate(event.timestamp)}</span></div><p className="mt-1 text-xs text-muted-foreground">{event.action || event.kind || event.source} · {event.location_id || 'No location'}</p><p className="mt-1 break-all font-mono text-[10px] text-muted-foreground">{event.event_id}</p></div>) : <p className="text-xs text-muted-foreground">No supporting events were returned.</p>}</div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function ReferenceList({ title, values }: { title: string; values: string[] }) {
  return <div className="space-y-2 rounded-lg border p-3"><h3 className="text-[11px] font-semibold text-muted-foreground">{title}</h3>{values.length ? <div className="space-y-1">{values.map((value) => <p key={value} className="break-all font-mono text-[10px]">{value}</p>)}</div> : <p className="text-xs text-muted-foreground">None</p>}</div>;
}
function titleCase(value: string) { return value.replace(/_/g, ' ').replace(/\b\w/g, (character: string) => character.toUpperCase()); }
function formatDate(value: string) { const date = new Date(value); return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }); }
