import { Badge } from './Badge'

interface StatusBadgeProps {
  status: 'completed' | 'failed' | 'running' | 'awaiting_approval' | 'pending' | 'succeeded' | 'active' | 'draft' | 'archived'
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const statusMap: Record<string, { variant: 'success' | 'error' | 'info' | 'warning' | 'neutral'; label: string }> = {
    completed: { variant: 'success', label: 'Completed' },
    succeeded: { variant: 'success', label: 'Succeeded' },
    failed: { variant: 'error', label: 'Failed' },
    running: { variant: 'info', label: 'Running' },
    awaiting_approval: { variant: 'warning', label: 'Awaiting Approval' },
    pending: { variant: 'neutral', label: 'Pending' },
    active: { variant: 'success', label: 'Active' },
    draft: { variant: 'neutral', label: 'Draft' },
    archived: { variant: 'neutral', label: 'Archived' },
  }

  const mapped = statusMap[status] || statusMap.pending

  return (
    <Badge variant={mapped.variant} className={className}>
      {mapped.label}
    </Badge>
  )
}

