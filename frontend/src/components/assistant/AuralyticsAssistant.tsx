import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Loader2, Paperclip, Send, Sparkles, X } from 'lucide-react'
import { Button } from '@/components/ui'
import { api } from '@/services/api'
import { cn } from '@/utils'
import type { AssistantCampaignCandidate, AssistantChatAction, AssistantImportPreview } from '@/types'

const ACCEPT = '.csv,.xlsx,.xls,.json,.pdf,.docx'

type ChatMessage = { role: 'user' | 'assistant'; content: string }

function campaignIdFromPath(pathname: string): string | undefined {
  const match = pathname.match(/\/app\/campaigns\/(camp-[A-Za-z0-9]+)/)
  return match?.[1]
}

export function AuralyticsAssistant() {
  const location = useLocation()
  const navigate = useNavigate()
  const campaignId = campaignIdFromPath(location.pathname)
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', content: 'How can I help with your campaigns?' },
  ])
  const [actions, setActions] = useState<AssistantChatAction[]>([])
  const [preview, setPreview] = useState<AssistantImportPreview | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    api.assistant
      .transcript()
      .then((data) => {
        if (data.messages?.length) {
          setMessages(data.messages as ChatMessage[])
        }
      })
      .catch(() => undefined)
  }, [open])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, preview, open])

  const send = async (text: string) => {
    const message = text.trim()
    if (!message || busy) return
    setInput('')
    setError(null)
    setMessages((prev) => [...prev, { role: 'user', content: message }])
    setBusy(true)
    try {
      const res = await api.assistant.chat({
        message,
        campaign_id: campaignId,
        import_id: preview?.import_id,
      })
      setMessages((prev) => [...prev, { role: 'assistant', content: res.reply }])
      setActions(res.actions || [])
      if (res.preview) setPreview(res.preview)
    } catch (err: any) {
      setError(err.message || 'The assistant could not reply.')
    } finally {
      setBusy(false)
    }
  }

  const upload = async (files: FileList | null) => {
    if (!files?.length) return
    setBusy(true)
    setError(null)
    setMessages((prev) => [...prev, { role: 'user', content: `Uploading ${files.length} file(s)…` }])
    try {
      const next = await api.assistant.upload(Array.from(files))
      setPreview(next)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Found ${next.detected_campaigns} campaign(s): ${next.completed_campaigns} completed, ${next.in_progress_campaigns} in progress, ${next.needs_review} needing review. Confirm before anything is saved.`,
        },
      ])
    } catch (err: any) {
      setError(err.message || 'File import failed.')
    } finally {
      setBusy(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const confirm = async () => {
    if (!preview) return
    setBusy(true)
    setError(null)
    try {
      const result = await api.assistant.confirmImport(preview.import_id)
      setPreview(result.preview)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Your campaign history has been imported. Completed: ${result.preview.completed_campaigns}. In progress: ${result.preview.in_progress_campaigns}. Needs review: ${result.preview.needs_review}.`,
        },
      ])
    } catch (err: any) {
      setError(err.message || 'Import could not be confirmed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <button
        type="button"
        className={cn(
          'fixed z-40 right-4 lg:right-6 bottom-20 lg:bottom-6 h-12 w-12 rounded-full',
          'ai-gradient-bg text-white shadow-[0_8px_24px_rgba(91,95,239,0.35)]',
          'hover:-translate-y-0.5 transition-transform duration-200',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40',
          'motion-reduce:transform-none motion-reduce:transition-none',
        )}
        aria-label="Ask Auralytics"
        title="Ask Auralytics"
        onClick={() => setOpen(true)}
      >
        <Sparkles className="h-5 w-5 mx-auto" />
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex justify-end items-end lg:items-stretch">
          <button className="absolute inset-0 bg-slate-900/25 lg:bg-slate-900/20" aria-label="Close assistant" onClick={() => setOpen(false)} />
          <aside
            className={cn(
              'relative w-full lg:w-[400px] max-h-[85vh] lg:max-h-none lg:h-full bg-surface border border-border lg:border-l',
              'rounded-t-2xl lg:rounded-none shadow-[-12px_0_40px_rgba(15,23,42,0.12)] flex flex-col animate-slide-in-right',
            )}
            role="dialog"
            aria-label="Auralytics Assistant"
          >
            <header className="px-4 py-3 border-b border-border/80 flex items-start justify-between gap-3 bg-gradient-to-r from-surface to-primary-soft/30">
              <div>
                <p className="text-sm font-semibold text-text">Auralytics Assistant</p>
                <p className="text-[11px] text-text-secondary">Campaign knowledge & workspace assistant</p>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setOpen(false)} aria-label="Close">
                <X className="h-4 w-4" />
              </Button>
            </header>

            <div className="px-4 py-3 border-b border-border/70">
              <p className="text-xs text-text-secondary">Import campaign history or ask questions about your workspace.</p>
              <input ref={fileRef} type="file" accept={ACCEPT} multiple className="hidden" onChange={(e) => upload(e.target.files)} />
              <Button type="button" variant="secondary" size="sm" className="mt-2" onClick={() => fileRef.current?.click()} disabled={busy}>
                <Paperclip className="h-3.5 w-3.5" /> Add Campaign Files
              </Button>
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
              {messages.map((msg, i) => (
                <div
                  key={`${msg.role}-${i}`}
                  className={cn(
                    'max-w-[92%] rounded-2xl px-3 py-2 text-sm leading-relaxed animate-fade-in',
                    msg.role === 'assistant' ? 'bg-muted/70 text-text' : 'ml-auto bg-primary-soft text-text',
                  )}
                >
                  {msg.content}
                </div>
              ))}

              {preview && <ImportPreviewCard preview={preview} busy={busy} onConfirm={confirm} onClassify={setPreview} navigate={navigate} />}

              {actions.map((action) => (
                <button
                  key={`${action.label}-${action.href}`}
                  type="button"
                  className="block w-full text-left rounded-xl border border-border px-3 py-2 text-xs font-semibold text-primary hover:bg-muted/60"
                  onClick={() => action.href && navigate(action.href)}
                >
                  {action.label}
                </button>
              ))}

              {error && <p className="text-xs text-danger">{error}</p>}
              <div ref={endRef} />
            </div>

            <form
              className="p-3 border-t border-border flex gap-2"
              onSubmit={(e) => {
                e.preventDefault()
                void send(input)
              }}
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about campaigns..."
                className="flex-1 h-10 px-3 rounded-[10px] border border-border bg-elevated text-sm text-text placeholder:text-text-secondary/70 focus:outline-none focus:ring-2 focus:ring-primary/30"
                disabled={busy}
              />
              <Button type="submit" size="icon" disabled={busy || !input.trim()} aria-label="Send">
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </form>
          </aside>
        </div>
      )}
    </>
  )
}

