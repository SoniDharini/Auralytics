import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  CheckCircle2,
  Plus,
  ShieldAlert,
  Sparkles,
  TrendingUp,
  XCircle,
} from 'lucide-react'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, useToast } from '@/components/ui'
import { cn, formatINR } from '@/utils'
import type { OptimizationRec } from '@/types'

export function OptimizationPage() {
  const { toast } = useToast()
  const [recommendations] = useState<OptimizationRec[]>([])
  const [recStatuses, setRecStatuses] = useState<Record<string, OptimizationRec['status']>>({})


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
      <header className="relative overflow-hidden rounded-[20px] border border-border bg-surface px-5 py-5 shadow-[0_8px_30px_rgba(17,24,39,0.04)] sm:px-6">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(1200px_circle_at_0%_-20%,rgba(91,95,239,0.10),transparent_45%),radial-gradient(800px_circle_at_100%_0%,rgba(139,92,246,0.08),transparent_40%)]" />
        <div className="relative flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">Optimization Agent</p>
            <h1 className="mt-1 text-[28px] font-bold tracking-tight sm:text-[32px]">What should we change?</h1>
            <p className="mt-1 text-text-secondary">
              AI recommends budget and creator adjustments. You decide before anything is applied.
            </p>
          </div>
          <Link to="/app/analytics">
            <Button variant="secondary" className="gap-2">
              View Analytics <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </header>

      <Card className="border-l-4 border-l-warning bg-amber-50/40">
        <CardContent className="py-4 flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="flex items-start gap-3 flex-1">
            <div className="h-10 w-10 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center shrink-0">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold text-text">AI recommends. You decide.</p>
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

      {recommendations.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center space-y-4">
            <div className="mx-auto h-14 w-14 rounded-2xl bg-violet-50 text-ai flex items-center justify-center">
              <Sparkles className="h-7 w-7" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-text">No optimization recommendations yet</h3>
              <p className="text-sm text-text-secondary mt-1 max-w-md mx-auto">
                Optimization Agent will analyze performance and recommend creator mix or budget adjustments once active campaigns begin collecting data. Approve, modify, or reject will appear here when recommendations exist — nothing is applied automatically.
              </p>
            </div>
            <Link to="/app/campaigns/new" className="inline-block mt-2">
              <Button size="lg" className="gap-2">
                <Plus className="h-4 w-4" /> Create Campaign
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {recommendations.map((rec) => {
            const status = recStatuses[rec.id] || rec.status
            const isResolved = status !== 'pending'

            return (
              <Card
                key={rec.id}
                className={cn('overflow-hidden transition-opacity', isResolved && 'opacity-60')}
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
      )}
    </div>
  )
}
