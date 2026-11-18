import { Badge } from '@/components/ui/badge'

// See planning/02-design.md#badges-entry-source-and-status-monochrome

const KIND_LABELS: Record<string, string> = {
  adjusting: 'Adjusting',
  opening: 'Opening',
  reversal: 'Reversal',
}

const SOURCE_LABELS: Record<string, string> = {
  auto: 'Auto',
  boss_approved: 'Approved',
  manual: 'Manual',
  system: 'System',
}

export function sourceLabel(source: string, kind: string): string {
  return KIND_LABELS[kind] ?? SOURCE_LABELS[source] ?? source
}

export function SourceBadge({ source, kind }: { source: string; kind: string }) {
  return <Badge variant="outline">{sourceLabel(source, kind)}</Badge>
}

export function StatusBadge({ status }: { status: string }) {
  if (status === 'posted') return <Badge variant="filled">Posted</Badge>
  if (status === 'pending_approval')
    return (
      <Badge variant="outline" className="border-dashed">
        Pending
      </Badge>
    )
  return <Badge variant="muted">{status === 'rejected' ? 'Rejected' : 'Proposed'}</Badge>
}
