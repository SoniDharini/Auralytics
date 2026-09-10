import type { CampaignCreator } from '@/types'

/** Show Groq-ranked eligible creators when classification ran. Incomplete/ineligible rows stay hidden. */
export function recommendedCampaignCreators(creators: CampaignCreator[]): CampaignCreator[] {
  const imported = creators.filter((entry) =>
    entry.creator?.data_source === 'historical_import' ||
    Boolean(entry.match_reasons?.find((reason) => reason.key === 'historical_import')),
  )
  const classified = creators.filter((entry) =>
    Boolean(entry.match_reasons?.find((reason) => reason.key === 'ai_discovery')),
  )
  const recommended = classified.filter((entry) => {
    const ai = entry.match_reasons?.find((reason) => reason.key === 'ai_discovery')
    if (!ai) return false
    const eligibility = String(ai.eligibility || 'ELIGIBLE').toUpperCase()
    return eligibility === 'ELIGIBLE'
  })
  const shownIds = new Set(recommended.map((entry) => entry.link_id))
  const shortlisted = creators.filter(
    (entry) => entry.status === 'SHORTLISTED' && !shownIds.has(entry.link_id),
  )
  if (imported.length > 0) {
    const importedIds = new Set(imported.map((entry) => entry.link_id))
    return [
      ...imported,
      ...recommended.filter((entry) => !importedIds.has(entry.link_id)),
      ...shortlisted.filter((entry) => !importedIds.has(entry.link_id)),
    ]
  }
  if (classified.length > 0) {
    return [...recommended, ...shortlisted]
  }
  return creators.filter((entry) => (entry.creator?.followers ?? 0) > 0)
}
