import React, { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { Search, Bell, Grid3x3, HelpCircle, ChevronDown, BookOpen, Play, Shield, Settings, LogOut, User } from 'lucide-react'
import { useStore } from '../../store/useStore'
import { cn } from '../../lib/utils'
import { projectsApi, searchApi } from '../../lib/api'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '../ui/DropdownMenu'

export function TopBar() {
  const navigate = useNavigate()
  const location = useLocation()
  const currentProject = useStore((state) => state.currentProject)
  const setCurrentProject = useStore((state) => state.setCurrentProject)
  const user = useStore((state) => state.user)
  const [showProjectMenu, setShowProjectMenu] = useState(false)
  const [showSearchResults, setShowSearchResults] = useState(false)
  const [showNotifications, setShowNotifications] = useState(false)
  const [showHelp, setShowHelp] = useState(false)
  const [showProfileMenu, setShowProfileMenu] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [healthStatus, setHealthStatus] = useState<'ok' | 'error'>('ok')
  const [projects, setProjects] = useState<any[]>([])
  const [loadingProjects, setLoadingProjects] = useState(true)
  const [notifications] = useState<any[]>([])

  // Fetch projects
  useEffect(() => {
    const fetchProjects = async () => {
      try {
        setLoadingProjects(true)
        const fetchedProjects = await projectsApi.list()
        setProjects(Array.isArray(fetchedProjects) ? fetchedProjects : [])
        if (!currentProject && fetchedProjects.length > 0) {
          setCurrentProject(fetchedProjects[0].name)
        }
      } catch (error) {
        console.error('Failed to fetch projects:', error)
      } finally {
        setLoadingProjects(false)
      }
    }
    fetchProjects()
  }, [currentProject, setCurrentProject])

  // Check health periodically
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch('http://localhost:8000/healthz')
        setHealthStatus(res.ok ? 'ok' : 'error')
      } catch {
        setHealthStatus('error')
      }
    }
    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  // Search functionality
  const searchTimeoutRef = useRef<NodeJS.Timeout>()
  useEffect(() => {
    if (searchQuery.trim().length < 2) {
      setSearchResults([])
      setShowSearchResults(false)
      return
    }

    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }

    searchTimeoutRef.current = setTimeout(async () => {
      try {
        const results = await searchApi.search(searchQuery)
        setSearchResults(results.slice(0, 10))
        setShowSearchResults(true)
      } catch (err) {
        console.debug('Search error (silent):', err)
        setSearchResults([])
      }
    }, 300)

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current)
      }
    }
  }, [searchQuery])

  // Close search results when clicking outside
  const searchRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowSearchResults(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Keyboard shortcut for search (Cmd/Ctrl + K)
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
        event.preventDefault()
        const searchInput = document.querySelector('input[placeholder*="Search"]') as HTMLInputElement
        if (searchInput) {
          searchInput.focus()
          searchInput.select()
        }
      }
      if (event.key === 'Escape') {
        setShowSearchResults(false)
        setShowNotifications(false)
        setShowHelp(false)
        setShowProfileMenu(false)
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])

  const handleSearchResultClick = (result: any) => {
    setShowSearchResults(false)
    setSearchQuery('')
    if (result.type === 'runbook') {
      navigate(`/runbooks/${result.id}`)
    } else if (result.type === 'run') {
      navigate(`/runs/${result.id}`)
    } else if (result.type === 'policy') {
      navigate(`/policies/${result.id}`)
    }
  }

  return (
    <header className="sticky top-0 z-40 bg-[#0f172a] border-b border-[#1e293b]">
      <div className="flex items-center justify-between px-6 py-3 h-14">
        {/* Left: Logo + Project Selector */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-[#3b82f6] flex items-center justify-center text-white font-bold text-sm">
              A
            </div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-gray-100">Acme Corp</span>
              <div className="relative">
                <button
                  onClick={() => setShowProjectMenu(!showProjectMenu)}
                  className="flex items-center gap-1 text-gray-300 hover:text-gray-100 transition-colors text-sm"
                >
                  <span>{currentProject || 'Production'}</span>
                  <ChevronDown className="w-4 h-4" />
                </button>
                {showProjectMenu && (
                  <div className="absolute left-0 mt-2 w-48 bg-[#1e293b] border border-[#334155] rounded-lg shadow-lg py-1 z-50">
                    {loadingProjects ? (
                      <div className="px-3 py-2 text-xs text-gray-400">Loading projects...</div>
                    ) : projects.length > 0 ? (
                      projects.map((project) => (
                        <button
                          key={project.id}
                          onClick={() => {
                            setCurrentProject(project.name)
                            setShowProjectMenu(false)
                          }}
                          className="w-full px-4 py-2 text-left text-sm text-gray-300 hover:bg-[#334155]"
                        >
                          {project.name}
                        </button>
                      ))
                    ) : (
                      <div className="px-3 py-2 text-xs text-gray-400">No projects found</div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Center: Search */}
        <div className="flex-1 max-w-2xl mx-8" ref={searchRef}>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search runbooks, runs, or integrations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => searchQuery.length >= 2 && setShowSearchResults(true)}
              className="w-full pl-10 pr-20 py-2 bg-[#1e293b] border border-[#334155] rounded-lg text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#3b82f6] focus:border-transparent text-sm"
            />
            <kbd className="absolute right-3 top-1/2 transform -translate-y-1/2 px-2 py-1 text-xs bg-[#334155] border border-[#475569] rounded text-gray-400">
              ⌘ K
            </kbd>
            {showSearchResults && searchResults.length > 0 && (
              <div className="absolute left-0 right-0 mt-2 bg-[#1e293b] border border-[#334155] rounded-lg shadow-xl max-h-96 overflow-y-auto z-50">
                {searchResults.map((result, index) => (
                  <button
                    key={`${result.type}-${result.id}-${index}`}
                    onClick={() => handleSearchResultClick(result)}
                    className="w-full px-4 py-3 text-left hover:bg-[#334155] transition-colors border-b border-[#334155] last:border-0"
                  >
                    <div className="flex items-center gap-3">
                      {result.type === 'runbook' && <BookOpen className="h-4 w-4 text-[#3b82f6]" />}
                      {result.type === 'run' && <Play className="h-4 w-4 text-[#10b981]" />}
                      {result.type === 'policy' && <Shield className="h-4 w-4 text-[#f59e0b]" />}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-white truncate">{result.name || result.id}</p>
                        <p className="text-xs text-gray-400 capitalize">{result.type}</p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
            {showSearchResults && searchQuery.length >= 2 && searchResults.length === 0 && (
              <div className="absolute left-0 right-0 mt-2 bg-[#1e293b] border border-[#334155] rounded-lg shadow-xl p-4 z-50">
                <p className="text-sm text-gray-400 text-center">No results found</p>
              </div>
            )}
          </div>
        </div>

        {/* Right: Icons */}
        <div className="flex items-center gap-3">
          {/* Grid Icon - Open quick actions */}
          <button
            className="p-2 rounded-lg hover:bg-[#1e293b] text-gray-400 hover:text-gray-200 transition-colors"
            onClick={() => {
              useStore.getState().addNotification({
                type: 'info',
                message: 'Quick actions menu coming soon',
              })
            }}
            title="Quick Actions"
          >
            <Grid3x3 className="w-5 h-5" />
          </button>

          {/* Notifications */}
          <div className="relative">
            <button
              className="relative p-2 rounded-lg hover:bg-[#1e293b] text-gray-400 hover:text-gray-200 transition-colors"
              onClick={() => setShowNotifications(!showNotifications)}
              title="Notifications"
            >
              <Bell className="w-5 h-5" />
              {notifications.length > 0 && (
                <span className="absolute top-1 right-1 w-2 h-2 bg-[#ef4444] rounded-full border-2 border-[#0f172a]" />
              )}
            </button>
            {showNotifications && (
              <div className="absolute right-0 mt-2 w-80 bg-[#1e293b] border border-[#334155] rounded-lg shadow-xl z-50">
                <div className="p-4 border-b border-[#334155]">
                  <h3 className="text-sm font-semibold text-white">Notifications</h3>
                </div>
                <div className="max-h-96 overflow-y-auto">
                  {notifications.length === 0 ? (
                    <div className="p-4 text-center text-sm text-gray-400">No new notifications</div>
                  ) : (
                    notifications.map((notif) => (
                      <div key={notif.id} className="p-4 border-b border-[#334155] hover:bg-[#334155] transition-colors">
                        <p className="text-sm text-white">{notif.message}</p>
                        <p className="text-xs text-gray-400 mt-1">
                          {notif.timestamp ? new Date(notif.timestamp).toLocaleString() : 'Just now'}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Help */}
          <button
            className="p-2 rounded-lg hover:bg-[#1e293b] text-gray-400 hover:text-gray-200 transition-colors"
            onClick={() => {
              setShowHelp(!showHelp)
              useStore.getState().addNotification({
                type: 'info',
                message: 'Help documentation and support coming soon',
              })
            }}
            title="Help & Support"
          >
            <HelpCircle className="w-5 h-5" />
          </button>

          {/* System Status */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#1e293b]">
            <div className={cn('w-2 h-2 rounded-full animate-pulse', healthStatus === 'ok' ? 'bg-[#10b981]' : 'bg-[#ef4444]')} />
            <span className="text-xs text-gray-300 font-medium">
              {healthStatus === 'ok' ? 'All Systems Operational' : 'System Issues Detected'}
            </span>
          </div>

          {/* User Profile */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-[#1e293b] transition-colors">
                <div className="w-8 h-8 rounded-full bg-[#3b82f6]/20 flex items-center justify-center text-[#3b82f6] text-sm font-semibold">
                  {user?.email?.[0]?.toUpperCase() || 'U'}
                </div>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <div className="px-2 py-1.5 border-b border-[#334155]">
                <p className="text-sm font-medium text-white">{user?.name || user?.email || 'User'}</p>
                <p className="text-xs text-gray-400">{user?.email}</p>
              </div>
              <DropdownMenuItem asChild>
                <Link to="/settings" className="flex items-center">
                  <Settings className="mr-2 h-4 w-4" />
                  Settings
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link to="/profile" className="flex items-center">
                  <User className="mr-2 h-4 w-4" />
                  Profile
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={async () => {
                  try {
                    const { authApi } = await import('../../lib/api')
                    await authApi.logout()
                    navigate('/login')
                  } catch (err) {
                    navigate('/login')
                  }
                }}
                className="text-[#ef4444]"
              >
                <LogOut className="mr-2 h-4 w-4" />
                Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}
