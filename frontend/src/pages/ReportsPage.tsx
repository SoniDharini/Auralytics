import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  BarChart3,
  Download,
  Eye,
  FileSpreadsheet,
  FileText,
  Loader2,
  Plus,
  Sparkles,
} from 'lucide-react'

import { api } from '@/services/api'
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  useToast,
} from '@/components/ui'
import { useAuth } from '@/context/AuthContext'
import { cn, formatINR } from '@/utils'
import type { Campaign } from '@/types'

const availableReports = [
  {
    id: 'rep-exec',
    name: 'Executive Campaign Performance',
    description: 'High-level ROI, spend efficiency, and ROAS breakdown for leadership.',
  },
  {
    id: 'rep-creator',
    name: 'Creator Efficiency Matrix',
    description: 'Individual creator metrics, conversion benchmarks, and engagement rates.',
  },
  {
    id: 'rep-budget',
    name: 'Budget & Pacing Audit',
    description: 'Detailed analysis of budget burn, category allocations, and reserve funds.',
  },
]

export function ReportsPage() {
  const { user } = useAuth()
  const { toast } = useToast()
  const [campaignsList, setCampaignsList] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)
  const [previewId, setPreviewId] = useState<string | null>(null)
  const [generatingId, setGeneratingId] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    api.campaigns
      .list()
      .then((data) => {
        if (mounted && data) {
          setCampaignsList(data)
          if (data.length > 0) {
            setPreviewId('rep-exec')
          }
        }
      })
      .catch(() => {
        setCampaignsList([])
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })

    return () => {
      mounted = false
    }
  }, [])

  const previewReport = availableReports.find((r) => r.id === previewId)
  const featuredCampaign = campaignsList[0]

  const handleGenerate = (id: string, name: string) => {
    setGeneratingId(id)
    setTimeout(() => {
      setGeneratingId(null)
      toast({
        type: 'success',
        title: 'Report generated',
        description: `${name} is ready for preview and export.`,
      })
    }, 1000)
  }

  const handleExport = (format: 'pdf' | 'csv', name: string) => {
    toast({
      type: 'info',
      title: `Exporting ${format.toUpperCase()}`,
      description: `${name} download ready.`,
    })
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-[32px] font-bold tracking-tight">Reports</h1>
          <p className="text-text-secondary mt-1">
            Generate executive-ready reports for stakeholders and leadership.
          </p>
        </div>
      </div>

      {loading && (
        <div className="py-16 flex justify-center items-center gap-2 text-text-secondary text-sm">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <span>Loading reports...</span>
        </div>
      )}

      {!loading && campaignsList.length === 0 && (
        <Card>
          <CardContent className="py-16 text-center space-y-4">
            <div className="mx-auto h-14 w-14 rounded-2xl bg-primary-soft text-primary flex items-center justify-center">
              <FileText className="h-7 w-7" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-text">No reports available yet</h3>
              <p className="text-sm text-text-secondary mt-1 max-w-md mx-auto">
                Reports are generated from your active campaigns. Create a campaign to unlock executive reporting.
              </p>
            </div>
            <Link to="/app/campaigns/new" className="inline-block mt-2">
              <Button size="lg" className="gap-2">
                <Plus className="h-4 w-4" /> Create Campaign
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {!loading && campaignsList.length > 0 && (
        <div className="grid lg:grid-cols-[1fr_1.4fr] gap-6">
          <div className="space-y-4">
            <h2 className="text-base font-semibold">Available Reports</h2>
            {availableReports.map((report) => (
              <Card
                key={report.id}
                className={cn(
                  'transition-all',
                  previewId === report.id && 'border-primary/40 ring-2 ring-primary/10',
                )}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-start gap-3">
                    <div className="h-10 w-10 rounded-xl bg-primary-soft text-primary flex items-center justify-center shrink-0">
                      <FileText className="h-5 w-5" />
                    </div>
                    <div>
                      <CardTitle className="text-sm">{report.name}</CardTitle>
                      <CardDescription>{report.description}</CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="ai"
                    className="gap-1.5"
                    disabled={generatingId === report.id}
                    onClick={() => handleGenerate(report.id, report.name)}
                  >
                    <Sparkles className="h-3.5 w-3.5" />
                    {generatingId === report.id ? 'Generating…' : 'Generate Report'}
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    className="gap-1.5"
                    onClick={() => setPreviewId(report.id)}
                  >
                    <Eye className="h-3.5 w-3.5" /> Preview
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="gap-1.5"
                    onClick={() => handleExport('pdf', report.name)}
                  >
                    <Download className="h-3.5 w-3.5" /> Export PDF
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="gap-1.5"
                    onClick={() => handleExport('csv', report.name)}
                  >
                    <FileSpreadsheet className="h-3.5 w-3.5" /> Export CSV
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>

          <div>
            {previewId && previewReport && featuredCampaign ? (
              <Card className="overflow-hidden">
                <div className="ai-gradient-bg px-6 py-8 text-white">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-widest opacity-80">InfluenceOS</p>
                      <h2 className="text-2xl font-bold mt-1">{previewReport.name}</h2>
                      <p className="text-sm opacity-90 mt-2">{user?.company_name || 'InfluenceOS Workspace'}</p>
                    </div>
                    <Badge variant="outline" className="bg-white/10 text-white border-white/30">
                      Executive Summary
                    </Badge>
                  </div>
                  <p className="text-xs opacity-75 mt-4">
                    Prepared for {user?.full_name || 'Authenticated User'} · {new Date().toLocaleDateString('en-IN', { dateStyle: 'long' })}
                  </p>
                </div>

                <CardContent className="p-6 space-y-6">
                  <section>
                    <h3 className="text-sm font-bold uppercase tracking-wide text-text-secondary mb-3">
                      Campaign Summary
                    </h3>
                    <div className="rounded-xl border border-border p-4 bg-page/50">
                      <p className="font-semibold text-lg">{featuredCampaign.name}</p>
                      <p className="text-sm text-text-secondary mt-1">
                        {featuredCampaign.objective} · {featuredCampaign.brand} ·{' '}
                        {featuredCampaign.status.toUpperCase()}
                      </p>
                    </div>
                  </section>

                  <section>
                    <h3 className="text-sm font-bold uppercase tracking-wide text-text-secondary mb-3">
                      Financial Metrics
                    </h3>
                    <div className="grid grid-cols-3 gap-3">
                      {[
                        { label: 'Total Budget', value: formatINR(featuredCampaign.budget, true) },
                        { label: 'Spend', value: formatINR(featuredCampaign.spend || 0, true) },
                        { label: 'Revenue', value: formatINR(featuredCampaign.revenue || 0, true), highlight: true },
                      ].map((m) => (
                        <div key={m.label} className="rounded-xl border border-border p-4 text-center">
                          <p className="text-[11px] text-text-secondary uppercase tracking-wide">{m.label}</p>
                          <p className={cn('text-xl font-bold mt-1', m.highlight && 'text-primary')}>{m.value}</p>
                        </div>
                      ))}
                    </div>
                  </section>
                </CardContent>
              </Card>
            ) : (
              <Card className="h-full min-h-[480px] flex items-center justify-center">
                <CardContent className="text-center py-16">
                  <BarChart3 className="h-12 w-12 mx-auto text-text-secondary/40 mb-4" />
                  <p className="font-semibold text-text">Select a report to preview</p>
                  <p className="text-sm text-text-secondary mt-1 max-w-xs mx-auto">
                    Generate or preview any report to see an executive summary here.
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
