import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { EmptyState } from '@/components/EmptyState';
import { getErrorMessage, investigationApi } from '@/services/api';

export function TimelineSection({ caseId }: { caseId: string }) {
  const [source, setSource] = useState('all');
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const [actor, setActor] = useState('');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 100;
  const filters = useMemo(() => ({
    page,
    page_size: pageSize,
    source: source === 'all' ? undefined : source,
    flagged_only: flaggedOnly || undefined,
    actor_id: actor.trim() || undefined,
    from: from ? new Date(from).toISOString() : undefined,
    to: to ? new Date(to).toISOString() : undefined,
  }), [page, source, flaggedOnly, actor, from, to]);
  const timelineQuery = useQuery({ queryKey: ['timeline', caseId, filters], queryFn: () => investigationApi.timeline(caseId, filters) });
  const hasFilters = source !== 'all' || flaggedOnly || actor.trim() || from || to;

  function clearFilters() {
    setSource('all');
    setFlaggedOnly(false);
    setActor('');
    setFrom('');
    setTo('');
    setPage(1);
  }

  return (
    <div className="section-stack">
      <Card>
        <CardHeader className="pb-3"><CardTitle>Unified event timeline</CardTitle><CardDescription>Chronological events returned by the correlation pipeline.</CardDescription></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <div className="space-y-1.5"><Label>Source</Label><Select value={source} onValueChange={(value) => { setSource(value); setPage(1); }}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">All sources</SelectItem><SelectItem value="cyber">Cyber</SelectItem><SelectItem value="physical">Physical</SelectItem><SelectItem value="video">Video</SelectItem><SelectItem value="document">Document</SelectItem></SelectContent></Select></div>
            <div className="space-y-1.5"><Label htmlFor="timeline-actor">Entity / actor</Label><Input id="timeline-actor" value={actor} onChange={(event) => { setActor(event.target.value); setPage(1); }} placeholder="e.g. user_007" /></div>
            <div className="space-y-1.5"><Label htmlFor="timeline-from">From</Label><Input id="timeline-from" type="datetime-local" value={from} onChange={(event) => { setFrom(event.target.value); setPage(1); }} /></div>
            <div className="space-y-1.5"><Label htmlFor="timeline-to">To</Label><Input id="timeline-to" type="datetime-local" value={to} onChange={(event) => { setTo(event.target.value); setPage(1); }} /></div>
            <div className="flex items-end justify-between gap-2">
              <label className="flex h-9 cursor-pointer items-center gap-2 text-xs text-muted-foreground"><Checkbox checked={flaggedOnly} onCheckedChange={(checked) => { setFlaggedOnly(checked === true); setPage(1); }} /> Flagged only</label>
              {hasFilters && <Button variant="ghost" size="sm" onClick={clearFilters}>Clear</Button>}
            </div>
          </div>
          {timelineQuery.isError && <Alert variant="destructive">{getErrorMessage(timelineQuery.error)}</Alert>}
          {timelineQuery.isLoading ? <div className="space-y-3"><Skeleton className="h-10 w-full" /><Skeleton className="h-10 w-full" /><Skeleton className="h-10 w-full" /></div> : timelineQuery.data?.analyzed ? (
            timelineQuery.data.events.length ? (
              <>
                <div className="flex items-center justify-between text-[11px] text-muted-foreground"><span>{timelineQuery.data.total} matching events</span><span>Page {timelineQuery.data.page}</span></div>
                <Table>
                  <TableHeader><TableRow><TableHead>Time</TableHead><TableHead>Entity</TableHead><TableHead>Source</TableHead><TableHead>Event</TableHead><TableHead>Location</TableHead><TableHead>Signal</TableHead></TableRow></TableHeader>
                  <TableBody>
                    {timelineQuery.data.events.map((event) => (
                      <TableRow key={event.event_id}>
                        <TableCell className="whitespace-nowrap text-[11px] text-muted-foreground">{formatDate(event.timestamp)}</TableCell>
                        <TableCell><span className="text-xs font-medium">{event.canonical_entity || event.actor_id || 'Unknown'}</span></TableCell>
                        <TableCell><Badge variant="secondary" className="capitalize">{event.source}</Badge></TableCell>
                        <TableCell><div className="max-w-[230px]"><p className="truncate text-xs font-medium">{event.action || event.kind || 'Event'}</p><p className="truncate text-[10px] text-muted-foreground">{event.event_id}</p></div></TableCell>
                        <TableCell className="max-w-[150px] truncate text-xs text-muted-foreground">{event.location_id || '—'}</TableCell>
                        <TableCell>{event.prediction === 1 ? <Badge variant="warning">Flagged · {formatScore(event.score)}</Badge> : <span className="text-xs text-muted-foreground">Context</span>}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                <div className="flex items-center justify-between border-t pt-3">
                  <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>Previous</Button>
                  <span className="text-[11px] text-muted-foreground">Showing {timelineQuery.data.events.length} of {timelineQuery.data.total}</span>
                  <Button size="sm" variant="outline" disabled={page * pageSize >= timelineQuery.data.total} onClick={() => setPage((value) => value + 1)}>Next</Button>
                </div>
                {timelineQuery.data.skipped_events.length > 0 && <p className="text-[11px] text-muted-foreground">{timelineQuery.data.skipped_events.length} input events were skipped because they did not contain usable timestamps.</p>}
              </>
            ) : <EmptyState title="No events match these filters" description="Adjust the filters or clear them to view the full timeline." />
          ) : <EmptyState title="Analysis not run yet" description="Run analysis for this case to generate the unified event timeline." />}
        </CardContent>
      </Card>
    </div>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}
function formatScore(value?: number) {
  return typeof value === 'number' ? `${(value * 100).toFixed(0)}%` : '—';
}
