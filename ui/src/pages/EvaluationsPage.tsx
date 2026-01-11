import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Plus,
  Search,
  TestTube,
  CheckCircle2,
  XCircle,
  Clock,
  Play,
  MoreVertical,
  Gauge,
  Zap,
  DollarSign,
  Shield,
  GitCompare,
  RefreshCw,
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
import { Progress } from '../components/ui/Progress'
import { mockEvaluations, type Evaluation } from '../lib/mock-data'
import { evalsApi } from '../lib/api'
import { useStore } from '../store/useStore'
import { Skeleton } from '../components/ui/Skeleton'

const evalTypeIcons = {
  accuracy: Gauge,
  latency: Zap,
  cost: DollarSign,
  safety: Shield,
  regression: GitCompare,
}

const evalTypeColors = {
  accuracy: 'bg-blue-500/10 text-blue-500',
  latency: 'bg-amber-500/10 text-amber-500',
  cost: 'bg-emerald-500/10 text-emerald-500',
  safety: 'bg-rose-500/10 text-rose-500',
  regression: 'bg-purple-500/10 text-purple-500',
}

const statusColors = {
  passed: 'bg-success/10 text-success border-success/20',
  failed: 'bg-error/10 text-error border-error/20',
  running: 'bg-primary/10 text-primary-light border-primary/20',
  pending: 'bg-gray-700 text-gray-400 border-gray-600',
}

const statusIcons = {
  passed: CheckCircle2,
  failed: XCircle,
  running: RefreshCw,
  pending: Clock,
}

