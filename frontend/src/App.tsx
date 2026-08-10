import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ToastProvider } from '@/components/ui'
import { AppLayout } from '@/layouts/AppLayout'
import { LandingPage } from '@/pages/LandingPage'
import { LoginPage } from '@/pages/LoginPage'
import { SignUpPage } from '@/pages/SignUpPage'
import { OnboardingPage } from '@/pages/OnboardingPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { CampaignsPage } from '@/pages/CampaignsPage'
import { CreateCampaignPage } from '@/pages/CreateCampaignPage'
import { CampaignDetailPage } from '@/pages/CampaignDetailPage'
import { DiscoveryPage } from '@/pages/DiscoveryPage'
import { InfluencerDetailPage } from '@/pages/InfluencerDetailPage'
import { ShortlistPage } from '@/pages/ShortlistPage'
import { OutreachPage } from '@/pages/OutreachPage'
import { ContractsPage } from '@/pages/ContractsPage'
import { ContractDetailPage } from '@/pages/ContractDetailPage'
import { AnalyticsPage } from '@/pages/AnalyticsPage'
import { OptimizationPage } from '@/pages/OptimizationPage'
import { ApprovalsPage } from '@/pages/ApprovalsPage'
import { AgentsPage } from '@/pages/AgentsPage'
import { ReportsPage } from '@/pages/ReportsPage'
import { NotificationsPage } from '@/pages/NotificationsPage'
import { SettingsPage } from '@/pages/SettingsPage'

export default function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignUpPage />} />
          <Route path="/onboarding" element={<OnboardingPage />} />

          <Route path="/app" element={<AppLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="campaigns" element={<CampaignsPage />} />
            <Route path="campaigns/new" element={<CreateCampaignPage />} />
            <Route path="campaigns/:id" element={<CampaignDetailPage />} />
            <Route path="discovery" element={<DiscoveryPage />} />
            <Route path="discovery/:id" element={<InfluencerDetailPage />} />
            <Route path="shortlist" element={<ShortlistPage />} />
            <Route path="outreach" element={<OutreachPage />} />
            <Route path="contracts" element={<ContractsPage />} />
            <Route path="contracts/:id" element={<ContractDetailPage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="optimization" element={<OptimizationPage />} />
            <Route path="approvals" element={<ApprovalsPage />} />
            <Route path="agents" element={<AgentsPage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="notifications" element={<NotificationsPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  )
}
