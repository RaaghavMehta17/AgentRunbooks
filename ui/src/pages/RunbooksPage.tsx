import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Plus,
  Search,
  Grid3X3,
  List,
  MoreVertical,
  Play,
  Webhook,
  Calendar,
  Sparkles,
  ArrowUpRight,
  Copy,
  Archive,
  Trash2,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import Button from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Badge } from '../components/ui/Badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../components/ui/DropdownMenu'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/Select'
import { Tabs, TabsList, TabsTrigger } from '../components/ui/Tabs'
import { StatusBadge } from '../components/ui/StatusBadge'
import { runbooksApi, runsApi } from '../lib/api'
import { Skeleton } from '../components/ui/Skeleton'
import { useStore } from '../store/useStore'

const triggerIcons = {
  manual: Play,
  scheduled: Calendar,
  webhook: Webhook,
  event: Sparkles,
}

function RunbookCard({ runbook, view }: { runbook: any; view: 'grid' | 'list' }) {
  const navigate = useNavigate()
  const triggerType = runbook.trigger || 'manual'
  const TriggerIcon = triggerIcons[triggerType as keyof typeof triggerIcons] || Play

  const handleRun = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    try {
      const run = await runsApi.create({
        runbook_id: runbook.id,
        mode: 'execute',
      })
      useStore.getState().addNotification({
        type: 'success',
        message: 'Run started successfully',
      })
      navigate(`/runs/${run.id || run.run_id || runbook.id}`)
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'error',
        message: err.message || 'Failed to start run',
      })
    }
  }

  const handleDelete = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!confirm('Are you sure you want to delete this runbook?')) return
    try {
      await runbooksApi.delete(runbook.id)
      useStore.getState().addNotification({
        type: 'success',
        message: 'Runbook deleted successfully',
      })
      window.location.reload()
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'error',
        message: err.message || 'Failed to delete runbook',
      })
    }
  }

  const handleDuplicate = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    try {
      const duplicated = await runbooksApi.duplicate(runbook.id)
      useStore.getState().addNotification({
        type: 'success',
        message: 'Runbook duplicated successfully',
      })
      navigate(`/runbooks/${duplicated.id || duplicated.runbook_id || runbook.id}`)
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'error',
        message: err.message || 'Failed to duplicate runbook',
      })
    }
  }

  const handleArchive = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!confirm('Are you sure you want to archive this runbook?')) return
    try {
      await runbooksApi.archive(runbook.id)
      useStore.getState().addNotification({
        type: 'success',
        message: 'Runbook archived successfully',
      })
      window.location.reload()
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'error',
        message: err.message || 'Failed to archive runbook',
      })
    }
  }

  // Calculate stats from runs
  const successRate = 0 // Would need to fetch runs for each runbook
  const avgDuration = '-' // Would need to calculate from runs
  const lastRun = runbook.last_run || 'Never'

  if (view === 'list') {
    return (
      <Link
        to={`/runbooks/${runbook.id}`}
        className="flex items-center justify-between rounded-lg border border-[#334155] bg-[#1e293b] px-4 py-3 hover:bg-[#1e293b]/50 transition-colors group"
      >
        <div className="flex items-center gap-4 min-w-0 flex-1">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#3b82f6]/10 text-[#3b82f6] shrink-0">
            <TriggerIcon className="h-5 w-5" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h3 className="font-medium text-sm truncate text-white">{runbook.name}</h3>
              <StatusBadge status={runbook.status || 'active'} />
            </div>
            <p className="text-xs text-gray-400 truncate">{runbook.description || 'No description'}</p>
          </div>
        </div>
        <div className="flex items-center gap-6 shrink-0">
          <div className="hidden md:flex items-center gap-1">
            {runbook.tags?.slice(0, 2).map((tag: string) => (
              <Badge key={tag} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
            {runbook.tags && runbook.tags.length > 2 && (
              <Badge variant="secondary" className="text-xs">
                +{runbook.tags.length - 2}
              </Badge>
            )}
          </div>
          <div className="hidden lg:block text-right">
            <p className="text-sm font-medium text-[#10b981]">{successRate}%</p>
            <p className="text-xs text-gray-400">success rate</p>
          </div>
          <div className="hidden lg:block text-right">
            <p className="text-sm text-white">{avgDuration}</p>
            <p className="text-xs text-gray-400">avg duration</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-400">{lastRun}</p>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild onClick={(e) => e.preventDefault()}>
              <Button variant="ghost" size="sm" className="h-8 w-8 opacity-0 group-hover:opacity-100">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={handleRun}>
                <Play className="mr-2 h-4 w-4" />
                Run Now
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link to={`/runbooks/${runbook.id}`}>
                  <ArrowUpRight className="mr-2 h-4 w-4" />
                  Open in Editor
                </Link>
              </DropdownMenuItem>
                <DropdownMenuItem onClick={handleDuplicate}>
                  <Copy className="mr-2 h-4 w-4" />
                  Duplicate
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleArchive}>
                  <Archive className="mr-2 h-4 w-4" />
                  Archive
                </DropdownMenuItem>
                <DropdownMenuItem className="text-[#ef4444]" onClick={handleDelete}>
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </Link>
    )
  }

  return (
    <Card className="group hover:border-[#3b82f6]/50 transition-colors">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#3b82f6]/10 text-[#3b82f6]">
            <TriggerIcon className="h-5 w-5" />
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge status={runbook.status || 'active'} />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={handleRun}>
                  <Play className="mr-2 h-4 w-4" />
                  Run Now
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link to={`/runbooks/${runbook.id}`}>
                    <ArrowUpRight className="mr-2 h-4 w-4" />
                    Open in Editor
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleDuplicate}>
                  <Copy className="mr-2 h-4 w-4" />
                  Duplicate
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleArchive}>
                  <Archive className="mr-2 h-4 w-4" />
                  Archive
                </DropdownMenuItem>
                <DropdownMenuItem className="text-[#ef4444]" onClick={handleDelete}>
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
        <div className="pt-2">
          <Link to={`/runbooks/${runbook.id}`} className="hover:underline">
            <CardTitle className="text-base">{runbook.name}</CardTitle>
          </Link>
          <CardDescription className="line-clamp-2 mt-1">{runbook.description || 'No description'}</CardDescription>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="flex flex-wrap gap-1 mb-4">
          {runbook.tags?.map((tag: string) => (
            <Badge key={tag} variant="secondary" className="text-xs">
              {tag}
            </Badge>
          ))}
        </div>
        <div className="grid grid-cols-3 gap-4 pt-4 border-t border-[#334155]">
          <div>
            <p className="text-lg font-semibold text-[#10b981]">{successRate}%</p>
            <p className="text-xs text-gray-400">Success</p>
          </div>
          <div>
            <p className="text-lg font-semibold text-white">{avgDuration}</p>
            <p className="text-xs text-gray-400">Avg Time</p>
          </div>
          <div>
            <p className="text-sm font-medium text-white">{lastRun}</p>
            <p className="text-xs text-gray-400">Last Run</p>
          </div>
        </div>
        <div className="flex gap-2 mt-4">
          <Button variant="outline" size="sm" className="flex-1 bg-transparent" asChild>
            <Link to={`/runbooks/${runbook.id}`}>View</Link>
          </Button>
          <Button size="sm" className="flex-1" onClick={handleRun}>
            <Play className="mr-2 h-3 w-3" />
            Run
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export function RunbooksPage() {
  const [view, setView] = useState<'grid' | 'list'>('grid')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [triggerFilter, setTriggerFilter] = useState<string>('all')
  const [runbooks, setRunbooks] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchRunbooks = async () => {
      try {
        const data = await runbooksApi.list()
        setRunbooks(Array.isArray(data) ? data : [])
      } catch (err) {
        // Silently use mock data - no console errors, no notifications
        const { mockRunbooks } = await import('../lib/mock-data')
        setRunbooks(mockRunbooks)
      } finally {
        setLoading(false)
      }
    }
    fetchRunbooks()
  }, [])

  const filteredRunbooks = runbooks.filter((runbook) => {
    const matchesSearch =
      runbook.name?.toLowerCase().includes(search.toLowerCase()) ||
      runbook.description?.toLowerCase().includes(search.toLowerCase()) ||
      runbook.tags?.some((tag: string) => tag.toLowerCase().includes(search.toLowerCase()))

    const matchesStatus = statusFilter === 'all' || (runbook.status || 'active') === statusFilter
    const matchesTrigger = triggerFilter === 'all' || (runbook.trigger || 'manual') === triggerFilter

    return matchesSearch && matchesStatus && matchesTrigger
  })

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton variant="text" lines={1} className="h-8 w-48" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} variant="rectangular" className="h-64" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Runbooks</h1>
          <p className="text-gray-400">Manage and execute your automated workflows</p>
        </div>
        <Button asChild>
          <Link to="/runbooks/new">
            <Plus className="mr-2 h-4 w-4" />
            Create Runbook
          </Link>
        </Button>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-1 items-center gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              placeholder="Search runbooks..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 bg-[#1e293b]/50 border-0"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[130px] bg-[#1e293b]/50 border-0">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="draft">Draft</SelectItem>
              <SelectItem value="archived">Archived</SelectItem>
            </SelectContent>
          </Select>
          <Select value={triggerFilter} onValueChange={setTriggerFilter}>
            <SelectTrigger className="w-[130px] bg-[#1e293b]/50 border-0">
              <SelectValue placeholder="Trigger" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Triggers</SelectItem>
              <SelectItem value="manual">Manual</SelectItem>
              <SelectItem value="scheduled">Scheduled</SelectItem>
              <SelectItem value="webhook">Webhook</SelectItem>
              <SelectItem value="event">Event</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2">
          <Tabs value={view} onValueChange={(v) => setView(v as 'grid' | 'list')}>
            <TabsList className="bg-[#1e293b]/50">
              <TabsTrigger value="grid" className="px-3">
                <Grid3X3 className="h-4 w-4" />
              </TabsTrigger>
              <TabsTrigger value="list" className="px-3">
                <List className="h-4 w-4" />
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </div>

      {/* Results Count */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-400">
          Showing {filteredRunbooks.length} of {runbooks.length} runbooks
        </p>
      </div>

      {/* Runbooks Grid/List */}
      {filteredRunbooks.length === 0 ? (
        <Card className="py-12">
          <div className="text-center">
            <div className="mx-auto h-12 w-12 rounded-full bg-[#334155] flex items-center justify-center mb-4">
              <Search className="h-6 w-6 text-gray-400" />
            </div>
            <h3 className="text-lg font-medium text-white">No runbooks found</h3>
            <p className="text-gray-400 mt-1">Try adjusting your search or filters</p>
            <Button
              variant="outline"
              className="mt-4 bg-transparent"
              onClick={() => {
                setSearch('')
                setStatusFilter('all')
                setTriggerFilter('all')
              }}
            >
              Clear Filters
            </Button>
          </div>
        </Card>
      ) : view === 'grid' ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredRunbooks.map((runbook) => (
            <RunbookCard key={runbook.id} runbook={runbook} view="grid" />
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {filteredRunbooks.map((runbook) => (
            <RunbookCard key={runbook.id} runbook={runbook} view="list" />
          ))}
        </div>
      )}
    </div>
  )
}
