import { useState, type FormEvent } from 'react'
import { AlertTriangle, CheckCircle2, ExternalLink, Loader2, Search } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '@/services/api'
import { Avatar, Badge, Button, Card, Modal, useToast } from '@/components/ui'
import { cn, formatNumber } from '@/utils'
import type { CampaignCreator, ManualSearchResult } from '@/types'

const NOT_AVAILABLE = 'N/A'

interface ManualCreatorSearchProps {
  campaignId: string
  disabled?: boolean
  onShortlisted: (entry: CampaignCreator) => void
}

function matchLabel(value?: string) {
  if (value === 'MATCH') return '✓'
  if (value === 'FAIL') return '✕'
  if (value === 'PARTIAL') return '⚠'
  return ''
}

export function ManualCreatorSearch({ campaignId, disabled, onShortlisted }: ManualCreatorSearchProps) {
  const { toast } = useToast()
  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [results, setResults] = useState<ManualSearchResult[]>([])
  const [pendingId, setPendingId] = useState<string | null>(null)
  const [overrideTarget, setOverrideTarget] = useState<ManualSearchResult | null>(null)

  const runSearch = async () => {
    const q = query.trim()
    if (!campaignId || searching || disabled || !q) return
    setSearching(true)
    setError(null)
    setMessage(null)
    try {
      const res = await api.discovery.searchCreator(campaignId, q)
      setResults(res.results || [])
      setMessage(res.message || (res.count === 0 ? 'No YouTube creator was found for this search.' : null))
    } catch (err: any) {
      setResults([])
      const status = err?.status
      if (status === 429) {
        setError(err.message || 'The daily YouTube Data API quota has been exhausted.')
      } else if (status === 503) {
        setError(err.message || 'YouTube API is not configured.')
      } else {
        setError(err?.message || 'Search failed. No fake creators were generated.')
      }
    } finally {
      setSearching(false)
    }
  }

  const shortlist = async (item: ManualSearchResult, confirmOverride = false) => {
    if (!item.channel_id || pendingId) return
    setPendingId(item.channel_id)
    try {
      const saved = await api.discovery.shortlistManual(campaignId, {
        channel_id: item.channel_id,
        confirm_override: confirmOverride,
        query: item.query || query,
      })
      setResults((prev) =>
        prev.map((row) =>
          row.channel_id === item.channel_id
            ? {
                ...row,
                already_shortlisted: true,
                already_in_campaign: true,
                shortlist_allowed: false,
                campaign_status: 'SHORTLISTED',
                influencer_id: saved.creator.id,
                link_id: saved.link_id,
              }
            : row,
        ),
      )
      onShortlisted(saved)
      toast({
        type: 'success',
        title: 'Shortlisted',
        description: `${saved.creator.name} was added using the existing shortlist workflow.`,
      })
      setOverrideTarget(null)
    } catch (err: any) {
      if (err?.status === 409) {
        setOverrideTarget(item)
      } else {
        toast({
          type: 'error',
          title: 'Could not shortlist',
          description: err?.message || 'The creator was not added to the shortlist.',
        })
      }
    } finally {
      setPendingId(null)
    }
  }

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    void runSearch()
  }

  return (
    <div className="space-y-3">
      <Card className="relative overflow-hidden p-4 border-primary/15">
        <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-primary via-accent to-transparent" />
        <div className="absolute -right-8 -top-8 h-24 w-24 rounded-full bg-primary/10 blur-2xl pointer-events-none" />
        <p className="relative text-sm font-semibold text-text">Have a creator in mind?</p>
        <p className="relative text-xs text-text-secondary mt-0.5">
          Search a real YouTube creator by name, @handle, or channel URL. This does not replace AI recommendations.
        </p>
        <form className="relative mt-3 flex flex-col sm:flex-row gap-2" onSubmit={onSubmit}>
          <div className="relative flex-1">
            <Search className="h-4 w-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-primary/70" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search creator name, @handle or YouTube channel URL..."
              className="w-full h-10 pl-10 pr-4 rounded-[12px] border border-border bg-surface text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/10 text-text transition"
              aria-label="Search YouTube creator"
              disabled={searching || disabled}
            />
          </div>
          <Button type="submit" disabled={searching || disabled || !query.trim()} className="gap-2 shrink-0">
            {searching ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Searching YouTube...
              </>
            ) : (
              <>
                <Search className="h-4 w-4" />
                Search
              </>
            )}
          </Button>
        </form>
      </Card>

      {error && (
        <Card className="p-4 flex items-start gap-3 border-danger/30 bg-danger/5">
          <AlertTriangle className="h-5 w-5 text-danger shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-text">Search failed</p>
            <p className="text-xs text-text-secondary mt-0.5">{error}</p>
          </div>
        </Card>
      )}

      {message && !error && results.length === 0 && !searching && (
        <p className="text-sm text-text-secondary px-1">{message}</p>
      )}

      {results.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <h2 className="text-sm font-semibold text-text">Search results</h2>
            <span className="text-xs text-text-secondary">YouTube Data API · choose the correct channel</span>
          </div>
          <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {results.map((item) => {
              const creator = item.creator
              const pending = pendingId === item.channel_id
              const req = item.requirement_match || {}
              return (
                <Card key={item.channel_id} className="p-4 flex flex-col gap-3">
                  <div className="flex items-start gap-3">
                    <Avatar name={creator.name} src={creator.avatar} size="lg" className="border border-border" />
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-text truncate">{creator.name}</p>
                      <p className="text-xs text-text-secondary truncate">{creator.username}</p>
                      <div className="mt-1.5 flex flex-wrap gap-1.5">
                        <Badge variant="outline">{(item.entity_type || 'UNKNOWN').replace(/_/g, ' ')}</Badge>
                        {item.tier && item.tier !== 'UNKNOWN' && (
                          <Badge variant="outline">{item.tier.replace(/_/g, ' ')}</Badge>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-y-2 text-xs">
                    <div>
                      <p className="text-text-secondary">Subscribers</p>
                      <p className="font-semibold">{creator.followers ? formatNumber(creator.followers) : NOT_AVAILABLE}</p>
                    </div>
                    <div>
                      <p className="text-text-secondary">Recent avg views</p>
                      <p className="font-semibold">
                        {item.recent_avg_views ? formatNumber(item.recent_avg_views) : (creator.avgViews ? formatNumber(creator.avgViews) : NOT_AVAILABLE)}
                      </p>
                    </div>
                    <div>
                      <p className="text-text-secondary">Location</p>
                      <p className="font-semibold">{creator.country || creator.location || NOT_AVAILABLE}</p>
                    </div>
                    <div>
                      <p className="text-text-secondary">Campaign fit</p>
                      <p className="font-semibold">
                        {typeof item.match_score === 'number' ? `${Math.round(item.match_score)}%` : NOT_AVAILABLE}
                      </p>
                    </div>
                  </div>

                  <div className="text-[11px] text-text-secondary space-y-0.5">
                    {req.location && <p>Location {matchLabel(req.location)} {req.location}</p>}
                    {req.creator_tier && <p>Creator tier {matchLabel(req.creator_tier)} {req.creator_tier}</p>}
                    {req.subscriber_range && <p>Follower range {matchLabel(req.subscriber_range)} {req.subscriber_range}</p>}
                    {req.view_requirement && req.view_requirement !== 'UNKNOWN' && (
                      <p>View requirement {matchLabel(req.view_requirement)} {req.view_requirement}</p>
                    )}
                    {item.persona_relevance?.target && item.persona_relevance.target !== 'UNKNOWN' && (
                      <p>
                        Persona {item.persona_relevance.target.replace(/_/g, ' ')}
                        {item.persona_relevance.level ? ` · ${item.persona_relevance.level}` : ''}
                        {item.persona_relevance.source && item.persona_relevance.source !== 'UNKNOWN'
                          ? ` · ${item.persona_relevance.source.replace(/_/g, '-')}`
                          : ''}
                      </p>
                    )}
                  </div>

                  {item.meets_requirements && (
                    <p className="text-xs font-medium text-success flex items-center gap-1">
                      <CheckCircle2 className="h-3.5 w-3.5" /> Meets campaign requirements
                    </p>
                  )}
                  {item.already_shortlisted && (
                    <p className="text-xs font-medium text-primary">✓ Already shortlisted</p>
                  )}
                  {item.already_recommended && !item.already_shortlisted && (
                    <p className="text-xs text-text-secondary">Already recommended for this campaign</p>
                  )}
                  {item.previously_rejected && (
                    <p className="text-xs text-warning">Previously rejected</p>
                  )}
                  {item.warning && !item.already_shortlisted && (
                    <p className={cn('text-xs', item.shortlist_allowed ? 'text-warning' : 'text-danger')}>
                      {item.warning}
                    </p>
                  )}
                  {item.mismatches.length > 0 && (
                    <ul className="text-[11px] text-text-secondary list-disc pl-4 space-y-0.5">
                      {item.mismatches.map((mismatch) => (
                        <li key={`${item.channel_id}-${mismatch.code}`}>{mismatch.detail}</li>
                      ))}
                    </ul>
                  )}

                  <div className="mt-auto flex gap-2">
                    {creator.id ? (
                      <Link to={`/app/discovery/${creator.id}?campaign=${campaignId}`} className="flex-1">
                        <Button variant="secondary" size="sm" className="w-full">
                          View Profile
                        </Button>
                      </Link>
                    ) : creator.profile_url ? (
                      <a href={creator.profile_url} target="_blank" rel="noopener noreferrer" className="flex-1">
                        <Button variant="secondary" size="sm" className="w-full gap-1">
                          Open Channel <ExternalLink className="h-3 w-3" />
                        </Button>
                      </a>
                    ) : null}
                    <Button
                      size="sm"
                      className="flex-1"
                      variant={item.already_shortlisted ? 'soft' : item.manual_override_required ? 'secondary' : 'primary'}
                      disabled={pending || item.already_shortlisted || !item.shortlist_allowed}
                      onClick={() => {
                        if (item.manual_override_required) {
                          setOverrideTarget(item)
                          return
                        }
                        void shortlist(item, false)
                      }}
                    >
                      {pending
                        ? 'Shortlisting...'
                        : item.already_shortlisted
                          ? 'Already Shortlisted'
                          : item.previously_rejected
                            ? 'Reconsider'
                            : item.manual_override_required
                              ? 'Shortlist Anyway'
                              : 'Shortlist'}
                    </Button>
                  </div>
                </Card>
              )
            })}
          </div>
        </div>
      )}

      <Modal
        open={!!overrideTarget}
        onClose={() => setOverrideTarget(null)}
        title="Shortlist this creator anyway?"
        footer={
          <>
            <Button variant="secondary" onClick={() => setOverrideTarget(null)}>
              Cancel
            </Button>
            <Button
              disabled={!!pendingId}
              onClick={() => overrideTarget && void shortlist(overrideTarget, true)}
            >
              {pendingId ? 'Shortlisting...' : 'Confirm manual shortlist'}
            </Button>
          </>
        }
      >
        <p className="text-sm text-text-secondary">
          This creator does not match one or more current Discovery requirements. Your campaign settings will not be
          changed.
        </p>
        {overrideTarget && (
          <ul className="mt-3 text-sm space-y-1.5">
            {overrideTarget.mismatches.map((mismatch) => (
              <li key={mismatch.code}>
                <span className="font-semibold">{mismatch.label}:</span> {mismatch.detail}
              </li>
            ))}
          </ul>
        )}
      </Modal>
    </div>
  )
}
