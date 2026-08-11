import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Bot,
  Check,
  CheckCircle2,
  Loader2,
  Sparkles,
  Target,
} from 'lucide-react'
import {
  Button,
  Card,
  CardContent,
  Input,
  Modal,
  Select,
  StepIndicator,
  Textarea,
} from '@/components/ui'
import type { CreatorTier, Platform } from '@/types'
import { cn, formatINR } from '@/utils'

const steps = ['Campaign', 'Audience', 'Creators', 'Budget', 'Goals', 'Review']

const campaignTypes = ['Product Launch', 'Awareness', 'Conversions', 'UGC', 'Always-on', 'Seasonal']
const objectives = [
  { value: 'launch', label: 'Product Launch' },
  { value: 'awareness', label: 'Brand Awareness' },
  { value: 'conversions', label: 'Conversions & Sales' },
  { value: 'engagement', label: 'Engagement' },
  { value: 'ugc', label: 'UGC Collection' },
]

const interestOptions = [
  'Skincare',
  'Clean beauty',
  'Wellness',
  'Fashion',
  'Fitness',
  'Lifestyle',
  'Travel',
  'Nutrition',
]
const languageOptions = ['English', 'Hindi', 'Tamil', 'Telugu', 'Marathi', 'Bengali']
const platformOptions: { id: Platform; label: string }[] = [
  { id: 'instagram', label: 'Instagram' },
  { id: 'youtube', label: 'YouTube' },
  { id: 'tiktok', label: 'TikTok' },
  { id: 'x', label: 'X' },
  { id: 'linkedin', label: 'LinkedIn' },
]
const tierOptions: { id: CreatorTier; label: string; desc: string }[] = [
  { id: 'nano', label: 'Nano', desc: '1K–10K followers' },
  { id: 'micro', label: 'Micro', desc: '10K–100K followers' },
  { id: 'mid-tier', label: 'Mid-tier', desc: '100K–500K followers' },
  { id: 'macro', label: 'Macro', desc: '500K–1M followers' },
  { id: 'celebrity', label: 'Celebrity', desc: '1M+ followers' },
]
const nicheOptions = ['Beauty', 'Skincare', 'Fashion', 'Lifestyle', 'Wellness', 'Fitness', 'Food', 'Education']
const primaryKpis = ['ROAS', 'CPA', 'Engagement Rate', 'Conversions', 'Reach', 'Brand Lift']
const secondaryKpis = ['CTR', 'Video Views', 'Story Views', 'Save Rate', 'Share Rate', 'Follower Growth']

import { api } from '@/services/api'

interface BudgetAllocation {
  id: string
  label: string
  amount: number
  color: string
}

const defaultAllocation: BudgetAllocation[] = [
  { id: 'micro', label: 'Micro Creators', amount: 90000, color: 'bg-primary' },
  { id: 'mid', label: 'Mid-tier Creators', amount: 70000, color: 'bg-accent' },
  { id: 'content', label: 'Content Production', amount: 20000, color: 'bg-ai' },
  { id: 'reserve', label: 'Reserve Fund', amount: 20000, color: 'bg-warning' },
]

const agentWorkflowSteps = [
  { agent: 'Supervisor Agent', task: 'Orchestrating campaign workflow', delay: 0 },
  { agent: 'Strategy Agent', task: 'Analyzing objectives and audience fit', delay: 1200 },
  { agent: 'Strategy Agent', task: 'Generating recommended creator mix', delay: 2400 },
  { agent: 'Discovery Agent', task: 'Scanning 487 influencers', delay: 3600 },
  { agent: 'Discovery Agent', task: 'Shortlisting top-fit creators', delay: 4800 },
  { agent: 'Outreach Agent', task: 'Preparing personalized messages', delay: 6000 },
]

