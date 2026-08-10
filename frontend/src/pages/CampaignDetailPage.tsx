import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  BarChart3,
  Bot,
  Calendar,
  Edit3,
  FileText,
  Mail,
  RefreshCw,
  Sparkles,
  TrendingUp,
  Users,
  Wallet,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  agentTimeline,
  campaignFunnel,
  campaigns,
  contracts,
  creatorPerformance,
  influencers,
  revenueSpendData,
} from '@/mock-data'
import {
  Avatar,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  ProgressBar,
  StatusChip,
  Tabs,
} from '@/components/ui'
import { cn, formatINR, formatNumber, statusLabel } from '@/utils'

const tabIds = [
  'overview',
  'strategy',
  'influencers',
  'outreach',
  'contracts',
  'performance',
  'agents',
] as const

type TabId = (typeof tabIds)[number]

const performanceColors: Record<string, string> = {
  excellent: '#16A34A',
  healthy: '#5B5FEF',
  needs_attention: '#EF4444',
}

export function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [activeTab, setActiveTab] = useState<TabId>('overview')

  const campaign = useMemo(
    () => campaigns.find((c) => c.id === id) ?? campaigns[0],
    [id],
  )

  const shortlisted = useMemo(
    () => influencers.filter((i) => i.shortlisted),
    [],
  )

  const campaignContracts = useMemo(
    () => contracts.filter((c) => c.campaign === campaign.name),
    [campaign.name],
  )

  const outreachCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    shortlisted.forEach((i) => {
      const s = i.status ?? 'not_contacted'
      counts[s] = (counts[s] ?? 0) + 1
    })
    return counts
  }, [shortlisted])

  const budgetUsedPct = campaign.budget > 0 ? (campaign.spend / campaign.budget) * 100 : 0
  const timelinePct = campaign.progress

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'strategy', label: 'AI Strategy' },
    { id: 'influencers', label: 'Influencers', count: shortlisted.length },
    { id: 'outreach', label: 'Outreach', count: shortlisted.length },
    { id: 'contracts', label: 'Contracts', count: campaignContracts.length },
    { id: 'performance', label: 'Performance' },
    { id: 'agents', label: 'Agent Activity' },
  ]

  const formatDate = (d: string) =>
    new Date(d).toLocaleDateString('en-IN', { month: 'short', day: 'numeric', year: 'numeric' })

  const maxFunnel = Math.max(...campaignFunnel.map((f) => f.value))

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start gap-3">
        <Link to="/app/campaigns">
          <Button variant="ghost" size="icon" aria-label="Back to campaigns">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl sm:text-[28px] font-bold tracking-tight truncate">
              {campaign.name}
            </h1>
            <StatusChip status={campaign.status} />
            <Badge variant={campaign.health === 'excellent' ? 'success' : campaign.health === 'healthy' ? 'primary' : 'danger'}>
              {statusLabel(campaign.health)}
            </Badge>
          </div>
          <div className="flex flex-wrap items-center gap-4 mt-2 text-sm text-text-secondary">
            <span className="flex items-center gap-1.5">
              <Calendar className="h-4 w-4" />
              {formatDate(campaign.startDate)} – {formatDate(campaign.endDate)}
            </span>
            <span>{campaign.brand}</span>
            <span className="bg-muted px-2 py-0.5 rounded-md text-xs font-semibold">{campaign.objective}</span>
          </div>
        </div>
        <Button variant="secondary" className="gap-2 shrink-0 hidden sm:inline-flex">
          <Edit3 className="h-4 w-4" /> Edit
        </Button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        {[
          { label: 'Budget', value: formatINR(campaign.budget, true), icon: Wallet, sub: `${Math.round(budgetUsedPct)}% used` },
          { label: 'Spend', value: formatINR(campaign.spend, true), icon: Wallet },
          { label: 'Revenue', value: formatINR(campaign.revenue, true), icon: TrendingUp, accent: 'text-success' },
          { label: 'ROAS', value: campaign.roas ? `${campaign.roas}x` : '—', icon: BarChart3, accent: 'text-primary' },
          { label: 'Creators', value: campaign.influencers.toString(), icon: Users, sub: `${formatNumber(campaign.reach)} reach` },
        ].map((m) => (
          <Card key={m.label}>
            <CardContent className="pt-4 pb-4">
              <div className="flex items-center justify-between mb-1">
                <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide">{m.label}</p>
                <m.icon className="h-4 w-4 text-text-secondary" />
              </div>
              <p className={cn('text-xl font-bold', m.accent)}>{m.value}</p>
              {m.sub && <p className="text-xs text-text-secondary mt-0.5">{m.sub}</p>}
            </CardContent>
          </Card>
        ))}
      </div>

      <Tabs tabs={tabs} active={activeTab} onChange={(t) => setActiveTab(t as TabId)} />

      {activeTab === 'overview' && (
        <div className="space-y-4 animate-fade-in">
          <div className="grid lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Budget Progress</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <ProgressBar value={budgetUsedPct} showLabel barClassName="bg-primary" />
                <div className="flex justify-between text-sm">
                  <span className="text-text-secondary">Spent {formatINR(campaign.spend)}</span>
                  <span className="font-semibold">{formatINR(campaign.budget - campaign.spend)} remaining</span>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Timeline Progress</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <ProgressBar value={timelinePct} showLabel barClassName="bg-accent" />
                <div className="flex justify-between text-sm">
                  <span className="text-text-secondary">{formatDate(campaign.startDate)}</span>
                  <span className="text-text-secondary">{formatDate(campaign.endDate)}</span>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: 'Conversions', value: formatNumber(campaign.conversions) },
              { label: 'Reach', value: formatNumber(campaign.reach) },
              { label: 'Avg. CPA', value: campaign.conversions ? formatINR(Math.round(campaign.spend / campaign.conversions)) : '—' },
              { label: 'Progress', value: `${campaign.progress}%` },
            ].map((k) => (
              <Card key={k.label}>
                <CardContent className="pt-4 pb-4">
                  <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide">{k.label}</p>
                  <p className="text-2xl font-bold mt-1">{k.value}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Campaign Funnel</CardTitle>
              <p className="text-sm text-text-secondary mt-0.5">Creator pipeline from discovery to completion</p>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {campaignFunnel.map((stage, i) => {
                  const pct = (stage.value / maxFunnel) * 100
                  const prev = i > 0 ? campaignFunnel[i - 1].value : null
                  const dropoff = prev ? Math.round(((prev - stage.value) / prev) * 100) : null
                  return (
                    <div key={stage.label}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium">{stage.label}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold">{stage.value}</span>
                          {dropoff !== null && dropoff > 0 && (
                            <span className="text-xs text-text-secondary">−{dropoff}%</span>
                          )}
                        </div>
                      </div>
                      <div className="h-2.5 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full rounded-full bg-primary transition-all duration-500"
                          style={{ width: `${pct}%`, opacity: 1 - i * 0.08 }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'strategy' && (
        <div className="animate-fade-in">
          <Card>
            <CardHeader>
              <div>
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-ai" />
                  <CardTitle>Strategy Report</CardTitle>
                </div>
                <p className="text-sm text-text-secondary mt-1">
                  Generated by Strategy Agent · Aug 10, 2026 at 10:32 AM
                </p>
              </div>
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" className="gap-1.5">
                  <RefreshCw className="h-3.5 w-3.5" /> Regenerate
                </Button>
                <Button variant="soft" size="sm" className="gap-1.5">
                  <Edit3 className="h-3.5 w-3.5" /> Edit
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid sm:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div>
                    <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-1">Objective</p>
                    <p className="text-sm font-medium">
                      Drive product launch awareness and conversions for GlowNaturals Summer Serum collection
                      targeting women 25–34 interested in clean beauty.
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-1">Audience</p>
                    <p className="text-sm font-medium">
                      Female-skewed, ages 22–34, metro India (Mumbai, Delhi, Bangalore). Interests: skincare,
                      clean beauty, wellness.
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-1">Creator Mix</p>
                    <div className="flex gap-3 mt-2">
                      <div className="flex-1 rounded-[10px] border border-border p-3 text-center bg-primary-soft/50">
                        <p className="text-2xl font-bold text-primary">8</p>
                        <p className="text-xs font-semibold text-text-secondary">Micro</p>
                      </div>
                      <div className="flex-1 rounded-[10px] border border-border p-3 text-center bg-violet-50">
                        <p className="text-2xl font-bold text-accent">3</p>
                        <p className="text-xs font-semibold text-text-secondary">Mid-tier</p>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="space-y-4">
                  <div>
                    <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-1">Platform Split</p>
                    <div className="space-y-2 mt-2">
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="font-medium">Instagram</span>
                          <span className="font-semibold">70%</span>
                        </div>
                        <div className="h-2 rounded-full bg-muted overflow-hidden">
                          <div className="h-full bg-primary rounded-full" style={{ width: '70%' }} />
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="font-medium">YouTube</span>
                          <span className="font-semibold">30%</span>
                        </div>
                        <div className="h-2 rounded-full bg-muted overflow-hidden">
                          <div className="h-full bg-accent rounded-full" style={{ width: '30%' }} />
                        </div>
                      </div>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-1">Content Strategy</p>
                    <p className="text-sm font-medium">
                      Prioritize Instagram Reels (routine demos, before/after) and YouTube Shorts for ingredient
                      education. UGC-style authentic testimonials over polished ads.
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-1">Posting Frequency</p>
                    <p className="text-sm font-medium">2–3 posts/week per creator · Peak windows: Tue–Thu 6–9 PM IST</p>
                  </div>
                </div>
              </div>

              <div className="border-t border-border pt-5">
                <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-3">KPI Targets</p>
                <div className="flex flex-wrap gap-2">
                  {['ROAS 3.0x', 'CPA ₹150', 'Engagement 5.5%', '400 conversions', '1.8M reach'].map((k) => (
                    <Badge key={k} variant="primary">{k}</Badge>
                  ))}
                </div>
              </div>

              <div className="rounded-[12px] border border-warning/30 bg-amber-50/50 p-4">
                <p className="text-xs font-semibold text-warning uppercase tracking-wide mb-2">Risks & Mitigations</p>
                <ul className="space-y-2 text-sm">
                  <li className="flex gap-2">
                    <span className="text-warning font-bold">•</span>
                    Seasonal competition may increase CPMs in September — reserve fund allocated for bid adjustments.
                  </li>
                  <li className="flex gap-2">
                    <span className="text-warning font-bold">•</span>
                    1 creator showing below-threshold niche match — Optimization Agent monitoring allocation.
                  </li>
                  <li className="flex gap-2">
                    <span className="text-warning font-bold">•</span>
                    Contract posting deadlines tight for 2 creators — Contract Agent flagged for review.
                  </li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'influencers' && (
        <Card className="animate-fade-in">
          <CardHeader>
            <CardTitle>Shortlisted Influencers</CardTitle>
            <p className="text-sm text-text-secondary mt-0.5">{shortlisted.length} creators in pipeline</p>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-text-secondary border-b border-border">
                  <th className="pb-3 font-semibold">Creator</th>
                  <th className="pb-3 font-semibold">Platform</th>
                  <th className="pb-3 font-semibold">Followers</th>
                  <th className="pb-3 font-semibold">Eng. Rate</th>
                  <th className="pb-3 font-semibold">AI Match</th>
                  <th className="pb-3 font-semibold">Est. Cost</th>
                  <th className="pb-3 font-semibold">Pred. ROAS</th>
                  <th className="pb-3 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody>
                {shortlisted.map((inf) => (
                  <tr key={inf.id} className="border-b border-border last:border-0 hover:bg-page/80">
                    <td className="py-3.5 pr-3">
                      <div className="flex items-center gap-3 min-w-[160px]">
                        <Avatar name={inf.name} size="sm" />
                        <div>
                          <p className="font-semibold">{inf.name}</p>
                          <p className="text-xs text-text-secondary">@{inf.username}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5 pr-3 capitalize">{inf.platform}</td>
                    <td className="py-3.5 pr-3">{formatNumber(inf.followers)}</td>
                    <td className="py-3.5 pr-3 font-medium">{inf.engagementRate}%</td>
                    <td className="py-3.5 pr-3">
                      <span className={cn('font-bold', inf.aiMatchScore >= 90 ? 'text-success' : inf.aiMatchScore >= 75 ? 'text-primary' : 'text-warning')}>
                        {inf.aiMatchScore}
                      </span>
                    </td>
                    <td className="py-3.5 pr-3">{formatINR(inf.estimatedCost)}</td>
                    <td className="py-3.5 pr-3 font-semibold text-primary">{inf.predictedRoas}x</td>
                    <td className="py-3.5">
                      {inf.status && <StatusChip status={inf.status} />}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {activeTab === 'outreach' && (
        <div className="space-y-4 animate-fade-in">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(outreachCounts).map(([status, count]) => (
              <Card key={status}>
                <CardContent className="pt-4 pb-4">
                  <StatusChip status={status} className="mb-2" />
                  <p className="text-3xl font-bold">{count}</p>
                  <p className="text-xs text-text-secondary mt-1">creators</p>
                </CardContent>
              </Card>
            ))}
          </div>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Mail className="h-4 w-4 text-text-secondary" />
                Outreach Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid sm:grid-cols-3 gap-6">
                <div className="text-center p-4 rounded-[12px] bg-page">
                  <p className="text-3xl font-bold text-primary">{outreachCounts.sent ?? 0}</p>
                  <p className="text-sm text-text-secondary mt-1">Messages Sent</p>
                </div>
                <div className="text-center p-4 rounded-[12px] bg-page">
                  <p className="text-3xl font-bold text-accent">{outreachCounts.replied ?? 0}</p>
                  <p className="text-sm text-text-secondary mt-1">Replies Received</p>
                </div>
                <div className="text-center p-4 rounded-[12px] bg-page">
                  <p className="text-3xl font-bold text-success">{outreachCounts.accepted ?? 0}</p>
                  <p className="text-sm text-text-secondary mt-1">Accepted</p>
                </div>
              </div>
              <p className="text-sm text-text-secondary mt-6">
                Outreach Agent has personalized {shortlisted.length} messages based on creator content history
                and audience demographics. {outreachCounts.awaiting_approval ?? 0} awaiting your approval.
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'contracts' && (
        <Card className="animate-fade-in">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-text-secondary" />
              Contracts
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {campaignContracts.length === 0 ? (
              <p className="text-sm text-text-secondary py-8 text-center">No contracts for this campaign yet.</p>
            ) : (
              campaignContracts.map((ct) => (
                <div
                  key={ct.id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-[12px] border border-border hover:bg-page/50 transition"
                >
                  <div className="flex items-start gap-3">
                    <Avatar name={ct.creator} size="md" />
                    <div>
                      <p className="font-semibold">{ct.creator}</p>
                      <p className="text-xs text-text-secondary">@{ct.username}</p>
                      <p className="text-xs text-text-secondary mt-1">
                        {formatDate(ct.startDate)} – {formatDate(ct.endDate)}
                      </p>
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {ct.deliverables.map((d) => (
                          <Badge key={d} variant="outline">{d}</Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-col items-start sm:items-end gap-2 shrink-0">
                    <p className="text-lg font-bold">{formatINR(ct.value)}</p>
                    <StatusChip status={ct.status} />
                    <Badge variant={ct.risk === 'Low' ? 'success' : ct.risk === 'Medium' ? 'warning' : 'danger'}>
                      {ct.risk} risk
                    </Badge>
                    {ct.aiRisks.length > 0 && (
                      <p className="text-xs text-danger max-w-[200px] text-right">{ct.aiRisks[0]}</p>
                    )}
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'performance' && (
        <div className="space-y-4 animate-fade-in">
          <div className="grid lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Revenue vs Spend</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[260px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={revenueSpendData}>
                      <defs>
                        <linearGradient id="detailRev" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#5B5FEF" stopOpacity={0.25} />
                          <stop offset="100%" stopColor="#5B5FEF" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="detailSpend" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#8B5CF6" stopOpacity={0.2} />
                          <stop offset="100%" stopColor="#8B5CF6" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
                      <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} />
                      <YAxis
                        tick={{ fontSize: 11, fill: '#6B7280' }}
                        axisLine={false}
                        tickLine={false}
                        tickFormatter={(v) => `₹${v / 1000}k`}
                      />
                      <Tooltip
                        contentStyle={{ borderRadius: 12, border: '1px solid #E5E7EB', fontSize: 12 }}
                        formatter={(value) => formatINR(Number(value))}
                      />
                      <Area type="monotone" dataKey="revenue" name="Revenue" stroke="#5B5FEF" fill="url(#detailRev)" strokeWidth={2} />
                      <Area type="monotone" dataKey="spend" name="Spend" stroke="#8B5CF6" fill="url(#detailSpend)" strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Creator ROAS Comparison</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[260px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={creatorPerformance} layout="vertical" margin={{ left: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" horizontal={false} />
                      <XAxis type="number" tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} />
                      <YAxis
                        type="category"
                        dataKey="influencer"
                        tick={{ fontSize: 11, fill: '#6B7280' }}
                        axisLine={false}
                        tickLine={false}
                        width={90}
                      />
                      <Tooltip
                        contentStyle={{ borderRadius: 12, border: '1px solid #E5E7EB', fontSize: 12 }}
                        formatter={(value) => [`${value}x`, 'ROAS']}
                      />
                      <Bar dataKey="roas" radius={[0, 6, 6, 0]} barSize={16}>
                        {creatorPerformance.map((entry) => (
                          <Cell key={entry.influencer} fill={performanceColors[entry.performance]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Creator Performance</CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-text-secondary border-b border-border">
                    <th className="pb-3 font-semibold">Creator</th>
                    <th className="pb-3 font-semibold">Spend</th>
                    <th className="pb-3 font-semibold">Reach</th>
                    <th className="pb-3 font-semibold">Conversions</th>
                    <th className="pb-3 font-semibold">Revenue</th>
                    <th className="pb-3 font-semibold">ROAS</th>
                    <th className="pb-3 font-semibold">CPA</th>
                  </tr>
                </thead>
                <tbody>
                  {creatorPerformance.map((row) => (
                    <tr key={row.influencer} className="border-b border-border last:border-0">
                      <td className="py-3 font-semibold">@{row.influencer}</td>
                      <td className="py-3">{formatINR(row.spend)}</td>
                      <td className="py-3">{formatNumber(row.reach)}</td>
                      <td className="py-3">{row.conversions}</td>
                      <td className="py-3">{formatINR(row.revenue)}</td>
                      <td className="py-3">
                        <span className={cn('font-bold', row.roas >= 3 ? 'text-success' : row.roas >= 2 ? 'text-primary' : 'text-danger')}>
                          {row.roas}x
                        </span>
                      </td>
                      <td className="py-3">₹{row.cpa}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'agents' && (
        <Card className="animate-fade-in">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bot className="h-4 w-4 text-ai" />
              Agent Activity Timeline
            </CardTitle>
            <p className="text-sm text-text-secondary mt-0.5">Real-time workflow events from your AI team</p>
          </CardHeader>
          <CardContent>
            <div className="relative">
              <div className="absolute left-[19px] top-2 bottom-2 w-px bg-border" />
              <div className="space-y-4">
                {agentTimeline.map((event) => {
                  const dotColor =
                    event.type === 'success'
                      ? 'bg-success'
                      : event.type === 'action'
                        ? 'bg-primary'
                        : event.type === 'human'
                          ? 'bg-accent'
                          : 'bg-text-secondary'
                  return (
                    <div key={event.id} className="flex gap-4 relative">
                      <div className={cn('h-2.5 w-2.5 rounded-full shrink-0 mt-2 ring-4 ring-white z-10', dotColor)} />
                      <div className="flex-1 pb-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-xs font-mono text-text-secondary">{event.time}</span>
                          <Badge variant={event.type === 'human' ? 'ai' : event.agent.includes('Supervisor') ? 'primary' : 'outline'}>
                            {event.agent}
                          </Badge>
                        </div>
                        <p className="text-sm font-medium mt-1">{event.message}</p>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
