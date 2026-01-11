import React from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  BookOpen,
  PlayCircle,
  CheckCircle,
  Plug,
  Shield,
  BarChart3,
  Activity,
  FileText,
  Settings,
  User,
} from 'lucide-react'
import { cn } from '../../lib/utils'
import { useStore } from '../../store/useStore'
import { approvalsApi } from '../../lib/api'

const mainNav = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Runbooks', href: '/runbooks', icon: BookOpen },
  { name: 'Runs', href: '/runs', icon: PlayCircle },
  { name: 'Approvals', href: '/approvals', icon: CheckCircle },
]

const configureNav = [
  { name: 'Integrations', href: '/integrations', icon: Plug },
  { name: 'Policies', href: '/policies', icon: Shield },
  { name: 'Evaluations', href: '/evaluations', icon: BarChart3 },
]

const observeNav = [
  { name: 'Analytics', href: '/observability', icon: Activity },
  { name: 'Audit Log', href: '/audit', icon: FileText },
]

export function Sidebar() {
  const user = useStore((state) => state.user)
  const [pendingApprovals, setPendingApprovals] = React.useState(0)

  React.useEffect(() => {
    const fetchApprovals = async () => {
      try {
        const approvals = await approvalsApi.list()
        const pending = Array.isArray(approvals)
          ? approvals.filter((a: any) => !a.approved).length
          : 0
        setPendingApprovals(pending)
      } catch (error) {
        console.error('Failed to fetch approvals:', error)
      }
    }
    fetchApprovals()
    const interval = setInterval(fetchApprovals, 10000) // Poll every 10s
    return () => clearInterval(interval)
  }, [])

  const renderNavSection = (items: typeof mainNav, sectionName: string) => (
    <div className="mb-6">
      <h3 className="px-3 mb-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
        {sectionName}
      </h3>
      <div className="space-y-1">
        {items.map((item) => {
          const Icon = item.icon
          const isApprovals = item.name === 'Approvals'
          return (
            <NavLink
              key={item.name}
              to={item.href}
              className={({ isActive }) =>
                cn(
                  'flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-[#1e293b] text-white'
                    : 'text-gray-400 hover:bg-[#1e293b] hover:text-gray-200'
                )
              }
            >
              <div className="flex items-center gap-3">
                <Icon className="w-5 h-5 flex-shrink-0" />
                <span>{item.name}</span>
              </div>
              {isApprovals && pendingApprovals > 0 && (
                <span className="px-2 py-0.5 text-xs font-semibold bg-[#ef4444] text-white rounded-full">
                  {pendingApprovals}
                </span>
              )}
            </NavLink>
          )
        })}
      </div>
    </div>
  )

  return (
    <div className="flex flex-col h-screen bg-[#0f172a] border-r border-[#1e293b] w-64">
      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-6 px-3">
        {renderNavSection(mainNav, 'Main')}
        {renderNavSection(configureNav, 'Configure')}
        {renderNavSection(observeNav, 'Observe')}

        {/* Settings */}
        <div className="mt-6">
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-[#1e293b] text-white'
                  : 'text-gray-400 hover:bg-[#1e293b] hover:text-gray-200'
              )
            }
          >
            <Settings className="w-5 h-5 flex-shrink-0" />
            <span>Settings</span>
          </NavLink>
        </div>
      </nav>

      {/* Footer: User Profile */}
      <div className="border-t border-[#1e293b] p-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-[#3b82f6]/20 flex items-center justify-center text-[#3b82f6] font-semibold">
            {user?.email
              ? user.email
                  .split('@')[0]
                  .split('.')
                  .map((n) => n[0])
                  .join('')
                  .toUpperCase()
                  .slice(0, 2) || 'U'
              : 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-200 truncate">
              {user?.email
                ? user.email
                    .split('@')[0]
                    .split('.')
                    .map((n) => n.charAt(0).toUpperCase() + n.slice(1))
                    .join(' ')
                : 'User'}
            </p>
          </div>
          <User className="w-4 h-4 text-gray-400" />
        </div>
      </div>
    </div>
  )
}
