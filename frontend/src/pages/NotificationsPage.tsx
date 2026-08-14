import { useMemo, useState } from 'react'
import {
  Bell,
  Bot,
  CheckCircle2,
  ExternalLink,
  FileSignature,
  IndianRupee,
  Megaphone,
  TrendingDown,
} from 'lucide-react'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Select, useToast } from '@/components/ui'
import { cn } from '@/utils'
import type { NotificationItem } from '@/types'

const typeConfig: Record<
  NotificationItem['type'],
  { icon: React.ComponentType<{ className?: string }>; label: string; color: string }
> = {
  agent: { icon: Bot, label: 'Agent', color: 'text-ai bg-violet-50' },
  approval: { icon: CheckCircle2, label: 'Approval', color: 'text-primary bg-primary-soft' },
  contract: { icon: FileSignature, label: 'Contract', color: 'text-amber-700 bg-amber-50' },
  performance: { icon: TrendingDown, label: 'Performance', color: 'text-danger bg-red-50' },
  budget: { icon: IndianRupee, label: 'Budget', color: 'text-warning bg-amber-50' },
  campaign: { icon: Megaphone, label: 'Campaign', color: 'text-success bg-green-50' },
}

const filterOptions = [
  { value: 'all', label: 'All types' },
  { value: 'agent', label: 'Agent' },
  { value: 'approval', label: 'Approval' },
  { value: 'contract', label: 'Contract' },
  { value: 'performance', label: 'Performance' },
  { value: 'budget', label: 'Budget' },
  { value: 'campaign', label: 'Campaign' },
]

export function NotificationsPage() {
  const { toast } = useToast()
  const [items, setItems] = useState<NotificationItem[]>([])
  const [typeFilter, setTypeFilter] = useState('all')

  const unreadCount = useMemo(() => items.filter((n) => !n.read).length, [items])

  const filtered = useMemo(() => {
    if (typeFilter === 'all') return items
    return items.filter((n) => n.type === typeFilter)
  }, [items, typeFilter])

  const markRead = (id: string) => {
    setItems((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)))
    toast({ type: 'success', title: 'Marked as read' })
  }

  const markAllRead = () => {
    setItems((prev) => prev.map((n) => ({ ...n, read: true })))
    toast({ type: 'success', title: 'All notifications marked as read' })
  }

  const viewAction = (item: NotificationItem) => {
    if (!item.read) markRead(item.id)
    toast({
      type: 'info',
      title: item.actionLabel || 'View action',
      description: item.title,
    })
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-[32px] font-bold tracking-tight">Notifications</h1>
          <p className="text-text-secondary mt-1">
            Stay updated on agent activity, approvals, and campaign alerts.
          </p>
        </div>
        {unreadCount > 0 && (
          <Badge variant="primary" pulse>
            {unreadCount} unread
          </Badge>
        )}
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 w-full">
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5 text-primary" />
              Inbox
            </CardTitle>
            <div className="flex flex-wrap items-end gap-3">
              <Select
                label="Filter by type"
                options={filterOptions}
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="min-w-[160px]"
              />
              {unreadCount > 0 && (
                <Button variant="secondary" size="sm" onClick={markAllRead}>
                  Mark all read
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          {filtered.length === 0 ? (
            <div className="text-center py-16 text-text-secondary">
              <Bell className="h-10 w-10 mx-auto mb-3 opacity-30" />
              <p className="font-semibold text-text">No notifications yet</p>
              <p className="text-sm mt-1">You will receive alerts here when AI agents require review or tasks complete.</p>
            </div>
          ) : (
            filtered.map((item) => (
              <NotificationRow
                key={item.id}
                item={item}
                onMarkRead={() => markRead(item.id)}
                onViewAction={() => viewAction(item)}
              />
            ))
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function NotificationRow({
  item,
  onMarkRead,
  onViewAction,
}: {
  item: NotificationItem
  onMarkRead: () => void
  onViewAction: () => void
}) {
  const config = typeConfig[item.type]
  const Icon = config.icon

  return (
    <div
      className={cn(
        'flex flex-col sm:flex-row sm:items-start gap-4 p-4 rounded-xl border transition-colors',
        item.read
          ? 'border-border bg-white'
          : 'border-primary/25 bg-primary-soft/20 shadow-[0_0_0_1px_rgba(91,95,239,0.08)]',
      )}
    >
      <div className={cn('h-10 w-10 rounded-xl flex items-center justify-center shrink-0', config.color)}>
        <Icon className="h-5 w-5" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className={cn('text-sm', !item.read && 'font-bold')}>{item.title}</p>
          {!item.read && (
            <span className="h-2 w-2 rounded-full bg-primary shrink-0" aria-label="Unread" />
          )}
          <Badge variant="outline" className="capitalize">
            {config.label}
          </Badge>
        </div>
        <p className="text-sm text-text-secondary mt-1">{item.body}</p>
        <p className="text-xs text-text-secondary mt-2">{item.timestamp}</p>
      </div>

      <div className="flex flex-wrap gap-2 shrink-0">
        {!item.read && (
          <Button variant="ghost" size="sm" onClick={onMarkRead}>
            Mark Read
          </Button>
        )}
        {item.actionLabel && (
          <Button size="sm" variant="secondary" className="gap-1.5" onClick={onViewAction}>
            {item.actionLabel}
            <ExternalLink className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>
    </div>
  )
}