export function CreateCampaignPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [showLaunchModal, setShowLaunchModal] = useState(false)
  const [workflowStep, setWorkflowStep] = useState(0)
  const [workflowComplete, setWorkflowComplete] = useState(false)
  const [createdCampaignId, setCreatedCampaignId] = useState<string>('camp-1')

  const [name, setName] = useState('')
  const [brand, setBrand] = useState('GlowNaturals')
  const [description, setDescription] = useState('')
  const [objective, setObjective] = useState('launch')
  const [startDate, setStartDate] = useState('2026-09-01')
  const [endDate, setEndDate] = useState('2026-10-15')
  const [selectedTypes, setSelectedTypes] = useState<string[]>(['Product Launch'])

  const [ageMin, setAgeMin] = useState(22)
  const [ageMax, setAgeMax] = useState(34)
  const [gender, setGender] = useState('female')
  const [locations, setLocations] = useState('Mumbai, Delhi, Bangalore, Pune')
  const [selectedInterests, setSelectedInterests] = useState<string[]>(['Skincare', 'Clean beauty', 'Wellness'])
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>(['English', 'Hindi'])
  const [persona, setPersona] = useState('')

  const [selectedPlatforms, setSelectedPlatforms] = useState<Platform[]>(['instagram', 'youtube'])
  const [selectedTiers, setSelectedTiers] = useState<CreatorTier[]>(['micro', 'mid-tier'])
  const [selectedNiches, setSelectedNiches] = useState<string[]>(['Beauty', 'Skincare', 'Lifestyle'])

  const [totalBudget, setTotalBudget] = useState(200000)
  const [allocation, setAllocation] = useState(defaultAllocation)

  const [primaryKpi, setPrimaryKpi] = useState('ROAS')
  const [secondaryKpiList, setSecondaryKpiList] = useState<string[]>(['Engagement Rate', 'Conversions'])
  const [targetRoas, setTargetRoas] = useState('3.0')
  const [targetCpa, setTargetCpa] = useState('150')
  const [targetEngagement, setTargetEngagement] = useState('5.5')
  const [targetConversions, setTargetConversions] = useState('400')

  const allocatedTotal = allocation.reduce((s, a) => s + a.amount, 0)
  const allocationValid = allocatedTotal === totalBudget

  const toggle = <T extends string>(list: T[], value: T, setter: (v: T[]) => void) => {
    setter(list.includes(value) ? list.filter((v) => v !== value) : [...list, value])
  }

  const updateAllocation = (id: string, amount: number) => {
    setAllocation((prev) => prev.map((a) => (a.id === id ? { ...a, amount: Math.max(0, amount) } : a)))
  }

  const objectiveLabel = objectives.find((o) => o.value === objective)?.label ?? objective

  const handleLaunch = async () => {
    setShowLaunchModal(true)
    setWorkflowStep(0)
    setWorkflowComplete(false)

    try {
      const payload = {
        name: name || 'New Influencer Campaign',
        brand: brand || 'GlowNaturals',
        description,
        budget: totalBudget,
        objective: objectiveLabel,
        start_date: startDate,
        end_date: endDate,
        status: 'active',
        health: 'excellent',
        campaign_types: selectedTypes,
        target_locations: locations,
        target_age_min: ageMin,
        target_age_max: ageMax,
        target_gender: gender,
        interests: selectedInterests,
        languages: selectedLanguages,
        platforms: selectedPlatforms,
        creator_tiers: selectedTiers,
        budget_allocation: allocation,
        primary_kpi: primaryKpi,
        target_roas: parseFloat(targetRoas) || 3.0,
        target_cpa: parseFloat(targetCpa) || 150,
      }
      const res = await api.campaigns.create(payload)
      if (res?.id) {
        setCreatedCampaignId(res.id)
      }
    } catch {
      // Keep default fallback
    }
  }

  useEffect(() => {
    if (!showLaunchModal) return
    const timers = agentWorkflowSteps.map((_, i) =>
      setTimeout(() => setWorkflowStep(i + 1), agentWorkflowSteps[i].delay + 800),
    )
    const completeTimer = setTimeout(() => {
      setWorkflowComplete(true)
      setTimeout(() => navigate(`/app/campaigns/${createdCampaignId}`), 1500)
    }, 7200)
    return () => {
      timers.forEach(clearTimeout)
      clearTimeout(completeTimer)
    }
  }, [showLaunchModal, createdCampaignId, navigate])

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Link to="/app/campaigns">
          <Button variant="ghost" size="icon" aria-label="Back to campaigns">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Create Campaign</h1>
          <p className="text-sm text-text-secondary mt-0.5">
            Your AI agent team will handle discovery, outreach, and optimization.
          </p>
        </div>
      </div>

      <Card>
        <CardContent className="pt-6">
          <StepIndicator steps={steps} current={step} className="mb-8" />

          {step === 1 && (
            <div className="space-y-4 animate-fade-in">
              <div>
                <h2 className="text-xl font-bold">Campaign details</h2>
                <p className="text-sm text-text-secondary mt-1">
                  Define the core brief for Strategy Agent.
                </p>
              </div>
              <Input label="Campaign name" placeholder="e.g. Summer Serum Launch" value={name} onChange={(e) => setName(e.target.value)} />
              <Input label="Brand" value={brand} onChange={(e) => setBrand(e.target.value)} />
              <Textarea
                label="Description"
                placeholder="Describe the campaign goals, product, and key messaging..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
              <Select label="Primary objective" options={objectives} value={objective} onChange={(e) => setObjective(e.target.value)} />
              <div className="grid sm:grid-cols-2 gap-4">
                <Input label="Start date" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
                <Input label="End date" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
              </div>
              <div>
                <p className="text-sm font-medium mb-2">Campaign type</p>
                <div className="flex flex-wrap gap-2">
                  {campaignTypes.map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => toggle(selectedTypes, t, setSelectedTypes)}
                      className={cn(
                        'px-3 py-1.5 rounded-full text-xs font-semibold border transition',
                        selectedTypes.includes(t)
                          ? 'bg-primary-soft border-primary/30 text-primary'
                          : 'bg-white border-border text-text-secondary hover:border-primary/30',
                      )}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4 animate-fade-in">
              <div>
                <h2 className="text-xl font-bold">Target audience</h2>
                <p className="text-sm text-text-secondary mt-1">
                  Discovery Agent uses this to score creator fit.
                </p>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-medium">Age range</p>
                  <span className="text-sm font-semibold text-primary">
                    {ageMin} – {ageMax}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-text-secondary">Min age</label>
                    <input
                      type="range"
                      min={18}
                      max={55}
                      value={ageMin}
                      onChange={(e) => setAgeMin(Math.min(Number(e.target.value), ageMax - 1))}
                      className="w-full accent-primary mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-text-secondary">Max age</label>
                    <input
                      type="range"
                      min={19}
                      max={65}
                      value={ageMax}
                      onChange={(e) => setAgeMax(Math.max(Number(e.target.value), ageMin + 1))}
                      className="w-full accent-primary mt-1"
                    />
                  </div>
                </div>
              </div>
              <Select
                label="Target gender"
                options={[
                  { value: 'all', label: 'All genders' },
                  { value: 'female', label: 'Female-skewed' },
                  { value: 'male', label: 'Male-skewed' },
                ]}
                value={gender}
                onChange={(e) => setGender(e.target.value)}
              />
              <Input label="Target locations" value={locations} onChange={(e) => setLocations(e.target.value)} />
              <div>
                <p className="text-sm font-medium mb-2">Interests</p>
                <div className="flex flex-wrap gap-2">
                  {interestOptions.map((i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => toggle(selectedInterests, i, setSelectedInterests)}
                      className={cn(
                        'px-3 py-1.5 rounded-full text-xs font-semibold border transition',
                        selectedInterests.includes(i)
                          ? 'bg-primary-soft border-primary/30 text-primary'
                          : 'bg-white border-border text-text-secondary hover:border-primary/30',
                      )}
                    >
                      {i}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-sm font-medium mb-2">Languages</p>
                <div className="flex flex-wrap gap-2">
                  {languageOptions.map((l) => (
                    <button
                      key={l}
                      type="button"
                      onClick={() => toggle(selectedLanguages, l, setSelectedLanguages)}
                      className={cn(
                        'px-3 py-1.5 rounded-full text-xs font-semibold border transition',
                        selectedLanguages.includes(l)
                          ? 'bg-primary-soft border-primary/30 text-primary'
                          : 'bg-white border-border text-text-secondary hover:border-primary/30',
                      )}
                    >
                      {l}
                    </button>
                  ))}
                </div>
              </div>
              <Textarea
                label="Customer persona"
                placeholder="Describe your ideal customer — demographics, pain points, buying behavior..."
                value={persona}
                onChange={(e) => setPersona(e.target.value)}
              />
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4 animate-fade-in">
              <div>
                <h2 className="text-xl font-bold">Creator preferences</h2>
                <p className="text-sm text-text-secondary mt-1">
                  Tell Discovery Agent what kind of creators to find.
                </p>
              </div>
              <div>
                <p className="text-sm font-medium mb-2">Platforms</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {platformOptions.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => toggle(selectedPlatforms, p.id, setSelectedPlatforms)}
                      className={cn(
                        'rounded-[12px] border p-3 text-sm font-semibold transition text-left',
                        selectedPlatforms.includes(p.id)
                          ? 'border-primary bg-primary-soft text-primary'
                          : 'border-border text-text-secondary hover:border-primary/30',
                      )}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-sm font-medium mb-2">Creator tiers</p>
                <div className="grid sm:grid-cols-2 gap-3">
                  {tierOptions.map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => toggle(selectedTiers, t.id, setSelectedTiers)}
                      className={cn(
                        'text-left rounded-[12px] border p-4 transition',
                        selectedTiers.includes(t.id)
                          ? 'border-primary bg-primary-soft'
                          : 'border-border hover:border-primary/30',
                      )}
                    >
                      <p className="text-sm font-semibold">{t.label}</p>
                      <p className="text-xs text-text-secondary mt-0.5">{t.desc}</p>
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-sm font-medium mb-2">Niches</p>
                <div className="flex flex-wrap gap-2">
                  {nicheOptions.map((n) => (
                    <button
                      key={n}
                      type="button"
                      onClick={() => toggle(selectedNiches, n, setSelectedNiches)}
                      className={cn(
                        'px-3 py-1.5 rounded-full text-xs font-semibold border transition',
                        selectedNiches.includes(n)
                          ? 'bg-primary-soft border-primary/30 text-primary'
                          : 'bg-white border-border text-text-secondary hover:border-primary/30',
                      )}
                    >
                      {n}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-4 animate-fade-in">
              <div>
                <h2 className="text-xl font-bold">Budget & allocation</h2>
                <p className="text-sm text-text-secondary mt-1">
                  AI-recommended split — adjust to match your priorities.
                </p>
              </div>
              <Input
                label="Total budget (INR)"
                type="number"
                value={totalBudget}
                onChange={(e) => setTotalBudget(Number(e.target.value) || 0)}
              />
              <div className="rounded-[12px] border border-border bg-primary-soft/50 p-4">
                <div className="flex items-center gap-2 mb-4">
                  <Sparkles className="h-4 w-4 text-ai" />
                  <p className="text-sm font-semibold text-ai">AI Recommended Allocation</p>
                </div>
                <div className="space-y-4">
                  {allocation.map((item) => {
                    const pct = totalBudget > 0 ? (item.amount / totalBudget) * 100 : 0
                    return (
                      <div key={item.id}>
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-sm font-medium">{item.label}</span>
                          <div className="flex items-center gap-2">
                            <input
                              type="number"
                              value={item.amount}
                              onChange={(e) => updateAllocation(item.id, Number(e.target.value) || 0)}
                              className="w-24 h-8 px-2 text-xs font-semibold text-right rounded-lg border border-border bg-white focus:outline-none focus:ring-2 focus:ring-primary/30"
                            />
                            <span className="text-xs text-text-secondary w-10">{Math.round(pct)}%</span>
                          </div>
                        </div>
                        <div className="h-3 rounded-full bg-muted overflow-hidden">
                          <div
                            className={cn('h-full rounded-full transition-all duration-300', item.color)}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
                <div className="mt-4 pt-3 border-t border-border flex items-center justify-between">
                  <span className="text-sm text-text-secondary">Allocated total</span>
                  <span
                    className={cn(
                      'text-sm font-bold',
                      allocationValid ? 'text-success' : 'text-danger',
                    )}
                  >
                    {formatINR(allocatedTotal)} / {formatINR(totalBudget)}
                  </span>
                </div>
                {!allocationValid && (
                  <p className="text-xs text-danger mt-1">
                    Allocation must equal total budget ({formatINR(totalBudget - allocatedTotal)} remaining)
                  </p>
                )}
              </div>
            </div>
          )}

          {step === 5 && (
            <div className="space-y-4 animate-fade-in">
              <div>
                <h2 className="text-xl font-bold">Goals & KPIs</h2>
                <p className="text-sm text-text-secondary mt-1">
                  Performance Agent will track these throughout the campaign.
                </p>
              </div>
              <Select
                label="Primary KPI"
                options={primaryKpis.map((k) => ({ value: k, label: k }))}
                value={primaryKpi}
                onChange={(e) => setPrimaryKpi(e.target.value)}
              />
              <div>
                <p className="text-sm font-medium mb-2">Secondary KPIs</p>
                <div className="flex flex-wrap gap-2">
                  {secondaryKpis.map((k) => (
                    <button
                      key={k}
                      type="button"
                      onClick={() => toggle(secondaryKpiList, k, setSecondaryKpiList)}
                      className={cn(
                        'px-3 py-1.5 rounded-full text-xs font-semibold border transition',
                        secondaryKpiList.includes(k)
                          ? 'bg-primary-soft border-primary/30 text-primary'
                          : 'bg-white border-border text-text-secondary hover:border-primary/30',
                      )}
                    >
                      {k}
                    </button>
                  ))}
                </div>
              </div>
              <div className="grid sm:grid-cols-2 gap-4">
                <Input label="Target ROAS" value={targetRoas} onChange={(e) => setTargetRoas(e.target.value)} hint="e.g. 3.0x" />
                <Input label="Target CPA (INR)" value={targetCpa} onChange={(e) => setTargetCpa(e.target.value)} />
                <Input label="Target engagement rate (%)" value={targetEngagement} onChange={(e) => setTargetEngagement(e.target.value)} />
                <Input label="Target conversions" value={targetConversions} onChange={(e) => setTargetConversions(e.target.value)} />
              </div>
            </div>
          )}

          {step === 6 && (
            <div className="space-y-5 animate-fade-in">
              <div className="text-center py-4">
                <div className="mx-auto h-14 w-14 rounded-2xl ai-gradient-bg text-white flex items-center justify-center mb-4">
                  <Target className="h-7 w-7" />
                </div>
                <h2 className="text-xl font-bold">Review your campaign</h2>
                <p className="text-sm text-text-secondary mt-1 max-w-md mx-auto">
                  Everything looks good. Launch to activate your AI agent team.
                </p>
              </div>

              <div className="grid sm:grid-cols-2 gap-4">
                {[
                  { title: 'Campaign', items: [name || 'Untitled Campaign', brand, objectiveLabel, `${startDate} → ${endDate}`] },
                  { title: 'Audience', items: [`Ages ${ageMin}–${ageMax}`, gender, locations, selectedInterests.slice(0, 3).join(', ')] },
                  { title: 'Creators', items: [selectedPlatforms.join(', '), selectedTiers.join(', '), selectedNiches.join(', ')] },
                  { title: 'Budget', items: [formatINR(totalBudget), ...allocation.map((a) => `${a.label}: ${formatINR(a.amount)}`)] },
                  { title: 'Goals', items: [`Primary: ${primaryKpi}`, `ROAS ${targetRoas}x`, `CPA ₹${targetCpa}`, `${targetConversions} conversions`] },
                ].map((section) => (
                  <div key={section.title} className="rounded-[12px] border border-border p-4 bg-page/50">
                    <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-2">
                      {section.title}
                    </p>
                    <ul className="space-y-1">
                      {section.items.map((item, i) => (
                        <li key={i} className="text-sm font-medium flex items-start gap-2">
                          <Check className="h-4 w-4 text-success shrink-0 mt-0.5" />
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>

              <div className="flex flex-col sm:flex-row gap-3 pt-2">
                <Button variant="ai" size="lg" className="flex-1 gap-2" onClick={handleLaunch}>
                  <Sparkles className="h-4 w-4" />
                  Launch AI Campaign
                </Button>
                <Button variant="secondary" size="lg" className="flex-1" onClick={() => navigate('/app/campaigns')}>
                  Save Draft
                </Button>
              </div>
            </div>
          )}

          {step < 6 && (
            <div className="mt-8 flex items-center justify-between gap-3">
              <Button variant="secondary" disabled={step === 1} onClick={() => setStep((s) => Math.max(1, s - 1))}>
                Back
              </Button>
              <Button
                onClick={() => setStep((s) => Math.min(6, s + 1))}
                disabled={step === 4 && !allocationValid}
              >
                Continue
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Modal
        open={showLaunchModal}
        onClose={() => {}}
        title=""
        className="max-w-md"
      >
        <div className="text-center -mt-2">
          <div className="mx-auto h-12 w-12 rounded-xl ai-gradient-bg text-white flex items-center justify-center mb-4">
            <Bot className="h-6 w-6" />
          </div>
          <h3 className="text-lg font-bold">Supervisor Agent has started building your campaign.</h3>
          <p className="text-sm text-text-secondary mt-2">
            Your AI team is working through the launch workflow.
          </p>
        </div>

        <div className="mt-6 space-y-3">
          {agentWorkflowSteps.map((s, i) => {
            const done = workflowStep > i
            const active = workflowStep === i + 1 && !workflowComplete
            const pending = workflowStep <= i
            return (
              <div
                key={i}
                className={cn(
                  'flex items-start gap-3 p-3 rounded-[10px] border transition-all duration-500',
                  done && 'border-success/30 bg-green-50/50',
                  active && 'border-primary/30 bg-primary-soft',
                  pending && !active && 'border-border bg-page/50 opacity-60',
                )}
              >
                <div className="mt-0.5">
                  {done ? (
                    <CheckCircle2 className="h-5 w-5 text-success" />
                  ) : active ? (
                    <Loader2 className="h-5 w-5 text-primary animate-spin" />
                  ) : (
                    <div className="h-5 w-5 rounded-full border-2 border-border" />
                  )}
                </div>
                <div className="min-w-0 text-left">
                  <p className="text-xs font-semibold text-ai">{s.agent}</p>
                  <p className="text-sm font-medium">{s.task}</p>
                </div>
              </div>
            )
          })}
        </div>

        {workflowComplete && (
          <div className="mt-4 text-center text-sm font-semibold text-success animate-fade-in">
            Campaign ready — redirecting to Command Center...
          </div>
        )}
      </Modal>
    </div>
  )
}