function ImportPreviewCard({
  preview,
  busy,
  onConfirm,
  onClassify,
  navigate,
}: {
  preview: AssistantImportPreview
  busy: boolean
  onConfirm: () => void
  onClassify: (preview: AssistantImportPreview) => void
  navigate: (to: string) => void
}) {
  const confirmed = preview.status === 'CONFIRMED'
  const inProgress = useMemo(
    () => preview.campaigns.filter((c) => c.classification === 'IN_PROGRESS' && c.continue_route),
    [preview.campaigns],
  )

  return (
    <div className="rounded-2xl border border-border bg-page/50 p-3 space-y-2">
      <p className="text-xs font-semibold text-text">Import preview</p>
      <p className="text-[11px] text-text-secondary">
        {preview.detected_campaigns} campaigns · {preview.completed_campaigns} completed · {preview.in_progress_campaigns} in progress ·{' '}
        {preview.needs_review} need review
      </p>
      <div className="max-h-48 overflow-y-auto space-y-2">
        {preview.campaigns.map((campaign) => (
          <CandidateRow
            key={campaign.key}
            campaign={campaign}
            importId={preview.import_id}
            confirmed={confirmed}
            onUpdate={onClassify}
            navigate={navigate}
          />
        ))}
      </div>
      {!confirmed && (
        <Button size="sm" className="w-full" onClick={onConfirm} disabled={busy}>
          Import
        </Button>
      )}
      {confirmed && inProgress[0]?.continue_route && (
        <Button size="sm" variant="secondary" className="w-full" onClick={() => navigate(inProgress[0].continue_route!)}>
          Review in-progress campaigns
        </Button>
      )}
    </div>
  )
}

