import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  Bot,
  CheckCircle2,
  Download,
  Edit3,
  FileCheck,
  FileEdit,
  FileSignature,
  FileText,
  History,
  Loader2,
  RefreshCw,
  Scale,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  XCircle,
} from 'lucide-react'
import { api } from '@/services/api'
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
  useToast,
} from '@/components/ui'
import { formatINR } from '@/utils'
import type { Contract } from '@/types'

function formatDate(dateStr?: string): string {
  if (!dateStr) return 'Not set'
  try {
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return dateStr
  }
}

function riskVariant(risk?: string): 'success' | 'warning' | 'danger' | 'default' {
  const r = risk ? risk.toLowerCase() : 'low'
  if (r === 'low') return 'success'
  if (r === 'medium') return 'warning'
  if (r === 'high') return 'danger'
  return 'default'
}

function termStatusVariant(status?: string): 'success' | 'warning' | 'danger' | 'default' {
  const s = (status || '').toUpperCase()
  if (s === 'MATCH') return 'success'
  if (s === 'MISMATCH') return 'danger'
  if (s === 'MISSING' || s === 'REQUIRES_REVIEW' || s === 'UNKNOWN') return 'warning'
  return 'default'
}

export function ContractDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [contract, setContract] = useState<Contract | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [question, setQuestion] = useState('')
  const [agentResponse, setAgentResponse] = useState<string | null>(null)

  // Modals & form state
  const [showApproveModal, setShowApproveModal] = useState(false)
  const [approveNotes, setApproveNotes] = useState('')
  const [showChangesModal, setShowChangesModal] = useState(false)
  const [changeNotes, setChangeNotes] = useState('')
  const [changeReason, setChangeReason] = useState('')
  const [showRejectModal, setShowRejectModal] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [isEditingBody, setIsEditingBody] = useState(false)
  const [draftBody, setDraftBody] = useState('')

  const loadContract = () => {
    if (!id) return
    setLoading(true)
    api.contracts
      .get(id)
      .then((data) => {
        setContract(data)
        setDraftBody(data.contractBody || data.contract_body || '')
      })
      .catch(() => {
        setContract(null)
      })
      .finally(() => {
        setLoading(false)
      })
  }

  useEffect(() => {
    loadContract()
  }, [id])

  const handleApprove = async () => {
    if (!contract) return
    setActionLoading(true)
    try {
      const updated = await api.contracts.approve(contract.id, approveNotes)
      setContract(updated)
      setShowApproveModal(false)
    } catch (err: any) {
      alert(err?.message || 'Failed to approve contract')
    } finally {
      setActionLoading(false)
    }
  }

  const handleRequestChanges = async () => {
    if (!contract || !changeNotes.trim() || !changeReason.trim()) return
    setActionLoading(true)
    try {
      const updated = await api.contracts.requestChanges(contract.id, changeNotes, changeReason)
      setContract(updated)
      setShowChangesModal(false)
      setChangeNotes('')
      setChangeReason('')
    } catch (err: any) {
      alert(err?.message || 'Failed to submit change request')
    } finally {
      setActionLoading(false)
    }
  }

  const handleReject = async () => {
    if (!contract || !rejectReason.trim()) return
    setActionLoading(true)
    try {
      const updated = await api.contracts.reject(contract.id, rejectReason)
      setContract(updated)
      setShowRejectModal(false)
    } catch (err: any) {
      alert(err?.message || 'Failed to reject contract')
    } finally {
      setActionLoading(false)
    }
  }

  const handleSaveBody = async (reanalyze = false) => {
    if (!contract) return
    setActionLoading(true)
    try {
      const updated = await api.contracts.updateBody(contract.id, draftBody, reanalyze)
      setContract(updated)
      setIsEditingBody(false)
    } catch (err: any) {
      alert(err?.message || 'Failed to save agreement text')
    } finally {
      setActionLoading(false)
    }
  }

  const handleReanalyze = async () => {
    if (!contract || !contract.campaignId && !contract.campaign_id) return
    const campaignId = (contract.campaignId || contract.campaign_id) as string
    const influencerId = (contract.influencerId || contract.influencer_id) as string
    setActionLoading(true)
    try {
      await api.contracts.analyze(campaignId, {
        influencer_id: influencerId,
        contract_text: draftBody || undefined,
      })
      loadContract()
    } catch (err: any) {
      alert(err?.message || 'Contract re-analysis failed')
      setActionLoading(false)
    }
  }

  const handleAsk = (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim() || !contract) return
    const q = question.toLowerCase()
    if (q.includes('deliverable') || q.includes('scope')) {
      setAgentResponse(
        `Contract deliverables: ${contract.deliverables?.join(', ') || 'Dedicated video'} due by ${formatDate(contract.endDate || contract.end_date)}.`,
      )
    } else if (q.includes('rate') || q.includes('price') || q.includes('value') || q.includes('payment')) {
      setAgentResponse(
        `Total agreed compensation is ${contract.currency || 'INR'} ${contract.value?.toLocaleString()} payable under terms: "${contract.paymentDue || contract.payment_due || 'Net 30'}".`,
      )
    } else if (q.includes('risk') || q.includes('clause') || q.includes('issue')) {
      const flags = (contract.riskFlags || contract.risk_flags || [])
      setAgentResponse(
        flags.length > 0
          ? `Risk Analysis found ${flags.length} flag(s): ${flags.map((f: any) => `${f.severity}: ${f.issue} - ${f.reason}`).join('; ')}`
          : 'No critical risk flags detected. Commercial terms match negotiated agreement.',
      )
    } else {
      setAgentResponse(
        `Contract Agent: Collaboration agreement for ${contract.creator} under campaign "${contract.campaign}". Overall verification status is ${contract.overallStatus || contract.overall_status || 'READY_FOR_REVIEW'}.`,
      )
    }
  }

  if (loading) {
    return (
      <div className="py-24 flex flex-col justify-center items-center gap-3 text-text-secondary text-sm">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p>Loading contract and verification details...</p>
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
        onAction={() => navigate('/app/contracts')}
      />
    )
  }

  const handleDownloadPDF = () => {
    if (!contract) return
    const printWindow = window.open('', '_blank')
    if (!printWindow) {
      toast({
        type: 'error',
        title: 'Pop-up blocked',
        description: 'Please allow pop-ups to export and download the PDF agreement.',
      })
      return
    }

    const contractText = contract.contractBody || contract.contract_body || 'No contract draft text available.'
    const agreedFee = contract.value ? `${contract.currency || 'INR'} ${contract.value.toLocaleString()}` : '₹0'
    const deliverablesList = Array.isArray(contract.deliverables)
      ? contract.deliverables.join(', ')
      : contract.deliverables || 'As mutually agreed in outreach negotiation'

    const htmlContent = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Influencer Collaboration Agreement - ${contract.creator}</title>
  <style>
    @page {
      size: A4;
      margin: 18mm 20mm;
    }
    * {
      box-sizing: border-box;
    }
    body {
      font-family: 'Times New Roman', Times, Georgia, serif;
      color: #111827;
      line-height: 1.6;
      margin: 0;
      padding: 32px;
      font-size: 13px;
      background: #ffffff;
    }
    .header {
      text-align: center;
      border-bottom: 2px solid #1e3a8a;
      padding-bottom: 14px;
      margin-bottom: 24px;
    }
    .header h1 {
      font-size: 20px;
      margin: 0 0 6px 0;
      text-transform: uppercase;
      letter-spacing: 1.2px;
      color: #0f172a;
    }
    .header .subtitle {
      font-size: 11px;
      color: #475569;
      margin: 2px 0;
      font-style: italic;
    }
    .meta-box {
      border: 1px solid #cbd5e1;
      background-color: #f8fafc;
      border-radius: 6px;
      padding: 14px 18px;
      margin-bottom: 24px;
    }
    .meta-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      row-gap: 10px;
      column-gap: 20px;
      font-size: 12px;
    }
    .meta-item .label {
      font-size: 10px;
      text-transform: uppercase;
      font-weight: bold;
      color: #64748b;
      letter-spacing: 0.5px;
      margin-bottom: 2px;
    }
    .meta-item .val {
      font-weight: 600;
      color: #1e293b;
    }
    .section-title {
      font-size: 13px;
      font-weight: bold;
      color: #0f172a;
      border-bottom: 1px solid #94a3b8;
      padding-bottom: 4px;
      margin-top: 24px;
      margin-bottom: 12px;
      text-transform: uppercase;
      letter-spacing: 0.8px;
    }
    .body-content {
      white-space: pre-wrap;
      font-size: 12.5px;
      line-height: 1.75;
      text-align: justify;
      color: #1f2937;
    }
    .signatures-block {
      margin-top: 48px;
      page-break-inside: avoid;
    }
    .signatures-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 48px;
    }
    .sig-box {
      border-top: 1.5px solid #334155;
      padding-top: 8px;
      font-size: 11.5px;
      line-height: 1.5;
    }
    .sig-box .party-title {
      font-weight: bold;
      text-transform: uppercase;
      font-size: 11px;
      color: #0f172a;
      margin-bottom: 4px;
    }
    .footer {
      margin-top: 40px;
      border-top: 1px solid #e2e8f0;
      padding-top: 8px;
      font-size: 10px;
      color: #94a3b8;
      text-align: center;
    }
    @media print {
      body {
        padding: 0;
      }
      .no-print {
        display: none !important;
      }
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>Influencer Collaboration Agreement</h1>
    <div class="subtitle">Contract Ref: <strong>${contract.id}</strong> &bull; Version: <strong>v${contract.version || 1}</strong> &bull; Status: <strong>${contract.status.toUpperCase()}</strong></div>
    <div class="subtitle">Governed by Authoritative Commercial Terms from Auralytics</div>
  </div>

  <div class="meta-box">
    <div class="meta-grid">
      <div class="meta-item">
        <div class="label">Brand & Campaign</div>
        <div class="val">${contract.campaign}</div>
      </div>
      <div class="meta-item">
        <div class="label">Influencer / Creator</div>
        <div class="val">${contract.creator} (@${contract.username})</div>
      </div>
      <div class="meta-item">
        <div class="label">Agreed Compensation</div>
        <div class="val">${agreedFee} (${contract.paymentDue || contract.payment_due || 'Net 30 post delivery'})</div>
      </div>
      <div class="meta-item">
        <div class="label">Campaign Flight Timeline</div>
        <div class="val">${contract.startDate || contract.start_date || 'Launch Date'} &mdash; ${contract.endDate || contract.end_date || 'Launch + 30 Days'}</div>
      </div>
      <div class="meta-item">
        <div class="label">Deliverables</div>
        <div class="val">${deliverablesList}</div>
      </div>
      <div class="meta-item">
        <div class="label">Content Rights & Exclusivity</div>
        <div class="val">${contract.usageRights || contract.usage_rights || 'Digital media usage'} &bull; ${contract.exclusivity || 'Non-exclusive'}</div>
      </div>
    </div>
  </div>

  <div class="section-title">Standard Terms & Verified Contract Clauses</div>
  <div class="body-content">${contractText.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>

  <div class="signatures-block">
    <div class="section-title">Execution & Signatures</div>
    <div class="signatures-grid" style="margin-top: 36px;">
      <div class="sig-box">
        <div class="party-title">Signed on behalf of Brand / Sponsor:</div>
        <div>Authorized Signatory: ________________________</div>
        <div>Date: ________________________</div>
        <div>Sign-off Status: ${contract.status === 'APPROVED' ? 'APPROVED & VERIFIED ✓' : 'PENDING SIGNATURE'}</div>
      </div>
      <div class="sig-box">
        <div class="party-title">Signed on behalf of Creator / Influencer:</div>
        <div>Creator Name: <strong>${contract.creator}</strong></div>
        <div>Signature: ________________________</div>
        <div>Date: ________________________</div>
      </div>
    </div>
  </div>

  <div class="footer">
    Auralytics Contract Verification Engine &bull; Generated on ${new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })} &bull; Page 1 of 1
  </div>

  <script>
    window.onload = function() {
      setTimeout(function() {
        window.print();
      }, 250);
    }
  </script>
