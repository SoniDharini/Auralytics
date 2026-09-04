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

export type WorkflowStepStatus =
  | 'COMPLETED'
  | 'CURRENT'
  | 'NEXT'
  | 'PENDING'
  | 'LOCKED'
  | 'FAILED'
  | 'WAITING_APPROVAL'

export interface CampaignWorkflowStep {
  key: string
  label: string
  status: WorkflowStepStatus | string
  route?: string | null
  tab?: string | null
  hint?: string | null
}

export interface CampaignWorkflowAction {
  key: string
  label: string
  description: string
  route: string
  tab?: string | null
  enabled: boolean
  running: boolean
}

export interface CampaignWorkflow {
  campaign_id: string
  current_step: string
  next_step: string
  progress_percentage: number
  blocking_reason?: string | null
  next_action: CampaignWorkflowAction
  steps: CampaignWorkflowStep[]
  discovered_count: number
  shortlisted_count: number
  outreach_count: number
  pending_approval: boolean
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

export type CampaignCreatorStatus =
  | 'DISCOVERED'
  | 'SHORTLISTED'
  | 'REJECTED'
  | 'CONTACTED'
  | 'NEGOTIATING'
  | 'ACCEPTED'
  | 'DECLINED'

export interface ConversationTurn {
  sender: 'BRAND' | 'INFLUENCER' | 'AI_DRAFT' | string
  message: string
  subject?: string
  message_type?: string
  timestamp?: string
  extracted_terms?: Record<string, any>
  conversation_state?: string
  terms?: Record<string, any>
}

export interface OutreachMessageItem {
  id: string
  campaignId?: string
  campaign_id?: string
  influencerId: string
  influencer_id?: string
  agentRunId?: string
  agent_run_id?: string
  influencerName: string
  influencer_name?: string
  influencerUsername: string
  influencer_username?: string
  campaignName: string
  campaign_name?: string
  channel: string
  subject?: string
  body: string
  message?: string
  shortDm?: string
  short_dm?: string
  callToAction?: string
  call_to_action?: string
  personalizationPoints?: string[]
  personalization_points?: string[]
  confidence?: number
  status: string
  sentAt?: string
  sent_at?: string
  reply?: string
  negotiationState?: string
  negotiation_state?: string
  responseStatus?: 'PENDING_RESPONSE' | 'ACCEPTED' | 'REJECTED' | string
  response_status?: string
  responseText?: string
  response_text?: string
  finalAmount?: number
  final_amount?: number
  currency?: string
  deliverables?: string[]
  timelineStart?: string
  timeline_start?: string
  timelineEnd?: string
  timeline_end?: string
  additionalTerms?: string
  additional_terms?: string
  rejectionReason?: string
  rejection_reason?: string
  rejectionNotes?: string
  rejection_notes?: string
  contractId?: string
  contract_id?: string
  extractedTerms?: Record<string, any>
  extracted_terms?: Record<string, any>
  conversationHistory?: ConversationTurn[]
  conversation_history?: ConversationTurn[]
  contactInfo?: {
    email?: string
    instagram?: string
    youtube?: string
  }
  createdAt?: string
  created_at?: string
}

export interface OutreachAcceptancePayload {
  response_notes?: string
  final_amount: number
  currency?: string
  deliverables: string[]
  timeline_start: string
  timeline_end: string
  additional_terms?: string
}

export interface OutreachRejectionPayload {
  rejection_reason: string
  rejection_notes?: string
}

export interface OutreachNegotiateResponse {
  conversation_state: string
  influencer_reply_summary: string
  extracted_terms: Record<string, any>
  recommended_action: string
  subject?: string
  message: string
  short_dm?: string
  confidence: number
  budget_constraint_warning?: string | null
  outreach_message?: OutreachMessageItem
}

/** One weighted, explainable input to a campaign match score. */
export interface MatchFactor {
  key: string
  label: string
  weight: number
  score?: number | null
  available?: boolean
  detail: string
  recommendation_reason?: string
  creator_tier?: string
  tier_match?: string
  eligibility?: string
  creator_entity_type?: string
  collaboration_suitability?: string
  recommendation_type?: string
  recent_avg_views?: number | null
  recent_momentum?: string
  persona_relevance?: {
    target?: string
    level?: string
    source?: string
    reason?: string
  }
  requirement_match?: Record<string, string>
  classification?: Record<string, string>
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

export interface ManualSearchMismatch {
  code: string
  label: string
  detail: string
}

export interface ManualSearchResult {
  channel_id: string
  influencer_id?: string | null
  link_id?: string | null
  campaign_status?: string | null
  already_in_campaign: boolean
  already_recommended: boolean
  already_shortlisted: boolean
  previously_rejected: boolean
  selection_source: string
  creator: Influencer
  entity_type: string
  collaboration_suitable: boolean
  shortlist_allowed: boolean
  meets_requirements: boolean
  manual_override_required: boolean
  eligibility?: string | null
  requirement_match?: Record<string, string>
  mismatches: ManualSearchMismatch[]
  warning?: string | null
  tier?: string | null
  match_score?: number | null
  persona_relevance?: {
    target?: string
    level?: string
    source?: string
    reason?: string
  } | null
  recent_avg_views?: number | null
  recent_momentum?: string | null
  query?: string | null
}

export interface ManualCreatorSearchResponse {
  campaign_id: string
  query: string
  query_kind: string
  count: number
  results: ManualSearchResult[]
  message?: string | null
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

export interface RiskFlag {
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | string
  issue: string
  reason: string
  recommended_review?: string
}

export interface ContractConflict {
  clause: string
  negotiated_term: string
  contract_term: string
  explanation: string
}

export interface ChangeRequestItem {
  version: number
  requested_changes: string
  reason: string
  requested_by?: string
  timestamp: string
}

export interface Contract {
  id: string
  campaignId?: string
  campaign_id?: string
  influencerId?: string
  influencer_id?: string
  outreachId?: string
  outreach_id?: string
  agentRunId?: string
  agent_run_id?: string
  creator: string
  username: string
  campaign: string
  value: number
  currency?: string
  status: ContractStatus | string
  version?: number
  startDate: string
  start_date?: string
  endDate: string
  end_date?: string
  paymentDue: string
  payment_due?: string
  risk: string
  deliverables: string[]
  usageRights: string
  usage_rights?: string
  exclusivity: string
  additionalTerms?: string
  additional_terms?: string
  contractBody?: string
  contract_body?: string
  aiRisks: string[]
  ai_risks?: string[]
  analysisJson?: Record<string, any>
  analysis_json?: Record<string, any>
  missingClauses?: string[]
  missing_clauses?: string[]
  conflicts?: ContractConflict[]
  riskFlags?: RiskFlag[]
  risk_flags?: RiskFlag[]
  commercialTermsMatch?: Record<string, any>
  commercial_terms_match?: Record<string, any>
  overallStatus?: string
  overall_status?: string
  approvedBy?: string
  approved_by?: string
  approvedAt?: string
  approved_at?: string
  changeRequests?: ChangeRequestItem[]
  change_requests?: ChangeRequestItem[]
  createdAt?: string
  created_at?: string
  updatedAt?: string
  updated_at?: string
}

export interface CompensationTerms {
  total: number
  currency: string
}

export interface PaymentScheduleTerms {
  structure: '50_50' | '100_completion' | 'custom' | string
  advance_percentage: number
  advance_amount: number
  balance_percentage: number
  balance_amount: number
  method: string
  balance_due_days: number
  terms_text?: string
}

export interface TimelineTerms {
  start_date: string
  end_date: string
  draft_submission_deadline?: string
  publishing_deadline?: string
}

export interface RevisionTerms {
  allowed_rounds: number
  scope: string
}

export interface ApprovalTerms {
  pre_publication_required: boolean
  review_window_days?: number
}

export interface ProductClaimsTerms {
  policy: string
  claim_guidelines?: string
}

export interface UsageRightsTerms {
  organic_reposting: boolean
  paid_ads: boolean
  website_use: boolean
  duration: string
  territory: string
}

export interface OwnershipTerms {
  copyright_owner: string
  license_grant?: string
}

export interface ExclusivityTerms {
  required: boolean
  category?: string
  duration_days: number
  scope?: string
}

export interface CancellationTerms {
  brand_cancellation?: string
  influencer_cancellation?: string
  force_majeure?: string
}

export interface TerminationTerms {
  grounds: string[]
}

export interface ContractTermsPayload {
  influencer_id?: string
  campaign_id?: string
  creator_name?: string
  creator_username?: string
  campaign_name?: string
  brand_name?: string
  compensation: CompensationTerms
  payment: PaymentScheduleTerms
  deliverables: string[]
  timeline: TimelineTerms
  revisions: RevisionTerms
  approval: ApprovalTerms
  product_claims: ProductClaimsTerms
  usage_rights: UsageRightsTerms
  ownership: OwnershipTerms
  exclusivity: ExclusivityTerms
  cancellation: CancellationTerms
  termination: TerminationTerms
  additional_terms?: string
}

export interface ContractReadiness {
  ready: boolean
  status: string
  missing_fields: string[]
  blocking_reason?: string | null
  final_terms?: Record<string, any>
  suggested_terms?: ContractTermsPayload | Record<string, any>
  creator_name?: string
  creator_username?: string
  outreach_status?: string
  shortlist_status?: string
  contract_id?: string
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
  contractId?: string | null
  contract_id?: string | null
  contract?: Contract | null
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
