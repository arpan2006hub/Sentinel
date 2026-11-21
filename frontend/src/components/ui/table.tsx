import * as React from 'react';
import { cn } from '@/lib/utils';

export const Table = React.forwardRef<HTMLTableElement, React.HTMLAttributes<HTMLTableElement>>(({ className, ...props }, ref) => (
  <div className="relative w-full overflow-auto"><table ref={ref} className={cn('w-full caption-bottom text-sm', className)} {...props} /></div>
));
Table.displayName = 'Table';
export const TableHeader = ({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) => <thead className={cn('[&_tr]:border-b', className)} {...props} />;
export const TableBody = ({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) => <tbody className={cn('[&_tr:last-child]:border-0', className)} {...props} />;
export const TableFooter = ({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) => <tfoot className={cn('border-t bg-muted/50 font-medium', className)} {...props} />;
export const TableRow = ({ className, ...props }: React.HTMLAttributes<HTMLTableRowElement>) => <tr className={cn('border-b transition-colors hover:bg-muted/35 data-[state=selected]:bg-muted', className)} {...props} />;
export const TableHead = ({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) => <th className={cn('h-10 px-4 text-left align-middle text-[10px] font-semibold uppercase tracking-[.09em] text-muted-foreground', className)} {...props} />;
export const TableCell = ({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) => <td className={cn('px-4 py-3 align-middle text-xs', className)} {...props} />;
export const TableCaption = ({ className, ...props }: React.HTMLAttributes<HTMLTableCaptionElement>) => <caption className={cn('mt-4 text-xs text-muted-foreground', className)} {...props} />;
