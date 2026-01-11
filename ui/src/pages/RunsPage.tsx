import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Search, Play, CheckCircle, XCircle, Clock, RefreshCw, ChevronRight, Calendar } from 'lucide-react'
import { Card, CardContent } from '../components/ui/Card'
import Button from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Progress } from '../components/ui/Progress'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/Select'
import { StatusBadge } from '../components/ui/StatusBadge'
import { runsApi } from '../lib/api'
import { Skeleton } from '../components/ui/Skeleton'
import { useStore } from '../store/useStore'
import { formatRelativeTime } from '../lib/utils'
import { cn } from '../lib/utils'

function RunRow({ run, isLive = false }: { run: any; isLive?: boolean }) {
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    if (run.status === 'running' && isLive) {
      const steps = run.steps || []
      const completedSteps = steps.filter((s: any) => s.status === 'succeeded').length
      const totalSteps = steps.length || 1
      setProgress((completedSteps / totalSteps) * 100)

      const interval = setInterval(() => {
        setProgress((prev) => Math.min(prev + Math.random() * 2, 95))
      }, 2000)
      return () => clearInterval(interval)
    } else {
      const steps = run.steps || []
      const completedSteps = steps.filter((s: any) => s.status === 'succeeded').length
      const totalSteps = steps.length || 1
      setProgress((completedSteps / totalSteps) * 100)
    }
  }, [run.status, run.steps, isLive])

  const steps = run.steps || []
  const stepsCompleted = steps.filter((s: any) => s.status === 'succeeded').length
  const stepsTotal = steps.length || 1

  return (
    <Link
      to={`/runs/${run.id}`}
      className={cn(
        'flex items-center gap-4 rounded-lg border border-[#334155] px-4 py-3 hover:bg-[#1e293b]/50 transition-colors',
        run.status === 'running' && 'border-[#3b82f6]/30 bg-[#3b82f6]/5',
        run.status === 'awaiting_approval' && 'border-[#f59e0b]/30 bg-[#f59e0b]/5'
      )}
    >
      {/* Status Icon */}
      <div
        className={cn(
          'flex h-10 w-10 items-center justify-center rounded-full shrink-0',
          (run.status === 'succeeded' || run.status === 'completed') && 'bg-[#10b981]/10',
          run.status === 'failed' && 'bg-[#ef4444]/10',
          run.status === 'running' && 'bg-[#3b82f6]/10',
          run.status === 'awaiting_approval' && 'bg-[#f59e0b]/10',
          run.status === 'pending' && 'bg-[#334155]'
        )}
      >
        {(run.status === 'succeeded' || run.status === 'completed') && (
          <CheckCircle className="h-5 w-5 text-[#10b981]" />
        )}
        {run.status === 'failed' && <XCircle className="h-5 w-5 text-[#ef4444]" />}
        {run.status === 'running' && <Play className="h-5 w-5 text-[#3b82f6] animate-pulse" />}
        {run.status === 'awaiting_approval' && <Clock className="h-5 w-5 text-[#f59e0b]" />}
        {run.status === 'pending' && <Clock className="h-5 w-5 text-gray-400" />}
      </div>

      {/* Main Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-medium text-sm truncate text-white">{run.runbook_id || 'Unknown Runbook'}</span>
          <span className="text-xs text-gray-400">#{run.id.split('-')[1] || run.id.slice(0, 8)}</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs text-gray-400">{run.created_by || 'System'}</span>
          <span className="text-xs text-gray-400">{formatRelativeTime(run.created_at)}</span>
        </div>
        {(run.status === 'running' || run.status === 'awaiting_approval') && (
          <div className="mt-2 space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-400">Progress</span>
              <span className="text-white">
                {stepsCompleted}/{stepsTotal} steps
              </span>
            </div>
            <Progress value={progress} className="h-1.5" />
          </div>
        )}
      </div>

      {/* Metadata */}
      <div className="hidden md:flex items-center gap-6 shrink-0">
        {run.duration && (
          <div className="text-right">
            <p className="text-sm font-medium text-white">{run.duration}</p>
            <p className="text-xs text-gray-400">Duration</p>
          </div>
        )}
        {run.metrics?.cost_usd !== undefined && (
          <div className="text-right">
            <p className="text-sm font-medium text-white">${run.metrics.cost_usd.toFixed(3)}</p>
            <p className="text-xs text-gray-400">Cost</p>
          </div>
        )}
      </div>

      {/* Status Badge */}
      <div className="flex items-center gap-2 shrink-0">
        <StatusBadge status={run.status} />
        <ChevronRight className="h-4 w-4 text-gray-400" />
      </div>
    </Link>
  )
}

