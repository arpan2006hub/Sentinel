import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Download, Plus, ShieldCheck } from 'lucide-react';
import { EmptyState } from '@/components/EmptyState';
import { StatusBadge } from '@/components/StatusBadge';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { downloadEvidence, evidenceApi, getErrorMessage } from '@/services/api';
import type { EvidenceItem } from '@/types/api';

export function EvidenceSection({ caseId }: { caseId: string }) {
  const queryClient = useQueryClient();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceItem | null>(null);
  const [sourceType, setSourceType] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [recordedAt, setRecordedAt] = useState('');
  const [locationId, setLocationId] = useState('');

  const evidenceQuery = useQuery({ queryKey: ['evidence', caseId], queryFn: () => evidenceApi.list(caseId) });
  const sourceTypesQuery = useQuery({ queryKey: ['evidence-source-types'], queryFn: evidenceApi.sourceTypes, staleTime: 60_000 });
  const verifyQuery = useQuery({
    queryKey: ['evidence-verify', selectedEvidence?.evidence_id],
    queryFn: () => evidenceApi.verify(selectedEvidence!.evidence_id),
    enabled: Boolean(selectedEvidence),
  });
  const auditVerifyQuery = useQuery({
    queryKey: ['evidence-audit-verify', selectedEvidence?.evidence_id],
    queryFn: () => evidenceApi.verifyAudit(selectedEvidence!.evidence_id),
    enabled: Boolean(selectedEvidence),
  });
  const auditQuery = useQuery({
    queryKey: ['evidence-audit', selectedEvidence?.evidence_id],
    queryFn: () => evidenceApi.audit(selectedEvidence!.evidence_id),
    enabled: Boolean(selectedEvidence),
  });

  const uploadMutation = useMutation({
    mutationFn: () => {
      if (!file || !sourceType) throw new Error('Choose a source type and file.');
      const metadata: Record<string, string> = {};
      if (recordedAt.trim()) metadata.recorded_at = recordedAt.trim();
      if (locationId.trim()) metadata.location_id = locationId.trim();
      return evidenceApi.upload(caseId, sourceType, file, metadata);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['evidence', caseId] });
      await queryClient.invalidateQueries({ queryKey: ['case-summary', caseId] });
      setUploadOpen(false);
      setFile(null);
      setRecordedAt('');
      setLocationId('');
    },
  });

  const downloadMutation = useMutation({
    mutationFn: (item: EvidenceItem) => downloadEvidence(item.evidence_id, item.file_name),
  });

  function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    uploadMutation.mutate();
  }

  return (
    <div className="section-stack">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 border-b px-5 py-4">
          <div><CardTitle>Evidence</CardTitle><CardDescription className="mt-1">Stored evidence, SHA-256 fingerprints and chain-of-custody verification.</CardDescription></div>
          <Button size="sm" onClick={() => setUploadOpen(true)}><Plus className="h-3.5 w-3.5" /> Upload</Button>
        </CardHeader>
        {evidenceQuery.isLoading ? (
          <div className="space-y-3 p-5"><Skeleton className="h-9 w-full" /><Skeleton className="h-9 w-full" /></div>
        ) : evidenceQuery.isError ? (
          <div className="p-5"><Alert variant="destructive">{getErrorMessage(evidenceQuery.error)}</Alert></div>
        ) : evidenceQuery.data?.evidence.length ? (
          <Table>
            <TableHeader><TableRow><TableHead>File</TableHead><TableHead>Source type</TableHead><TableHead>Status</TableHead><TableHead>Size</TableHead><TableHead>Added</TableHead><TableHead className="text-right">Actions</TableHead></TableRow></TableHeader>
            <TableBody>
              {evidenceQuery.data.evidence.map((item) => (
                <TableRow key={item.evidence_id}>
                  <TableCell><div className="max-w-[280px]"><p className="truncate text-xs font-medium">{item.file_name}</p><p className="truncate font-mono text-[10px] text-muted-foreground">{item.file_hash}</p></div></TableCell>
                  <TableCell><Badge variant="secondary">{item.source_type}</Badge></TableCell>
                  <TableCell><StatusBadge status={item.processing_status} /></TableCell>
                  <TableCell className="whitespace-nowrap tabular-nums">{formatBytes(item.file_size_bytes)}</TableCell>
                  <TableCell className="whitespace-nowrap text-muted-foreground">{formatDate(item.ingested_at)}</TableCell>
                  <TableCell><div className="flex justify-end gap-1">
                    <Button variant="ghost" size="icon" title="Verify integrity and audit chain" aria-label={`Verify ${item.file_name}`} onClick={() => setSelectedEvidence(item)}><ShieldCheck className="h-4 w-4" /></Button>
                    <Button variant="ghost" size="icon" title="Download evidence" aria-label={`Download ${item.file_name}`} disabled={downloadMutation.isPending} onClick={() => downloadMutation.mutate(item)}><Download className="h-4 w-4" /></Button>
                  </div></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyState title="No evidence uploaded" description="Upload logs, documents or video evidence to this case." action={<Button size="sm" onClick={() => setUploadOpen(true)}><Plus className="h-4 w-4" /> Upload evidence</Button>} />
        )}
        {downloadMutation.isError && <div className="px-5 pb-4 text-xs text-destructive">{getErrorMessage(downloadMutation.error)}</div>}
        <div className="border-t px-5 py-3 text-[11px] text-muted-foreground">{evidenceQuery.data?.total ?? 0} evidence items</div>
      </Card>

      <Dialog open={uploadOpen} onOpenChange={(open) => { setUploadOpen(open); if (!open) uploadMutation.reset(); }}>
        <DialogContent>
          <DialogHeader><DialogTitle>Upload evidence</DialogTitle><DialogDescription>Files are stored by the backend and fingerprinted with SHA-256.</DialogDescription></DialogHeader>
          <form className="space-y-4" onSubmit={submitUpload}>
            <div className="space-y-2">
              <Label htmlFor="evidence-source">Source type</Label>
              <Select value={sourceType} onValueChange={setSourceType}>
                <SelectTrigger id="evidence-source"><SelectValue placeholder="Choose evidence source" /></SelectTrigger>
                <SelectContent>
                  {sourceTypesQuery.data?.map((item) => <SelectItem key={item.source_type} value={item.source_type}>{item.source_type} · {item.processor}</SelectItem>)}
                </SelectContent>
              </Select>
              {sourceTypesQuery.isError && <p className="text-xs text-destructive">{getErrorMessage(sourceTypesQuery.error)}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="evidence-file">Evidence file</Label>
              <Input id="evidence-file" type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} required />
              {file && <p className="text-[11px] text-muted-foreground">{file.name} · {formatBytes(file.size)}</p>}
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2"><Label htmlFor="recorded-at">Recorded at <span className="font-normal text-muted-foreground">(optional ISO 8601)</span></Label><Input id="recorded-at" value={recordedAt} onChange={(event) => setRecordedAt(event.target.value)} placeholder="2026-01-16T21:58:00Z" /></div>
              <div className="space-y-2"><Label htmlFor="location-id">Location ID <span className="font-normal text-muted-foreground">(optional)</span></Label><Input id="location-id" value={locationId} onChange={(event) => setLocationId(event.target.value)} placeholder="ZONE-SERVER-ROOM" /></div>
            </div>
            <p className="text-[11px] leading-5 text-muted-foreground">Recorded time and location are used when available for video and document correlation.</p>
            {uploadMutation.isError && <Alert variant="destructive">{getErrorMessage(uploadMutation.error)}</Alert>}
            <div className="flex justify-end gap-2 pt-1">
              <Button variant="outline" type="button" onClick={() => setUploadOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={uploadMutation.isPending || !file || !sourceType || sourceTypesQuery.isLoading}>{uploadMutation.isPending ? 'Uploading…' : 'Upload evidence'}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(selectedEvidence)} onOpenChange={(open) => { if (!open) setSelectedEvidence(null); }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>Evidence integrity</DialogTitle><DialogDescription className="break-all font-mono">{selectedEvidence?.file_name} · {selectedEvidence?.evidence_id}</DialogDescription></DialogHeader>
          <div className="grid gap-3 sm:grid-cols-2">
            <VerificationCard title="SHA-256 integrity" loading={verifyQuery.isLoading} error={verifyQuery.isError ? getErrorMessage(verifyQuery.error) : null} valid={verifyQuery.data?.integrity === 'verified'} detail={verifyQuery.data?.message ?? verifyQuery.data?.integrity} />
            <VerificationCard title="Audit chain" loading={auditVerifyQuery.isLoading} error={auditVerifyQuery.isError ? getErrorMessage(auditVerifyQuery.error) : null} valid={auditVerifyQuery.data?.valid} detail={auditVerifyQuery.data ? `${auditVerifyQuery.data.records} records · ${auditVerifyQuery.data.legacy_unverifiable} legacy unverifiable` : undefined} />
          </div>
          {verifyQuery.data && <div className="space-y-1 rounded-lg border p-3"><p className="text-[11px] font-medium text-muted-foreground">Computed SHA-256</p><p className="break-all font-mono text-[11px]">{verifyQuery.data.computed_hash}</p></div>}
          <div className="space-y-2">
            <div className="flex items-center justify-between"><h3 className="text-xs font-semibold">Chain of custody</h3><Badge variant="outline">{auditQuery.data?.length ?? 0} records</Badge></div>
            {auditQuery.isLoading ? <Skeleton className="h-16 w-full" /> : auditQuery.isError ? <p className="text-xs text-muted-foreground">{getErrorMessage(auditQuery.error)}</p> : auditQuery.data?.length ? (
              <div className="max-h-48 space-y-2 overflow-auto rounded-lg border p-3">
                {auditQuery.data.map((record) => <div key={record.audit_id} className="flex items-start justify-between gap-3 text-[11px]"><div><p className="font-medium capitalize">{record.action.replace(/_/g, ' ')}</p><p className="text-muted-foreground">{record.actor} · {formatDate(record.timestamp)}</p></div><span className="max-w-[180px] truncate font-mono text-muted-foreground">{record.audit_id}</span></div>)}
              </div>
            ) : <p className="text-xs text-muted-foreground">No audit records returned.</p>}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function VerificationCard({ title, loading, error, valid, detail }: { title: string; loading: boolean; error: string | null; valid?: boolean; detail?: string | null }) {
  return (
    <Card className="shadow-none">
      <CardContent className="space-y-2 p-3">
        <div className="flex items-center justify-between gap-2"><p className="text-xs font-medium">{title}</p>{loading ? <Badge variant="secondary">Checking</Badge> : error ? <Badge variant="destructive">Error</Badge> : <Badge variant={valid ? 'success' : 'destructive'}>{valid ? 'Verified' : 'Failed'}</Badge>}</div>
        <p className="text-[11px] text-muted-foreground">{error ?? detail ?? (loading ? 'Verification in progress…' : 'No verification result.')}</p>
      </CardContent>
    </Card>
  );
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}
