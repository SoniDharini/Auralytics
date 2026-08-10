import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Plus, Upload, ArrowRight, Sparkles } from 'lucide-react'
import {
  aiInsights,
  campaignHealth,
  campaigns,
  dashboardMetrics,
  revenueSpendData,
  workspace,
} from '@/mock-data'
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  InsightCard,
  MetricCard,
  StatusChip,
} from '@/components/ui'
import { formatINR, getGreeting } from '@/utils'
import { cn } from '@/utils'

const ranges = ['7 Days', '30 Days', '90 Days', 'Custom']

export function DashboardPage() {
  const [range, setRange] = useState('30 Days')
  const firstTime = false

  if (firstTime) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16 animate-fade-in">
        <div className="h-14 w-14 mx-auto rounded-2xl ai-gradient-bg text-white flex items-center justify-center mb-5">
          <Sparkles className="h-7 w-7" />
        </div>
        <h1 className="text-3xl font-bold">Create your first autonomous campaign.</h1>
        <p className="mt-3 text-text-secondary">
          Tell us your objective, audience and budget. Your AI agent team will handle the rest.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3 text-sm">
          {['Create Brief', 'Discover', 'Collaborate', 'Optimize'].map((s, i) => (
            <div key={s} className="flex items-center gap-3">
              <span className="rounded-full bg-white border border-border px-3 py-1.5 font-semibold">{s}</span>
              {i < 3 && <ArrowRight className="h-4 w-4 text-text-secondary" />}
            </div>
          ))}
        </div>
        <Link to="/app/campaigns/new" className="inline-block mt-8">
          <Button size="lg">Create First Campaign</Button>
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-[32px] font-bold tracking-tight">
            {getGreeting()}, {workspace.user.split(' ')[0]}
          </h1>
          <p className="text-text-secondary mt-1">
            Here&apos;s how your influencer campaigns are performing.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" className="gap-2">
            <Upload className="h-4 w-4" /> Import Data
          </Button>
          <Link to="/app/campaigns/new">
            <Button className="gap-2">
              <Plus className="h-4 w-4" /> Create Campaign
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {dashboardMetrics.map((m) => (
          <MetricCard key={m.id} metric={m} />
        ))}
      </div>

      <div className="grid xl:grid-cols-[1.6fr_1fr] gap-4">
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Campaign Revenue vs Spend</CardTitle>
              <p className="text-sm text-text-secondary mt-0.5">Track efficiency across the selected period</p>
            </div>
            <div className="flex flex-wrap gap-1">
              {ranges.map((r) => (
                <button
                  key={r}
                  onClick={() => setRange(r)}
                  className={cn(
                    'px-2.5 py-1 rounded-lg text-xs font-semibold transition',
                    range === r ? 'bg-primary text-white' : 'bg-muted text-text-secondary hover:text-text',
                  )}
                >
                  {r}
                </button>
              ))}
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={revenueSpendData}>
                  <defs>
                    <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#5B5FEF" stopOpacity={0.25} />
                      <stop offset="100%" stopColor="#5B5FEF" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="spend" x1="0" y1="0" x2="0" y2="1">
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
                    contentStyle={{
                      borderRadius: 12,
                      border: '1px solid #E5E7EB',
                      fontSize: 12,
                    }}
                    formatter={(value) => formatINR(Number(value))}
                  />
                  <Area type="monotone" dataKey="revenue" name="Revenue" stroke="#5B5FEF" fill="url(#rev)" strokeWidth={2} />
                  <Area type="monotone" dataKey="spend" name="Spend" stroke="#8B5CF6" fill="url(#spend)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Campaign Health</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { label: 'Excellent', value: campaignHealth.excellent, color: 'bg-success', text: 'text-success' },
              { label: 'Healthy', value: campaignHealth.healthy, color: 'bg-primary', text: 'text-primary' },
              { label: 'Needs Attention', value: campaignHealth.needsAttention, color: 'bg-danger', text: 'text-danger' },
            ].map((item) => (
              <div key={item.label} className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <span className={cn('h-2.5 w-2.5 rounded-full', item.color)} />
                  <span className="text-sm font-medium">{item.label}</span>
                </div>
                <span className={cn('text-2xl font-bold', item.text)}>{item.value}</span>
              </div>
            ))}
            <div className="pt-2">
              <div className="h-3 rounded-full overflow-hidden flex">
                <div className="bg-success" style={{ width: '25%' }} />
                <div className="bg-primary" style={{ width: '62.5%' }} />
                <div className="bg-danger" style={{ width: '12.5%' }} />
              </div>
              <p className="text-xs text-text-secondary mt-3">
                8 campaigns monitored by Performance Agent
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid xl:grid-cols-[1.5fr_1fr] gap-4">
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Top Campaigns</CardTitle>
              <p className="text-sm text-text-secondary mt-0.5">Click a row to open the Command Center</p>
            </div>
            <Link to="/app/campaigns" className="text-sm font-semibold text-primary hover:underline">
              View all
            </Link>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-text-secondary border-b border-border">
                  <th className="pb-3 font-semibold">Campaign</th>
                  <th className="pb-3 font-semibold">Status</th>
                  <th className="pb-3 font-semibold">Budget</th>
                  <th className="pb-3 font-semibold">Spend</th>
                  <th className="pb-3 font-semibold">Revenue</th>
                  <th className="pb-3 font-semibold">ROAS</th>
                  <th className="pb-3 font-semibold">Progress</th>
                </tr>
              </thead>
              <tbody>
                {campaigns.slice(0, 4).map((c) => (
                  <tr key={c.id} className="border-b border-border last:border-0 hover:bg-page/80">
                    <td className="py-3.5 pr-3">
                      <Link to={`/app/campaigns/${c.id}`} className="font-semibold hover:text-primary">
                        {c.name}
                      </Link>
                      <p className="text-xs text-text-secondary">{c.influencers} creators</p>
                    </td>
                    <td className="py-3.5 pr-3">
                      <StatusChip status={c.status} />
                    </td>
                    <td className="py-3.5 pr-3">{formatINR(c.budget, true)}</td>
                    <td className="py-3.5 pr-3">{formatINR(c.spend, true)}</td>
                    <td className="py-3.5 pr-3">{formatINR(c.revenue, true)}</td>
                    <td className="py-3.5 pr-3 font-semibold text-primary">{c.roas ? `${c.roas}x` : '—'}</td>
                    <td className="py-3.5">
                      <div className="flex items-center gap-2 min-w-[100px]">
                        <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
                          <div className="h-full bg-primary rounded-full" style={{ width: `${c.progress}%` }} />
                        </div>
                        <span className="text-xs font-semibold w-8">{c.progress}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>

        <div className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <h2 className="text-base font-semibold flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-ai" /> AI Insights
            </h2>
            <Link to="/app/optimization" className="text-xs font-semibold text-primary">
              Optimization Center
            </Link>
          </div>
          {aiInsights.map((insight) => (
            <InsightCard
              key={insight.id}
              insight={insight}
              onPrimary={() => {}}
              onSecondary={() => {}}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