function EvaluationCard({ evaluation }: { evaluation: Evaluation }) {
  const TypeIcon = evalTypeIcons[evaluation.type]
  const StatusIcon = statusIcons[evaluation.status]
  const scorePercentage = evaluation.score ? (evaluation.score / evaluation.maxScore) * 100 : 0
  const passRate = evaluation.testCases > 0 ? ((evaluation.passedCases / evaluation.testCases) * 100).toFixed(0) : '0'

  const handleRun = async () => {
    try {
      const result = await evalsApi.run({ runbook_id: evaluation.runbookId })
      useStore.getState().addNotification({
        type: 'success',
        message: `Evaluation "${evaluation.name}" started successfully`,
      })
      // Navigate to the new eval result if available
      if (result.id) {
        window.location.href = `/evaluations/${result.id}`
      }
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'info',
        message: `Running evaluation: ${evaluation.name} (mock mode)`,
      })
    }
  }

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete evaluation "${evaluation.name}"?`)) return
    try {
      await evalsApi.delete(evaluation.id)
      useStore.getState().addNotification({
        type: 'success',
        message: 'Evaluation deleted successfully',
      })
      window.location.reload()
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'info',
        message: `Delete evaluation: ${evaluation.name} (mock mode)`,
      })
    }
  }

  return (
    <Card className="group hover:border-primary/50 transition-colors bg-gray-800 border-gray-700">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${evalTypeColors[evaluation.type]}`}>
            <TypeIcon className="h-5 w-5" />
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className={`${statusColors[evaluation.status]} capitalize`}>
              <StatusIcon className={`mr-1 h-3 w-3 ${evaluation.status === 'running' ? 'animate-spin' : ''}`} />
              {evaluation.status}
            </Badge>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={handleRun}>
                  <Play className="mr-2 h-4 w-4" />
                  Run Evaluation
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link to={`/evaluations/${evaluation.id}`}>View Results</Link>
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => {
                    useStore.getState().addNotification({
                      type: 'info',
                      message: 'Test case editor coming soon',
                    })
                  }}
                >
                  Edit Test Cases
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem className="text-error" onClick={handleDelete}>
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
        <div className="pt-2">
          <Link to={`/evaluations/${evaluation.id}`} className="hover:underline">
            <CardTitle className="text-base text-white">{evaluation.name}</CardTitle>
          </Link>
          <CardDescription className="mt-1">
            <Link to={`/runbooks/${evaluation.runbookId}`} className="hover:underline text-gray-400">
              {evaluation.runbookName}
            </Link>
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        {/* Score Progress */}
        {evaluation.score !== undefined && (
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-400">Score</span>
              <span
                className={`text-lg font-bold ${
                  scorePercentage >= 90 ? 'text-success' : scorePercentage >= 70 ? 'text-warning' : 'text-error'
                }`}
              >
                {evaluation.score}/{evaluation.maxScore}
              </span>
            </div>
            <Progress
              value={evaluation.score || 0}
              max={evaluation.maxScore}
              className={`h-2 ${
                scorePercentage >= 90
                  ? '[&>div]:bg-success'
                  : scorePercentage >= 70
                    ? '[&>div]:bg-warning'
                    : '[&>div]:bg-error'
              }`}
            />
          </div>
        )}

        {/* Test Cases */}
        <div className="flex items-center gap-2 mb-4">
          <Badge variant="outline" className="text-xs capitalize bg-gray-700 border-gray-600">
            {evaluation.type}
          </Badge>
          <span className="text-xs text-gray-400">
            {evaluation.passedCases}/{evaluation.testCases} tests passed
          </span>
        </div>

        <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-700">
          <div>
            <p className="text-lg font-semibold text-success">{passRate}%</p>
            <p className="text-xs text-gray-400">Pass Rate</p>
          </div>
          <div>
            <p className="text-lg font-semibold text-white">{evaluation.testCases}</p>
            <p className="text-xs text-gray-400">Test Cases</p>
          </div>
          <div>
            <p className="text-sm font-medium text-white">{evaluation.duration || '-'}</p>
            <p className="text-xs text-gray-400">Duration</p>
          </div>
        </div>

        <div className="flex gap-2 mt-4">
          <Button variant="outline" size="sm" className="flex-1 bg-transparent border-gray-700" asChild>
            <Link to={`/evaluations/${evaluation.id}`}>View Results</Link>
          </Button>
          <Button size="sm" className="flex-1" onClick={handleRun}>
            <Play className="mr-2 h-3 w-3" />
            Re-run
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export function EvaluationsPage() {
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  // Initialize with mock data immediately - no loading state needed
  const [evaluations, setEvaluations] = useState<Evaluation[]>(mockEvaluations)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    // Try to fetch from backend in the background (non-blocking)
    const fetchEvaluations = async () => {
      try {
        const data = await evalsApi.list()
        // Transform backend data to match Evaluation interface
        const evalsList = Array.isArray(data) ? data : []
        if (evalsList.length > 0) {
          setEvaluations(evalsList)
        }
      } catch {
        // Keep using mock data - already set
      }
    }
    fetchEvaluations()
  }, [])

  const filteredEvaluations = evaluations.filter((evaluation) => {
    const matchesSearch =
      evaluation.name.toLowerCase().includes(search.toLowerCase()) ||
      evaluation.runbookName.toLowerCase().includes(search.toLowerCase())
    const matchesType = typeFilter === 'all' || evaluation.type === typeFilter
    const matchesStatus = statusFilter === 'all' || evaluation.status === statusFilter
    return matchesSearch && matchesType && matchesStatus
  })

  const stats = {
    total: evaluations.length,
    passed: evaluations.filter((e) => e.status === 'passed').length,
    failed: evaluations.filter((e) => e.status === 'failed').length,
    avgScore: evaluations.filter((e) => e.score).length > 0
      ? Math.round(
          evaluations.filter((e) => e.score).reduce((sum, e) => sum + (e.score || 0), 0) /
            evaluations.filter((e) => e.score).length
        )
      : 0,
  }

  const handleRunAll = async () => {
    try {
      const runningEvals = evaluations.filter((e) => e.status !== 'running' && e.status !== 'pending')
      let successCount = 0
      for (const evalItem of runningEvals) {
        try {
          await evalsApi.run({ runbook_id: evalItem.runbookId })
          successCount++
        } catch (err) {
          console.debug('Failed to run evaluation:', err)
        }
      }
      useStore.getState().addNotification({
        type: successCount > 0 ? 'success' : 'info',
        message: `Started ${successCount} evaluation(s)`,
      })
      // Refresh evaluations
      try {
        const data = await evalsApi.list()
        setEvaluations(Array.isArray(data) ? data : [])
      } catch {
        // Keep existing evaluations
      }
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'info',
        message: 'Running all evaluations... (mock mode)',
      })
    }
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
          <h1 className="text-2xl font-semibold text-white">Evaluations</h1>
          <p className="text-gray-400">Test and validate your runbook agent quality</p>
        </div>
        <Button asChild>
          <Link to="/evaluations/new">
            <Plus className="mr-2 h-4 w-4" />
            New Evaluation
          </Link>
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary-light">
                <TestTube className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{stats.total}</p>
                <p className="text-xs text-gray-400">Total Evaluations</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-success/10 text-success">
                <CheckCircle2 className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{stats.passed}</p>
                <p className="text-xs text-gray-400">Passed</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-error/10 text-error">
                <XCircle className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{stats.failed}</p>
                <p className="text-xs text-gray-400">Failed</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-info/10 text-info">
                <Gauge className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{stats.avgScore}%</p>
                <p className="text-xs text-gray-400">Avg Score</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <Input
            placeholder="Search evaluations..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 bg-gray-800 border-gray-700"
          />
        </div>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-[140px] bg-gray-800 border-gray-700">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="accuracy">Accuracy</SelectItem>
            <SelectItem value="latency">Latency</SelectItem>
            <SelectItem value="cost">Cost</SelectItem>
            <SelectItem value="safety">Safety</SelectItem>
            <SelectItem value="regression">Regression</SelectItem>
          </SelectContent>
        </Select>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[140px] bg-gray-800 border-gray-700">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="passed">Passed</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
            <SelectItem value="running">Running</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" className="bg-transparent border-gray-700" onClick={handleRunAll}>
          <Play className="mr-2 h-4 w-4" />
          Run All
        </Button>
      </div>

      {/* Results */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-400">
          Showing {filteredEvaluations.length} of {evaluations.length} evaluations
        </p>
      </div>

      {/* Evaluations Grid */}
      {filteredEvaluations.length === 0 ? (
        <Card className="py-12 bg-gray-800 border-gray-700">
          <div className="text-center">
            <div className="mx-auto h-12 w-12 rounded-full bg-gray-700 flex items-center justify-center mb-4">
              <Search className="h-6 w-6 text-gray-400" />
            </div>
            <h3 className="text-lg font-medium text-white">No evaluations found</h3>
            <p className="text-gray-400 mt-1">Try adjusting your search or filters</p>
          </div>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredEvaluations.map((evaluation) => (
            <EvaluationCard key={evaluation.id} evaluation={evaluation} />
          ))}
        </div>
      )}
    </div>
  )
}
