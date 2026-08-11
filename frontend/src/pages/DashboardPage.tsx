import { useEffect, useState } from 'react'
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
import { Plus } from 'lucide-react'
import {
  aiInsights,
  campaignHealth,
  dashboardMetrics as initialMetrics,
  revenueSpendData as initialRevenueSpendData,
} from '@/mock-data'
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  InsightCard,
  MetricCard,
} from '@/components/ui'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/services/api'
import { formatINR, getGreeting } from '@/utils'
import { cn } from '@/utils'

const ranges = ['7 Days', '30 Days', '90 Days', 'Custom']

export function DashboardPage() {
  const { user } = useAuth()
  const [range, setRange] = useState('30 Days')
  const [metrics, setMetrics] = useState(initialMetrics)
  const [chartData, setChartData] = useState(initialRevenueSpendData)

  const displayName = user?.full_name ? user.full_name.split(' ')[0] : 'Aaditya'

  useEffect(() => {
    let mounted = true
    api.analytics
      .get()
      .then((data) => {
        if (mounted && data) {
          if (data.metrics && data.metrics.length > 0) setMetrics(data.metrics as any)
          if (data.revenueSpendData && data.revenueSpendData.length > 0) setChartData(data.revenueSpendData as any)
        }
      })
      .catch(() => {})

    return () => {
      mounted = false
    }
  }, [])

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-[32px] font-bold tracking-tight">
            {getGreeting()}, {displayName}
          </h1>
          <p className="text-text-secondary mt-1">
            6 autonomous agents are managing your influencer campaigns.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <Link to="/app/campaigns/new">
            <Button size="lg" className="gap-2">
              <Plus className="h-4 w-4" /> Create Campaign
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3 sm:gap-4">
        {metrics.map((card) => (
          <MetricCard key={card.id} metric={card as any} />
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Revenue vs Influencer Spend</CardTitle>
              <p className="text-xs text-text-secondary mt-1">
                Attributed revenue generated across all campaigns
              </p>
            </div>
            <div className="flex gap-1 bg-page p-1 rounded-[10px] border border-border">
              {ranges.map((r) => (
                <button
                  key={r}
                  onClick={() => setRange(r)}
                  className={cn(
                    'px-2.5 py-1 text-xs rounded-md transition font-medium',
                    range === r ? 'bg-white shadow-xs text-text font-semibold' : 'text-text-secondary hover:text-text',
                  )}
                >
                  {r}
                </button>
              ))}
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <defs>
                    <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#4F46E5" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10B981" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis dataKey="month" stroke="#94a3b8" fontSize={11} tickLine={false} />
                  <YAxis
                    stroke="#94a3b8"
                    fontSize={11}
                    tickLine={false}
                    tickFormatter={(v) => `₹${v / 100000}L`}
                  />
                  <Tooltip
                    formatter={(v: any) => formatINR(Number(v))}
                    contentStyle={{
                      backgroundColor: '#ffffff',
                      borderColor: '#e2e8f0',
                      borderRadius: 12,
                      fontSize: 12,
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="spend"
                    name="Spend"
                    stroke="#4F46E5"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#spendGrad)"
                  />
                  <Area
                    type="monotone"
                    dataKey="revenue"
                    name="Revenue"
                    stroke="#10B981"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#revGrad)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="flex items-center justify-center gap-6 mt-4 pt-4 border-t border-border text-xs">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-primary" />
                <span className="text-text-secondary">Spend</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-success" />
                <span className="text-text-secondary">Revenue</span>
              </div>
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
                Live campaign health monitored by Performance Agent
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold">AI Strategic Insights</h2>
            <p className="text-xs text-text-secondary">Proactive optimization alerts from Strategy and Performance agents</p>
          </div>
          <Link to="/app/approvals" className="text-xs font-semibold text-primary hover:underline">
            View Approval Center →
          </Link>
        </div>
        <div className="grid md:grid-cols-3 gap-4">
          {aiInsights.map((insight) => (
            <InsightCard key={insight.id} insight={insight} />
          ))}
        </div>
      </div>
    </div>
  )
}