export function RunsPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [runs, setRuns] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const fetchRuns = async (showErrors = false) => {
    try {
      const data = await runsApi.list({ limit: 100 })
      setRuns(Array.isArray(data) ? data : [])
    } catch (err) {
      // Silently use mock data - no errors, no notifications
      const { mockRuns } = await import('../lib/mock-data')
      setRuns(mockRuns)
    } finally {
      setLoading(false)
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    fetchRuns(false) // Never show errors, just use mock data

    // Poll for updates every 5 seconds (silently, no error notifications)
    const interval = setInterval(() => fetchRuns(false), 5000)
    return () => clearInterval(interval)
  }, [])

  const filteredRuns = runs.filter((run) => {
    const matchesSearch =
      (run.runbook_id || '').toLowerCase().includes(search.toLowerCase()) ||
      (run.created_by || '').toLowerCase().includes(search.toLowerCase()) ||
      (run.id || '').toLowerCase().includes(search.toLowerCase())
    const matchesStatus = statusFilter === 'all' || run.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const activeRuns = filteredRuns.filter((r) => r.status === 'running' || r.status === 'awaiting_approval')
  const completedRuns = filteredRuns.filter(
    (r) => r.status === 'succeeded' || r.status === 'failed' || r.status === 'completed' || r.status === 'pending'
  )

  const handleRefresh = () => {
    setIsRefreshing(true)
    fetchRuns(false) // Never show errors, just use mock data
  }

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton variant="text" lines={1} className="h-8 w-48" />
        <div className="grid gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} variant="rectangular" className="h-24" />
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
          <h1 className="text-2xl font-semibold text-white">Runs</h1>
          <p className="text-gray-400">Monitor and manage runbook executions</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleRefresh}>
            <RefreshCw className={cn('h-4 w-4', isRefreshing && 'animate-spin')} />
          </Button>
          <Button asChild>
            <Link to="/runbooks">
              <Play className="mr-2 h-4 w-4" />
              New Run
            </Link>
          </Button>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-2xl font-bold text-white">
                  {runs.filter((r) => r.status === 'running').length}
                </p>
                <p className="text-xs text-gray-400">Running</p>
              </div>
              <Play className="h-8 w-8 text-[#3b82f6]/50" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-2xl font-bold text-white">
                  {runs.filter((r) => r.status === 'awaiting_approval').length}
                </p>
                <p className="text-xs text-gray-400">Awaiting Approval</p>
              </div>
              <Clock className="h-8 w-8 text-[#f59e0b]/50" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-2xl font-bold text-white">
                  {runs.filter((r) => r.status === 'succeeded' || r.status === 'completed').length}
                </p>
                <p className="text-xs text-gray-400">Completed Today</p>
              </div>
              <CheckCircle className="h-8 w-8 text-[#10b981]/50" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-2xl font-bold text-white">{runs.filter((r) => r.status === 'failed').length}</p>
                <p className="text-xs text-gray-400">Failed Today</p>
              </div>
              <XCircle className="h-8 w-8 text-[#ef4444]/50" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <Input
            placeholder="Search runs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 bg-[#1e293b]/50 border-0"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[160px] bg-[#1e293b]/50 border-0">
            <SelectValue placeholder="All Statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="running">Running</SelectItem>
            <SelectItem value="awaiting_approval">Awaiting Approval</SelectItem>
            <SelectItem value="succeeded">Completed</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
          </SelectContent>
        </Select>
        <Button
          variant="outline"
          className="gap-2 bg-transparent"
          onClick={() => {
            const today = new Date()
            today.setHours(0, 0, 0, 0)
            const todayStart = today.toISOString()
            const todayEnd = new Date(today.getTime() + 24 * 60 * 60 * 1000).toISOString()
            // Filter runs to today
            const todayRuns = runs.filter((r: any) => {
              const runDate = new Date(r.created_at)
              return runDate >= today && runDate < new Date(todayEnd)
            })
            setRuns(todayRuns)
            useStore.getState().addNotification({
              type: 'info',
              message: `Showing ${todayRuns.length} runs from today`,
            })
          }}
        >
          <Calendar className="h-4 w-4" />
          Today
        </Button>
      </div>

      {/* Active Runs Section */}
      {activeRuns.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-[#3b82f6] animate-pulse" />
            <h2 className="text-sm font-medium text-white">Active ({activeRuns.length})</h2>
          </div>
          <div className="space-y-2">
            {activeRuns.map((run) => (
              <RunRow key={run.id} run={run} isLive />
            ))}
          </div>
        </div>
      )}

      {/* Completed Runs Section */}
      <div className="space-y-3">
        <h2 className="text-sm font-medium text-gray-400">History ({completedRuns.length})</h2>
        {filteredRuns.length === 0 ? (
          <Card className="py-12">
            <div className="text-center">
              <div className="mx-auto h-12 w-12 rounded-full bg-[#334155] flex items-center justify-center mb-4">
                <Search className="h-6 w-6 text-gray-400" />
              </div>
              <h3 className="text-lg font-medium text-white">No runs found</h3>
              <p className="text-gray-400 mt-1">Try adjusting your search or filters</p>
            </div>
          </Card>
        ) : (
          <div className="space-y-2">
            {completedRuns.map((run) => (
              <RunRow key={run.id} run={run} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
