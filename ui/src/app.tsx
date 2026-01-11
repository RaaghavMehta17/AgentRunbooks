import React, { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useStore } from './store/useStore'
import { AppLayout } from './components/layout/AppLayout'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { RunbooksPage } from './pages/RunbooksPage'
import { RunbookDetailPage } from './pages/RunbookDetailPage'
import { RunsPage } from './pages/RunsPage'
import { RunDetailPage } from './pages/RunDetailPage'
import { PoliciesPage } from './pages/PoliciesPage'
import { PolicyDetailPage } from './pages/PolicyDetailPage'
import { ApprovalsPage } from './pages/ApprovalsPage'
import { EvaluationsPage } from './pages/EvaluationsPage'
import { EvaluationDetailPage } from './pages/EvaluationDetailPage'
import { IntegrationsPage } from './pages/IntegrationsPage'
import { ProjectsPage } from './pages/ProjectsPage'
import { TenantsPage } from './pages/TenantsPage'
import { RunbookCreatePage } from './pages/RunbookCreatePage'
import { ObservabilityPage } from './pages/ObservabilityPage'
import { AuditPage } from './pages/AuditPage'
import { SettingsPage } from './pages/SettingsPage'
import { DataManagementPage } from './pages/DataManagementPage'
import { HelpPage } from './pages/HelpPage'
import { StatusPage } from './pages/StatusPage'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = useStore((state) => state.token)

  if (!token) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

export default function App() {
  const theme = useStore((state) => state.theme)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [theme])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <PrivateRoute>
              <AppLayout />
            </PrivateRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="runbooks" element={<RunbooksPage />} />
          <Route path="runbooks/:id" element={<RunbookDetailPage />} />
          <Route path="runs" element={<RunsPage />} />
          <Route path="runs/:id" element={<RunDetailPage />} />
          <Route path="policies" element={<PoliciesPage />} />
          <Route path="policies/:id" element={<PolicyDetailPage />} />
          <Route path="approvals" element={<ApprovalsPage />} />
          <Route path="evaluations" element={<EvaluationsPage />} />
          <Route path="evaluations/:id" element={<EvaluationDetailPage />} />
          <Route path="integrations" element={<IntegrationsPage />} />
          <Route path="projects" element={<ProjectsPage />} />
          <Route path="tenants" element={<TenantsPage />} />
          <Route path="runbooks/new" element={<RunbookCreatePage />} />
          <Route path="observability" element={<ObservabilityPage />} />
          <Route path="audit" element={<AuditPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="data" element={<DataManagementPage />} />
          <Route path="help" element={<HelpPage />} />
          <Route path="status" element={<StatusPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
