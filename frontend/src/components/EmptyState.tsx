import type { ReactNode } from 'react';
import { Inbox } from 'lucide-react';

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <span className="empty-state-icon"><Inbox className="h-5 w-5" /></span>
      <h3>{title}</h3>
      <p>{description}</p>
      {action && <div className="pt-2">{action}</div>}
    </div>
  );
}
