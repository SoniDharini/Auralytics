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
  description?: string
  campaign_types?: string[]
  target_locations?: string
  target_age_min?: number
  target_age_max?: number
  target_gender?: string
  interests?: string[]
  languages?: string[]
  platforms?: Platform[]
  creator_tiers?: CreatorTier[]
  budget_allocation?: { id: string; label: string; amount: number; color?: string; rationale?: string }[]
  workflow_state?: string
  workflowState?: string
  keywords?: string[]
  min_followers?: number
  max_followers?: number
  last_discovery_at?: string
  primary_kpi?: string
  target_roas?: number
  target_cpa?: number
  created_at?: string
  updated_at?: string
}

export interface CampaignActivity {
  id: string
  user_id: string
  campaign_id?: string | null
  activity_type: string
  title: string
  description?: string | null
  metadata_json?: Record<string, any> | null
  created_at: string
}

export interface DashboardSummary {
  total_campaigns: number
  active_campaigns: number
  pending_campaigns: number
  completed_campaigns: number
  total_spend: number
  total_revenue: number
  average_roas: number
  pending_approvals: number
}

export interface Influencer {
  id: string
  external_id?: string | null
  name: string
  username: string
  description?: string | null
  avatar?: string | null
  profile_url?: string | null
  thumbnail_url?: string | null
  platform: Platform | string
  verified: boolean
  niches: string[]
  followers: number
  total_views?: number
  content_count?: number
  engagementRate: number
  avgViews: number
  avgLikes: number
  avgComments: number
  estimatedCost?: number | null
  location?: string | null
  country?: string | null
  aiMatchScore?: number | null
  predictedRoas?: number | null
  audienceFit?: number | null
  authenticity?: number | null
  brandSafety?: number | null
  nicheMatch?: number | null
  budgetFit?: number | null
  audienceGender?: { male: number; female: number; other: number } | null
  audienceAge?: { range: string; percent: number }[] | null
  topCountries?: { country: string; percent: number }[] | null
  topCities?: string[] | null
  interests?: string[]
  whyRecommended?: string | null
  shortlisted?: boolean
  status?: OutreachStatus
  data_source?: string
  source_fetched_at?: string | null
  created_at?: string
  updated_at?: string
  businessEmail?: string | null
  emailSource?: string | null
  emailVerified?: boolean
  lastUploadAt?: string | null
  metricsSampleSize?: number
  metricsSource?: string | null
}

export type CampaignCreatorStatus = 'DISCOVERED' | 'SHORTLISTED' | 'REJECTED' | 'CONTACTED'

/** One weighted, explainable input to a campaign match score. */
export interface MatchFactor {
  key: string
  label: string
  weight: number
  score: number | null
  available: boolean
  detail: string
}

/** A creator as seen from inside one campaign. */
export interface CampaignCreator {
  link_id: string
  campaign_id: string
  status: CampaignCreatorStatus
  match_score?: number | null
  match_reasons?: MatchFactor[] | null
  discovery_query?: string | null
  discovered_at: string
  creator: Influencer
}

export interface CampaignCreatorListResponse {
  campaign_id: string
  source: string
  count: number
  total: number
  page: number
  limit: number
  creators: CampaignCreator[]
}

export interface DiscoveryStats {
  queries: string[]
  raw_candidates: number
  unique_channels: number
  enriched_channels: number
  passed_filters: number
  filtered_out: number
  created: number
  updated: number
  reused_from_cache: number
}

export interface DiscoveryResponse {
  campaign_id: string
  source: string
  status: string
  count: number
  stats: DiscoveryStats
  creators: CampaignCreator[]
}

export interface IntegrationStatus {
  youtube: {
    configured: boolean
    max_creators?: number
  }
  instagram: {
    configured: boolean
    api_version?: string
  }
}

export interface InfluencerFetchResponse {
  campaign_id: string
  status: string
  total_discovered: number
  providers: Record<
    string,
    {
      status: string
      fetched: number
      created: number
      updated: number
      message?: string | null
    }
  >
  influencers?: Influencer[]
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

export interface AgentRun {
  id: string
  userId: string
  campaignId: string
  agentName: string
  agentVersion: string
  status: string
  trigger: string
  inputSummary?: string | null
  outputJson?: Record<string, unknown> | null
  confidence?: number | null
  requiresApproval: boolean
  errorMessage?: string | null
  provider?: string | null
  model?: string | null
  providerLatencyMs?: number | null
  startedAt?: string | null
  completedAt?: string | null
  createdAt: string
}

export interface CampaignStrategy {
  id: string
  campaignId: string
  agentRunId?: string | null
  strategyJson: Record<string, any>
  version: number
  createdAt: string
  updatedAt: string
}

export interface SupervisorStartResponse {
  campaignId: string
  workflowState: string
  next?: string | null
  message: string
  agentRun?: AgentRun | null
}

export interface AIStatus {
  provider: string
  configured: boolean
  reachable: boolean
  model_configured: boolean
  model?: string | null
  detail?: string | null
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