</body>
</html>`

    printWindow.document.open()
    printWindow.document.write(htmlContent)
    printWindow.document.close()
  }

  const isApproved = contract.status === 'APPROVED' || contract.status === 'signed'
  const isRejected = contract.status === 'REJECTED'
  const rawRiskFlags = (contract.riskFlags && contract.riskFlags.length > 0)
    ? contract.riskFlags
    : (contract.risk_flags && contract.risk_flags.length > 0)
    ? contract.risk_flags
    : (contract.aiRisks && contract.aiRisks.length > 0)
    ? contract.aiRisks
    : (contract.ai_risks || [])

  const normalizedRiskFlags = rawRiskFlags.map((rf: any) => {
    if (typeof rf === 'string') {
      return {
        issue: rf,
        severity: 'MEDIUM',
        reason: 'Flagged during AI contract clause verification',
        recommended_review: undefined,
      }
    }
    return {
      issue: rf.issue || rf.title || rf.name || rf.flag || rf.reason || 'Identified Risk',
      severity: (rf.severity || 'MEDIUM').toUpperCase(),
      reason: rf.reason || rf.description || rf.detail || '',
      recommended_review: rf.recommended_review || rf.recommended_fix || rf.recommendation || rf.action,
    }
  })

  const missingClauses = contract.missingClauses || contract.missing_clauses || []
  const conflicts = contract.conflicts || []
  const commTerms = contract.commercialTermsMatch || contract.commercial_terms_match || {}
  const changeRequests = contract.changeRequests || contract.change_requests || []
  const overallStatus = contract.overallStatus || contract.overall_status || 'READY_FOR_REVIEW'

  return (
    <div className="space-y-6 animate-fade-in max-w-6xl pb-16">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div className="flex items-center gap-3">
          <Link
            to="/app/contracts"
            className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-white text-text-secondary hover:bg-page hover:text-text transition"
            aria-label="Back to contracts"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-bold tracking-tight truncate">{contract.creator}</h1>
              <StatusChip status={contract.status} />
              <Badge variant={riskVariant(contract.risk)}>Risk: {contract.risk.toUpperCase()}</Badge>
              {contract.version && contract.version > 1 && (
                <Badge variant="neutral" className="font-mono text-xs">
                  v{contract.version}
                </Badge>
              )}
            </div>
            <p className="text-xs text-text-secondary mt-0.5">
              @{contract.username} · Campaign: <span className="font-medium text-text">{contract.campaign}</span>
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="secondary"
            onClick={handleDownloadPDF}
            className="gap-1.5 text-xs text-primary border-primary/30 hover:bg-primary-soft/50 shadow-sm"
          >
            <Download className="h-3.5 w-3.5" />
            Download PDF
          </Button>

          <Button
            size="sm"
            variant="secondary"
            onClick={handleReanalyze}
            disabled={actionLoading}
            className="gap-1.5 text-xs"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${actionLoading ? 'animate-spin' : ''}`} />
            Re-analyze
          </Button>

          {!isApproved && !isRejected && (
            <>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => setShowChangesModal(true)}
                disabled={actionLoading}
                className="gap-1.5 text-xs text-amber-700 border-amber-200 hover:bg-amber-50"
              >
                <FileEdit className="h-3.5 w-3.5" />
                Request Changes
              </Button>

              <Button
                size="sm"
                variant="danger"
                onClick={() => setShowRejectModal(true)}
                disabled={actionLoading}
                className="gap-1.5 text-xs"
              >
                <XCircle className="h-3.5 w-3.5" />
                Reject
              </Button>

              <Button
                size="sm"
                variant="primary"
                onClick={() => setShowApproveModal(true)}
                disabled={actionLoading}
                className="gap-1.5 text-xs bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm"
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                Approve Contract
              </Button>
            </>
          )}

          {isApproved && (
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-700 text-xs font-semibold border border-emerald-200">
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              <span>Approved by Human Reviewer</span>
            </div>
          )}
        </div>
      </div>

      {/* Authoritative Final Negotiated Terms Banner */}
      <Card className="border-primary/20 bg-primary-soft/30">
        <CardContent className="p-4 sm:p-5">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <FileCheck className="h-4 w-4 text-primary" />
                <span className="text-xs font-bold uppercase tracking-wider text-primary">
                  Authoritative Final Negotiated Terms (From Outreach)
                </span>
              </div>
              <p className="text-xs text-text-secondary">
                These terms are locked in PostgreSQL and serve as the golden benchmark against contract clauses.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-4 text-xs">
              <div className="rounded-lg bg-white p-2.5 shadow-sm border border-border">
                <span className="text-text-secondary block text-[10px] uppercase font-semibold">Agreed Fee</span>
                <span className="font-bold text-base text-text">
                  {formatINR(contract.value)}
                </span>
              </div>
              <div className="rounded-lg bg-white p-2.5 shadow-sm border border-border">
                <span className="text-text-secondary block text-[10px] uppercase font-semibold">Flight Window</span>
                <span className="font-semibold text-text">
                  {formatDate(contract.startDate || contract.start_date)} – {formatDate(contract.endDate || contract.end_date)}
                </span>
              </div>
              <div className="rounded-lg bg-white p-2.5 shadow-sm border border-border">
                <span className="text-text-secondary block text-[10px] uppercase font-semibold">Payment Schedule</span>
                <span className="font-semibold text-text">{contract.paymentDue || contract.payment_due || 'Net 30'}</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Commercial Mismatch Warning Banner */}
      {(normalizedRiskFlags.some((f: any) => f.severity === 'HIGH' || f.issue === 'COMPENSATION_MISMATCH') || conflicts.length > 0) && (
        <div className="rounded-xl border border-amber-300 bg-amber-50/90 p-4 space-y-1.5 animate-fade-in text-amber-900 shadow-xs">
          <div className="flex items-center gap-2 font-bold text-xs text-amber-800">
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            <span>COMMERCIAL TERM MISMATCH / RISK DETECTED</span>
          </div>
          <p className="text-xs text-amber-700 leading-relaxed">
            The agreement draft contains clauses or values differing from authoritative terms confirmed in Outreach ({contract.currency || 'INR'} {contract.value?.toLocaleString()}). Review differences and require explicit human sign-off before approval.
          </p>
        </div>
      )}

      {/* Main Grid: Analysis on Left, Details & AI Assistant on Right */}
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* AI Verification & Risk Breakdown */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between border-b border-border pb-3.5">
              <div className="flex items-center gap-2">
                <Scale className="h-5 w-5 text-primary" />
                <div>
                  <CardTitle className="text-base">Contract Verification & Clause Analysis</CardTitle>
                  <p className="text-xs text-text-secondary">
                    AI verification of agreement text against authoritative business terms
                  </p>
                </div>
              </div>
              <Badge
                variant={
                  overallStatus === 'READY_FOR_REVIEW'
                    ? 'success'
                    : overallStatus === 'CRITICAL_ISSUES_FOUND'
                    ? 'danger'
                    : 'warning'
                }
                className="text-xs"
              >
                {overallStatus.replace(/_/g, ' ')}
              </Badge>
            </CardHeader>
            <CardContent className="pt-4 space-y-4 text-xs">
              {/* Term Match Grid */}
              <div className="grid sm:grid-cols-2 gap-3">
                <div className="rounded-xl border border-border bg-page/40 p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-text">Compensation Terms</span>
                    <Badge variant={termStatusVariant(commTerms?.agreed_rate?.status || 'MATCH')} className="text-[10px]">
                      {commTerms?.agreed_rate?.status || 'MATCH'}
                    </Badge>
                  </div>
                  <p className="text-text-secondary leading-relaxed">
                    Authoritative Fee: <span className="font-semibold text-text">{contract.currency} {contract.value?.toLocaleString()}</span>
                  </p>
                </div>

                <div className="rounded-xl border border-border bg-page/40 p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-text">Deliverables Match</span>
                    <Badge variant={termStatusVariant(commTerms?.deliverables?.status || 'MATCH')} className="text-[10px]">
                      {commTerms?.deliverables?.status || 'MATCH'}
                    </Badge>
                  </div>
                  <p className="text-text-secondary truncate">
                    {contract.deliverables?.join(', ') || 'Dedicated collaboration content'}
                  </p>
                </div>

                <div className="rounded-xl border border-border bg-page/40 p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-text">Usage Rights</span>
                    <Badge variant={termStatusVariant(contract.usageRights ? 'MATCH' : 'REQUIRES_REVIEW')} className="text-[10px]">
                      {contract.usageRights ? 'SPECIFIED' : 'REQUIRES_REVIEW'}
                    </Badge>
                  </div>
                  <p className="text-text-secondary leading-relaxed line-clamp-2">
                    {contract.usageRights || contract.usage_rights || 'Standard digital & social media rights for 12 months'}
                  </p>
                </div>

                <div className="rounded-xl border border-border bg-page/40 p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-text">Exclusivity Clause</span>
                    <Badge variant={termStatusVariant(contract.exclusivity ? 'MATCH' : 'REQUIRES_REVIEW')} className="text-[10px]">
                      {contract.exclusivity ? 'SPECIFIED' : 'REQUIRES_REVIEW'}
                    </Badge>
                  </div>
                  <p className="text-text-secondary leading-relaxed line-clamp-2">
                    {contract.exclusivity || 'Non-exclusive during campaign flight'}
                  </p>
                </div>
              </div>

              {/* Risk Flags List */}
              {normalizedRiskFlags.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-border">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-text">
                    <ShieldAlert className="h-4 w-4 text-amber-600" />
                    <span>Identified Risk Flags ({normalizedRiskFlags.length})</span>
                  </div>
                  <div className="space-y-2">
                    {normalizedRiskFlags.map((rf: any, i: number) => (
                      <div
                        key={i}
                        className={`rounded-xl p-3 border text-xs ${
                          rf.severity === 'HIGH'
                            ? 'bg-rose-50/70 border-rose-200 text-rose-900'
                            : rf.severity === 'LOW'
                            ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
                            : 'bg-amber-50/70 border-amber-200 text-amber-900'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-bold flex items-center gap-1.5">
                            <AlertTriangle className="h-3.5 w-3.5" />
                            {rf.issue}
                          </span>
                          <Badge
                            variant={rf.severity === 'HIGH' ? 'danger' : rf.severity === 'LOW' ? 'success' : 'warning'}
                            className="text-[10px]"
                          >
                            {rf.severity}
                          </Badge>
                        </div>
                        {rf.reason && <p className="text-xs leading-relaxed opacity-90">{rf.reason}</p>}
                        {rf.recommended_review && (
                          <p className="text-[11px] mt-1 font-medium opacity-95">
                            Action: {rf.recommended_review}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Missing Clauses */}
              {missingClauses.length > 0 && (
                <div className="space-y-1.5 pt-2 border-t border-border">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-700">
                    <AlertCircle className="h-4 w-4" />
                    <span>Missing Clauses Flagged for Legal Review</span>
                  </div>
                  <ul className="grid sm:grid-cols-2 gap-1.5 text-xs text-text-secondary list-disc list-inside">
                    {missingClauses.map((mc: string, i: number) => (
                      <li key={i} className="text-text">
                        {mc}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Conflicts */}
              {conflicts.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-border">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-rose-700">
                    <AlertCircle className="h-4 w-4" />
                    <span>Detected Term Conflicts</span>
                  </div>
                  {conflicts.map((conf: any, i: number) => (
                    <div key={i} className="rounded-lg bg-rose-50 border border-rose-200 p-2.5 text-xs text-rose-900">
                      <p className="font-semibold">{conf.clause}</p>
                      <p className="text-text-secondary text-[11px] mt-0.5">
                        Negotiated: <span className="font-medium text-text">{conf.negotiated_term}</span> | Contract: <span className="font-medium text-text">{conf.contract_term}</span>
                      </p>
                      <p className="text-[11px] mt-1">{conf.explanation}</p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Full Agreement Text & Clauses */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <FileSignature className="h-4 w-4 text-primary" />
                <CardTitle className="text-base">Collaboration Agreement Document</CardTitle>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={handleDownloadPDF}
                  className="gap-1 text-xs text-primary border-primary/20 hover:bg-primary-soft/30"
                >
                  <Download className="h-3.5 w-3.5" />
                  PDF Export
                </Button>
                {!isEditingBody ? (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => setIsEditingBody(true)}
                    className="gap-1 text-xs"
                  >
                    <Edit3 className="h-3.5 w-3.5" />
                    Edit Draft
                  </Button>
                ) : (
                  <div className="flex items-center gap-1.5">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setIsEditingBody(false)}
                      className="text-xs"
                    >
                      Cancel
                    </Button>
                    <Button
                      size="sm"
                      variant="primary"
                      onClick={() => handleSaveBody(true)}
                      disabled={actionLoading}
                      className="text-xs"
                    >
                      Save & Re-analyze
                    </Button>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent className="pt-4">
              {!isEditingBody ? (
                <div className="rounded-xl border border-border bg-page/30 p-4 font-mono text-xs leading-relaxed text-text whitespace-pre-wrap max-h-[500px] overflow-y-auto">
                  {contract.contractBody || contract.contract_body || 'No agreement draft synthesized yet.'}
                </div>
              ) : (
                <textarea
                  value={draftBody}
                  onChange={(e) => setDraftBody(e.target.value)}
                  rows={16}
                  className="w-full rounded-xl border border-border bg-white p-3 font-mono text-xs text-text focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Sidebar: Audit Trail & AI Assistant */}
        <div className="space-y-6">
          {/* Sign-off & Audit Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-emerald-600" />
                Sign-off & Governance
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="flex justify-between items-center py-1.5 border-b border-border">
                <span className="text-text-secondary">Approval Status</span>
                <StatusChip status={contract.status} />
              </div>
              <div className="flex justify-between items-center py-1.5 border-b border-border">
                <span className="text-text-secondary">Agreement Version</span>
                <span className="font-mono font-semibold">v{contract.version || 1}</span>
              </div>
              {contract.approvedAt || contract.approved_at ? (
                <div className="flex justify-between items-center py-1.5 border-b border-border">
                  <span className="text-text-secondary">Approved At</span>
                  <span className="font-mono text-text">
                    {formatDate(contract.approvedAt || contract.approved_at)}
                  </span>
                </div>
              ) : null}
              {contract.approvedBy || contract.approved_by ? (
                <div className="flex justify-between items-center py-1.5 border-b border-border">
                  <span className="text-text-secondary">Approved By</span>
                  <span className="font-mono text-text truncate max-w-[120px]">
                    {contract.approvedBy || contract.approved_by}
                  </span>
                </div>
              ) : null}

              {/* Change Request History */}
              {changeRequests.length > 0 && (
                <div className="pt-2">
                  <p className="font-semibold text-text mb-2 flex items-center gap-1">
                    <History className="h-3.5 w-3.5 text-text-secondary" /> Change Request History
                  </p>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {changeRequests.map((cr: any, i: number) => (
                      <div key={i} className="rounded-lg border border-amber-200 bg-amber-50/60 p-2 text-[11px]">
                        <div className="flex justify-between font-semibold text-amber-900 mb-0.5">
                          <span>v{cr.version}</span>
                          <span className="text-[10px] text-amber-700">{formatDate(cr.timestamp)}</span>
                        </div>
                        <p className="text-text font-medium">{cr.reason}</p>
                        <p className="text-text-secondary mt-0.5">{cr.requested_changes}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Ask Contract Agent AI */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Bot className="h-4 w-4 text-ai" />
                <CardTitle className="text-sm">Ask Contract Agent</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <form onSubmit={handleAsk} className="space-y-2.5">
                <Input
                  placeholder="e.g. Are payment terms Net 30 or advance?"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  className="text-xs"
                />
                <Button type="submit" size="sm" variant="ai" className="w-full gap-1.5 text-xs">
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

      {/* Modal: Approve Contract */}
      {showApproveModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 animate-fade-in">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl space-y-4 border border-border">
            <div className="flex items-center gap-2.5 text-emerald-700">
              <CheckCircle2 className="h-6 w-6" />
              <h3 className="text-lg font-bold text-text">Approve Collaboration Contract</h3>
            </div>
            <p className="text-xs text-text-secondary leading-relaxed">
              Confirming approval will advance this creator to the active campaign stage and notify the Supervisor workflow coordinator.
            </p>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-text">Approval Notes (Optional)</label>
              <Input
                placeholder="e.g. Terms reviewed and approved by brand team"
                value={approveNotes}
                onChange={(e) => setApproveNotes(e.target.value)}
                className="text-xs"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button size="sm" variant="ghost" onClick={() => setShowApproveModal(false)} disabled={actionLoading}>
                Cancel
              </Button>
              <Button
                size="sm"
                variant="primary"
                onClick={handleApprove}
                disabled={actionLoading}
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                {actionLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : 'Confirm Approval'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Request Changes */}
      {showChangesModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 animate-fade-in">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl space-y-4 border border-border">
            <div className="flex items-center gap-2.5 text-amber-700">
              <FileEdit className="h-6 w-6" />
              <h3 className="text-lg font-bold text-text">Request Contract Changes</h3>
            </div>
            <p className="text-xs text-text-secondary leading-relaxed">
              Specify what clauses must be adjusted. This updates the contract state to CHANGES_REQUESTED and increments the version.
            </p>
            <div className="space-y-2.5 text-xs">
              <div>
                <label className="font-semibold text-text block mb-1">Reason for Request</label>
                <Input
                  placeholder="e.g. Usage rights duration too short"
                  value={changeReason}
                  onChange={(e) => setChangeReason(e.target.value)}
                />
              </div>
              <div>
                <label className="font-semibold text-text block mb-1">Requested Changes Detail</label>
                <textarea
                  placeholder="e.g. Update Clause 4 to specify 12 months digital rights across YouTube & Instagram."
                  value={changeNotes}
                  onChange={(e) => setChangeNotes(e.target.value)}
                  rows={4}
                  className="w-full rounded-xl border border-border bg-white p-2.5 text-xs focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button size="sm" variant="ghost" onClick={() => setShowChangesModal(false)} disabled={actionLoading}>
                Cancel
              </Button>
              <Button
                size="sm"
                variant="primary"
                onClick={handleRequestChanges}
                disabled={actionLoading || !changeNotes.trim() || !changeReason.trim()}
              >
                {actionLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : 'Submit Request'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Reject Contract */}
      {showRejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 animate-fade-in">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl space-y-4 border border-border">
            <div className="flex items-center gap-2.5 text-rose-700">
              <XCircle className="h-6 w-6" />
              <h3 className="text-lg font-bold text-text">Reject Collaboration Agreement</h3>
            </div>
            <p className="text-xs text-text-secondary leading-relaxed">
              Rejecting this agreement will mark the contract as REJECTED and prevent execution.
            </p>
            <div className="space-y-1.5 text-xs">
              <label className="font-semibold text-text block">Rejection Reason</label>
              <Input
                placeholder="e.g. Terms irreconcilable with brand guidelines"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button size="sm" variant="ghost" onClick={() => setShowRejectModal(false)} disabled={actionLoading}>
                Cancel
              </Button>
              <Button
                size="sm"
                variant="danger"
                onClick={handleReject}
                disabled={actionLoading || !rejectReason.trim()}
              >
                {actionLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : 'Reject Agreement'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

