import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  CheckCircle2,
  ShieldAlert,
  Sparkles,
  TrendingUp,
  XCircle,
} from 'lucide-react'
import { optimizations } from '@/mock-data'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, useToast } from '@/components/ui'
import { cn, formatINR } from '@/utils'
import type { OptimizationRec } from '@/types'

const extraRecommendations: OptimizationRec[] = [
  {
    id: 'opt-2',
    title: 'Creator Mix Adjustment',
    current: { creator: 'SaraGlows', remaining: 12000, roas: 2.43 },
    moves: [
      { to: 'MayaSkincare', amount: 5000 },
      { to: 'NehaBeauty', amount: 3000 },
    ],
    expectedRevenue: '₹18,000–₹22,000',
    confidence: 82,
    status: 'pending',
  },
  {
    id: 'opt-3',
    title: 'Platform Budget Shift',
    current: { creator: 'YouTube (KabirWellness)', remaining: 28000, roas: 2.21 },
    moves: [{ to: 'Instagram Reels', amount: 8000 }],
    expectedRevenue: '₹24,000–₹29,000',
    confidence: 78,
    status: 'pending',
  },
]

const allRecommendations = [...optimizations, ...extraRecommendations]

export function OptimizationPage() {
  const { toast } = useToast()
  const [recStatuses, setRecStatuses] = useState<Record<string, OptimizationRec['status']>>(() =>
    Object.fromEntries(allRecommendations.map((r) => [r.id, r.status])),
  )

  const handleAction = (id: string, action: 'approved' | 'rejected' | 'modified') => {
    setRecStatuses((prev) => ({ ...prev, [id]: action === 'modified' ? 'pending' : action }))
    const messages = {
      approved: {
        title: 'Recommendation approved',
        description: 'Sent to Approval Center for final review before budget changes apply.',
        type: 'success' as const,
      },
      rejected: {
        title: 'Recommendation rejected',
        description: 'Optimization Agent will learn from this decision.',
        type: 'info' as const,
      },
      modified: {
        title: 'Modification saved',
        description: 'Your changes have been noted. Re-submit when ready for approval.',
        type: 'warning' as const,
      },
    }
    toast(messages[action])
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-[32px] font-bold tracking-tight">Optimization Center</h1>
        <p className="text-text-secondary mt-1">
          AI-powered recommendations to improve campaign ROI.
        </p>
      </div>

      <Card className="border-l-4 border-l-warning bg-amber-50/30">
        <CardContent className="py-4 flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="flex items-start gap-3 flex-1">
            <div className="h-10 w-10 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center shrink-0">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold text-text">Human approval required for money changes</p>
              <p className="text-sm text-text-secondary mt-1 leading-relaxed">
                All budget reallocations, rate adjustments, and spend modifications require your explicit approval
                before the Optimization Agent executes changes. No financial actions are applied automatically.
              </p>
            </div>
          </div>
          <Link to="/app/approvals">
            <Button variant="secondary" className="gap-2 shrink-0">
              Approval Center <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </CardContent>
      </Card>

      <div className="flex items-center gap-2 text-sm text-text-secondary">
        <Sparkles className="h-4 w-4 text-ai" />
        {allRecommendations.filter((r) => recStatuses[r.id] === 'pending').length} pending recommendations from
        Optimization Agent
      </div>

      <div className="grid gap-4">
        {allRecommendations.map((rec) => {
          const status = recStatuses[rec.id]
          const isResolved = status !== 'pending'

          return (
            <Card
              key={rec.id}
              className={cn(
                'overflow-hidden transition-opacity',
                isResolved && 'opacity-60',
              )}
            >
              <CardHeader className="border-b border-border bg-page/50">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-xl ai-gradient-bg text-white flex items-center justify-center">
                      <TrendingUp className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <CardTitle>{rec.title}</CardTitle>
                        <Badge variant="ai">AI Generated</Badge>
                        {status === 'approved' && (
                          <Badge variant="success">
                            <CheckCircle2 className="h-3 w-3" /> Approved
                          </Badge>
                        )}
                        {status === 'rejected' && (
                          <Badge variant="danger">
                            <XCircle className="h-3 w-3" /> Rejected
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-text-secondary mt-0.5">{rec.confidence}% confidence</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-text-secondary">Expected incremental revenue</p>
                    <p className="text-lg font-bold text-success">{rec.expectedRevenue}</p>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="pt-5 space-y-5">
                <div className="grid sm:grid-cols-[1fr_auto_1fr] gap-4 items-center">
                  <div className="rounded-[12px] border border-border bg-red-50/50 p-4">
                    <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide">Reduce from</p>
                    <p className="text-base font-bold mt-1">@{rec.current.creator}</p>
                    <div className="mt-2 flex flex-wrap gap-3 text-sm">
                      <span>
                        <span className="text-text-secondary">Remaining: </span>
                        <span className="font-semibold">{formatINR(rec.current.remaining)}</span>
                      </span>
                      <span>
                        <span className="text-text-secondary">ROAS: </span>
                        <span className="font-semibold text-danger">{rec.current.roas}x</span>
                      </span>
                    </div>
                  </div>

                  <ArrowRight className="h-5 w-5 text-text-secondary hidden sm:block" />

                  <div className="space-y-2">
                    <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide">Reallocate to</p>
                    {rec.moves.map((move) => (
                      <div
                        key={move.to}
                        className="rounded-[12px] border border-border bg-green-50/50 p-3 flex items-center justify-between"
                      >
                        <span className="font-semibold text-sm">@{move.to}</span>
                        <span className="text-sm font-bold text-success">+{formatINR(move.amount)}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {!isResolved && (
                  <div className="flex flex-wrap gap-2 pt-2 border-t border-border">
                    <Button variant="danger" size="sm" onClick={() => handleAction(rec.id, 'rejected')}>
                      <XCircle className="h-4 w-4" /> Reject
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => handleAction(rec.id, 'modified')}>
                      Modify
                    </Button>
                    <Button size="sm" onClick={() => handleAction(rec.id, 'approved')}>
                      <CheckCircle2 className="h-4 w-4" /> Approve Recommendation
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>

      <div className="text-center pt-2">
        <Link to="/app/approvals" className="text-sm font-semibold text-primary hover:underline inline-flex items-center gap-1">
          View all pending approvals in Approval Center <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </div>
  )
}
