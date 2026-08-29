import type { CampaignCreator } from '@/types'

/** Prefer Groq-ranked creators when classification ran. YouTube-only results stay visible. */
export function recommendedCampaignCreators(creators: CampaignCreator[]): CampaignCreator[] {
  const recommended = creators.filter((entry) => {
    const ai = entry.match_reasons?.find((reason) => reason.key === 'ai_discovery')
    if (!ai) return false
    return String(ai.eligibility || 'ELIGIBLE').toUpperCase() !== 'NOT_ELIGIBLE'
  })
  if (recommended.length === 0) return creators

  const shownIds = new Set(recommended.map((entry) => entry.link_id))
  const shortlisted = creators.filter(
    (entry) => entry.status === 'SHORTLISTED' && !shownIds.has(entry.link_id),
  )
  return [...recommended, ...shortlisted]
}
