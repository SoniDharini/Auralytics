export type AgentStatus = 'active' | 'idle' | 'processing' | 'completed' | 'error'

export type CampaignStatus = 'draft' | 'planning' | 'active' | 'paused' | 'completed' | 'needs_attention'

export type HealthStatus = 'excellent' | 'healthy' | 'needs_attention'

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'edited'

export type ContractStatus = 'signed' | 'pending_signature' | 'expired' | 'at_risk'

export type OutreachStatus =
  | 'not_contacted'
  | 'draft_ready'
  | 'awaiting_approval'
  | 'sent'
  | 'replied'
  | 'negotiating'
  | 'accepted'
  | 'rejected'

export type Platform = 'instagram' | 'youtube' | 'tiktok' | 'x' | 'linkedin'

export type CreatorTier = 'nano' | 'micro' | 'mid-tier' | 'macro' | 'celebrity'

export interface MetricCard {
  id: string
  label: string
  value: string
  context: string
  trend?: {
    value: string
    positive: boolean
  }
  sparkline?: number[]
}

export interface Agent {
  id: string
  name: string
  role: string
  status: AgentStatus
  currentTask: string
  lastAction: string
  tasksCompleted: number
  avgExecutionTime: string
  successRate: number
  lastActive: string
  progress?: number
  startedAt?: string
}

export interface Campaign {
  id: string
  name: string
  brand: string
  status: CampaignStatus
  health: HealthStatus
  budget: number
  spend: number
  revenue: number
  roas: number
  influencers: number
  progress: number
  startDate: string
  endDate: string
  conversions: number
  reach: number
  objective: string
}

export interface Influencer {
  id: string
  name: string
  username: string
  avatar: string
  platform: Platform
  verified: boolean
  niches: string[]
  followers: number
  engagementRate: number
  avgViews: number
  avgLikes: number
  avgComments: number
  estimatedCost: number
  location: string
  aiMatchScore: number
  predictedRoas: number
  audienceFit: number
  authenticity: number
  brandSafety: number
  nicheMatch: number
  budgetFit: number
  audienceGender: { male: number; female: number; other: number }
  audienceAge: { range: string; percent: number }[]
  topCountries: { country: string; percent: number }[]
  topCities: string[]
  interests: string[]
  whyRecommended: string
  shortlisted?: boolean
  status?: OutreachStatus
}

export interface ApprovalItem {
  id: string
  agent: string
  type: 'outreach' | 'negotiation' | 'budget' | 'campaign' | 'contract'
  action: string
  reason: string
  campaign: string
  financialImpact: string
  confidence: number
  timestamp: string
  status: ApprovalStatus
}

export interface Contract {
  id: string
  creator: string
  username: string
  campaign: string
  value: number
  status: ContractStatus
  startDate: string
  endDate: string
  paymentDue: string
  risk: string
  deliverables: string[]
  usageRights: string
  exclusivity: string
  aiRisks: string[]
}

export interface Insight {
  id: string
  title: string
  body: string
  impact: string
  confidence: number
  action: string
  type?: 'opportunity' | 'warning' | 'info'
}

export interface NotificationItem {
  id: string
  type: 'campaign' | 'agent' | 'approval' | 'contract' | 'performance' | 'budget'
  title: string
  body: string
  timestamp: string
  read: boolean
  actionLabel?: string
}

export interface TimelineEvent {
  id: string
  time: string
  agent: string
  message: string
  type: 'info' | 'success' | 'action' | 'human'
}

export interface OptimizationRec {
  id: string
  title: string
  current: { creator: string; remaining: number; roas: number }
  moves: { to: string; amount: number }[]
  expectedRevenue: string
  confidence: number
  status: 'pending' | 'approved' | 'rejected'
}

export interface FunnelStage {
  label: string
  value: number
}
