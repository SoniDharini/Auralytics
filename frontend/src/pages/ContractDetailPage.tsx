import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowLeft,
  Bot,
  FileText,
  Send,
  Sparkles,
} from 'lucide-react'
import { contracts } from '@/mock-data'
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  Input,
  StatusChip,
} from '@/components/ui'
import { cn, formatINR } from '@/utils'

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

const FAKE_RESPONSES = [
  'Based on clause 4.2, the creator must deliver all assets within 48 hours of approval. Current timeline shows 4 days remaining.',
  'The exclusivity window runs for 30 days post-publication. No competing skincare brands are permitted during this period.',
  'Payment is net-15 after final deliverable approval. Given one pending deliverable, payment may be delayed by up to 7 days.',
  'Usage rights grant GlowNaturals 90-day organic and paid amplification across owned channels.',
]

export function ContractDetailPage() {
  const { id } = useParams<{ id: string }>()
  const contract = contracts.find((c) => c.id === id)
  const [question, setQuestion] = useState('')
  const [agentResponse, setAgentResponse] = useState<string | null>(null)

  if (!contract) {
    return (
      <EmptyState
        icon={FileText}
        title="Contract not found"
        description="This contract may have been removed or the link is incorrect."
        actionLabel="Back to Contracts"
        onAction={() => window.history.back()}
      />
    )
  }

  const handleAsk = (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim()) return
    const response = FAKE_RESPONSES[Math.floor(Math.random() * FAKE_RESPONSES.length)]
    setAgentResponse(response)
    setQuestion('')
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <Link
            to="/app/contracts"
            className="mt-1 inline-flex h-9 w-9 items-center justify-center rounded-[10px] border border-border bg-white text-text-secondary hover:bg-muted transition"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight">{contract.creator}</h1>
              <StatusChip status={contract.status} />
              <Badge variant={contract.risk === 'High' ? 'danger' : contract.risk === 'Medium' ? 'warning' : 'success'}>
                {contract.risk} Risk
              </Badge>
            </div>
            <p className="text-sm text-text-secondary mt-1">
              @{contract.username} · {contract.campaign} · {formatINR(contract.value)}
            </p>
          </div>
        </div>
      </div>

      <div className="grid xl:grid-cols-[1.1fr_1fr] gap-4">
        {/* PDF Preview Placeholder */}
        <Card className="overflow-hidden">
          <CardHeader className="border-b border-border bg-muted/40">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary" />
              <CardTitle>Contract Document</CardTitle>
            </div>
            <Badge variant="outline">PDF Preview</Badge>
          </CardHeader>
          <CardContent className="p-0">
            <div className="bg-[#fafafa] min-h-[520px] p-8">
              <div className="mx-auto max-w-md bg-white border border-border rounded-lg shadow-sm p-8 space-y-5">
                <div className="text-center border-b border-border pb-5">
                  <p className="text-[10px] uppercase tracking-widest text-text-secondary font-semibold">
                    Influencer Collaboration Agreement
                  </p>
                  <h2 className="text-lg font-bold mt-2">{contract.campaign}</h2>
                  <p className="text-xs text-text-secondary mt-1">GlowNaturals × @{contract.username}</p>
                </div>

                <div className="space-y-3 text-xs text-text-secondary leading-relaxed">
                  <p>
                    <span className="font-semibold text-text">Parties:</span> GlowNaturals Pvt. Ltd. and{' '}
                    {contract.creator} (&quot;Creator&quot;).
                  </p>
                  <p>
                    <span className="font-semibold text-text">Term:</span> {formatDate(contract.startDate)} to{' '}
                    {formatDate(contract.endDate)}.
                  </p>
                  <p>
                    <span className="font-semibold text-text">Compensation:</span> {formatINR(contract.value)}{' '}
                    payable by {formatDate(contract.paymentDue)}.
                  </p>
                  <p>
                    <span className="font-semibold text-text">Deliverables:</span>
                  </p>
                  <ul className="list-disc pl-4 space-y-1">
                    {contract.deliverables.map((d) => (
                      <li key={d}>{d}</li>
                    ))}
                  </ul>
                  <p>
                    <span className="font-semibold text-text">Usage Rights:</span> {contract.usageRights} from
                    publication date.
                  </p>
                  <p>
                    <span className="font-semibold text-text">Exclusivity:</span> {contract.exclusivity} in the
                    skincare category.
                  </p>
                </div>

                <div className="pt-4 border-t border-dashed border-border flex justify-between items-end">
                  <div className="space-y-1">
                    <div className="h-8 w-24 border-b border-text/30" />
                    <p className="text-[10px] text-text-secondary">GlowNaturals</p>
                  </div>
                  <div className="space-y-1 text-right">
                    <div className="h-8 w-24 border-b border-text/30 ml-auto" />
                    <p className="text-[10px] text-text-secondary">{contract.creator}</p>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* AI Summary Panel */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-lg bg-violet-50 text-ai flex items-center justify-center">
                  <Sparkles className="h-4 w-4" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <CardTitle>AI Contract Summary</CardTitle>
                    <Badge variant="ai">AI Generated</Badge>
                  </div>
                  <p className="text-xs text-text-secondary mt-0.5">Extracted by Contract Agent</p>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {[
                { label: 'Payment', value: `${formatINR(contract.value)} due ${formatDate(contract.paymentDue)}` },
                { label: 'Deliverables', value: contract.deliverables.join(', ') },
                { label: 'Deadline', value: formatDate(contract.endDate) },
                { label: 'Usage Rights', value: contract.usageRights },
                { label: 'Exclusivity', value: contract.exclusivity },
                { label: 'Payment Due', value: formatDate(contract.paymentDue) },
              ].map((item) => (
                <div key={item.label} className="flex flex-col sm:flex-row sm:items-start gap-1 sm:gap-4 py-2 border-b border-border last:border-0">
                  <span className="text-xs font-semibold text-text-secondary uppercase tracking-wide sm:w-32 shrink-0">
                    {item.label}
                  </span>
                  <span className="text-sm text-text">{item.value}</span>
                </div>
              ))}
            </CardContent>
          </Card>

          {contract.aiRisks.length > 0 && (
            <Card className="border-l-4 border-l-warning">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-warning" />
                  <CardTitle>AI Risks</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {contract.aiRisks.map((risk) => (
                  <div
                    key={risk}
                    className="flex items-start gap-3 rounded-[10px] bg-amber-50 border border-amber-100 px-3 py-2.5"
                  >
                    <Badge variant="warning" className="shrink-0 mt-0.5">
                      Warning
                    </Badge>
                    <p className="text-sm text-text">{risk}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Bot className="h-4 w-4 text-ai" />
                <CardTitle>Ask Contract Agent</CardTitle>
              </div>
              <p className="text-xs text-text-secondary">Quick questions about this agreement</p>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleAsk} className="flex gap-2">
                <Input
                  placeholder="e.g. What are the reshoot obligations?"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  className="flex-1"
                />
                <Button type="submit" size="icon" disabled={!question.trim()}>
                  <Send className="h-4 w-4" />
                </Button>
              </form>
              {agentResponse && (
                <div
                  className={cn(
                    'mt-3 rounded-[10px] border border-indigo-100 bg-indigo-50/60 px-3 py-2.5 text-sm text-text animate-fade-in',
                  )}
                >
                  <p className="text-xs font-semibold text-ai mb-1 flex items-center gap-1">
                    <Sparkles className="h-3 w-3" /> Contract Agent
                  </p>
                  {agentResponse}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
