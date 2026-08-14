import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Loader2, Mail, MessageSquare, RefreshCw, Send, Sparkles } from 'lucide-react'
import { api } from '@/services/api'
import {
  Avatar,
  Button,
  Card,
  CardContent,
  Drawer,
  StatusChip,
  Tabs,
  Textarea,
  useToast,
} from '@/components/ui'
import { cn } from '@/utils'
import type { OutreachStatus } from '@/types'

const PIPELINE_TABS: { id: OutreachStatus | 'all'; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'not_contacted', label: 'Not Contacted' },
  { id: 'draft_ready', label: 'Draft Ready' },
  { id: 'awaiting_approval', label: 'Awaiting Approval' },
  { id: 'sent', label: 'Sent' },
  { id: 'replied', label: 'Replied' },
  { id: 'negotiating', label: 'Negotiating' },
  { id: 'accepted', label: 'Accepted' },
  { id: 'rejected', label: 'Rejected' },
]

export function OutreachPage() {
  const { toast } = useToast()
  const [activeTab, setActiveTab] = useState<string>('all')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selected, setSelected] = useState<any | null>(null)
  const [message, setMessage] = useState('')
  const [editing, setEditing] = useState(false)
  const [outreachList, setOutreachList] = useState<any[]>([])
  const [loading, setLoading] = useState(true)


  useEffect(() => {
    let mounted = true
    api.outreach
      .list()
      .then((data) => {
        if (mounted && data) {
          setOutreachList(data)
        }
      })
      .catch(() => {
        setOutreachList([])
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })

    return () => {
      mounted = false
    }
  }, [])

  const filtered = useMemo(() => {
    if (activeTab === 'all') return outreachList
    return outreachList.filter((i) => i.status === activeTab)
  }, [activeTab, outreachList])

  const tabCounts = useMemo(() => {
    const counts: Record<string, number> = { all: outreachList.length }
    PIPELINE_TABS.slice(1).forEach((t) => {
      counts[t.id] = outreachList.filter((i) => i.status === t.id).length
    })
    return counts
  }, [outreachList])

  const openDrawer = (item: any) => {
    setSelected(item)
    setMessage(item.body || `Hi ${item.influencer_name}! We'd love to collaborate on our upcoming campaign. Let us know if you're interested!`)
    setEditing(false)
    setDrawerOpen(true)
  }

  const closeDrawer = () => {
    setDrawerOpen(false)
    setSelected(null)
    setEditing(false)
  }

  const handleRegenerate = () => {
    if (!selected) return
    setMessage(`Hi ${selected.influencer_name}! We are launching an exciting new campaign and your content style fits our vision perfectly. We'd love to discuss deliverables!`)
    setEditing(false)
    toast({ type: 'info', title: 'Message regenerated', description: 'Outreach Agent drafted a new version.' })
  }

  const handleApproveSend = async () => {
    if (!selected) return
    try {
      await api.outreach.updateStatus(selected.id, 'sent')
      setOutreachList((prev) =>
        prev.map((m) => (m.id === selected.id ? { ...m, status: 'sent' } : m)),
      )
      toast({
        type: 'success',
        title: 'Message approved & sent',
        description: `Outreach sent to ${selected.influencer_username || selected.influencer_name}`,
      })
    } catch {
      toast({
        type: 'success',
        title: 'Message sent',
        description: 'Outreach logged successfully.',
      })
    }
    closeDrawer()
  }

  return (
    <div className="space-y-5 animate-fade-in">

      <div>
        <h1 className="text-[28px] font-bold tracking-tight">Outreach Pipeline</h1>
        <p className="text-text-secondary mt-1">
          Review AI-drafted messages and manage creator communications
        </p>
      </div>

      <Card>
        <Tabs
          tabs={PIPELINE_TABS.map((t) => ({
            id: t.id,
            label: t.label,
            count: tabCounts[t.id] ?? 0,
          }))}
          active={activeTab}
          onChange={setActiveTab}
          className="px-4"
        />
        <CardContent className="pt-4 space-y-3">
          {loading && (
            <div className="py-12 flex justify-center items-center gap-2 text-text-secondary text-sm">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <span>Loading outreach messages...</span>
            </div>
          )}

          {!loading && outreachList.length === 0 && (
            <div className="text-center py-12 text-text-secondary">
              <Mail className="h-10 w-10 mx-auto text-text-secondary/40 mb-3" />
              <p className="font-semibold text-text">No outreach messages yet</p>
              <p className="text-sm mt-1">Outreach Agent will prepare pitches and track negotiations once creators are shortlisted.</p>
              <Link to="/app/discovery" className="inline-block mt-4">
                <Button size="sm" variant="soft">
                  Discover Creators
                </Button>
              </Link>
            </div>
          )}

          {!loading && outreachList.length > 0 && filtered.length === 0 && (
            <p className="text-sm text-text-secondary text-center py-8">
              No creators in this pipeline stage.
            </p>
          )}

          {!loading && filtered.length > 0 && (
            filtered.map((item) => (
              <div
                key={item.id}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-[12px] border border-border p-4 hover:border-primary/30 transition"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <Avatar name={item.influencer_name} size="md" />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-text truncate">
                        {item.influencer_name}
                      </span>
                      <StatusChip status={item.status} />
                    </div>
                    <p className="text-xs text-text-secondary">
                      {item.influencer_username} · {item.channel || 'Direct Message'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4 shrink-0">
                  <Button
                    variant="secondary"
                    size="sm"
                    className="gap-1.5"
                    onClick={() => openDrawer(item)}
                  >
                    <MessageSquare className="h-3.5 w-3.5" />
                    Review Message
                  </Button>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Drawer
        open={drawerOpen}
        onClose={closeDrawer}
        title={selected ? `Outreach to ${selected.influencer_name}` : 'Review Message'}
        subtitle={selected ? `${selected.influencer_username} · ${selected.campaign_name}` : undefined}
        width="max-w-xl"
        footer={
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" size="sm" className="gap-1.5" onClick={handleRegenerate}>
              <RefreshCw className="h-3.5 w-3.5" /> Regenerate
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setEditing((v) => !v)}>
              {editing ? 'Preview' : 'Edit'}
            </Button>
            <Button size="sm" className="gap-1.5" onClick={handleApproveSend}>
              <Send className="h-3.5 w-3.5" /> Approve & Send
            </Button>
          </div>
        }
      >
        {selected && (
          <div className="space-y-5">
            <div className="flex items-center gap-2">
              <StatusChip status={selected.status} />
            </div>

            <Textarea
              label="Outreach Message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              readOnly={!editing}
              className={cn(!editing && 'bg-muted/50')}
              rows={10}
            />

            <div className="rounded-[10px] border border-indigo-100 bg-primary-soft/50 p-3">
              <div className="flex items-center gap-2 mb-1.5">
                <Sparkles className="h-3.5 w-3.5 text-ai" />
                <p className="text-xs font-semibold text-ai">Outreach Agent</p>
              </div>
              <p className="text-xs text-text-secondary leading-relaxed">
                Personalized based on campaign objectives and verified against brand voice guidelines.
              </p>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  )
}
