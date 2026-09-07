import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Button, CampaignJourney, StatusChip } from '@/components/ui'
import type { Campaign, CampaignWorkflow } from '@/types'

interface CampaignContextHeaderProps {
  campaign: Campaign
  workflow?: CampaignWorkflow | null
  currentStageName: string
  currentTab?: string
}

export function CampaignContextHeader({
  campaign,
  workflow,
  currentStageName,
  currentTab,
}: CampaignContextHeaderProps) {
  const returnTab = currentTab || 'overview'

  return (
    <div className="rounded-[16px] border border-border bg-surface/90 p-4 space-y-3 shadow-sm mb-4">
      {/* Breadcrumb & Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 border-b border-border/60 pb-3">
        <div className="flex items-center gap-2 text-xs text-text-secondary flex-wrap">
          <Link
            to="/app/campaigns"
            className="hover:text-primary transition font-medium"
          >
            Campaigns
          </Link>
          <span aria-hidden>/</span>
          <Link
            to={`/app/campaigns/${campaign.id}?tab=${returnTab}`}
            className="font-semibold text-text hover:text-primary transition truncate max-w-[220px]"
            title={campaign.name}
          >
            {campaign.name}
          </Link>
          <span aria-hidden>/</span>
          <span className="font-semibold text-primary">{currentStageName}</span>
          <StatusChip status={campaign.status} />
        </div>

        <Link to={`/app/campaigns/${campaign.id}?tab=${returnTab}`}>
          <Button size="sm" variant="secondary" className="h-7 text-xs gap-1.5">
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Campaign Workspace
          </Button>
        </Link>
      </div>

      {/* Campaign Journey Progress */}
      {workflow && workflow.steps && (
        <div>
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <p className="text-[10px] font-bold uppercase tracking-wider text-text-secondary">
              Campaign Lifecycle Journey
            </p>
            <p className="text-[11px] text-text-secondary tabular-nums">
              {workflow.progress_percentage}% complete
            </p>
          </div>
          <CampaignJourney steps={workflow.steps} compact />
        </div>
      )}
    </div>
  )
}
