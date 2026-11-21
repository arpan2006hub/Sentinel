import { useMemo, useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Plus, Search } from 'lucide-react';
import { EmptyState } from '@/components/EmptyState';
import { StatusBadge } from '@/components/StatusBadge';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Textarea } from '@/components/ui/textarea';
import { caseApi, getErrorMessage } from '@/services/api';
import type { InvestigationCase } from '@/types/api';

const EMPTY_CASES: InvestigationCase[] = [];

export function DashboardPage() {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('all');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');

  const casesQuery = useQuery({
    queryKey: ['cases'],
    queryFn: () => caseApi.list({ page: 1, page_size: 100 }),
    refetchInterval: 30_000,
  });
  const createMutation = useMutation({
    mutationFn: caseApi.create,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['cases'] });
      setCreateOpen(false);
      setTitle('');
      setDescription('');
    },
  });

  const cases = casesQuery.data?.cases ?? EMPTY_CASES;
  const filteredCases = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return cases.filter((item) => {
      const matchesText = !needle || `${item.title} ${item.description} ${item.case_id}`.toLowerCase().includes(needle);
      return matchesText && (status === 'all' || item.status === status);
    });
  }, [cases, search, status]);

  function createCase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanTitle = title.trim();
    if (!cleanTitle) return;
    createMutation.mutate({ title: cleanTitle, description: description.trim() });
  }

  return (
    <div className="page-stack">
      <section className="page-heading">
        <div>
          <div className="page-kicker">Workspace</div>
          <h1>Cases</h1>
          <p>Manage investigations and review evidence collected by Sentinel.</p>
        </div>
        <Button onClick={() => setCreateOpen(true)}><Plus className="h-4 w-4" /> New case</Button>
      </section>

      {casesQuery.isError && (
        <Alert variant="destructive" className="flex items-center justify-between gap-4">
          <span>{getErrorMessage(casesQuery.error)}</span>
          <Button size="sm" variant="outline" onClick={() => casesQuery.refetch()}>Retry</Button>
        </Alert>
      )}

      <Card>
        <CardHeader className="border-b px-5 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle>All investigations</CardTitle>
              <CardDescription className="mt-1">Cases returned by the local Sentinel API.</CardDescription>
            </div>
            <Badge variant="outline">{casesQuery.data?.total ?? 0} cases</Badge>
          </div>
        </CardHeader>
        <div className="flex flex-wrap items-center gap-3 border-b px-5 py-3">
          <div className="relative min-w-[220px] flex-1 sm:max-w-sm">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search cases" className="pl-9" aria-label="Search cases" />
          </div>
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="w-[170px]" aria-label="Filter cases by status"><SelectValue placeholder="All statuses" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="open">Open</SelectItem>
              <SelectItem value="investigating">Investigating</SelectItem>
              <SelectItem value="closed">Closed</SelectItem>
              <SelectItem value="archived">Archived</SelectItem>
            </SelectContent>
          </Select>
          {(search || status !== 'all') && <Button variant="ghost" size="sm" onClick={() => { setSearch(''); setStatus('all'); }}>Clear filters</Button>}
        </div>

        {casesQuery.isLoading ? (
          <div className="space-y-3 p-5"><Skeleton className="h-10 w-full" /><Skeleton className="h-10 w-full" /><Skeleton className="h-10 w-full" /></div>
        ) : filteredCases.length === 0 ? (
          <EmptyState
            title={cases.length ? 'No matching cases' : 'No cases yet'}
            description={cases.length ? 'Change the search or status filter.' : 'Create an investigation case to start collecting evidence.'}
            action={!cases.length ? <Button size="sm" onClick={() => setCreateOpen(true)}><Plus className="h-4 w-4" /> Create case</Button> : undefined}
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="min-w-[250px]">Case</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Evidence</TableHead>
                <TableHead>Events</TableHead>
                <TableHead>Anomalies</TableHead>
                <TableHead>Updated</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredCases.map((item) => (
                <TableRow key={item.case_id}>
                  <TableCell>
                    <div className="grid gap-1">
                      <Link className="table-link" to={`/cases/${item.case_id}/overview`}>{item.title}</Link>
                      <span className="truncate text-[11px] text-muted-foreground">{item.description || item.case_id}</span>
                    </div>
                  </TableCell>
                  <TableCell><StatusBadge status={item.status} /></TableCell>
                  <TableCell className="tabular-nums">{item.evidence_count}</TableCell>
                  <TableCell className="tabular-nums">{item.event_count}</TableCell>
                  <TableCell className="tabular-nums">{item.anomaly_count}</TableCell>
                  <TableCell className="whitespace-nowrap text-muted-foreground">{formatDate(item.updated_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        <div className="border-t px-5 py-3 text-[11px] text-muted-foreground">Showing {filteredCases.length} of {casesQuery.data?.total ?? 0} cases · 100 results per request</div>
      </Card>

      <Dialog open={createOpen} onOpenChange={(open) => { setCreateOpen(open); if (!open) createMutation.reset(); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create case</DialogTitle>
            <DialogDescription>Create an investigation before uploading evidence or running analysis.</DialogDescription>
          </DialogHeader>
          <form className="space-y-4" onSubmit={createCase}>
            <div className="space-y-2">
              <Label htmlFor="case-title">Title</Label>
              <Input id="case-title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="e.g. Unusual after-hours access" maxLength={255} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="case-description">Description <span className="font-normal text-muted-foreground">(optional)</span></Label>
              <Textarea id="case-description" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Briefly describe the incident or concern." rows={3} />
            </div>
            {createMutation.isError && <p className="text-xs text-destructive">{getErrorMessage(createMutation.error)}</p>}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={createMutation.isPending || !title.trim()}>{createMutation.isPending ? 'Creating…' : 'Create case'}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
}
