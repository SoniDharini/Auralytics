import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, MapPin, Sparkles } from 'lucide-react'
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from 'recharts'
import { influencers } from '@/mock-data'
import {
  Avatar,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  ProgressBar,
  ProgressRing,
} from '@/components/ui'
import { PlatformIcon } from '@/components/ui/PlatformIcon'
import { cn, formatINR, formatNumber } from '@/utils'

const historicalCampaigns = [
  {
    campaign: 'GlowNaturals Vitamin C Launch',
    brand: 'GlowNaturals',
    spend: 18000,
    revenue: 64800,
    roas: 3.6,
    conversions: 124,
  },
  {
    campaign: 'Clean Beauty Awareness Q2',
    brand: 'GlowNaturals',
    spend: 22000,
    revenue: 57200,
    roas: 2.6,
    conversions: 98,
  },
  {
    campaign: 'Summer Skincare Routine',
    brand: 'DermaCo',
    spend: 15000,
    revenue: 42000,
    roas: 2.8,
    conversions: 76,
  },
]

export function InfluencerDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [shortlisted, setShortlisted] = useState(false)

  const influencer = useMemo(() => {
    const found = influencers.find((i) => i.id === id)
    return found ?? influencers[0]
  }, [id])

  const scores = [
    { label: 'Overall Match', value: influencer.aiMatchScore, color: '#5B5FEF' },
    { label: 'Audience Match', value: influencer.audienceFit, color: '#7C3AED' },
    { label: 'Niche Match', value: influencer.nicheMatch, color: '#8B5CF6' },
    { label: 'Budget Fit', value: influencer.budgetFit, color: '#6366F1' },
    { label: 'Authenticity', value: influencer.authenticity, color: '#16A34A' },
    { label: 'Brand Safety', value: influencer.brandSafety, color: '#0EA5E9' },
  ]

  const radarData = scores.map((s) => ({ metric: s.label.replace(' Match', '').replace(' Fit', ''), score: s.value }))

  return (
    <div className="space-y-6 animate-fade-in">
      <Link
        to="/app/discovery"
        className="inline-flex items-center gap-1.5 text-sm font-semibold text-text-secondary hover:text-primary transition"
      >
        <ArrowLeft className="h-4 w-4" /> Back to Discovery
      </Link>

      <Card>
        <CardContent className="pt-5">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-5">
            <div className="flex items-start gap-4">
              <Avatar name={influencer.name} size="xl" />
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h1 className="text-2xl font-bold">{influencer.name}</h1>
                  {influencer.verified && (
                    <CheckCircle2 className="h-5 w-5 text-primary" aria-label="Verified" />
                  )}
                </div>
                <p className="text-text-secondary mt-0.5">@{influencer.username}</p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <span className="inline-flex items-center gap-1.5 rounded-md bg-muted px-2 py-1 text-xs font-semibold capitalize">
                    <PlatformIcon platform={influencer.platform} />
                    {influencer.platform}
                  </span>
                  <span className="inline-flex items-center gap-1 text-xs text-text-secondary">
                    <MapPin className="h-3.5 w-3.5" />
                    {influencer.location}
                  </span>
                  {influencer.niches.map((n) => (
                    <Badge key={n} variant="outline">
                      {n}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
            <Button
              size="lg"
              variant={shortlisted || influencer.shortlisted ? 'soft' : 'primary'}
              onClick={() => setShortlisted((v) => !v)}
              className="shrink-0"
            >
              {shortlisted || influencer.shortlisted ? 'Added to Shortlist' : 'Add to Shortlist'}
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
        {[
          { label: 'Followers', value: formatNumber(influencer.followers) },
          { label: 'Engagement', value: `${influencer.engagementRate}%` },
          { label: 'Avg Views', value: formatNumber(influencer.avgViews) },
          { label: 'Avg Likes', value: formatNumber(influencer.avgLikes) },
          { label: 'Avg Comments', value: formatNumber(influencer.avgComments) },
          { label: 'Est. Cost', value: formatINR(influencer.estimatedCost, true) },
        ].map((m) => (
          <Card key={m.label} className="p-4">
            <p className="text-xs text-text-secondary">{m.label}</p>
            <p className="text-xl font-bold mt-1">{m.value}</p>
          </Card>
        ))}
      </div>

      <div className="grid xl:grid-cols-[1.2fr_1fr] gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-ai" /> AI Evaluation
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {scores.map((s) => (
                <div key={s.label} className="flex items-center gap-3">
                  <ProgressRing value={s.value} size={52} stroke={4} color={s.color} />
                  <div>
                    <p className="text-xs text-text-secondary">{s.label}</p>
                    <p className="text-sm font-semibold">{s.value}%</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="h-[260px]">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="70%">
                  <PolarGrid stroke="#E5E7EB" />
                  <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11, fill: '#6B7280' }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 10, fill: '#9CA3AF' }} />
                  <Radar
                    name="Score"
                    dataKey="score"
                    stroke="#5B5FEF"
                    fill="#5B5FEF"
                    fillOpacity={0.2}
                    strokeWidth={2}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <CardTitle>Why AI recommends this creator</CardTitle>
              <Badge variant="ai">AI Generated</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-text leading-relaxed">{influencer.whyRecommended}</p>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <div className="rounded-[10px] bg-primary-soft p-3">
                <p className="text-xs text-text-secondary">Predicted ROAS</p>
                <p className="text-lg font-bold text-primary">{influencer.predictedRoas}x</p>
              </div>
              <div className="rounded-[10px] bg-violet-50 p-3">
                <p className="text-xs text-text-secondary">AI Match Score</p>
                <p className="text-lg font-bold text-ai">{influencer.aiMatchScore}%</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Audience Analytics</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <p className="text-sm font-semibold mb-3">Gender Distribution</p>
            <div className="space-y-2">
              {[
                { label: 'Female', value: influencer.audienceGender.female, color: 'bg-primary' },
                { label: 'Male', value: influencer.audienceGender.male, color: 'bg-accent' },
                { label: 'Other', value: influencer.audienceGender.other, color: 'bg-muted' },
              ].map((g) => (
                <div key={g.label} className="flex items-center gap-3">
                  <span className="text-xs w-12 text-text-secondary">{g.label}</span>
                  <div className="flex-1">
                    <ProgressBar value={g.value} barClassName={cn(g.color)} size="sm" />
                  </div>
                  <span className="text-xs font-semibold w-8">{g.value}%</span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <p className="text-sm font-semibold mb-3">Age Distribution</p>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {influencer.audienceAge.map((a) => (
                <div key={a.range} className="rounded-[10px] border border-border p-3">
                  <p className="text-xs text-text-secondary">{a.range}</p>
                  <p className="text-lg font-bold">{a.percent}%</p>
                  <ProgressBar value={a.percent} size="sm" className="mt-2" />
                </div>
              ))}
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-4">
            <div>
              <p className="text-sm font-semibold mb-2">Top Countries</p>
              <ul className="space-y-2">
                {influencer.topCountries.map((c) => (
                  <li key={c.country} className="flex justify-between text-sm">
                    <span>{c.country}</span>
                    <span className="font-semibold">{c.percent}%</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-sm font-semibold mb-2">Top Cities</p>
              <div className="flex flex-wrap gap-1.5">
                {influencer.topCities.map((city) => (
                  <Badge key={city} variant="outline">
                    {city}
                  </Badge>
                ))}
              </div>
            </div>
            <div>
              <p className="text-sm font-semibold mb-2">Interests</p>
              <div className="flex flex-wrap gap-1.5">
                {influencer.interests.map((interest) => (
                  <Badge key={interest} variant="primary">
                    {interest}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Historical Campaign Results</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-text-secondary border-b border-border">
                <th className="pb-3 font-semibold">Campaign</th>
                <th className="pb-3 font-semibold">Brand</th>
                <th className="pb-3 font-semibold">Spend</th>
                <th className="pb-3 font-semibold">Revenue</th>
                <th className="pb-3 font-semibold">ROAS</th>
                <th className="pb-3 font-semibold">Conversions</th>
              </tr>
            </thead>
            <tbody>
              {historicalCampaigns.map((row) => (
                <tr key={row.campaign} className="border-b border-border last:border-0">
                  <td className="py-3.5 pr-3 font-semibold">{row.campaign}</td>
                  <td className="py-3.5 pr-3 text-text-secondary">{row.brand}</td>
                  <td className="py-3.5 pr-3">{formatINR(row.spend, true)}</td>
                  <td className="py-3.5 pr-3">{formatINR(row.revenue, true)}</td>
                  <td className="py-3.5 pr-3 font-semibold text-primary">{row.roas}x</td>
                  <td className="py-3.5">{row.conversions}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  )
}
