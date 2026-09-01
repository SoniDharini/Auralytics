import { useEffect, useState } from 'react'
import {
  Banknote,
  FileCheck,
  FileText,
  Loader2,
  Lock,
  Scale,
  ShieldCheck,
  Sparkles,
  X,
} from 'lucide-react'
import { Badge, Button, Card, CardContent, Modal } from '@/components/ui'
import { formatINR } from '@/utils'
import type { ContractReadiness, ContractTermsPayload } from '@/types'

interface ContractTermsModalProps {
  isOpen: boolean
  onClose: () => void
  readinessData?: ContractReadiness | null
  creatorName: string
  creatorUsername: string
  campaignName: string
  agreedRate: number
  currency?: string
  initialDeliverables?: string[]
  startDate?: string
  endDate?: string
  additionalNotes?: string
  onConfirm: (confirmedTerms: ContractTermsPayload) => Promise<void>
  loading?: boolean
}

export function ContractTermsModal({
  isOpen,
  onClose,
  readinessData,
  creatorName,
  creatorUsername,
  campaignName,
  agreedRate,
  currency = 'INR',
  initialDeliverables = ['1 Dedicated collaboration video'],
  startDate = 'Launch Date',
  endDate = 'Launch + 30',
  additionalNotes = '',
  onConfirm,
  loading = false,
}: ContractTermsModalProps) {
  // Compensation & Payment State
  const totalCompensation = agreedRate > 0 ? agreedRate : (readinessData?.final_terms?.agreed_rate || 50000)
  const curr = currency || readinessData?.final_terms?.currency || 'INR'

  const [paymentStructure, setPaymentStructure] = useState<'50_50' | '100_completion' | 'custom'>('50_50')
  const [advancePercent, setAdvancePercent] = useState<number>(50)
  const [advanceAmount, setAdvanceAmount] = useState<number>(round(totalCompensation * 0.5))
  const [balanceAmount, setBalanceAmount] = useState<number>(round(totalCompensation * 0.5))
  const [paymentMethod, setPaymentMethod] = useState<string>('Bank Transfer')
  const [balanceDueDays, setBalanceDueDays] = useState<number>(7)

  // Deliverables & Timeline
  const [deliverables, setDeliverables] = useState<string[]>(initialDeliverables)
  const [newDeliverable, setNewDeliverable] = useState('')
  const [flightStart, setFlightStart] = useState<string>(startDate)
  const [flightEnd, setFlightEnd] = useState<string>(endDate)
  const [draftDeadline, setDraftDeadline] = useState<string>('3 days prior to publishing')

  // Revisions & Approval
  const [revisionRounds, setRevisionRounds] = useState<number>(2)
  const [preApprovalRequired, setPreApprovalRequired] = useState<boolean>(true)
  const [productClaimsPolicy, setProductClaimsPolicy] = useState<'BRAND_APPROVED_ONLY' | 'INDEPENDENT_PERMITTED'>('BRAND_APPROVED_ONLY')

  // Usage Rights & Ownership
  const [organicReposting, setOrganicReposting] = useState<boolean>(true)
  const [paidAdsRights, setPaidAdsRights] = useState<boolean>(false)
  const [websiteUsage, setWebsiteUsage] = useState<boolean>(true)
  const [usageDuration, setUsageDuration] = useState<string>('3 Months')
  const [usageTerritory, setUsageTerritory] = useState<string>('India')
  const [copyrightOwner, setCopyrightOwner] = useState<string>('INFLUENCER')

  // Exclusivity
  const [exclusivityRequired, setExclusivityRequired] = useState<boolean>(false)
  const [exclusivityCategory, setExclusivityCategory] = useState<string>(campaignName || 'Direct Competitor Products')
  const [exclusivityDuration, setExclusivityDuration] = useState<number>(30)

  // Additional Terms
  const [additionalTerms, setAdditionalTerms] = useState<string>(additionalNotes)

  function round(val: number): number {
    return Math.round((val + Number.EPSILON) * 100) / 100
  }

  // Synchronize payment amounts when structure or percentage changes
  useEffect(() => {
    if (paymentStructure === '50_50') {
      const adv = round(totalCompensation * 0.5)
      setAdvancePercent(50)
      setAdvanceAmount(adv)
      setBalanceAmount(round(totalCompensation - adv))
    } else if (paymentStructure === '100_completion') {
      setAdvancePercent(0)
      setAdvanceAmount(0)
      setBalanceAmount(totalCompensation)
    } else if (paymentStructure === 'custom') {
      const adv = round(totalCompensation * (advancePercent / 100))
      setAdvanceAmount(adv)
      setBalanceAmount(round(totalCompensation - adv))
    }
  }, [paymentStructure, advancePercent, totalCompensation])

  // Prepopulate from readiness suggested terms when opened
  useEffect(() => {
    if (readinessData?.suggested_terms) {
      const st = readinessData.suggested_terms as any
      if (st.payment) {
        setPaymentStructure(st.payment.structure || '50_50')
        setPaymentMethod(st.payment.method || 'Bank Transfer')
        setBalanceDueDays(st.payment.balance_due_days || 7)
      }
      if (st.revisions?.allowed_rounds !== undefined) {
        setRevisionRounds(st.revisions.allowed_rounds)
      }
      if (st.approval?.pre_publication_required !== undefined) {
        setPreApprovalRequired(st.approval.pre_publication_required)
      }
      if (st.usage_rights) {
        setOrganicReposting(Boolean(st.usage_rights.organic_reposting))
        setPaidAdsRights(Boolean(st.usage_rights.paid_ads))
        setUsageDuration(st.usage_rights.duration || '3 Months')
        setUsageTerritory(st.usage_rights.territory || 'India')
      }
      if (st.exclusivity) {
        setExclusivityRequired(Boolean(st.exclusivity.required))
        setExclusivityDuration(st.exclusivity.duration_days || 30)
      }
    }
  }, [readinessData])

  const handleAddDeliverable = () => {
    if (!newDeliverable.trim()) return
    setDeliverables([...deliverables, newDeliverable.trim()])
    setNewDeliverable('')
  }

  const handleRemoveDeliverable = (idx: number) => {
    setDeliverables(deliverables.filter((_, i) => i !== idx))
  }

  const handleConfirm = async () => {
    const payload: ContractTermsPayload = {
      creator_name: creatorName,
      creator_username: creatorUsername,
      campaign_name: campaignName,
      compensation: {
        total: totalCompensation,
        currency: curr,
      },
      payment: {
        structure: paymentStructure,
        advance_percentage: advancePercent,
        advance_amount: advanceAmount,
        balance_percentage: 100 - advancePercent,
        balance_amount: balanceAmount,
        method: paymentMethod,
        balance_due_days: balanceDueDays,
        terms_text:
          advanceAmount > 0
            ? `${curr} ${advanceAmount.toLocaleString()} (${advancePercent}%) advance payable upon execution; remaining ${curr} ${balanceAmount.toLocaleString()} (${100 - advancePercent}%) payable via ${paymentMethod} within ${balanceDueDays} days of completion.`
            : `100% of fee (${curr} ${totalCompensation.toLocaleString()}) payable via ${paymentMethod} within ${balanceDueDays} days of completion and approval.`,
      },
      deliverables: deliverables.length > 0 ? deliverables : ['1 Dedicated collaboration video'],
      timeline: {
        start_date: flightStart,
        end_date: flightEnd,
        draft_submission_deadline: draftDeadline,
        publishing_deadline: flightStart,
      },
      revisions: {
        allowed_rounds: revisionRounds,
        scope: 'Factual accuracy, brand guidelines, approved product claims, and agreed deliverable requirements.',
      },
      approval: {
        pre_publication_required: preApprovalRequired,
        review_window_days: 3,
      },
      product_claims: {
        policy: productClaimsPolicy,
        claim_guidelines:
          productClaimsPolicy === 'BRAND_APPROVED_ONLY'
            ? 'Creator shall not make unapproved efficacy, performance, medical, or comparative product claims.'
            : 'Creator may share genuine personal experiences consistent with standard consumer protection guidelines.',
      },
      usage_rights: {
        organic_reposting: organicReposting,
        paid_ads: paidAdsRights,
        website_use: websiteUsage,
        duration: usageDuration,
        territory: usageTerritory,
      },
      ownership: {
        copyright_owner: copyrightOwner,
        license_grant: `Influencer retains copyright and grants Brand a ${usageDuration} non-exclusive marketing license for ${usageTerritory}.`,
      },
      exclusivity: {
        required: exclusivityRequired,
        category: exclusivityCategory,
        duration_days: exclusivityDuration,
        scope: exclusivityRequired ? `No direct competitor product endorsements in ${exclusivityCategory} category for ${exclusivityDuration} days.` : 'Non-exclusive.',
      },
      cancellation: {
        brand_cancellation: 'Brand may cancel prior to draft submission with payment for work performed. Advance is refundable if work has not commenced.',
        influencer_cancellation: 'Creator cancellation requires full refund of any advance received and return of gifted products.',
        force_majeure: 'Neither party liable for failure due to unforeseen events beyond reasonable control.',
      },
      termination: {
        grounds: [
          'Material breach of agreement terms',
          'Failure to deliver content by agreed deadline',
          'Publication without required brand pre-approval',
          'Violation of brand safety or product claim guidelines',
        ],
      },
      additional_terms: additionalTerms,
    }

    await onConfirm(payload)
  }

  return (
    <Modal
      open={isOpen}
      onClose={onClose}
      title="Contract Terms & Commercial Parameters Review"
      className="max-w-4xl"
    >
      <div className="space-y-6 max-h-[75vh] overflow-y-auto pr-1">
        {/* 1. Header Summary Banner */}
        <div className="rounded-xl border border-primary/20 bg-primary-soft/30 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <span className="font-bold text-sm text-text">{creatorName}</span>
              <span className="text-xs text-text-secondary">(@{creatorUsername})</span>
            </div>
            <p className="text-xs text-text-secondary">
              Campaign: <span className="font-medium text-text">{campaignName}</span>
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="rounded-lg bg-white px-3 py-1.5 border border-border shadow-xs text-right">
              <span className="text-[10px] text-text-secondary block font-semibold uppercase">Agreed Fee</span>
              <span className="font-bold text-sm text-primary">{formatINR(totalCompensation)}</span>
            </div>
            <Badge variant="success" className="gap-1 text-[11px] font-semibold">
              <Lock className="h-3 w-3" /> Authoritative Negotiated Terms
            </Badge>
          </div>
        </div>

        {/* 2. Payment Structure Section */}
        <Card className="border-border">
          <CardContent className="p-4 space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <div className="flex items-center gap-2">
                <Banknote className="h-4 w-4 text-primary" />
                <h4 className="font-bold text-sm text-text">1. Payment Structure & Schedule</h4>
              </div>
              <span className="text-xs font-mono font-bold text-text">Total: {formatINR(totalCompensation)}</span>
            </div>

            {/* Structure Radio Options */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <label
                className={`cursor-pointer rounded-xl border p-3 flex flex-col gap-1 transition ${
                  paymentStructure === '50_50'
                    ? 'border-primary bg-primary-soft/40 shadow-xs'
                    : 'border-border bg-page/40 hover:bg-page'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-text">50% Advance + 50% Balance</span>
                  <input
                    type="radio"
                    name="paymentStructure"
                    checked={paymentStructure === '50_50'}
                    onChange={() => setPaymentStructure('50_50')}
                    className="text-primary focus:ring-primary h-3.5 w-3.5"
                  />
                </div>
                <span className="text-[11px] text-text-secondary">Suggested safe industry standard</span>
                <span className="text-xs font-semibold text-primary mt-1">
                  {formatINR(totalCompensation * 0.5)} + {formatINR(totalCompensation * 0.5)}
                </span>
              </label>

              <label
                className={`cursor-pointer rounded-xl border p-3 flex flex-col gap-1 transition ${
                  paymentStructure === '100_completion'
                    ? 'border-primary bg-primary-soft/40 shadow-xs'
                    : 'border-border bg-page/40 hover:bg-page'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-text">100% on Completion</span>
                  <input
                    type="radio"
                    name="paymentStructure"
                    checked={paymentStructure === '100_completion'}
                    onChange={() => setPaymentStructure('100_completion')}
                    className="text-primary focus:ring-primary h-3.5 w-3.5"
                  />
                </div>
                <span className="text-[11px] text-text-secondary">Full payment upon approved delivery</span>
                <span className="text-xs font-semibold text-text mt-1">{formatINR(totalCompensation)}</span>
              </label>

              <label
                className={`cursor-pointer rounded-xl border p-3 flex flex-col gap-1 transition ${
                  paymentStructure === 'custom'
                    ? 'border-primary bg-primary-soft/40 shadow-xs'
                    : 'border-border bg-page/40 hover:bg-page'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-text">Custom Split</span>
                  <input
                    type="radio"
                    name="paymentStructure"
                    checked={paymentStructure === 'custom'}
                    onChange={() => setPaymentStructure('custom')}
                    className="text-primary focus:ring-primary h-3.5 w-3.5"
                  />
                </div>
                <span className="text-[11px] text-text-secondary">Configure custom advance percentage</span>
                <span className="text-xs font-semibold text-text mt-1">
                  {advancePercent}% / {100 - advancePercent}%
                </span>
              </label>
            </div>

            {/* Custom Split Slider */}
            {paymentStructure === 'custom' && (
              <div className="rounded-xl bg-page p-3 border border-border space-y-2">
                <div className="flex justify-between text-xs font-semibold">
                  <span>Advance: {advancePercent}% ({formatINR(advanceAmount)})</span>
                  <span>Balance: {100 - advancePercent}% ({formatINR(balanceAmount)})</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  value={advancePercent}
                  onChange={(e) => setAdvancePercent(Number(e.target.value))}
                  className="w-full h-1.5 bg-border rounded-lg appearance-none cursor-pointer accent-primary"
                />
              </div>
            )}

            {/* Payment Method & Timing */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
              <div>
                <label className="block text-xs font-semibold text-text mb-1">Payment Method</label>
                <select
                  value={paymentMethod}
                  onChange={(e) => setPaymentMethod(e.target.value)}
                  className="w-full rounded-lg border border-border bg-white p-2 text-xs font-medium text-text focus:outline-none focus:ring-2 focus:ring-primary/20"
                >
                  <option value="Bank Transfer">Bank Transfer (NEFT / RTGS / Wire)</option>
                  <option value="UPI">UPI Transfer</option>
                  <option value="Payment Gateway">Payment Gateway / Escrow</option>
                  <option value="Corporate Invoice">Corporate Invoice / Net Terms</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-text mb-1">Final Balance Due Window</label>
                <select
                  value={balanceDueDays}
                  onChange={(e) => setBalanceDueDays(Number(e.target.value))}
                  className="w-full rounded-lg border border-border bg-white p-2 text-xs font-medium text-text focus:outline-none focus:ring-2 focus:ring-primary/20"
                >
                  <option value={0}>Immediately upon approval</option>
                  <option value={7}>Within 7 days post completion (Net 7)</option>
                  <option value={15}>Within 15 days post completion (Net 15)</option>
                  <option value={30}>Within 30 days post completion (Net 30)</option>
                </select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 3. Deliverables & Flight Timeline */}
        <Card className="border-border">
          <CardContent className="p-4 space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-primary" />
                <h4 className="font-bold text-sm text-text">2. Deliverables & Flight Timeline</h4>
              </div>
              <span className="text-xs text-text-secondary">{deliverables.length} Deliverable(s)</span>
            </div>

            <div className="space-y-2">
              <label className="block text-xs font-semibold text-text">Agreed Content Deliverables</label>
              <div className="space-y-1.5">
                {deliverables.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between gap-2 p-2 rounded-lg bg-page border border-border text-xs">
                    <span className="font-medium text-text">{item}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveDeliverable(idx)}
                      className="text-text-secondary hover:text-danger p-0.5 rounded transition"
                      aria-label="Remove deliverable"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>

              <div className="flex gap-2 pt-1">
                <input
                  type="text"
                  placeholder="e.g. 1 Dedicated YouTube Video, 2 Instagram Reels"
                  value={newDeliverable}
                  onChange={(e) => setNewDeliverable(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      handleAddDeliverable()
                    }
                  }}
                  className="flex-1 rounded-lg border border-border bg-white px-3 py-1.5 text-xs text-text focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
                <Button size="sm" variant="secondary" onClick={handleAddDeliverable} className="text-xs">
                  Add Deliverable
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
              <div>
                <label className="block text-xs font-semibold text-text mb-1">Campaign Start</label>
                <input
                  type="text"
                  value={flightStart}
                  onChange={(e) => setFlightStart(e.target.value)}
                  className="w-full rounded-lg border border-border bg-white p-2 text-xs font-medium text-text focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-text mb-1">Campaign End</label>
                <input
                  type="text"
                  value={flightEnd}
                  onChange={(e) => setFlightEnd(e.target.value)}
                  className="w-full rounded-lg border border-border bg-white p-2 text-xs font-medium text-text focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-text mb-1">Draft Submission</label>
                <input
                  type="text"
                  value={draftDeadline}
                  onChange={(e) => setDraftDeadline(e.target.value)}
                  className="w-full rounded-lg border border-border bg-white p-2 text-xs font-medium text-text focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 4. Revisions, Approval & Product Claims */}
        <Card className="border-border">
          <CardContent className="p-4 space-y-4">
            <div className="flex items-center gap-2 border-b border-border pb-2.5">
              <ShieldCheck className="h-4 w-4 text-primary" />
              <h4 className="font-bold text-sm text-text">3. Revisions, Approval & Product Claims</h4>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-text mb-1">Included Revision Rounds</label>
                <select
                  value={revisionRounds}
                  onChange={(e) => setRevisionRounds(Number(e.target.value))}
                  className="w-full rounded-lg border border-border bg-white p-2 text-xs font-medium text-text focus:outline-none focus:ring-2 focus:ring-primary/20"
                >
                  <option value={0}>0 (No revisions included)</option>
                  <option value={1}>1 Revision Round</option>
                  <option value={2}>2 Revision Rounds (Recommended)</option>
                  <option value={3}>3 Revision Rounds</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-text mb-1">Brand Pre-Publication Approval</label>
                <select
                  value={preApprovalRequired ? 'true' : 'false'}
                  onChange={(e) => setPreApprovalRequired(e.target.value === 'true')}
                  className="w-full rounded-lg border border-border bg-white p-2 text-xs font-medium text-text focus:outline-none focus:ring-2 focus:ring-primary/20"
                >
                  <option value="true">REQUIRED (Submit draft before posting)</option>
                  <option value="false">NOT REQUIRED (Creator self-publishes)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-text mb-1">Product Claims Policy</label>
                <select
                  value={productClaimsPolicy}
                  onChange={(e) => setProductClaimsPolicy(e.target.value as any)}
                  className="w-full rounded-lg border border-border bg-white p-2 text-xs font-medium text-text focus:outline-none focus:ring-2 focus:ring-primary/20"
                >
                  <option value="BRAND_APPROVED_ONLY">Brand-Approved Claims Only (Safe)</option>
                  <option value="INDEPENDENT_PERMITTED">Creator Personal Review Allowed</option>
                </select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 5. Usage Rights, Ownership & Exclusivity */}
        <Card className="border-border">
          <CardContent className="p-4 space-y-4">
            <div className="flex items-center gap-2 border-b border-border pb-2.5">
              <Scale className="h-4 w-4 text-primary" />
              <h4 className="font-bold text-sm text-text">4. Usage Rights, Ownership & Exclusivity</h4>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-3">
                <label className="block text-xs font-semibold text-text">Permitted Usage Rights</label>
                <div className="space-y-2 text-xs">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={organicReposting}
                      onChange={(e) => setOrganicReposting(e.target.checked)}
                      className="rounded text-primary focus:ring-primary h-4 w-4"
                    />
                    <span className="text-text font-medium">Organic Social Reposting & Sharing</span>
                  </label>

                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={paidAdsRights}
                      onChange={(e) => setPaidAdsRights(e.target.checked)}
                      className="rounded text-primary focus:ring-primary h-4 w-4"
                    />
                    <span className="text-text font-medium">Paid Advertising & Spark Ads (Whitelisting)</span>
                  </label>

                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={websiteUsage}
                      onChange={(e) => setWebsiteUsage(e.target.checked)}
                      className="rounded text-primary focus:ring-primary h-4 w-4"
                    />
                    <span className="text-text font-medium">Website, Landing Page & Email Marketing</span>
                  </label>
                </div>

                <div className="grid grid-cols-2 gap-2 pt-1">
                  <div>
                    <label className="block text-[11px] font-semibold text-text-secondary mb-1">License Duration</label>
                    <select
                      value={usageDuration}
                      onChange={(e) => setUsageDuration(e.target.value)}
                      className="w-full rounded-lg border border-border bg-white p-1.5 text-xs font-medium text-text focus:outline-none"
                    >
                      <option value="30 Days">30 Days</option>
                      <option value="3 Months">3 Months (Standard)</option>
                      <option value="6 Months">6 Months</option>
                      <option value="12 Months">12 Months</option>
                      <option value="Perpetual">Perpetual</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold text-text-secondary mb-1">Territory</label>
                    <select
                      value={usageTerritory}
                      onChange={(e) => setUsageTerritory(e.target.value)}
                      className="w-full rounded-lg border border-border bg-white p-1.5 text-xs font-medium text-text focus:outline-none"
                    >
                      <option value="India">India</option>
                      <option value="Worldwide">Worldwide</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <label className="block text-xs font-semibold text-text">Category Exclusivity</label>
                <div className="space-y-2 text-xs">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={exclusivityRequired}
                      onChange={(e) => setExclusivityRequired(e.target.checked)}
                      className="rounded text-primary focus:ring-primary h-4 w-4"
                    />
                    <span className="text-text font-medium">Require Competitor Category Exclusivity</span>
                  </label>
                </div>

                {exclusivityRequired && (
                  <div className="space-y-2 rounded-xl bg-page p-3 border border-border animate-fade-in">
                    <div>
                      <label className="block text-[11px] font-semibold text-text-secondary mb-1">Restricted Category</label>
                      <input
                        type="text"
                        value={exclusivityCategory}
                        onChange={(e) => setExclusivityCategory(e.target.value)}
                        placeholder="e.g. Skincare serums, Sunscreen"
                        className="w-full rounded-lg border border-border bg-white p-1.5 text-xs text-text focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-text-secondary mb-1">Duration (Days Post-Publishing)</label>
                      <select
                        value={exclusivityDuration}
                        onChange={(e) => setExclusivityDuration(Number(e.target.value))}
                        className="w-full rounded-lg border border-border bg-white p-1.5 text-xs text-text focus:outline-none"
                      >
                        <option value={15}>15 Days</option>
                        <option value={30}>30 Days (Standard)</option>
                        <option value={60}>60 Days</option>
                        <option value={90}>90 Days</option>
                      </select>
                    </div>
                  </div>
                )}

                <div className="pt-2">
                  <label className="block text-[11px] font-semibold text-text-secondary mb-1">IP & Copyright Model</label>
                  <select
                    value={copyrightOwner}
                    onChange={(e) => setCopyrightOwner(e.target.value)}
                    className="w-full rounded-lg border border-border bg-white p-1.5 text-xs font-medium text-text focus:outline-none"
                  >
                    <option value="INFLUENCER">Influencer Retains Copyright (Standard)</option>
                    <option value="BRAND">Full Work-for-Hire Assignment to Brand</option>
                  </select>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 6. Additional Conditions */}
        <div>
          <label className="block text-xs font-semibold text-text mb-1">Additional Agreed Terms / Notes (Optional)</label>
          <textarea
            value={additionalTerms}
            onChange={(e) => setAdditionalTerms(e.target.value)}
            rows={2}
            placeholder="e.g. Gifted product kit to be dispatched within 48h. High-resolution raw video file delivered via Drive."
            className="w-full rounded-xl border border-border bg-white p-2.5 text-xs text-text focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
      </div>

      {/* Modal Actions Footer */}
      <div className="flex items-center justify-between border-t border-border pt-4 mt-4">
        <Button variant="ghost" size="sm" onClick={onClose} disabled={loading} className="text-xs">
          Cancel
        </Button>

        <Button
          variant="primary"
          size="md"
          onClick={handleConfirm}
          disabled={loading}
          className="gap-2 bg-primary hover:bg-primary/90 text-white font-bold text-xs shadow-md"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Synthesizing Complete Agreement...</span>
            </>
          ) : (
            <>
              <FileCheck className="h-4 w-4" />
              <span>Confirm Terms & Generate Contract</span>
            </>
          )}
        </Button>
      </div>
    </Modal>
  )
}