function CandidateRow({
  campaign,
  importId,
  confirmed,
  onUpdate,
  navigate,
}: {
  campaign: AssistantCampaignCandidate
  importId: string
  confirmed: boolean
  onUpdate: (preview: AssistantImportPreview) => void
  navigate: (to: string) => void
}) {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded-xl border border-border/80 bg-surface px-2.5 py-2">
      <button type="button" className="w-full text-left" onClick={() => setOpen((v) => !v)}>
        <p className="text-xs font-semibold text-text truncate">{campaign.campaign_name || 'Untitled campaign'}</p>
        <p className="text-[10px] text-text-secondary">
          {campaign.classification} · {campaign.current_stage || '—'} · {campaign.creators.length} creator(s)
        </p>
      </button>
      {open && (
        <div className="mt-2 space-y-1.5">
          {campaign.warnings.map((warning) => (
            <p key={warning} className="text-[10px] text-warning">
              {warning}
            </p>
          ))}
          {campaign.duplicate && (
            <p className="text-[10px] text-text-secondary">Possible existing campaign: {campaign.duplicate.campaign_name}</p>
          )}
          {campaign.conflicts.map((conflict) => (
            <div key={`${conflict.entity}-${conflict.field}`} className="space-y-1">
              <p className="text-[10px] font-medium text-text">
                {conflict.entity} {conflict.field}
              </p>
              <div className="flex flex-wrap gap-1">
                {conflict.values.map((value, i) => (
                  <button
                    key={i}
                    type="button"
                    className="text-[10px] px-2 py-1 rounded-lg border border-border hover:border-primary/40"
                    onClick={async () => {
                      const next = await api.assistant.resolveConflict(importId, {
                        campaign_key: campaign.key,
                        entity: conflict.entity,
                        field: conflict.field,
                        chosen_value: value.value,
                      })
                      onUpdate(next)
                    }}
                  >
                    Use {String(value.value)}
                  </button>
                ))}
              </div>
            </div>
          ))}
          {campaign.classification === 'NEEDS_REVIEW' && !confirmed && (
            <div className="flex flex-wrap gap-1">
              {['COMPLETED', 'IN_PROGRESS'].map((label) => (
                <button
                  key={label}
                  type="button"
                  className="text-[10px] px-2 py-1 rounded-lg border border-border"
                  onClick={async () => {
                    const next = await api.assistant.classify(importId, {
                      campaign_key: campaign.key,
                      classification: label,
                    })
                    onUpdate(next)
                  }}
                >
                  {label === 'COMPLETED' ? 'Completed' : 'Still Active'}
                </button>
              ))}
            </div>
          )}
          {confirmed && campaign.classification === 'COMPLETED' && campaign.continue_route && (
            <button type="button" className="text-[11px] font-semibold text-primary" onClick={() => navigate(campaign.continue_route!)}>
              View Campaign
            </button>
          )}
          {confirmed && campaign.classification !== 'COMPLETED' && campaign.continue_route && (
            <button type="button" className="text-[11px] font-semibold text-primary" onClick={() => navigate(campaign.continue_route!)}>
              Continue Campaign
            </button>
          )}
        </div>
      )}
    </div>
  )
}
