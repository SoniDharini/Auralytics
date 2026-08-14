import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Bot,
  FileText,
  Loader2,
  Sparkles,
} from 'lucide-react'
import { api } from '@/services/api'
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  Input,
  StatusChip,
} from '@/components/ui'
import { formatINR } from '@/utils'
import type { Contract } from '@/types'


function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    })
  } catch {
    return dateStr
  }
}

export function ContractDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [contract, setContract] = useState<Contract | null>(null)
  const [loading, setLoading] = useState(true)
  const [question, setQuestion] = useState('')
  const [agentResponse, setAgentResponse] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    api.contracts
      .get(id)
      .then((data) => {
        setContract(data)
      })
      .catch(() => {
        setContract(null)
      })
      .finally(() => {
        setLoading(false)
      })
  }, [id])

  if (loading) {
    return (
      <div className="py-24 flex flex-col justify-center items-center gap-3 text-text-secondary text-sm">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p>Loading contract details...</p>
      </div>
    )
  }

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
    setAgentResponse(
      `Contract Agent review: Terms for ${contract.creator} specify ${contract.usageRights || 'standard digital rights'} under campaign ${contract.campaign}.`,
    )
  }

  return (
    <div className="space-y-6 animate-fade-in max-w-5xl">
      <div className="flex items-center gap-3">
        <Link
          to="/app/contracts"
          className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-white text-text-secondary hover:bg-page hover:text-text transition"
          aria-label="Back to contracts"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight truncate">{contract.creator}</h1>
            <StatusChip status={contract.status} />
          </div>
          <p className="text-sm text-text-secondary mt-0.5">
            @{contract.username} · {contract.campaign}
          </p>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Agreement Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-text-secondary font-medium uppercase tracking-wide">Contract Value</p>
                  <p className="text-xl font-bold text-text mt-1">{formatINR(contract.value)}</p>
                </div>
                <div>
                  <p className="text-xs text-text-secondary font-medium uppercase tracking-wide">Payment Due</p>
                  <p className="text-base font-semibold text-text mt-1">{formatDate(contract.paymentDue)}</p>
                </div>
              </div>

              <div className="grid sm:grid-cols-2 gap-4 pt-3 border-t border-border">
                <div>
                  <p className="text-xs text-text-secondary font-medium uppercase tracking-wide">Start Date</p>
                  <p className="font-medium text-text mt-0.5">{formatDate(contract.startDate)}</p>
                </div>
                <div>
                  <p className="text-xs text-text-secondary font-medium uppercase tracking-wide">End Date</p>
                  <p className="font-medium text-text mt-0.5">{formatDate(contract.endDate)}</p>
                </div>
              </div>

              <div className="pt-3 border-t border-border">
                <p className="text-xs text-text-secondary font-medium uppercase tracking-wide mb-2">Deliverables</p>
                <ul className="space-y-1.5 list-disc list-inside text-text">
                  {contract.deliverables?.map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
              </div>

              <div className="grid sm:grid-cols-2 gap-4 pt-3 border-t border-border">
                <div>
                  <p className="text-xs text-text-secondary font-medium uppercase tracking-wide">Usage Rights</p>
                  <p className="font-medium text-text mt-0.5">{contract.usageRights || 'Standard digital rights'}</p>
                </div>
                <div>
                  <p className="text-xs text-text-secondary font-medium uppercase tracking-wide">Exclusivity</p>
                  <p className="font-medium text-text mt-0.5">{contract.exclusivity || 'Non-exclusive'}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Bot className="h-4 w-4 text-ai" />
                <CardTitle>Ask Contract Agent</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <form onSubmit={handleAsk} className="space-y-3">
                <Input
                  placeholder="e.g. When are deliverables due?"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                />
                <Button type="submit" size="sm" variant="ai" className="w-full gap-1.5">
                  <Sparkles className="h-3.5 w-3.5" /> Ask AI Agent
                </Button>
              </form>

              {agentResponse && (
                <div className="rounded-xl border border-violet-100 bg-violet-50/50 p-3 text-xs leading-relaxed">
                  <p className="font-semibold text-ai mb-1">Contract Agent Response:</p>
                  <p className="text-text">{agentResponse}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
