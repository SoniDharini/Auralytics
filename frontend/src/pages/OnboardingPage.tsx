import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle2, Sparkles } from 'lucide-react'
import { Button, Input, Select, StepIndicator, Textarea } from '@/components/ui'
import { cn } from '@/utils'

const steps = ['Brand', 'Audience', 'Objectives', 'Platforms', 'Finish']
const industries = [
  { value: 'beauty', label: 'Beauty & Personal Care' },
  { value: 'fashion', label: 'Fashion' },
  { value: 'tech', label: 'Technology' },
  { value: 'food', label: 'Food & Beverage' },
  { value: 'finance', label: 'Finance' },
]
const objectives = ['Brand awareness', 'Engagement', 'Conversions', 'Lead generation', 'Product launch']
const platforms = ['Instagram', 'YouTube', 'TikTok', 'X', 'LinkedIn']
const interests = ['Skincare', 'Wellness', 'Fashion', 'Fitness', 'Clean beauty', 'Lifestyle', 'Travel']

export function OnboardingPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [selectedObjectives, setSelectedObjectives] = useState<string[]>(['Product launch', 'Conversions'])
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(['Instagram', 'YouTube'])
  const [selectedInterests, setSelectedInterests] = useState<string[]>(['Skincare', 'Clean beauty'])

  const toggle = (list: string[], value: string, setter: (v: string[]) => void) => {
    setter(list.includes(value) ? list.filter((v) => v !== value) : [...list, value])
  }

  const finish = () => {
    localStorage.setItem('auralytics_onboarded', '1')
    navigate('/app')
  }

  return (
    <div className="min-h-screen bg-page flex items-center justify-center p-4 sm:p-8">
      <div className="w-full max-w-2xl">
        <div className="flex items-center gap-2.5 mb-8">
          <div className="h-8 w-8 rounded-lg ai-gradient-bg text-white font-bold flex items-center justify-center">A</div>
          <div>
            <p className="font-bold text-sm">Auralytics</p>
            <p className="text-[11px] text-text-secondary">Workspace setup</p>
          </div>
        </div>

        <div className="bg-white border border-border rounded-[16px] p-6 sm:p-8 shadow-sm">
          <StepIndicator steps={steps} current={step} className="mb-8" />

          {step === 1 && (
            <div className="space-y-4 animate-fade-in">
              <h1 className="text-2xl font-bold">Tell us about your brand</h1>
              <p className="text-sm text-text-secondary">This helps Strategy Agent tailor campaign recommendations.</p>
              <Input label="Company name" defaultValue="GlowNaturals" />
              <Select label="Industry" options={industries} defaultValue="beauty" />
              <Input label="Website" defaultValue="https://glownaturals.com" />
              <Input label="Primary market" defaultValue="India" />
              <Input label="Average campaign budget" defaultValue="₹2,00,000" />
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4 animate-fade-in">
              <h1 className="text-2xl font-bold">Define your audience</h1>
              <p className="text-sm text-text-secondary">Discovery Agent uses this to score creator fit.</p>
              <div className="grid sm:grid-cols-2 gap-4">
                <Input label="Target age" defaultValue="25–34" />
                <Select
                  label="Target gender"
                  options={[
                    { value: 'all', label: 'All' },
                    { value: 'female', label: 'Female-skewed' },
                    { value: 'male', label: 'Male-skewed' },
                  ]}
                  defaultValue="female"
                />
              </div>
              <Input label="Target locations" defaultValue="Mumbai, Delhi, Bangalore" />
              <div>
                <p className="text-sm font-medium mb-2">Interest categories</p>
                <div className="flex flex-wrap gap-2">
                  {interests.map((i) => (
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
              <Textarea label="Customer persona (optional)" placeholder="Describe your ideal customer..." />
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4 animate-fade-in">
              <h1 className="text-2xl font-bold">What are your objectives?</h1>
              <p className="text-sm text-text-secondary">Select all that apply for this workspace.</p>
              <div className="grid sm:grid-cols-2 gap-3">
                {objectives.map((o) => (
                  <button
                    key={o}
                    type="button"
                    onClick={() => toggle(selectedObjectives, o, setSelectedObjectives)}
                    className={cn(
                      'text-left rounded-[12px] border p-4 transition',
                      selectedObjectives.includes(o)
                        ? 'border-primary bg-primary-soft'
                        : 'border-border hover:border-primary/30',
                    )}
                  >
                    <p className="text-sm font-semibold">{o}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-4 animate-fade-in">
              <h1 className="text-2xl font-bold">Preferred platforms</h1>
              <p className="text-sm text-text-secondary">You can change these per campaign later.</p>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {platforms.map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => toggle(selectedPlatforms, p, setSelectedPlatforms)}
                    className={cn(
                      'rounded-[12px] border p-4 text-sm font-semibold transition',
                      selectedPlatforms.includes(p)
                        ? 'border-primary bg-primary-soft text-primary'
                        : 'border-border text-text-secondary hover:border-primary/30',
                    )}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 5 && (
            <div className="text-center py-8 animate-fade-in">
              <div className="mx-auto h-16 w-16 rounded-2xl ai-gradient-bg text-white flex items-center justify-center mb-5">
                <CheckCircle2 className="h-8 w-8" />
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold">Your AI marketing workspace is ready.</h1>
              <p className="mt-3 text-sm text-text-secondary max-w-md mx-auto">
                Strategy, Discovery, Outreach, and Performance agents are standing by for GlowNaturals Marketing.
              </p>
              <div className="mt-6 inline-flex items-center gap-2 text-xs font-semibold text-ai bg-violet-50 px-3 py-1.5 rounded-full">
                <Sparkles className="h-3.5 w-3.5" />
                Supervisor Agent initialized
              </div>
            </div>
          )}

          <div className="mt-8 flex items-center justify-between gap-3">
            <Button
              variant="secondary"
              disabled={step === 1}
              onClick={() => setStep((s) => Math.max(1, s - 1))}
            >
              Back
            </Button>
            {step < 5 ? (
              <Button onClick={() => setStep((s) => Math.min(5, s + 1))}>Continue</Button>
            ) : (
              <Button onClick={finish} size="lg">
                Launch Dashboard
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
