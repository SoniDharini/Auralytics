import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AlertTriangle,
  Bell,
  Building2,
  Key,
  LogOut,
  Palette,
  Shield,
  Sparkles,
  Target,
  User,
  Users,
  Webhook,
} from 'lucide-react'
import { Button, Card, CardContent, CardHeader, CardTitle, Input, Select, useToast } from '@/components/ui'
import { PageAmbientBackground, PageHeader } from '@/components/brand/VisualSystem'
import { LogoutConfirmationModal } from '@/components/auth/LogoutConfirmationModal'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/services/api'
import { cn } from '@/utils'

const sections = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'organization', label: 'Organization', icon: Building2 },
  { id: 'brand', label: 'Brand Preferences', icon: Palette },
  { id: 'ai', label: 'AI Preferences', icon: Sparkles },
  { id: 'campaign', label: 'Campaign Defaults', icon: Target },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'security', label: 'Security', icon: Shield },
  { id: 'team', label: 'Team Members', icon: Users },
  { id: 'integrations', label: 'API Integrations', icon: Webhook },
] as const

type SectionId = (typeof sections)[number]['id']

export function SettingsPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const { user, logout, updateUser } = useAuth()
  const [activeSection, setActiveSection] = useState<SectionId>('profile')
  const [logoutOpen, setLogoutOpen] = useState(false)

  const [fullName, setFullName] = useState(user?.full_name || 'Aaditya Sharma')
  const [companyName, setCompanyName] = useState(user?.company_name || 'GlowNaturals')
  const [role, setRole] = useState(user?.role || 'marketing_manager')

  const [aiPrefs, setAiPrefs] = useState({
    recommendations: true,
    autoAnalysis: true,
    autoDraft: true,
    humanApproval: true,
    autoBudget: false,
  })

  const [notifPrefs, setNotifPrefs] = useState({
    email: true,
    push: true,
    approvals: true,
    performance: true,
  })

  const handleSave = async () => {
    try {
      const updated = await api.auth.updateProfile({
        full_name: fullName,
        company_name: companyName,
        role: role,
      })
      updateUser(updated)
      toast({ type: 'success', title: 'Settings saved', description: 'Your preferences have been updated.' })
    } catch (err: any) {
      toast({ type: 'error', title: 'Update failed', description: err.message || 'Could not save profile changes.' })
    }
  }

  const handleLogoutConfirm = async () => {
    setLogoutOpen(false)
    await logout()
    navigate('/login')
  }

  const displayName = user?.full_name || fullName
  const displayEmail = user?.email || 'aaditya@glownaturals.com'
  const displayOrg = user?.company_name || companyName

  return (
    <div className="relative space-y-5 animate-fade-in">
      <PageAmbientBackground variant="default" className="h-[300px]" />
      <PageHeader
        eyebrow="Workspace"
        title="Settings"
        description="Manage your workspace, AI behavior, and team preferences."
      />

      <div className="relative flex flex-col lg:flex-row gap-6">
        <nav className="lg:w-56 shrink-0">
          <Card className="p-2 lg:sticky lg:top-6">
            <ul className="flex lg:flex-col gap-1 overflow-x-auto lg:overflow-visible">
              {sections.map(({ id, label, icon: Icon }) => (
                <li key={id}>
                  <button
                    onClick={() => setActiveSection(id)}
                    className={cn(
                      'w-full flex items-center gap-2.5 px-3 py-2.5 rounded-[10px] text-sm font-medium transition whitespace-nowrap',
                      activeSection === id
                        ? 'bg-primary-soft text-primary shadow-[inset_0_0_0_1px_color-mix(in_srgb,var(--auralytics-primary)_18%,transparent)]'
                        : 'text-text-secondary hover:bg-muted hover:text-text',
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    {label}
                  </button>
                </li>
              ))}
            </ul>
          </Card>
        </nav>

        <div className="flex-1 min-w-0">
          {activeSection === 'profile' && (
            <SettingsSection title="Profile" description="Your personal account details.">
              <div className="grid sm:grid-cols-2 gap-4">
                <Input
                  label="Full name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
                <Input
                  label="Email"
                  type="email"
                  value={displayEmail}
                  disabled
                />
                <Input
                  label="Job role"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                />
                <Input label="Phone" placeholder="+91 98765 43210" />
              </div>

              <div className="mt-8 pt-6 border-t border-border">
                <h3 className="text-sm font-semibold text-text">Account Session</h3>
                <p className="mt-1 text-sm text-text-secondary">
                  You are currently signed in as <span className="font-semibold text-text">{displayName}</span> ({displayEmail}).
                </p>
                <Button
                  type="button"
                  variant="secondary"
                  className="mt-4 border-danger/40 text-danger hover:bg-red-50 hover:border-danger/50"
                  onClick={() => setLogoutOpen(true)}
                >
                  <LogOut className="h-4 w-4" />
                  Logout
                </Button>
              </div>
            </SettingsSection>
          )}

          {activeSection === 'organization' && (
            <SettingsSection title="Organization" description="Workspace and company settings.">
              <div className="grid sm:grid-cols-2 gap-4">
                <Input
                  label="Organization name"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                />
                <Select
                  label="Industry"
                  options={[
                    { value: 'beauty', label: 'Beauty & Skincare' },
                    { value: 'fashion', label: 'Fashion' },
                    { value: 'tech', label: 'Technology' },
                  ]}
                  defaultValue="beauty"
                />
                <Input label="Website" defaultValue="https://glownaturals.com" />
                <Select
                  label="Timezone"
                  options={[
                    { value: 'ist', label: 'Asia/Kolkata (IST)' },
                    { value: 'utc', label: 'UTC' },
                  ]}
                  defaultValue="ist"
                />
              </div>
            </SettingsSection>
          )}

          {activeSection === 'brand' && (
            <SettingsSection title="Brand Preferences" description="Default brand voice and guidelines.">
              <div className="space-y-4">
                <Input label="Primary brand" defaultValue={displayOrg} />
                <Select
                  label="Brand voice"
                  options={[
                    { value: 'professional', label: 'Professional & trustworthy' },
                    { value: 'friendly', label: 'Friendly & approachable' },
                    { value: 'bold', label: 'Bold & energetic' },
                  ]}
                  defaultValue="professional"
                />
                <Input label="Target audience" defaultValue="Women 25–34, clean beauty enthusiasts" />
              </div>
            </SettingsSection>
          )}

          {activeSection === 'ai' && (
            <SettingsSection
              title="AI Preferences"
              description="Control how autonomous agents behave in your workspace."
            >
              <div className="space-y-4">
                <ToggleRow
                  label="AI recommendations"
                  description="Surface optimization and creator suggestions proactively."
                  checked={aiPrefs.recommendations}
                  onChange={(v) => setAiPrefs((p) => ({ ...p, recommendations: v }))}
                />
                <ToggleRow
                  label="Automatic analysis"
                  description="Run performance analysis on campaigns without manual triggers."
                  checked={aiPrefs.autoAnalysis}
                  onChange={(v) => setAiPrefs((p) => ({ ...p, autoAnalysis: v }))}
                />
                <ToggleRow
                  label="Automatic draft generation"
                  description="Let Outreach Agent prepare message drafts automatically."
                  checked={aiPrefs.autoDraft}
                  onChange={(v) => setAiPrefs((p) => ({ ...p, autoDraft: v }))}
                />
                <ToggleRow
                  label="Human approval requirements"
                  description="Require your approval before agents send outreach or modify campaigns."
                  checked={aiPrefs.humanApproval}
                  onChange={(v) => setAiPrefs((p) => ({ ...p, humanApproval: v }))}
                />

                <div className="rounded-xl border border-danger/30 bg-red-50/60 p-4 space-y-3">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="h-5 w-5 text-danger shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-semibold text-danger">Automatic budget modification</p>
                      <p className="text-xs text-text-secondary mt-1">
                        Allowing agents to modify budgets without approval can lead to unintended spend.
                        This feature requires explicit acknowledgment and cannot be enabled without warnings.
                      </p>
                    </div>
                  </div>
                  <ToggleRow
                    label="Enable automatic budget changes"
                    description="Disabled for safety. Agents must request approval for all budget moves."
                    checked={aiPrefs.autoBudget}
                    onChange={() => {
                      toast({
                        type: 'warning',
                        title: 'Feature restricted',
                        description:
                          'Automatic budget modification cannot be enabled. All budget changes require human approval.',
                      })
                    }}
                    disabled
                    dangerous
                  />
                </div>
              </div>
            </SettingsSection>
          )}

          {activeSection === 'campaign' && (
            <SettingsSection title="Campaign Defaults" description="Default values for new campaigns.">
              <div className="grid sm:grid-cols-2 gap-4">
                <Input label="Default budget (INR)" type="number" defaultValue="150000" />
                <Select
                  label="Default objective"
                  options={[
                    { value: 'awareness', label: 'Awareness' },
                    { value: 'conversions', label: 'Conversions' },
                    { value: 'launch', label: 'Product Launch' },
                  ]}
                  defaultValue="awareness"
                />
                <Select
                  label="Preferred platforms"
                  options={[
                    { value: 'instagram', label: 'Instagram' },
                    { value: 'multi', label: 'Multi-platform' },
                  ]}
                  defaultValue="instagram"
                />
                <Input label="Default campaign duration (days)" type="number" defaultValue="30" />
              </div>
            </SettingsSection>
          )}

          {activeSection === 'notifications' && (
            <SettingsSection title="Notifications" description="Choose how you receive alerts.">
              <div className="space-y-4">
                <ToggleRow
                  label="Email notifications"
                  description="Receive digest and critical alerts via email."
                  checked={notifPrefs.email}
                  onChange={(v) => setNotifPrefs((p) => ({ ...p, email: v }))}
                />
                <ToggleRow
                  label="Push notifications"
                  description="Browser push for urgent approvals and agent updates."
                  checked={notifPrefs.push}
                  onChange={(v) => setNotifPrefs((p) => ({ ...p, push: v }))}
                />
                <ToggleRow
                  label="Approval alerts"
                  description="Notify when agent actions need your review."
                  checked={notifPrefs.approvals}
                  onChange={(v) => setNotifPrefs((p) => ({ ...p, approvals: v }))}
                />
                <ToggleRow
                  label="Performance alerts"
                  description="Alert when ROAS or conversion metrics drop below thresholds."
                  checked={notifPrefs.performance}
                  onChange={(v) => setNotifPrefs((p) => ({ ...p, performance: v }))}
                />
              </div>
            </SettingsSection>
          )}

          {activeSection === 'security' && (
            <SettingsSection title="Security" description="Protect your account and workspace.">
              <div className="space-y-4">
                <Input label="Current password" type="password" placeholder="••••••••" />
                <Input label="New password" type="password" placeholder="••••••••" />
                <ToggleRow
                  label="Two-factor authentication"
                  description="Add an extra layer of security to your account."
                  checked={false}
                  onChange={() =>
                    toast({ type: 'info', title: '2FA setup', description: 'Redirecting to authentication setup…' })
                  }
                />
              </div>
            </SettingsSection>
          )}

          {activeSection === 'team' && (
            <SettingsSection title="Team Members" description="Manage who has access to this workspace.">
              <div className="space-y-3">
                {[
                  { name: displayName, email: displayEmail, role: 'Admin' },
                  { name: 'Priya Mehta', email: 'priya@glownaturals.com', role: 'Editor' },
                  { name: 'Rohan Singh', email: 'rohan@glownaturals.com', role: 'Viewer' },
                ].map((member) => (
                  <div
                    key={member.email}
                    className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl border border-border"
                  >
                    <div>
                      <p className="text-sm font-semibold">{member.name}</p>
                      <p className="text-xs text-text-secondary">{member.email}</p>
                    </div>
                    <Select
                      options={[
                        { value: 'admin', label: 'Admin' },
                        { value: 'editor', label: 'Editor' },
                        { value: 'viewer', label: 'Viewer' },
                      ]}
                      defaultValue={member.role.toLowerCase()}
                      className="w-32"
                    />
                  </div>
                ))}
                <Button variant="secondary" className="gap-2">
                  <Users className="h-4 w-4" /> Invite member
                </Button>
              </div>
            </SettingsSection>
          )}

          {activeSection === 'integrations' && (
            <SettingsSection title="API Integrations" description="Connect external platforms and services.">
              <div className="space-y-3">
                {[
                  { name: 'Instagram Graph API', status: 'Connected', connected: true },
                  { name: 'Shopify', status: 'Connected', connected: true },
                  { name: 'Google Analytics', status: 'Not connected', connected: false },
                ].map((integration) => (
                  <div
                    key={integration.name}
                    className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl border border-border"
                  >
                    <div className="flex items-center gap-3">
                      <div className="h-9 w-9 rounded-lg bg-muted flex items-center justify-center">
                        <Key className="h-4 w-4 text-text-secondary" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold">{integration.name}</p>
                        <p className="text-xs text-text-secondary">{integration.status}</p>
                      </div>
                    </div>
                    <Button variant={integration.connected ? 'secondary' : 'primary'} size="sm">
                      {integration.connected ? 'Configure' : 'Connect'}
                    </Button>
                  </div>
                ))}
              </div>
            </SettingsSection>
          )}

          <div className="mt-6 flex justify-end">
            <Button onClick={handleSave}>Save changes</Button>
          </div>
        </div>
      </div>

      <LogoutConfirmationModal
        open={logoutOpen}
        onClose={() => setLogoutOpen(false)}
        onConfirm={handleLogoutConfirm}
      />
    </div>
  )
}

function SettingsSection({
  title,
  description,
  children,
}: {
  title: string
  description: string
  children: React.ReactNode
}) {
  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>{title}</CardTitle>
          <p className="text-sm text-text-secondary mt-0.5">{description}</p>
        </div>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

function ToggleRow({
  label,
  description,
  checked,
  onChange,
  disabled,
  dangerous,
}: {
  label: string
  description: string
  checked: boolean
  onChange: (value: boolean) => void
  disabled?: boolean
  dangerous?: boolean
}) {
  return (
    <div
      className={cn(
        'flex items-start justify-between gap-4 p-4 rounded-xl border border-border',
        disabled && 'opacity-70',
        dangerous && 'border-danger/20 bg-red-50/30',
      )}
    >
      <div className="min-w-0">
        <p className="text-sm font-semibold">{label}</p>
        <p className="text-xs text-text-secondary mt-0.5">{description}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={cn(
          'relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40',
          disabled && 'cursor-not-allowed',
          checked ? (dangerous ? 'bg-danger/60' : 'bg-primary') : 'bg-muted',
        )}
      >
        <span
          className={cn(
            'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition',
            checked ? 'translate-x-5' : 'translate-x-0',
          )}
        />
      </button>
    </div>
  )
}
