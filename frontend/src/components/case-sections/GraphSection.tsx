import { useCallback, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/EmptyState';
import { EvidenceGraph } from '@/components/EvidenceGraph';
import { getErrorMessage, investigationApi } from '@/services/api';

const nodeTypes = [
  { label: 'User', color: '#2563eb' },
  { label: 'Event', color: '#64748b' },
  { label: 'Location', color: '#7c3aed' },
  { label: 'Document', color: '#0891b2' },
  { label: 'Object', color: '#0f766e' },
  { label: 'Evidence', color: '#0f766e' },
  { label: 'Anomaly', color: '#ea580c' },
];

export function GraphSection({ caseId }: { caseId: string }) {
  const [selectedNode, setSelectedNode] = useState<Record<string, unknown> | null>(null);
  const graphQuery = useQuery({ queryKey: ['graph', caseId], queryFn: () => investigationApi.graph(caseId) });
  const selectNode = useCallback((node: Record<string, unknown>) => setSelectedNode(Object.keys(node).length ? node : null), []);

  const connectedNodes = selectedNode && Array.isArray(selectedNode.connected_nodes)
    ? selectedNode.connected_nodes.filter((value): value is string => typeof value === 'string')
    : [];
  const relationshipCount = selectedNode && typeof selectedNode.relationship_count === 'number' ? selectedNode.relationship_count : 0;
  const nodeAttributes = selectedNode
    ? Object.entries(selectedNode).filter(([key]) => key !== 'connected_nodes' && key !== 'relationship_count')
    : [];

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 border-b px-5 py-4">
        <div><CardTitle>Evidence relationship graph</CardTitle><CardDescription className="mt-1">Hover to reveal labels. Select a node to focus its direct relationships.</CardDescription></div>
        {graphQuery.data?.analyzed && <div className="flex gap-2"><Badge variant="outline">{graphQuery.data.elements.nodes.length} nodes</Badge><Badge variant="outline">{graphQuery.data.elements.edges.length} edges</Badge></div>}
      </CardHeader>
      <CardContent className="p-4">
        {graphQuery.isLoading ? <Skeleton className="h-[600px] w-full" /> : graphQuery.isError ? <Alert variant="destructive">{getErrorMessage(graphQuery.error)}</Alert> : graphQuery.data?.analyzed && graphQuery.data.elements.nodes.length ? (
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_260px]">
            <div className="graph-frame"><EvidenceGraph data={graphQuery.data} onSelect={selectNode} /></div>
            <aside className="space-y-4">
              <div>
                <h3 className="text-xs font-semibold">Selected node</h3>
                <p className="mt-1 text-[11px] text-muted-foreground">Attributes and directly connected records from the graph response.</p>
              </div>
              {selectedNode ? (
                <div className="space-y-3">
                  <div className="rounded-lg border p-3">
                    {nodeAttributes.map(([key, value]) => (
                      <div key={key} className="border-b py-2 first:pt-0 last:border-0 last:pb-0">
                        <p className="text-[10px] capitalize text-muted-foreground">{key.replace(/_/g, ' ')}</p>
                        <p className="mt-0.5 break-all text-xs font-medium">{formatValue(value)}</p>
                      </div>
                    ))}
                    <div className="border-t pt-2">
                      <p className="text-[10px] text-muted-foreground">Relationships</p>
                      <p className="mt-0.5 text-sm font-semibold tabular-nums">{relationshipCount}</p>
                    </div>
                  </div>
                  {connectedNodes.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-[11px] font-semibold">Connected nodes</h4>
                      <div className="flex max-h-32 flex-wrap gap-1.5 overflow-auto">
                        {connectedNodes.map((label, index) => <Badge key={`${label}-${index}`} variant="secondary" className="max-w-full truncate font-normal">{label}</Badge>)}
                      </div>
                    </div>
                  )}
                </div>
              ) : <EmptyState title="No node selected" description="Choose a user, event, location or evidence node." />}
              <div className="space-y-2 border-t pt-3">
                <h3 className="text-xs font-semibold">Node types</h3>
                <div className="grid grid-cols-2 gap-2">
                  {nodeTypes.map((type) => (
                    <div key={type.label} className="flex items-center gap-2 text-[11px] text-muted-foreground">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: type.color }} />
                      {type.label}
                    </div>
                  ))}
                </div>
              </div>
            </aside>
          </div>
        ) : <EmptyState title="Evidence graph unavailable" description="Run analysis for this case to generate its relationship graph." />}
      </CardContent>
    </Card>
  );
}

function formatValue(value: unknown): string {
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value);
  try { return JSON.stringify(value) ?? String(value); } catch { return String(value); }
}
