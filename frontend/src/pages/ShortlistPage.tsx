import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, Loader2, Sparkles, Users, Wand2 } from 'lucide-react'
import { api } from '@/services/api'
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
import type { Influencer } from '@/types'

export function ShortlistPage() {
  const { toast } = useToast()
  const [shortlisted, setShortlisted] = useState<Influencer[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    api.influencers
      .list('shortlisted=true')
      .then((data) => {
        if (mounted && data) {
          setShortlisted(data.filter((i) => i.shortlisted))
        }
      })
      .catch(() => {
        setShortlisted([])
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })

    return () => {
      mounted = false
    }
  }, [])

  const totals = useMemo(() => {
    const selected = shortlisted.length
    const expectedSpend = shortlisted.reduce((s, i) => s + (i.estimatedCost || 0), 0)
    const predictedRevenue = expectedSpend * 2.8
    const predictedRoas = expectedSpend > 0 ? 2.8 : 0
    return { selected, expectedSpend, predictedRevenue, predictedRoas }
  }, [shortlisted])

  const handleApprove = () => {
    if (shortlisted.length === 0) return
    toast({
      type: 'success',
      title: 'Shortlist approved',
      description: `Outreach Agent will begin preparing personalized messages for ${shortlisted.length} creator${shortlisted.length !== 1 ? 's' : ''}.`,
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
            Review and approve shortlisted creators for your campaigns.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" className="gap-2" disabled={shortlisted.length === 0}>
            <Wand2 className="h-4 w-4" /> Optimize Selection
          </Button>
          <Button className="gap-2" onClick={handleApprove} disabled={shortlisted.length === 0}>
            Approve Shortlist
          </Button>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: 'Selected', value: String(totals.selected) },
          { label: 'Expected Spend', value: formatINR(totals.expectedSpend, true) },
          { label: 'Predicted Revenue', value: formatINR(totals.predictedRevenue, true) },
          { label: 'Predicted ROAS', value: `${totals.predictedRoas.toFixed(2)}x` },
        ].map((s) => (
          <Card key={s.label} className="p-4">
            <p className="text-xs text-text-secondary">{s.label}</p>
            <p className="text-2xl font-bold mt-1">{s.value}</p>
          </Card>
        ))}
      </div>

      {shortlisted.length > 0 && (
        <div className="flex items-start gap-3 rounded-[12px] border border-violet-100 bg-violet-50/60 px-4 py-3">
          <Sparkles className="h-4 w-4 text-ai mt-0.5 shrink-0" />
          <p className="text-sm text-text">
            <span className="font-semibold text-ai">AI Recommendation: </span>
            This creator mix provides balanced engagement and audience fit for your target campaign demographics.
          </p>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Shortlisted Creators</CardTitle>
        </CardHeader>
        <CardContent>
          {loading && (
            <div className="py-12 flex justify-center items-center gap-2 text-text-secondary text-sm">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <span>Loading shortlist...</span>
            </div>
          )}

          {!loading && shortlisted.length === 0 && (
            <div className="text-center py-12 text-text-secondary">
              <Users className="h-10 w-10 mx-auto text-text-secondary/40 mb-3" />
              <p className="font-semibold text-text">No shortlisted creators yet</p>
              <p className="text-sm mt-1">Discover and shortlist creators from the Discovery catalog to begin campaign outreach.</p>
              <Link to="/app/discovery" className="inline-block mt-4">
                <Button size="sm" variant="soft">
                  Open Discovery Catalog
                </Button>
              </Link>
            </div>
          )}

          {!loading && shortlisted.length > 0 && (
            <div className="overflow-x-auto">
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
                        <span className="font-semibold text-ai">{inf.aiMatchScore ? `${inf.aiMatchScore}%` : '—'}</span>
                      </td>
                      <td className="py-3.5 pr-3">
                        <span className="font-semibold text-primary">{inf.predictedRoas ? `${inf.predictedRoas}x` : '—'}</span>
                      </td>
                      <td className="py-3.5 pr-3">{inf.audienceFit ? `${inf.audienceFit}%` : '—'}</td>
                      <td className="py-3.5 pr-3">
                        {inf.estimatedCost ? formatINR(inf.estimatedCost, true) : 'Not Available'}
                      </td>
                      <td className="py-3.5">
                        <StatusChip status={inf.status ?? 'not_contacted'} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
