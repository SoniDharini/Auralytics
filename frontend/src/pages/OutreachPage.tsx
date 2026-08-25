import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Camera,
  Check,
  CheckCircle2,
  Copy,
  ExternalLink,
  Loader2,
  Mail,
  MessageSquare,
  RefreshCw,
  Sparkles,
  UserCheck,
  Video,
} from 'lucide-react'
import { api } from '@/services/api'
import {
  Avatar,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Drawer,
  StatusChip,
  Textarea,
  useToast,
} from '@/components/ui'
import { cn } from '@/utils'

export function OutreachPage() {
  const { toast } = useToast()
  const [outreachList, setOutreachList] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedItem, setSelectedItem] = useState<any | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [mode, setMode] = useState<'email' | 'dm'>('email')
  const [editedBody, setEditedBody] = useState('')
  const [editedShortDm, setEditedShortDm] = useState('')
  const [generating, setGenerating] = useState(false)
  const [copiedEmail, setCopiedEmail] = useState(false)
  const [copiedDm, setCopiedDm] = useState(false)

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await api.outreach.list()
      setOutreachList(data || [])
    } catch (err: any) {
      toast({ type: 'error', title: 'Failed to load outreach messages', description: err?.message })
      setOutreachList([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const openReview = (item: any) => {
    setSelectedItem(item)
    setEditedBody(item.body || item.message || '')
    setEditedShortDm(item.shortDm || item.short_dm || item.body || '')
    setMode('email')
    setDrawerOpen(true)
  }

  const closeReview = () => {
    setDrawerOpen(false)
    setSelectedItem(null)
  }

  const handleCopyText = (text: string, type: 'email' | 'dm') => {
    navigator.clipboard.writeText(text)
    if (type === 'email') {
      setCopiedEmail(true)
      setTimeout(() => setCopiedEmail(false), 2000)
      toast({ type: 'success', title: 'Email copied', description: 'Message copied to clipboard.' })
    } else {
      setCopiedDm(true)
      setTimeout(() => setCopiedDm(false), 2000)
      toast({ type: 'success', title: 'Social DM copied', description: 'Short DM copied to clipboard.' })
    }
    if (selectedItem?.id) {
      api.outreach.updateStatus(selectedItem.id, 'COPIED').catch(() => {})
    }
  }

  const handleRegenerate = async () => {
    if (!selectedItem) return
    setGenerating(true)
    try {
      const campaignId = selectedItem.campaignId || selectedItem.campaign_id || 'camp-1'
      const influencerId = selectedItem.influencerId || selectedItem.influencer_id
      const res = await api.agents.runOutreach(campaignId, influencerId)
      if (res.agentRun?.status === 'FAILED') {
        toast({ type: 'error', title: 'Outreach Agent failed', description: res.agentRun.errorMessage || 'Error generating outreach pitch' })
      } else {
        toast({ type: 'success', title: 'Pitch regenerated', description: 'Outreach Agent created a new personalized proposal.' })
        await loadData()
      }
    } catch (err: any) {
      toast({ type: 'error', title: 'Regeneration failed', description: err?.message || 'Could not run Outreach Agent' })
    } finally {
      setGenerating(false)
    }
  }

  const getSubtitle = () => {
    if (!selectedItem) return undefined
    const username = selectedItem.influencerUsername || selectedItem.influencer_username || 'creator'
    const campaign = selectedItem.campaignName || selectedItem.campaign_name || ''
    return `@${username} · ${campaign}`
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-[28px] font-bold tracking-tight">AI Outreach Assistant</h1>
        <p className="text-text-secondary mt-1">
          Review personalized creator collaboration messages generated from Discovery recommendations. No automated sending — you remain in full control.
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Shortlisted Creator Messages ({outreachList.length})</CardTitle>
            <Link to="/app/discovery">
              <Button size="sm" variant="soft" className="gap-1.5">
                <Sparkles className="h-3.5 w-3.5" /> Discovery Center
              </Button>
            </Link>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading ? (
            <div className="py-12 flex justify-center items-center gap-2 text-text-secondary text-sm">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <span>Loading outreach proposals...</span>
            </div>
          ) : outreachList.length === 0 ? (
            <div className="text-center py-12 text-text-secondary space-y-3">
              <Mail className="h-10 w-10 mx-auto text-text-secondary/40" />
              <div>
                <p className="font-semibold text-text">No outreach proposals generated yet</p>
                <p className="text-xs text-text-secondary mt-1">
                  Once Discovery Agent ranks creators, Outreach Agent will draft personalized pitches.
                </p>
              </div>
              <Link to="/app/campaigns" className="inline-block pt-2">
                <Button size="sm">Go to Campaigns</Button>
              </Link>
            </div>
          ) : (
            outreachList.map((item) => (
              <div
                key={item.id}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-xl border border-border p-4 hover:border-primary/30 transition bg-page/40"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <Avatar name={item.influencerName || item.influencer_name} size="md" />
                  <div className="min-w-0 space-y-0.5">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-text truncate">
                        {item.influencerName || item.influencer_name}
                      </span>
                      <Badge variant="primary" className="text-[11px]">
                        @{item.influencerUsername || item.influencer_username}
                      </Badge>
                      <StatusChip status={item.status || 'READY'} />
                    </div>
                    <p className="text-xs text-text-secondary">
                      Campaign: <span className="font-medium text-text">{item.campaignName || item.campaign_name}</span> · Channel: {item.channel || 'EMAIL'}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    variant="secondary"
                    size="sm"
                    className="gap-1.5"
                    onClick={() => openReview(item)}
                  >
                    <MessageSquare className="h-3.5 w-3.5" />
                    Review Proposal
                  </Button>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {/* Review Drawer */}
      <Drawer
        open={drawerOpen}
        onClose={closeReview}
        title={selectedItem ? `Outreach: ${selectedItem.influencerName || selectedItem.influencer_name}` : 'Review Pitch'}
        subtitle={getSubtitle()}
        width="max-w-2xl"
      >
        {selectedItem && (
          <div className="space-y-6">
            {/* Creator Overview & Match Reason */}
            <div className="rounded-xl border border-border bg-page/50 p-4 space-y-2">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <UserCheck className="h-4 w-4 text-primary" />
                  <span className="font-semibold text-sm">Selected Shortlisted Creator</span>
                </div>
                <StatusChip status={selectedItem.status || 'READY'} />
              </div>
              <p className="text-xs text-text-secondary leading-relaxed">
                Shortlisted by Discovery Agent for {selectedItem.campaignName || selectedItem.campaign_name}.
              </p>
            </div>

            {/* Collaboration Channels */}
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
                Collaboration Channels
              </h4>
              <div className="grid sm:grid-cols-3 gap-2">
                {/* Email */}
                <div className="p-3 rounded-lg border border-border bg-page/30 space-y-1">
                  <div className="flex items-center justify-between text-xs text-text-secondary">
                    <span className="flex items-center gap-1 font-semibold text-text">
                      <Mail className="h-3.5 w-3.5 text-primary" /> Email
                    </span>
                  </div>
                  <p className="text-xs truncate font-mono text-text">
                    {selectedItem.contactInfo?.email || selectedItem.email || 'Not publicly available'}
                  </p>
                  {selectedItem.contactInfo?.email && selectedItem.contactInfo.email !== 'Not publicly available' && (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="mt-1 w-full gap-1 text-[11px]"
                      onClick={() => handleCopyText(selectedItem.contactInfo.email, 'email')}
                    >
                      <Copy className="h-3 w-3" /> Copy Email
                    </Button>
                  )}
                </div>

                {/* Instagram */}
                <div className="p-3 rounded-lg border border-border bg-page/30 space-y-1">
                  <div className="flex items-center justify-between text-xs text-text-secondary">
                    <span className="flex items-center gap-1 font-semibold text-text">
                      <Camera className="h-3.5 w-3.5 text-pink-500" /> Instagram
                    </span>
                  </div>
                  <p className="text-xs truncate font-mono text-text">
                    @{selectedItem.influencerUsername || selectedItem.influencer_username}
                  </p>
                  <a
                    href={`https://instagram.com/${selectedItem.influencerUsername || selectedItem.influencer_username}`}
                    target="_blank"
                    rel="noreferrer"
                    className="block"
                  >
                    <Button size="sm" variant="ghost" className="mt-1 w-full gap-1 text-[11px]">
                      <ExternalLink className="h-3 w-3" /> Open Instagram
                    </Button>
                  </a>
                </div>

                {/* YouTube */}
                <div className="p-3 rounded-lg border border-border bg-page/30 space-y-1">
                  <div className="flex items-center justify-between text-xs text-text-secondary">
                    <span className="flex items-center gap-1 font-semibold text-text">
                      <Video className="h-3.5 w-3.5 text-red-500" /> YouTube
                    </span>
                  </div>
                  <p className="text-xs truncate font-mono text-text">
                    {selectedItem.influencerName || selectedItem.influencer_name}
                  </p>
                  <a
                    href={`https://youtube.com/@${selectedItem.influencerUsername || selectedItem.influencer_username}`}
                    target="_blank"
                    rel="noreferrer"
                    className="block"
                  >
                    <Button size="sm" variant="ghost" className="mt-1 w-full gap-1 text-[11px]">
                      <ExternalLink className="h-3 w-3" /> Open Channel
                    </Button>
                  </a>
                </div>
              </div>
            </div>

            {/* AI Generated Message */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
                  AI Generated Pitch
                </h4>
                <div className="flex items-center gap-1 bg-muted p-1 rounded-lg">
                  <button
                    type="button"
                    className={cn(
                      'px-2.5 py-1 text-xs font-semibold rounded-md transition',
                      mode === 'email' ? 'bg-card text-text shadow-sm' : 'text-text-secondary hover:text-text',
                    )}
                    onClick={() => setMode('email')}
                  >
                    Professional Email
                  </button>
                  <button
                    type="button"
                    className={cn(
                      'px-2.5 py-1 text-xs font-semibold rounded-md transition',
                      mode === 'dm' ? 'bg-card text-text shadow-sm' : 'text-text-secondary hover:text-text',
                    )}
                    onClick={() => setMode('dm')}
                  >
                    Short Social DM
                  </button>
                </div>
              </div>

              {mode === 'email' && selectedItem.subject && (
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-text-secondary">Subject Line</label>
                  <div className="p-2.5 rounded-lg border border-border bg-page/60 text-xs font-medium text-text">
                    {selectedItem.subject}
                  </div>
                </div>
              )}

              <Textarea
                label={mode === 'email' ? 'Email Body' : 'Short Social DM'}
                value={mode === 'email' ? editedBody : editedShortDm}
                onChange={(e) =>
                  mode === 'email' ? setEditedBody(e.target.value) : setEditedShortDm(e.target.value)
                }
                rows={9}
              />

              <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                <Button
                  size="sm"
                  variant="secondary"
                  className="gap-1.5 text-xs"
                  onClick={handleRegenerate}
                  disabled={generating}
                >
                  {generating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                  Regenerate Pitch
                </Button>

                <div className="flex items-center gap-2">
                  {mode === 'email' ? (
                    <Button
                      size="sm"
                      className="gap-1.5"
                      onClick={() => handleCopyText(editedBody, 'email')}
                    >
                      {copiedEmail ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
                      {copiedEmail ? 'Copied!' : 'Copy Email'}
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      className="gap-1.5"
                      onClick={() => handleCopyText(editedShortDm, 'dm')}
                    >
                      {copiedDm ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
                      {copiedDm ? 'Copied!' : 'Copy Social DM'}
                    </Button>
                  )}
                </div>
              </div>
            </div>

            {/* Personalization Points */}
            <div className="rounded-xl border border-primary/20 bg-primary-soft/40 p-4 space-y-2">
              <div className="flex items-center gap-2 text-primary font-semibold text-xs">
                <Sparkles className="h-3.5 w-3.5 text-ai" />
                <span>AI Personalization & Alignment</span>
              </div>
              <ul className="space-y-1.5 text-xs text-text-secondary">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-3.5 w-3.5 text-success shrink-0" />
                  <span>Campaign aligned with creator's primary content niche</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-3.5 w-3.5 text-success shrink-0" />
                  <span>Content style matches campaign target objectives</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-3.5 w-3.5 text-success shrink-0" />
                  <span>Selected & ranked via Auralytics Discovery Agent</span>
                </li>
              </ul>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  )
}
