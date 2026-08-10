import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, Sparkles, Wand2 } from 'lucide-react'
import { influencers } from '@/mock-data'
import {
  Avatar,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  StatusChip,
  useToast,
} from '@/components/ui'
import { formatINR } from '@/utils'

const SUMMARY = {
  selected: 8,
  expectedSpend: 142000,
  predictedRevenue: 431000,
  predictedRoas: 3.03,
  budgetRemaining: 58000,
}

export function ShortlistPage() {
  const { toast } = useToast()

  const shortlisted = useMemo(
    () => influencers.filter((i) => i.shortlisted),
    [],
  )

  const handleApprove = () => {
    toast({
      type: 'success',
      title: 'Shortlist approved',
      description: 'Outreach Agent will begin preparing personalized messages for 8 creators.',
    })
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <Link
            to="/app/discovery"
            className="inline-flex items-center gap-1.5 text-sm font-semibold text-text-secondary hover:text-primary transition mb-2"
          >
            <ArrowLeft className="h-4 w-4" /> Back to Discovery
          </Link>
          <h1 className="text-[28px] font-bold tracking-tight">Campaign Shortlist</h1>
          <p className="text-text-secondary mt-1">
            Review AI-selected creators for GlowNaturals Summer Launch
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" className="gap-2">
            <Wand2 className="h-4 w-4" /> Optimize Selection
          </Button>
          <Button className="gap-2" onClick={handleApprove}>
            Approve Shortlist
          </Button>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: 'Selected', value: String(SUMMARY.selected) },
          { label: 'Expected Spend', value: formatINR(SUMMARY.expectedSpend, true) },
          { label: 'Predicted Revenue', value: formatINR(SUMMARY.predictedRevenue, true) },
          { label: 'Predicted ROAS', value: `${SUMMARY.predictedRoas}x` },
        ].map((s) => (
          <Card key={s.label} className="p-4">
            <p className="text-xs text-text-secondary">{s.label}</p>
            <p className="text-2xl font-bold mt-1">{s.value}</p>
          </Card>
        ))}
      </div>

      <div className="flex items-start gap-3 rounded-[12px] border border-violet-100 bg-violet-50/60 px-4 py-3">
        <Sparkles className="h-4 w-4 text-ai mt-0.5 shrink-0" />
        <p className="text-sm text-text">
          <span className="font-semibold text-ai">AI Recommendation: </span>
          This combination provides strong audience coverage while remaining{' '}
          <span className="font-semibold">{formatINR(SUMMARY.budgetRemaining)}</span> under budget.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Shortlisted Creators</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-text-secondary border-b border-border">
                <th className="pb-3 font-semibold">Influencer</th>
                <th className="pb-3 font-semibold">Match Score</th>
                <th className="pb-3 font-semibold">Predicted ROAS</th>
                <th className="pb-3 font-semibold">Audience Fit</th>
                <th className="pb-3 font-semibold">Cost</th>
                <th className="pb-3 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {shortlisted.map((inf) => (
                <tr key={inf.id} className="border-b border-border last:border-0 hover:bg-page/80">
                  <td className="py-3.5 pr-3">
                    <div className="flex items-center gap-3">
                      <Avatar name={inf.name} size="sm" />
                      <div>
                        <Link
                          to={`/app/discovery/${inf.id}`}
                          className="font-semibold hover:text-primary"
                        >
                          {inf.name}
                        </Link>
                        <p className="text-xs text-text-secondary">@{inf.username}</p>
                      </div>
                    </div>
                  </td>
                  <td className="py-3.5 pr-3">
                    <span className="font-semibold text-ai">{inf.aiMatchScore}%</span>
                  </td>
                  <td className="py-3.5 pr-3">
                    <span className="font-semibold text-primary">{inf.predictedRoas}x</span>
                  </td>
                  <td className="py-3.5 pr-3">{inf.audienceFit}%</td>
                  <td className="py-3.5 pr-3">{formatINR(inf.estimatedCost, true)}</td>
                  <td className="py-3.5">
                    <StatusChip status={inf.status ?? 'not_contacted'} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  )
}
