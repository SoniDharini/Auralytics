import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  Bot,
  Calendar,
  Camera,
  Check,
  CheckCircle2,
  ChevronRight,
  Clock,
  Copy,
  DollarSign,
  ExternalLink,
  FileCheck,
  FileText,
  IndianRupee,
  Layers,
  Loader2,
  Mail,
  MessageSquare,
  RefreshCw,
  Send,
  Sparkles,
  User,
  UserX,
  Video,
  XCircle,
} from 'lucide-react'
import { api } from '@/services/api'
import {
  Avatar,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Drawer,
  Textarea,
  useToast,
} from '@/components/ui'
import { cn, formatINR } from '@/utils'
import { ContractTermsModal } from '@/components/contracts/ContractTermsModal'
import type { ConversationTurn, ContractReadiness, ContractTermsPayload, OutreachAcceptancePayload, OutreachMessageItem, OutreachRejectionPayload } from '@/types'

const REJECTION_REASONS = [
  'Budget mismatch',
  'Deliverables mismatch',
  'Timeline mismatch',
  'Influencer declined',
  'Campaign requirements mismatch',
  'Influencer unavailable',
  'No response',
  'Other',
]

export function OutreachPage() {
  const { toast } = useToast()
  const navigate = useNavigate()
  const [outreachList, setOutreachList] = useState<OutreachMessageItem[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedItem, setSelectedItem] = useState<OutreachMessageItem | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [mode, setMode] = useState<'email' | 'dm'>('email')
  const [editedBody, setEditedBody] = useState('')
  const [editedShortDm, setEditedShortDm] = useState('')
  const [generating, setGenerating] = useState(false)
  const [copiedEmail, setCopiedEmail] = useState(false)
  const [copiedDm, setCopiedDm] = useState(false)
  const [savingAcceptance, setSavingAcceptance] = useState(false)
  const [savingRejection, setSavingRejection] = useState(false)
  const [generatingContract, setGeneratingContract] = useState(false)

  // Contract Terms Confirmation Modal State
  const [showTermsModal, setShowTermsModal] = useState(false)
  const [readinessData, setReadinessData] = useState<ContractReadiness | null>(null)
  const [loadingReadiness, setLoadingReadiness] = useState(false)

  // Negotiation box state
  const [influencerReply, setInfluencerReply] = useState('')
  const [userInstruction, setUserInstruction] = useState('')
  const [negotiating, setNegotiating] = useState(false)

  // Response Workflow State
  const [responseMode, setResponseMode] = useState<'PENDING' | 'ACCEPTED' | 'REJECTED'>('PENDING')
  
  // Acceptance Form State
  const [acceptanceForm, setAcceptanceForm] = useState({
    response_notes: '',
    final_amount: '',
    currency: 'INR',
    deliverables: '',
    timeline_start: '',
    timeline_end: '',
    additional_terms: '',
  })

  // Rejection Form State
  const [rejectionForm, setRejectionForm] = useState({
    rejection_reason: 'Budget mismatch',
    rejection_notes: '',
  })

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await api.outreach.list()
      setOutreachList(data || [])
    } catch (err: any) {
      toast({ type: 'error', title: 'Failed to load outreach messages', description: err?.message })
      setOutreachList([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const openReview = (item: OutreachMessageItem) => {
    setSelectedItem(item)
    setEditedBody(item.body || item.message || '')
    setEditedShortDm(item.shortDm || item.short_dm || item.body || '')
    setInfluencerReply(item.reply || item.responseText || item.response_text || '')
    setUserInstruction('')

    const terms = item.extractedTerms || item.extracted_terms || {}
    const finalAmountVal = item.finalAmount || item.final_amount || terms.final_amount || terms.agreed_rate || ''
    const deliverablesVal = Array.isArray(item.deliverables) && item.deliverables.length > 0
      ? item.deliverables.join(', ')
      : Array.isArray(terms.deliverables) && terms.deliverables.length > 0
      ? terms.deliverables.join(', ')
      : '1 Dedicated Video + 1 Story'

    const timelineStartVal = item.timelineStart || item.timeline_start || terms.timeline_start || new Date().toISOString().split('T')[0]
    const nextMonth = new Date()
    nextMonth.setDate(nextMonth.getDate() + 30)
    const timelineEndVal = item.timelineEnd || item.timeline_end || terms.timeline_end || nextMonth.toISOString().split('T')[0]

    setAcceptanceForm({
      response_notes: item.responseText || item.response_text || item.reply || '',
      final_amount: finalAmountVal ? String(finalAmountVal) : '',
      currency: item.currency || terms.currency || 'INR',
      deliverables: deliverablesVal,
      timeline_start: timelineStartVal,
      timeline_end: timelineEndVal,
      additional_terms: item.additionalTerms || item.additional_terms || terms.additional_terms || '',
    })

    setRejectionForm({
      rejection_reason: item.rejectionReason || item.rejection_reason || 'Budget mismatch',
      rejection_notes: item.rejectionNotes || item.rejection_notes || '',
    })

    const statusVal = (item.responseStatus || item.response_status || item.status || 'PENDING_RESPONSE').toUpperCase()
    if (statusVal === 'ACCEPTED') {
      setResponseMode('ACCEPTED')
    } else if (statusVal === 'REJECTED' || statusVal === 'DECLINED') {
      setResponseMode('REJECTED')
    } else {
      setResponseMode('PENDING')
    }

    setMode('email')
    setDrawerOpen(true)
  }

  const closeReview = () => {
    setDrawerOpen(false)
    setSelectedItem(null)
  }

  const handleCopyText = (text: string, type: 'email' | 'dm') => {
    navigator.clipboard.writeText(text)
    if (type === 'email') {
      setCopiedEmail(true)
      setTimeout(() => setCopiedEmail(false), 2000)
      toast({ type: 'success', title: 'Email copied', description: 'Message copied to clipboard.' })
    } else {
      setCopiedDm(true)
      setTimeout(() => setCopiedDm(false), 2000)
      toast({ type: 'success', title: 'Social DM copied', description: 'Short DM copied to clipboard.' })
    }
    if (selectedItem?.id) {
      api.outreach.updateStatus(selectedItem.id, 'COPIED').catch(() => {})
    }
  }

  const handleRegenerate = async () => {
    if (!selectedItem) return
    setGenerating(true)
    try {
      const campaignId = selectedItem.campaignId || selectedItem.campaign_id || 'camp-1'
      const influencerId = selectedItem.influencerId || selectedItem.influencer_id
      const res = await api.agents.runOutreach(campaignId, influencerId)
      if (res.agentRun?.status === 'FAILED') {
        toast({ type: 'error', title: 'Outreach Agent failed', description: res.agentRun.errorMessage || 'Error generating outreach pitch' })
      } else {
        toast({ type: 'success', title: 'Pitch regenerated', description: 'Outreach Agent created a new personalized proposal.' })
        await loadData()
      }
    } catch (err: any) {
      toast({ type: 'error', title: 'Regeneration failed', description: err?.message || 'Could not run Outreach Agent' })
    } finally {
      setGenerating(false)
    }
  }

  const handleNegotiateFollowup = async () => {
    if (!selectedItem || !influencerReply.trim()) {
      toast({ type: 'error', title: 'Creator reply required', description: 'Please paste the influencer\'s response before generating a follow-up.' })
      return
    }
    setNegotiating(true)
    try {
      const res = await api.outreach.negotiate(selectedItem.id, influencerReply, userInstruction.trim() || undefined)
      toast({
        type: 'success',
        title: `Follow-up Generated (${res.conversation_state})`,
        description: res.influencer_reply_summary || 'Outreach Agent synthesized a tailored counteroffer / response.',
      })
      if (res.budget_constraint_warning) {
        toast({
          type: 'warning',
          title: 'Budget Constraint Warning',
          description: res.budget_constraint_warning,
        })
      }
      setEditedBody(res.message)
      if (res.short_dm) setEditedShortDm(res.short_dm)
      if (res.outreach_message) {
        setSelectedItem(res.outreach_message)
      }
      await loadData()
    } catch (err: any) {
      toast({ type: 'error', title: 'Negotiation follow-up failed', description: err?.message || 'Error processing creator reply' })
    } finally {
      setNegotiating(false)
    }
  }

  // Handle Save Acceptance
  const handleSaveAcceptance = async () => {
    if (!selectedItem) return
    const numAmount = parseFloat(String(acceptanceForm.final_amount).replace(/[^\d.]/g, ''))
    if (isNaN(numAmount) || numAmount <= 0) {
      toast({
        type: 'error',
        title: 'Valid amount required',
        description: 'Please enter a valid final collaboration amount (e.g. ₹75,000) before saving.',
      })
      return
    }
    if (!acceptanceForm.deliverables.trim()) {
      toast({
        type: 'error',
        title: 'Deliverables required',
        description: 'Please specify the agreed deliverables (e.g. 2 Instagram Reels + 1 Story).',
      })
      return
    }
    if (!acceptanceForm.timeline_start.trim() || !acceptanceForm.timeline_end.trim()) {
      toast({
        type: 'error',
        title: 'Timeline required',
        description: 'Please specify the agreed start and end dates.',
      })
      return
    }

    setSavingAcceptance(true)
    try {
      const deliverablesList = acceptanceForm.deliverables
        .split(',')
        .map((d) => d.trim())
        .filter(Boolean)

      const payload: OutreachAcceptancePayload = {
        response_notes: acceptanceForm.response_notes.trim() || undefined,
        final_amount: numAmount,
        currency: acceptanceForm.currency,
        deliverables: deliverablesList.length > 0 ? deliverablesList : [acceptanceForm.deliverables.trim()],
        timeline_start: acceptanceForm.timeline_start.trim(),
        timeline_end: acceptanceForm.timeline_end.trim(),
        additional_terms: acceptanceForm.additional_terms.trim() || undefined,
      }

      const updated = await api.outreach.saveAcceptance(selectedItem.id, payload)
      setSelectedItem(updated)
      setResponseMode('ACCEPTED')
      toast({
        type: 'success',
        title: 'Collaboration Accepted & Terms Saved',
        description: `Agreed terms (${acceptanceForm.currency} ${numAmount.toLocaleString()}) saved. Ready for contract generation.`,
      })
      await loadData()
    } catch (err: any) {
      toast({ type: 'error', title: 'Failed to save acceptance', description: err?.message })
    } finally {
      setSavingAcceptance(false)
    }
  }

  // Handle Save Rejection
  const handleSaveRejection = async () => {
    if (!selectedItem) return
    setSavingRejection(true)
    try {
      const payload: OutreachRejectionPayload = {
        rejection_reason: rejectionForm.rejection_reason,
        rejection_notes: rejectionForm.rejection_notes.trim() || undefined,
      }

      const updated = await api.outreach.saveRejection(selectedItem.id, payload)
      setSelectedItem(updated)
      setResponseMode('REJECTED')
      toast({
        type: 'warning',
        title: 'Collaboration Rejected',
        description: `Recorded rejection reason: ${rejectionForm.rejection_reason}. Influencer remains in history.`,
      })
      await loadData()
    } catch (err: any) {
      toast({ type: 'error', title: 'Failed to save rejection', description: err?.message })
    } finally {
      setSavingRejection(false)
    }
  }

  // Handle Opening Pre-Contract Terms Review Modal
  const handleOpenTermsModal = async () => {
    if (!selectedItem) return

    const isAcceptedStatus = (selectedItem.responseStatus || selectedItem.response_status || selectedItem.status) === 'ACCEPTED'
    const finalAmountVal = selectedItem.finalAmount || selectedItem.final_amount

    if (!isAcceptedStatus || !finalAmountVal || Number(finalAmountVal) <= 0) {
      toast({
        type: 'error',
        title: 'Incomplete collaboration details',
        description: 'Please complete and save the agreed collaboration details before generating the contract.',
      })
      return
    }

    setShowTermsModal(true)
    setLoadingReadiness(true)
    try {
      const campId = selectedItem.campaignId || selectedItem.campaign_id
      const infId = selectedItem.influencerId || selectedItem.influencer_id
      if (campId && infId) {
        const res = await api.contracts.checkReadiness(campId, infId)
        setReadinessData(res)
      }
    } catch {
      // safe fallback, modal uses selectedItem
    } finally {
      setLoadingReadiness(false)
    }
  }

  // Handle Confirmed Contract Generation
  const handleConfirmAndGenerateContract = async (confirmedTerms: ContractTermsPayload) => {
    if (!selectedItem) return

    setGeneratingContract(true)
    try {
      const res = await api.outreach.generateContract(selectedItem.id, { confirmed_terms: confirmedTerms })
      if (res.agentRun?.status === 'FAILED') {
        toast({
          type: 'error',
          title: 'Contract Generation Failed',
          description: res.agentRun.errorMessage || 'Grok was unable to synthesize contract draft. Please try again.',
        })
      } else {
        toast({
          type: 'success',
          title: 'Contract Synthesized Successfully',
          description: 'Redirecting to contract review and sign-off...',
        })
        setShowTermsModal(false)

        // Find the generated contract ID and immediately redirect
        let targetContractId = res.contractId || (res as any).contract_id || (res.contract ? res.contract.id : null)

        if (!targetContractId) {
          const campaignId = selectedItem.campaignId || selectedItem.campaign_id
          const influencerId = selectedItem.influencerId || selectedItem.influencer_id
          const contracts = await api.contracts.list(undefined, campaignId, influencerId)
          if (contracts && contracts.length > 0) {
            targetContractId = contracts[0].id
          }
        }

        if (targetContractId) {
          navigate(`/app/contracts/${targetContractId}`)
          return
        } else {
          navigate('/app/contracts')
          return
        }
      }
    } catch (err: any) {
      toast({ type: 'error', title: 'Contract generation failed', description: err?.message || 'Please try again.' })
    } finally {
      setGeneratingContract(false)
    }
  }

  // Derive workflow metrics & progress
  const workflowStats = useMemo(() => {
    const total = outreachList.length
    const accepted = outreachList.filter(
      (i) => (i.responseStatus || i.response_status || i.status) === 'ACCEPTED' || Boolean(i.contractId || i.contract_id),
    ).length
    const rejected = outreachList.filter(
      (i) => (i.responseStatus || i.response_status || i.status) === 'REJECTED' || (i.responseStatus || i.response_status || i.status) === 'DECLINED',
    ).length
    const contracted = outreachList.filter((i) => Boolean(i.contractId || i.contract_id) || i.status === 'CONTRACT_GENERATED').length
    const pending = total - accepted - rejected

    let progressPct = 0
    if (total > 0) {
      const score = (contracted * 1.0 + (accepted - contracted) * 0.75 + rejected * 0.5 + pending * 0.25) / total
      progressPct = Math.round(score * 100)
    }

    return { total, accepted, rejected, contracted, pending, progressPct }
  }, [outreachList])

  const currentItemStatus = (selectedItem?.responseStatus || selectedItem?.response_status || selectedItem?.status || 'PENDING_RESPONSE').toUpperCase()
  const isAcceptedConfirmed = currentItemStatus === 'ACCEPTED' || Boolean(selectedItem?.contractId || selectedItem?.contract_id)
  const isRejectedConfirmed = currentItemStatus === 'REJECTED' || currentItemStatus === 'DECLINED'
  const isContractReady = Boolean(selectedItem?.contractId || selectedItem?.contract_id) || selectedItem?.status === 'CONTRACT_GENERATED'

  const conversationHistory: ConversationTurn[] = selectedItem?.conversationHistory || selectedItem?.conversation_history || []

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-[30px] font-bold tracking-tight">AI Outreach & Response Hub</h1>
          <p className="text-text-secondary mt-1">
            Track creator outreach proposals, record received influencer responses, confirm commercial terms, and coordinate Contract Agent handoff.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full bg-primary/10 text-primary border border-primary/20">
          <Sparkles className="h-3.5 w-3.5" />
          <span>Outreach + Contract Agent Active</span>
        </div>
      </div>

      {/* Dynamic Workflow Timeline & Progress Card */}
      <Card className="border-border/80 bg-gradient-to-r from-card via-page to-card">
        <CardContent className="p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/60 pb-3">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-primary" />
              <span className="text-sm font-semibold text-text">Campaign Lifecycle Progress</span>
            </div>
            <div className="flex items-center gap-3 text-xs text-text-secondary font-medium">
              <span>{workflowStats.total} Shortlisted Creators</span>
              <span>·</span>
              <span className="text-success font-semibold">{workflowStats.accepted} Accepted</span>
              <span>·</span>
              <span className="text-danger font-semibold">{workflowStats.rejected} Rejected</span>
              <span>·</span>
              <span className="text-primary font-semibold">{workflowStats.contracted} Contracts</span>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs font-medium">
              <span className="text-text-secondary">Stage Completion Status</span>
              <span className="text-primary font-semibold">{workflowStats.progressPct}% Complete</span>
            </div>
            <div className="h-2 w-full bg-border rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-primary via-indigo-500 to-success transition-all duration-500 rounded-full"
                style={{ width: `${Math.max(15, workflowStats.progressPct)}%` }}
              />
            </div>
          </div>

          {/* Lifecycle Steps Indicator */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2 pt-1 text-[11px]">
            <div className="p-2 rounded-lg bg-card border border-success/30 flex items-center gap-1.5 text-success font-medium">
              <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">1. Strategy</span>
            </div>
            <div className="p-2 rounded-lg bg-card border border-success/30 flex items-center gap-1.5 text-success font-medium">
              <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">2. Discovery</span>
            </div>
            <div className="p-2 rounded-lg bg-card border border-success/30 flex items-center gap-1.5 text-success font-medium">
              <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">3. Shortlist</span>
            </div>
            <div className="p-2 rounded-lg bg-card border border-success/30 flex items-center gap-1.5 text-success font-medium">
              <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">4. Outreach Pitch</span>
            </div>
            <div className={cn(
              "p-2 rounded-lg bg-card border flex items-center gap-1.5 font-medium transition",
              workflowStats.accepted > 0 || workflowStats.rejected > 0
                ? "border-success/30 text-success"
                : "border-primary/40 text-primary bg-primary/5"
            )}>
              <Clock className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">5. Response Recording</span>
            </div>
            <div className={cn(
              "p-2 rounded-lg bg-card border flex items-center gap-1.5 font-medium transition",
              workflowStats.accepted > 0
                ? "border-success/30 text-success"
                : "border-border text-text-secondary"
            )}>
              <DollarSign className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">6. Terms Confirmed</span>
            </div>
            <div className={cn(
              "p-2 rounded-lg bg-card border flex items-center gap-1.5 font-medium transition",
              workflowStats.contracted > 0
                ? "border-success/30 text-success font-semibold"
                : "border-border text-text-secondary"
            )}>
              <FileCheck className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">7. Contract Draft</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Outreach List Card */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <CardTitle>Creator Outreach & Collaboration Records</CardTitle>
              <p className="text-xs text-text-secondary mt-0.5">
                Select a creator to review pitches, record responses, confirm agreed terms, or generate formal contracts.
              </p>
            </div>
            <Badge variant="outline" className="self-start text-xs font-mono">
              {outreachList.length} creator proposal{outreachList.length === 1 ? '' : 's'}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          {loading && (
            <div className="py-16 flex flex-col justify-center items-center gap-2 text-text-secondary text-sm">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
              <span>Loading outreach proposals & response records...</span>
            </div>
          )}

          {!loading && outreachList.length === 0 && (
            <div className="text-center py-16 text-text-secondary space-y-3">
              <Mail className="h-10 w-10 mx-auto text-text-secondary/40" />
              <div className="space-y-1">
                <p className="font-semibold text-text">No outreach proposals generated yet</p>
                <p className="text-sm text-text-secondary max-w-md mx-auto">
                  Shortlist verified creators from the Discovery Center to generate personalized proposals and initiate collaborations.
                </p>
              </div>
              <Link to="/app/discovery">
                <Button size="sm" variant="ai" className="mt-2 gap-1.5">
                  <Sparkles className="h-3.5 w-3.5" /> Go to Discovery Center
                </Button>
              </Link>
            </div>
          )}

          {!loading && outreachList.length > 0 && (
            <div className="grid gap-3">
              {outreachList.map((item) => {
                const itemStatus = (item.responseStatus || item.response_status || item.status || 'PENDING_RESPONSE').toUpperCase()
                const isItemAccepted = itemStatus === 'ACCEPTED' || Boolean(item.contractId || item.contract_id)
                const isItemRejected = itemStatus === 'REJECTED' || itemStatus === 'DECLINED'
                const itemContractId = item.contractId || item.contract_id

                return (
                  <div
                    key={item.id}
                    onClick={() => openReview(item)}
                    className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-xl border border-border p-4 hover:border-primary/40 hover:bg-page/50 transition cursor-pointer bg-card/60"
                  >
                    <div className="flex items-center gap-3.5 min-w-0">
                      <Avatar name={item.influencerName || item.influencer_name || 'Creator'} size="md" />
                      <div className="min-w-0 space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-bold text-text truncate">
                            {item.influencerName || item.influencer_name}
                          </span>
                          <Badge variant="primary" className="text-[11px] font-mono">
                            @{item.influencerUsername || item.influencer_username}
                          </Badge>
                          <span className="text-xs text-text-secondary">·</span>
                          <span className="text-xs text-text-secondary truncate max-w-[150px]">
                            {item.campaignName || item.campaign_name}
                          </span>
                        </div>

                        {/* Status indicators */}
                        <div className="flex items-center gap-2 flex-wrap text-xs">
                          {isItemAccepted ? (
                            <Badge variant="outline" className="bg-success-soft/40 text-success border-success/30 font-semibold gap-1 text-[11px]">
                              <CheckCircle2 className="h-3 w-3" /> Collaboration Accepted
                            </Badge>
                          ) : isItemRejected ? (
                            <Badge variant="outline" className="bg-danger-soft/40 text-danger border-danger/30 font-semibold gap-1 text-[11px]">
                              <XCircle className="h-3 w-3" /> Collaboration Rejected
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="bg-amber-500/10 text-amber-600 border-amber-500/30 font-semibold gap-1 text-[11px]">
                              <Clock className="h-3 w-3" /> Pending Response
                            </Badge>
                          )}

                          {itemContractId && (
                            <Badge variant="outline" className="bg-primary/10 text-primary border-primary/25 font-semibold gap-1 text-[11px]">
                              <FileCheck className="h-3 w-3" /> Contract Drafted
                            </Badge>
                          )}

                          {item.finalAmount && Number(item.finalAmount) > 0 && (
                            <span className="font-semibold text-text text-[11px]">
                              {formatINR(Number(item.finalAmount))}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-end sm:self-center">
                      <Button size="sm" variant="secondary" className="text-xs gap-1">
                        <span>Review & Manage</span>
                        <ChevronRight className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Review & Response Management Drawer */}
      <Drawer
        open={drawerOpen}
        onClose={closeReview}
        title={selectedItem?.influencerName || selectedItem?.influencer_name || 'Creator Collaboration'}
        subtitle={
          selectedItem
            ? `@${selectedItem.influencerUsername || selectedItem.influencer_username} · ${selectedItem.campaignName || selectedItem.campaign_name}`
            : undefined
        }
        width="max-w-2xl"
      >
        {selectedItem && (
          <div className="space-y-6 pb-6">
            {/* 1. OUTREACH PROPOSAL SECTION */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider flex items-center gap-1.5">
                  <Mail className="h-3.5 w-3.5 text-primary" />
                  <span>Outreach Proposal</span>
                </h4>
                <div className="flex items-center gap-1 bg-muted p-0.5 rounded-lg">
                  <button
                    type="button"
                    className={cn(
                      'px-2.5 py-1 text-xs font-semibold rounded-md transition',
                      mode === 'email' ? 'bg-card text-text shadow-sm' : 'text-text-secondary hover:text-text',
                    )}
                    onClick={() => setMode('email')}
                  >
                    Email Pitch
                  </button>
                  <button
                    type="button"
                    className={cn(
                      'px-2.5 py-1 text-xs font-semibold rounded-md transition',
                      mode === 'dm' ? 'bg-card text-text shadow-sm' : 'text-text-secondary hover:text-text',
                    )}
                    onClick={() => setMode('dm')}
                  >
                    Short Social DM
                  </button>
                </div>
              </div>

              {mode === 'email' && selectedItem.subject && (
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-text-secondary">Subject Line</label>
                  <div className="p-2.5 rounded-lg border border-border bg-page/60 text-xs font-medium text-text">
                    {selectedItem.subject}
                  </div>
                </div>
              )}

              <Textarea
                label={mode === 'email' ? 'Personalized Pitch Body' : 'Short Social DM'}
                value={mode === 'email' ? editedBody : editedShortDm}
                onChange={(e) =>
                  mode === 'email' ? setEditedBody(e.target.value) : setEditedShortDm(e.target.value)
                }
                rows={6}
              />

              <div className="flex flex-wrap items-center justify-between gap-2 pt-0.5">
                <Button
                  size="sm"
                  variant="secondary"
                  className="gap-1.5 text-xs"
                  onClick={handleRegenerate}
                  disabled={generating}
                >
                  {generating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                  Regenerate Proposal
                </Button>

                <Button
                  size="sm"
                  className="gap-1.5 text-xs"
                  onClick={() => handleCopyText(mode === 'email' ? editedBody : editedShortDm, mode)}
                >
                  {(mode === 'email' ? copiedEmail : copiedDm) ? (
                    <Check className="h-3.5 w-3.5 text-success" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}
                  {(mode === 'email' ? copiedEmail : copiedDm) ? 'Copied to Clipboard!' : `Copy ${mode === 'email' ? 'Email' : 'DM'}`}
                </Button>
              </div>
            </div>

            {/* Optional AI Negotiation Box (if user wants to test counteroffers) */}
            <div className="rounded-xl border border-border/80 bg-page/40 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-text">
                  <Sparkles className="h-3.5 w-3.5 text-primary" />
                  <span>AI Negotiation Assistant (Optional)</span>
                </div>
                <Badge variant="outline" className="text-[10px]">
                  Groq LLM Engine
                </Badge>
              </div>
              <Textarea
                placeholder="Paste influencer message here to analyze or generate follow-up counteroffers..."
                value={influencerReply}
                onChange={(e) => setInfluencerReply(e.target.value)}
                rows={2}
              />
              <div className="flex items-center justify-between gap-2">
                <input
                  type="text"
                  placeholder="Optional steering (e.g. 'Counteroffer ₹60,000')"
                  className="flex-1 px-3 py-1.5 text-xs rounded-lg border border-border bg-card text-text font-mono"
                  value={userInstruction}
                  onChange={(e) => setUserInstruction(e.target.value)}
                />
                <Button
                  size="sm"
                  variant="secondary"
                  className="text-xs gap-1 shrink-0"
                  onClick={handleNegotiateFollowup}
                  disabled={negotiating || !influencerReply.trim()}
                >
                  {negotiating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Bot className="h-3.5 w-3.5" />}
                  <span>Generate Follow-up</span>
                </Button>
              </div>
            </div>

            {/* 2. INFLUENCER RESPONSE SECTION (CORE PRODUCT REQUIREMENT) */}
            <div className="rounded-xl border-2 border-border/90 bg-card p-5 space-y-4 shadow-sm">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/60 pb-3">
                <div>
                  <h3 className="text-sm font-bold text-text uppercase tracking-wider flex items-center gap-2">
                    <MessageSquare className="h-4 w-4 text-primary" />
                    <span>Influencer Response</span>
                  </h3>
                  <p className="text-xs text-text-secondary mt-0.5">
                    Record the response received from this influencer.
                  </p>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-text-secondary font-medium">Current Status:</span>
                  {isAcceptedConfirmed ? (
                    <Badge variant="outline" className="bg-success-soft/50 text-success border-success/30 font-bold text-xs">
                      ACCEPTED
                    </Badge>
                  ) : isRejectedConfirmed ? (
                    <Badge variant="outline" className="bg-danger-soft/50 text-danger border-danger/30 font-bold text-xs">
                      REJECTED
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="bg-amber-500/10 text-amber-600 border-amber-500/30 font-bold text-xs">
                      PENDING RESPONSE
                    </Badge>
                  )}
                </div>
              </div>

              {/* Status Action Buttons */}
              <div className="flex items-center gap-3">
                <Button
                  type="button"
                  size="md"
                  className={cn(
                    'flex-1 gap-2 font-bold text-xs transition-all shadow-sm',
                    responseMode === 'ACCEPTED' || isAcceptedConfirmed
                      ? 'bg-success text-white ring-2 ring-success/30'
                      : 'bg-page hover:bg-success/15 text-text border border-border'
                  )}
                  onClick={() => setResponseMode('ACCEPTED')}
                >
                  <CheckCircle2 className="h-4 w-4 text-success" />
                  <span>ACCEPTED</span>
                </Button>

                <Button
                  type="button"
                  size="md"
                  className={cn(
                    'flex-1 gap-2 font-bold text-xs transition-all shadow-sm',
                    responseMode === 'REJECTED' || isRejectedConfirmed
                      ? 'bg-danger text-white ring-2 ring-danger/30'
                      : 'bg-page hover:bg-danger/15 text-text border border-border'
                  )}
                  onClick={() => setResponseMode('REJECTED')}
                >
                  <XCircle className="h-4 w-4 text-danger" />
                  <span>REJECTED</span>
                </Button>
              </div>

              {/* 3. ACCEPTED FLOW: COLLABORATION ACCEPTED FORM */}
              {responseMode === 'ACCEPTED' && (
                <div className="pt-2 space-y-4 animate-fade-in border-t border-border">
                  <div className="flex items-center gap-2 text-success font-bold text-sm">
                    <CheckCircle2 className="h-4 w-4" />
                    <span>COLLABORATION ACCEPTED ✓</span>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-text">
                      Influencer Response / Notes
                    </label>
                    <Textarea
                      placeholder="e.g. 'Creator confirmed via email. Interested in a dedicated video and story shoutout.'"
                      value={acceptanceForm.response_notes}
                      onChange={(e) =>
                        setAcceptanceForm((prev) => ({ ...prev, response_notes: e.target.value }))
                      }
                      rows={2}
                    />
                  </div>

                  <div className="grid sm:grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-text flex items-center gap-1">
                        <IndianRupee className="h-3.5 w-3.5 text-primary" />
                        <span>Final Collaboration Amount *</span>
                      </label>
                      <div className="relative">
                        <span className="absolute left-3 top-2.5 text-xs text-text-secondary font-mono">
                          {acceptanceForm.currency === 'INR' ? '₹' : '$'}
                        </span>
                        <input
                          type="number"
                          placeholder="e.g. 75000"
                          className="w-full pl-7 pr-3 py-2 text-xs rounded-lg border border-border bg-card text-text font-mono focus:ring-1 focus:ring-primary focus:outline-none"
                          value={acceptanceForm.final_amount}
                          onChange={(e) =>
                            setAcceptanceForm((prev) => ({ ...prev, final_amount: e.target.value }))
                          }
                        />
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-text">
                        Currency *
                      </label>
                      <select
                        className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-card text-text focus:ring-1 focus:ring-primary focus:outline-none"
                        value={acceptanceForm.currency}
                        onChange={(e) =>
                          setAcceptanceForm((prev) => ({ ...prev, currency: e.target.value }))
                        }
                      >
                        <option value="INR">INR (₹)</option>
                        <option value="USD">USD ($)</option>
                        <option value="EUR">EUR (€)</option>
                        <option value="GBP">GBP (£)</option>
                      </select>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-text">
                      Agreed Deliverables *
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. 2 Instagram Reels + 1 Story (or 1 Dedicated YouTube Video)"
                      className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-card text-text focus:ring-1 focus:ring-primary focus:outline-none"
                      value={acceptanceForm.deliverables}
                      onChange={(e) =>
                        setAcceptanceForm((prev) => ({ ...prev, deliverables: e.target.value }))
                      }
                    />
                  </div>

                  <div className="grid sm:grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-text flex items-center gap-1">
                        <Calendar className="h-3 w-3 text-text-secondary" />
                        <span>Agreed Start Date *</span>
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. 2026-09-01"
                        className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-card text-text font-mono focus:ring-1 focus:ring-primary focus:outline-none"
                        value={acceptanceForm.timeline_start}
                        onChange={(e) =>
                          setAcceptanceForm((prev) => ({ ...prev, timeline_start: e.target.value }))
                        }
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-text flex items-center gap-1">
                        <Calendar className="h-3 w-3 text-text-secondary" />
                        <span>Agreed End Date *</span>
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. 2026-09-30"
                        className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-card text-text font-mono focus:ring-1 focus:ring-primary focus:outline-none"
                        value={acceptanceForm.timeline_end}
                        onChange={(e) =>
                          setAcceptanceForm((prev) => ({ ...prev, timeline_end: e.target.value }))
                        }
                      />
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-text">
                      Additional Terms (Optional)
                    </label>
                    <Textarea
                      placeholder="e.g. 'Content draft review required 3 days prior to publishing. 12 months digital ad rights.'"
                      value={acceptanceForm.additional_terms}
                      onChange={(e) =>
                        setAcceptanceForm((prev) => ({ ...prev, additional_terms: e.target.value }))
                      }
                      rows={2}
                    />
                  </div>

                  <div className="pt-2 flex justify-end">
                    <Button
                      size="sm"
                      className="bg-success hover:bg-success/90 text-white font-semibold text-xs gap-1.5"
                      onClick={handleSaveAcceptance}
                      disabled={savingAcceptance}
                    >
                      {savingAcceptance ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                      <span>SAVE ACCEPTANCE</span>
                    </Button>
                  </div>
                </div>
              )}

              {/* 4. REJECTED FLOW: COLLABORATION REJECTED FORM */}
              {responseMode === 'REJECTED' && (
                <div className="pt-2 space-y-4 animate-fade-in border-t border-border">
                  <div className="flex items-center gap-2 text-danger font-bold text-sm">
                    <XCircle className="h-4 w-4" />
                    <span>COLLABORATION REJECTED</span>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-text">
                      Reason for Rejection *
                    </label>
                    <select
                      className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-card text-text focus:ring-1 focus:ring-primary focus:outline-none"
                      value={rejectionForm.rejection_reason}
                      onChange={(e) =>
                        setRejectionForm((prev) => ({ ...prev, rejection_reason: e.target.value }))
                      }
                    >
                      {REJECTION_REASONS.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-text">
                      Additional Notes (Optional)
                    </label>
                    <Textarea
                      placeholder="e.g. 'Creator rate was ₹1,50,000 which exceeded campaign budget limit.'"
                      value={rejectionForm.rejection_notes}
                      onChange={(e) =>
                        setRejectionForm((prev) => ({ ...prev, rejection_notes: e.target.value }))
                      }
                      rows={3}
                    />
                  </div>

                  <div className="pt-2 flex justify-end">
                    <Button
                      size="sm"
                      variant="danger"
                      className="font-semibold text-xs gap-1.5"
                      onClick={handleSaveRejection}
                      disabled={savingRejection}
                    >
                      {savingRejection ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <XCircle className="h-3.5 w-3.5" />}
                      <span>SAVE REJECTION</span>
                    </Button>
                  </div>
                </div>
              )}
            </div>

            {/* 5. NEXT STEP: GENERATE CONTRACT BANNER (Appears ONLY after saved Acceptance) */}
            {isAcceptedConfirmed && !isContractReady && (
              <div className="rounded-xl border-2 border-primary/40 bg-gradient-to-r from-primary/10 via-page to-primary/5 p-5 space-y-3 animate-fade-in shadow-sm">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-primary font-bold text-sm">
                    <Sparkles className="h-4 w-4" />
                    <span>NEXT STEP</span>
                  </div>
                  <Badge variant="outline" className="bg-success-soft text-success border-success/30 font-semibold text-[11px] gap-1">
                    <Check className="h-3 w-3" /> Collaboration Accepted
                  </Badge>
                </div>
                <p className="text-xs text-text-secondary leading-relaxed">
                  The agreed collaboration details are confirmed and ready for contract drafting. The Contract Agent will synthesize a formal agreement preserving your authoritative commercial terms.
                </p>
                <div className="pt-2 flex justify-end">
                  <Button
                    size="md"
                    className="gap-2 bg-primary hover:bg-primary/90 text-white font-bold text-xs shadow-md"
                    onClick={handleOpenTermsModal}
                    disabled={generatingContract}
                  >
                    <FileText className="h-4 w-4" />
                    <span>REVIEW TERMS & GENERATE CONTRACT</span>
                    <ArrowRight className="h-3.5 w-3.5 ml-1" />
                  </Button>
                </div>
              </div>
            )}

            {/* 6. CONTRACT READY BANNER (Appears after Contract Generation) */}
            {isContractReady && (
              <div className="rounded-xl border-2 border-success/50 bg-gradient-to-r from-success-soft/30 via-page to-success-soft/20 p-5 space-y-3 animate-fade-in shadow-sm">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-success font-bold text-sm">
                    <FileCheck className="h-5 w-5 text-success" />
                    <span>CONTRACT READY ✓</span>
                  </div>
                  <Badge variant="outline" className="bg-success text-white border-transparent font-semibold text-[11px]">
                    Contract Agent: Completed
                  </Badge>
                </div>
                <p className="text-xs text-text-secondary leading-relaxed">
                  Formal contract draft has been successfully generated and persisted in PostgreSQL. You can review agreement clauses, payment schedules, and AI risk analysis.
                </p>
                <div className="pt-2 flex justify-end gap-2">
                  <Button
                    size="sm"
                    className="gap-2 bg-success hover:bg-success/90 text-white font-bold text-xs shadow-sm"
                    onClick={async () => {
                      let contractId = selectedItem.contractId || selectedItem.contract_id
                      if (!contractId) {
                        const campaignId = selectedItem.campaignId || selectedItem.campaign_id
                        const influencerId = selectedItem.influencerId || selectedItem.influencer_id
                        const contracts = await api.contracts.list(undefined, campaignId, influencerId)
                        if (contracts && contracts.length > 0) {
                          contractId = contracts[0].id
                        }
                      }
                      if (contractId) {
                        navigate(`/app/contracts/${contractId}`)
                      } else {
                        navigate('/app/contracts')
                      }
                    }}
                  >
                    <FileText className="h-4 w-4" />
                    <span>VIEW CONTRACT</span>
                    <ArrowRight className="h-3.5 w-3.5 ml-1" />
                  </Button>
                </div>
              </div>
            )}

            {/* 7. REJECTED STATUS BANNER */}
            {isRejectedConfirmed && (
              <div className="rounded-xl border border-danger/30 bg-danger-soft/20 p-4 space-y-2 animate-fade-in">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-danger font-bold text-xs">
                    <UserX className="h-4 w-4" />
                    <span>COLLABORATION REJECTED</span>
                  </div>
                  <Badge variant="outline" className="text-[10px] text-danger border-danger/30">
                    Reason: {selectedItem.rejectionReason || selectedItem.rejection_reason || rejectionForm.rejection_reason}
                  </Badge>
                </div>
                <p className="text-xs text-text-secondary leading-relaxed">
                  Collaboration for this creator has ended. Contract generation is disabled. The creator remains safely in your campaign history.
                </p>
                {(selectedItem.rejectionNotes || selectedItem.rejection_notes) && (
                  <p className="text-[11px] text-text font-mono bg-card/60 p-2 rounded border border-border">
                    Notes: {selectedItem.rejectionNotes || selectedItem.rejection_notes}
                  </p>
                )}
              </div>
            )}

            {/* Collaboration Contact Channels */}
            <div className="space-y-2 pt-2 border-t border-border">
              <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
                Direct Channels
              </h4>
              <div className="grid sm:grid-cols-3 gap-2">
                <div className="p-3 rounded-lg border border-border bg-page/30 space-y-1">
                  <span className="flex items-center gap-1 font-semibold text-xs text-text">
                    <Mail className="h-3.5 w-3.5 text-primary" /> Email
                  </span>
                  <p className="text-xs truncate font-mono text-text">
                    {selectedItem.contactInfo?.email || 'Not publicly available'}
                  </p>
                  {Boolean(selectedItem.contactInfo?.email && selectedItem.contactInfo.email !== 'Not publicly available') && (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="mt-1 w-full gap-1 text-[11px]"
                      onClick={() => handleCopyText(selectedItem.contactInfo?.email || '', 'email')}
                    >
                      <Copy className="h-3 w-3" /> Copy Email
                    </Button>
                  )}
                </div>

                <div className="p-3 rounded-lg border border-border bg-page/30 space-y-1">
                  <span className="flex items-center gap-1 font-semibold text-xs text-text">
                    <Camera className="h-3.5 w-3.5 text-pink-500" /> Instagram
                  </span>
                  <p className="text-xs truncate font-mono text-text">
                    @{selectedItem.influencerUsername || selectedItem.influencer_username}
                  </p>
                  <a
                    href={`https://instagram.com/${selectedItem.influencerUsername || selectedItem.influencer_username}`}
                    target="_blank"
                    rel="noreferrer"
                    className="block"
                  >
                    <Button size="sm" variant="ghost" className="mt-1 w-full gap-1 text-[11px]">
                      <ExternalLink className="h-3 w-3" /> Open Instagram
                    </Button>
                  </a>
                </div>

                <div className="p-3 rounded-lg border border-border bg-page/30 space-y-1">
                  <span className="flex items-center gap-1 font-semibold text-xs text-text">
                    <Video className="h-3.5 w-3.5 text-red-500" /> YouTube
                  </span>
                  <p className="text-xs truncate font-mono text-text">
                    {selectedItem.influencerName || selectedItem.influencer_name}
                  </p>
                  <a
                    href={`https://youtube.com/@${selectedItem.influencerUsername || selectedItem.influencer_username}`}
                    target="_blank"
                    rel="noreferrer"
                    className="block"
                  >
                    <Button size="sm" variant="ghost" className="mt-1 w-full gap-1 text-[11px]">
                      <ExternalLink className="h-3 w-3" /> Open Channel
                    </Button>
                  </a>
                </div>
              </div>
            </div>

            {/* Conversation History Timeline */}
            {conversationHistory && conversationHistory.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-border">
                <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider flex items-center justify-between">
                  <span>Activity & Conversation History ({conversationHistory.length} events)</span>
                </h4>
                <div className="rounded-xl border border-border bg-page/40 p-3 space-y-3 max-h-56 overflow-y-auto">
                  {conversationHistory.map((turn, idx) => (
                    <div
                      key={idx}
                      className={cn(
                        'p-3 rounded-lg text-xs space-y-1',
                        turn.sender === 'INFLUENCER'
                          ? 'bg-primary/5 border border-primary/20 text-text ml-4'
                          : turn.sender === 'BRAND'
                          ? 'bg-card border border-border mr-4'
                          : 'bg-ai-soft/30 border border-ai/20 text-text',
                      )}
                    >
                      <div className="flex items-center justify-between font-semibold">
                        <span className="flex items-center gap-1.5">
                          {turn.sender === 'INFLUENCER' ? (
                            <>
                              <User className="h-3.5 w-3.5 text-primary" /> Creator Reply
                            </>
                          ) : turn.sender === 'BRAND' ? (
                            <>
                              <Send className="h-3.5 w-3.5 text-text-secondary" /> Brand Action
                            </>
                          ) : (
                            <>
                              <Bot className="h-3.5 w-3.5 text-ai" /> AI Draft
                            </>
                          )}
                        </span>
                        {turn.timestamp && (
                          <span className="text-[10px] text-text-secondary font-mono">
                            {new Date(turn.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        )}
                      </div>
                      <p className="whitespace-pre-wrap leading-relaxed">{turn.message}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Drawer>

      {/* Pre-Contract Terms Configuration Modal */}
      {selectedItem && (
        <ContractTermsModal
          isOpen={showTermsModal}
          onClose={() => setShowTermsModal(false)}
          readinessData={readinessData}
          creatorName={selectedItem.influencerName || selectedItem.influencer_name || 'Creator'}
          creatorUsername={selectedItem.influencerUsername || selectedItem.influencer_username || 'creator'}
          campaignName={selectedItem.campaignName || selectedItem.campaign_name || 'Campaign'}
          agreedRate={Number(selectedItem.finalAmount || selectedItem.final_amount || 0)}
          currency={selectedItem.currency || 'INR'}
          initialDeliverables={
            Array.isArray(selectedItem.deliverables) && selectedItem.deliverables.length > 0
              ? selectedItem.deliverables
              : ['1 Dedicated collaboration video']
          }
          startDate={selectedItem.timelineStart || selectedItem.timeline_start || 'Launch Date'}
          endDate={selectedItem.timelineEnd || selectedItem.timeline_end || 'Launch + 30'}
          additionalNotes={selectedItem.additionalTerms || selectedItem.additional_terms || ''}
          onConfirm={handleConfirmAndGenerateContract}
          loading={generatingContract || loadingReadiness}
        />
      )}
    </div>
  )
}
