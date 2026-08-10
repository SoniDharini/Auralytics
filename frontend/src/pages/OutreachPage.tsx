import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { MessageSquare, RefreshCw, Sparkles, Send } from 'lucide-react'
import { influencers, outreachMessage } from '@/mock-data'
import {
  Avatar,
  Badge,
  Button,
  Card,
  CardContent,
  Drawer,
  ProgressRing,
  StatusChip,
  Tabs,
  Textarea,
  useToast,
} from '@/components/ui'
import { cn, formatINR } from '@/utils'
import type { Influencer, OutreachStatus } from '@/types'

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

function getMessageForInfluencer(inf: Influencer): string {
  return outreachMessage.replace('Aditi', inf.name.split(' ')[0]).replace('@AditiBeauty', `@${inf.username}`)
}

const AI_EXPLANATION =
  'Personalized from creator content history, audience demographics, and campaign brief. Tone adjusted to match prior successful outreach in beauty vertical.'

const COUNTER_MESSAGE =
  "Hi Riya, thank you for sharing your rate. Based on similar campaigns and your audience metrics, we'd love to collaborate at ₹26,000 for 2 Reels + 3 Stories. This aligns with your historical average and keeps the partnership sustainable for both sides. Happy to discuss deliverables!"

export function OutreachPage() {
  const { toast } = useToast()
  const [activeTab, setActiveTab] = useState<string>('all')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selected, setSelected] = useState<Influencer | null>(null)
  const [message, setMessage] = useState('')
  const [editing, setEditing] = useState(false)
  const [counterAmount, setCounterAmount] = useState(26000)

  const withStatus = useMemo(
    () => influencers.filter((i) => i.status),
    [],
  )

  const filtered = useMemo(() => {
    if (activeTab === 'all') return withStatus
    return withStatus.filter((i) => i.status === activeTab)
  }, [activeTab, withStatus])

  const tabCounts = useMemo(() => {
    const counts: Record<string, number> = { all: withStatus.length }
    PIPELINE_TABS.slice(1).forEach((t) => {
      counts[t.id] = withStatus.filter((i) => i.status === t.id).length
    })
    return counts
  }, [withStatus])

  const openDrawer = (inf: Influencer) => {
    setSelected(inf)
    setMessage(getMessageForInfluencer(inf))
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
    setMessage(getMessageForInfluencer(selected))
    setEditing(false)
    toast({ type: 'info', title: 'Message regenerated', description: 'Outreach Agent drafted a new version.' })
  }

  const handleApproveSend = () => {
    toast({
      type: 'success',
      title: 'Message approved & sent',
      description: selected ? `Outreach sent to @${selected.username}` : 'Outreach sent successfully.',
    })
    closeDrawer()
  }

  const isNegotiating = selected?.status === 'negotiating'

  return (
    <div className="space-y-5 animate-fade-in">
      <div>
        <h1 className="text-[28px] font-bold tracking-tight">Outreach Pipeline</h1>
        <p className="text-text-secondary mt-1">
          Review AI-drafted messages and manage creator negotiations
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
          {filtered.length === 0 ? (
            <p className="text-sm text-text-secondary text-center py-8">
              No creators in this pipeline stage.
            </p>
          ) : (
            filtered.map((inf) => (
              <div
                key={inf.id}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-[12px] border border-border p-4 hover:border-primary/30 transition"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <Avatar name={inf.name} size="md" />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Link
                        to={`/app/discovery/${inf.id}`}
                        className="font-semibold hover:text-primary truncate"
                      >
                        {inf.name}
                      </Link>
                      <StatusChip status={inf.status!} />
                    </div>
                    <p className="text-xs text-text-secondary">@{inf.username} · {formatINR(inf.estimatedCost, true)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4 shrink-0">
                  <div className="flex items-center gap-2">
                    <ProgressRing value={inf.aiMatchScore} size={40} stroke={3} color="#7C3AED" />
                    <span className="text-xs text-text-secondary">Match</span>
                  </div>
                  <Button
                    variant="secondary"
                    size="sm"
                    className="gap-1.5"
                    onClick={() => openDrawer(inf)}
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
        title={selected ? `Outreach to @${selected.username}` : 'Review Message'}
        subtitle={selected ? `${selected.name} · ${selected.platform}` : undefined}
        width="max-w-xl"
        footer={
          isNegotiating ? (
            <div className="flex flex-wrap gap-2">
              <Button variant="danger" size="sm" onClick={closeDrawer}>
                Reject
              </Button>
              <Button variant="secondary" size="sm" onClick={() => toast({ type: 'info', title: 'Counter sent', description: `Counteroffer of ${formatINR(counterAmount)} sent to @${selected?.username}` })}>
                Counter at {formatINR(counterAmount, true)}
              </Button>
              <Button size="sm" onClick={() => toast({ type: 'success', title: 'Quote accepted', description: 'Moving to contract stage.' })}>
                Accept Quote
              </Button>
            </div>
          ) : (
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
          )
        }
      >
        {selected && (
          <div className="space-y-5">
            <div className="flex items-center gap-2">
              <StatusChip status={selected.status!} />
              <Badge variant="ai">Match {selected.aiMatchScore}%</Badge>
            </div>

            {isNegotiating ? (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-[10px] border border-border p-3">
                    <p className="text-xs text-text-secondary">Creator Quote</p>
                    <p className="text-lg font-bold text-warning">₹35K</p>
                  </div>
                  <div className="rounded-[10px] border border-border p-3">
                    <p className="text-xs text-text-secondary">Historical Avg</p>
                    <p className="text-lg font-bold">₹24K</p>
                  </div>
                  <div className="rounded-[10px] border border-border p-3 col-span-2">
                    <p className="text-xs text-text-secondary">Campaign Recommended</p>
                    <p className="text-lg font-bold text-primary">₹25–27K</p>
                  </div>
                </div>

                <div className="rounded-[10px] bg-muted p-3 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Predicted ROAS at ₹35K</span>
                    <span className="font-semibold text-warning">1.7x</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Predicted ROAS at ₹26K</span>
                    <span className="font-semibold text-success">2.4x</span>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1.5">Counter Amount (₹)</label>
                  <input
                    type="number"
                    value={counterAmount}
                    onChange={(e) => setCounterAmount(Number(e.target.value))}
                    className="w-full h-10 px-3 rounded-[10px] border border-border text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                  />
                </div>

                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <p className="text-sm font-semibold">AI Counteroffer Message</p>
                    <Badge variant="ai">AI Generated</Badge>
                  </div>
                  <div className="rounded-[10px] border border-violet-100 bg-violet-50/50 p-3 text-sm leading-relaxed">
                    {COUNTER_MESSAGE}
                  </div>
                </div>
              </>
            ) : (
              <>
                <Textarea
                  label="Outreach Message"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  readOnly={!editing}
                  className={cn(!editing && 'bg-muted/50')}
                  rows={12}
                />

                <div className="rounded-[10px] border border-indigo-100 bg-primary-soft/50 p-3">
                  <div className="flex items-center gap-2 mb-1.5">
                    <Sparkles className="h-3.5 w-3.5 text-ai" />
                    <p className="text-xs font-semibold text-ai">AI Explanation</p>
                  </div>
                  <p className="text-xs text-text-secondary leading-relaxed">{AI_EXPLANATION}</p>
                </div>
              </>
            )}
          </div>
        )}
      </Drawer>
    </div>
  )
}
