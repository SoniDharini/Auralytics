export const CAMPAIGN_TYPE_OPTIONS = [
  'Product Launch',
  'Awareness',
  'Conversions',
  'UGC',
  'Always-on',
  'Seasonal',
] as const

export const OTHER_CAMPAIGN_TYPE = 'Other'

export const ALL_CAMPAIGN_TYPE_OPTIONS = [...CAMPAIGN_TYPE_OPTIONS, OTHER_CAMPAIGN_TYPE]

export const AGE_ABSOLUTE_MIN = 1
export const AGE_ABSOLUTE_MAX = 120
export const AGE_DROPDOWN_MIN = 13
export const AGE_DROPDOWN_MAX = 80

export const AGE_DROPDOWN_OPTIONS = Array.from(
  { length: AGE_DROPDOWN_MAX - AGE_DROPDOWN_MIN + 1 },
  (_, i) => AGE_DROPDOWN_MIN + i,
)

const PREDEFINED = new Set<string>(CAMPAIGN_TYPE_OPTIONS)

export function parseIntegerAge(value: string | number | null | undefined): number | null {
  if (value === '' || value == null) return null
  const n = typeof value === 'number' ? value : Number(String(value).trim())
  if (!Number.isFinite(n)) return null
  const rounded = Math.round(n)
  if (rounded < AGE_ABSOLUTE_MIN || rounded > AGE_ABSOLUTE_MAX) return null
  return rounded
}

export function ageRangeError(min: number | null, max: number | null): string | null {
  if (min == null || max == null) return 'Enter a valid minimum and maximum age.'
  if (min > max) return 'Maximum age must be greater than or equal to minimum age.'
  return null
}

export function splitCampaignTypes(types: string[] | undefined | null): {
  selected: string[]
  customType: string
  otherSelected: boolean
} {
  const incoming = types || []
  const predefined = incoming.filter((t) => PREDEFINED.has(t))
  const custom = incoming.filter((t) => t !== OTHER_CAMPAIGN_TYPE && !PREDEFINED.has(t))
  const otherSelected = custom.length > 0 || incoming.includes(OTHER_CAMPAIGN_TYPE)
  return {
    selected: otherSelected ? [...predefined, OTHER_CAMPAIGN_TYPE] : predefined,
    customType: custom[0] || '',
    otherSelected,
  }
}

export function assembleCampaignTypes(selected: string[], customType: string): string[] {
  const types = selected.filter((t) => PREDEFINED.has(t))
  if (selected.includes(OTHER_CAMPAIGN_TYPE)) {
    const custom = customType.trim()
    if (custom) types.push(custom)
  }
  return types
}
