import { useState } from 'react'
import {
  BarChart3,
  Download,
  Eye,
  FileSpreadsheet,
  FileText,
  Sparkles,
  TrendingUp,
} from 'lucide-react'
import {
  campaigns,
  creatorPerformance,
  performanceInsights,
  platformPerformance,
  reports,
  workspace,
} from '@/mock-data'
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
import { cn, formatINR } from '@/utils'

const featuredCampaign = campaigns[0]

export function ReportsPage() {
  const { toast } = useToast()
  const [previewId, setPreviewId] = useState<string | null>(null)
  const [generatingId, setGeneratingId] = useState<string | null>(null)

  const previewReport = reports.find((r) => r.id === previewId)

  const handleGenerate = (id: string, name: string) => {
    setGeneratingId(id)
    setTimeout(() => {
      setGeneratingId(null)
      toast({
        type: 'success',
        title: 'Report generated',
        description: `${name} is ready for preview and export.`,
      })
    }, 1200)
  }

  const handleExport = (format: 'pdf' | 'csv', name: string) => {
    toast({
      type: 'info',
      title: `Exporting ${format.toUpperCase()}`,
      description: `${name} download will begin shortly.`,
    })
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-[32px] font-bold tracking-tight">Reports</h1>
        <p className="text-text-secondary mt-1">
          Generate executive-ready reports for stakeholders and leadership.
        </p>
      </div>

      <div className="grid lg:grid-cols-[1fr_1.4fr] gap-6">
        <div className="space-y-4">
          <h2 className="text-base font-semibold">Available Reports</h2>
          {reports.map((report) => (
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
          {previewId && previewReport ? (
            <ReportPreview title={previewReport.name} />
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
    </div>
  )
}

function ReportPreview({ title }: { title: string }) {
  const topCreators = creatorPerformance.slice(0, 4)

  return (
    <Card className="overflow-hidden">
      <div className="ai-gradient-bg px-6 py-8 text-white">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest opacity-80">Auralytics</p>
            <h2 className="text-2xl font-bold mt-1">{title}</h2>
            <p className="text-sm opacity-90 mt-2">{workspace.name}</p>
          </div>
          <Badge variant="outline" className="bg-white/10 text-white border-white/30">
            Executive Summary
          </Badge>
        </div>
        <p className="text-xs opacity-75 mt-4">
          Prepared for {workspace.user} · {new Date().toLocaleDateString('en-IN', { dateStyle: 'long' })}
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
              {featuredCampaign.objective} · {featuredCampaign.influencers} creators ·{' '}
              {featuredCampaign.progress}% complete
            </p>
            <div className="mt-3 h-2 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full bg-primary rounded-full"
                style={{ width: `${featuredCampaign.progress}%` }}
              />
            </div>
          </div>
        </section>

        <section>
          <h3 className="text-sm font-bold uppercase tracking-wide text-text-secondary mb-3">
            Financial Performance
          </h3>
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: 'Total Spend', value: formatINR(featuredCampaign.spend, true) },
              { label: 'Revenue', value: formatINR(featuredCampaign.revenue, true) },
              { label: 'ROAS', value: `${featuredCampaign.roas}x`, highlight: true },
            ].map((m) => (
              <div key={m.label} className="rounded-xl border border-border p-4 text-center">
                <p className="text-[11px] text-text-secondary uppercase tracking-wide">{m.label}</p>
                <p className={cn('text-xl font-bold mt-1', m.highlight && 'text-primary')}>{m.value}</p>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h3 className="text-sm font-bold uppercase tracking-wide text-text-secondary mb-3">
            Top Creators
          </h3>
          <div className="overflow-x-auto rounded-xl border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-text-secondary border-b border-border bg-muted/40">
                  <th className="px-4 py-2.5 font-semibold">Creator</th>
                  <th className="px-4 py-2.5 font-semibold">Spend</th>
                  <th className="px-4 py-2.5 font-semibold">Revenue</th>
                  <th className="px-4 py-2.5 font-semibold">ROAS</th>
                </tr>
              </thead>
              <tbody>
                {topCreators.map((c) => (
                  <tr key={c.influencer} className="border-b border-border last:border-0">
                    <td className="px-4 py-2.5 font-semibold">@{c.influencer}</td>
                    <td className="px-4 py-2.5">{formatINR(c.spend, true)}</td>
                    <td className="px-4 py-2.5">{formatINR(c.revenue, true)}</td>
                    <td className="px-4 py-2.5 font-semibold text-primary">{c.roas}x</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h3 className="text-sm font-bold uppercase tracking-wide text-text-secondary mb-3">
            Platform Performance
          </h3>
          <div className="space-y-2">
            {platformPerformance.map((p) => (
              <div key={p.platform} className="flex items-center gap-3">
                <span className="text-sm font-medium w-24">{p.platform}</span>
                <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full"
                    style={{ width: `${Math.min((p.roas / 4) * 100, 100)}%` }}
                  />
                </div>
                <span className="text-sm font-bold text-primary w-14 text-right">{p.roas}x</span>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h3 className="text-sm font-bold uppercase tracking-wide text-text-secondary mb-3 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-ai" /> Key Insights
          </h3>
          <ul className="space-y-2">
            {performanceInsights.map((ins) => (
              <li key={ins.id} className="text-sm flex gap-2">
                <TrendingUp className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                <span>
                  <strong>{ins.title}:</strong> {ins.body}
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section className="grid sm:grid-cols-2 gap-4">
          <div className="rounded-xl border border-border p-4">
            <h4 className="text-sm font-semibold mb-2">Lessons Learned</h4>
            <ul className="text-sm text-text-secondary space-y-1.5 list-disc list-inside">
              <li>Instagram Reels drive 71% of campaign revenue — prioritize short-form video.</li>
              <li>Micro creators deliver superior CPA efficiency vs mid-tier alternatives.</li>
              <li>Early budget reallocation prevented ₹18K in wasted spend.</li>
            </ul>
          </div>
          <div className="rounded-xl border border-primary/20 bg-primary-soft/30 p-4">
            <h4 className="text-sm font-semibold mb-2 text-primary">Next Recommendations</h4>
            <ul className="text-sm space-y-1.5 list-disc list-inside">
              <li>Scale NehaBeauty allocation by ₹6,000 based on 4.1x ROAS.</li>
              <li>Reduce RiyaStyle spend and reallocate to top performers.</li>
              <li>Launch Men&apos;s Skincare Pilot with approved creator mix.</li>
            </ul>
          </div>
        </section>
      </CardContent>
    </Card>
  )
}
