import { Badge } from '@/components/ui/badge';

const variants: Record<string, 'success' | 'warning' | 'destructive' | 'muted' | 'secondary'> = {
  open: 'success',
  investigating: 'warning',
  closed: 'muted',
  archived: 'muted',
  queued: 'secondary',
  running: 'warning',
  completed: 'success',
  failed: 'destructive',
  processed: 'success',
  pending: 'secondary',
  skipped: 'warning',
  error: 'destructive',
  verified: 'success',
};

export function StatusBadge({ status }: { status?: string | null }) {
  const value = status || 'unknown';
  return <Badge variant={variants[value.toLowerCase()] ?? 'outline'} className="capitalize">{value.replace(/_/g, ' ')}</Badge>;
}
