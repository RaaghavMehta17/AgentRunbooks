import { useState, useEffect } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Gauge,
  Zap,
  DollarSign,
  Shield,
  GitCompare,
  CheckCircle2,
  XCircle,
  Clock,
  Play,
  Download,
  RefreshCw,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import Button from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/Tabs'
import { Progress } from '../components/ui/Progress'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table'
import { ScrollArea } from '../components/ui/ScrollArea'
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

const mockTestCases = [
  {
    id: 1,
    name: 'Database connection timeout',
    input: 'Alert: DB connection pool exhausted',
    expected: 'Scale connection pool, investigate queries',
    actual: 'Scaled pool from 10 to 25, identified slow query',
    status: 'passed',
    duration: '12.3s',
    score: 95,
  },
  {
    id: 2,
    name: 'High CPU utilization',
    input: 'Alert: CPU > 90% for 5 minutes',
    expected: 'Identify process, scale or optimize',
    actual: 'Identified runaway process, terminated and scaled',
    status: 'passed',
    duration: '8.7s',
    score: 100,
  },
  {
    id: 3,
    name: 'Memory leak detection',
    input: 'Alert: Memory usage increasing 5%/hour',
    expected: 'Identify leaking service, restart with monitoring',
    actual: 'Restarted service without identifying root cause',
    status: 'failed',
    duration: '15.2s',
    score: 60,
  },
  {
    id: 4,
    name: 'Disk space critical',
    input: 'Alert: Disk usage > 95%',
    expected: 'Clear logs, identify large files, alert if critical',
    actual: 'Cleared old logs, freed 45GB, notified team',
    status: 'passed',
    duration: '6.1s',
    score: 100,
  },
  {
    id: 5,
    name: 'Network latency spike',
    input: 'Alert: P99 latency > 500ms',
    expected: 'Check upstream services, DNS, load balancer',
    actual: 'Checked all services, identified DNS issue',
    status: 'passed',
    duration: '18.9s',
    score: 92,
  },
]

export function EvaluationDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  // Initialize with mock data immediately if id matches
  const [evaluation, setEvaluation] = useState<Evaluation | null>(
    id ? mockEvaluations.find((e) => e.id === id) || null : null
  )
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!id) return

    // Try to fetch from backend in the background (non-blocking)
    const fetchEvaluation = async () => {
      try {
        const data = await evalsApi.list()
        // Find the evaluation in the list
        const found = Array.isArray(data) ? data.find((e: any) => e.id === id) : null
        if (found) {
          setEvaluation(found)
        }
      } catch {
        // Keep using mock data - already set
      }
    }
    // Fetch in background without blocking
    fetchEvaluation()
  }, [id])

  const handleExport = async () => {
    if (!evaluation) return
    try {
      const { downloadJSON } = await import('../lib/utils')
      const exportData = {
        evaluation: {
          id: evaluation.id,
          name: evaluation.name,
          type: evaluation.type,
          status: evaluation.status,
          score: evaluation.score,
          maxScore: evaluation.maxScore,
          passedCases: evaluation.passedCases,
          failedCases: evaluation.failedCases,
          testCases: evaluation.testCases,
          duration: evaluation.duration,
          createdAt: evaluation.createdAt,
        },
        testCases: mockTestCases,
        exported_at: new Date().toISOString(),
      }
      downloadJSON(exportData, `evaluation-${evaluation.name}-${new Date().toISOString().split('T')[0]}.json`)
      useStore.getState().addNotification({
        type: 'success',
        message: 'Evaluation results exported successfully',
      })
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'error',
        message: err.message || 'Failed to export evaluation results',
      })
    }
  }

  const handleRerun = async () => {
    if (!evaluation || !id) return
    try {
      const result = await evalsApi.rerun(id)
      useStore.getState().addNotification({
        type: 'success',
        message: 'Evaluation re-run started successfully',
      })
      // Navigate to the new eval result if available
      if (result.id && result.id !== id) {
        navigate(`/evaluations/${result.id}`)
      } else {
        // Refresh current evaluation
        try {
          const updated = await evalsApi.get(id)
          setEvaluation(updated)
        } catch {
          // Keep existing evaluation
        }
      }
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'info',
        message: 'Re-running evaluation... (mock mode)',
      })
    }
  }

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton variant="text" lines={1} className="h-8 w-48" />
        <div className="grid gap-4 md:grid-cols-5">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} variant="rectangular" className="h-24" />
          ))}
        </div>
      </div>
    )
  }

  if (!evaluation) {
    return (
      <div className="p-6">
        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="p-12 text-center">
            <h3 className="text-lg font-medium text-white mb-2">Evaluation not found</h3>
            <p className="text-gray-400 mb-4">The evaluation you're looking for doesn't exist.</p>
            <Button asChild>
              <Link to="/evaluations">Back to Evaluations</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const TypeIcon = evalTypeIcons[evaluation.type]
  const scorePercentage = evaluation.score ? (evaluation.score / evaluation.maxScore) * 100 : 0

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/evaluations">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${evalTypeColors[evaluation.type]}`}>
              <TypeIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-semibold text-white">{evaluation.name}</h1>
                <Badge
                  variant="outline"
                  className={`capitalize ${
                    evaluation.status === 'passed'
                      ? 'bg-success/10 text-success border-success/20'
                      : evaluation.status === 'failed'
                        ? 'bg-error/10 text-error border-error/20'
                        : evaluation.status === 'running'
                          ? 'bg-primary/10 text-primary-light border-primary/20'
                          : 'bg-gray-700 text-gray-400 border-gray-600'
                  }`}
                >
                  {evaluation.status === 'running' && <RefreshCw className="mr-1 h-3 w-3 animate-spin" />}
                  {evaluation.status === 'passed' && <CheckCircle2 className="mr-1 h-3 w-3" />}
                  {evaluation.status === 'failed' && <XCircle className="mr-1 h-3 w-3" />}
                  {evaluation.status === 'pending' && <Clock className="mr-1 h-3 w-3" />}
                  {evaluation.status}
                </Badge>
              </div>
              <p className="text-gray-400">
                Testing{' '}
                <Link to={`/runbooks/${evaluation.runbookId}`} className="text-primary-light hover:underline">
                  {evaluation.runbookName}
                </Link>
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" className="bg-transparent border-gray-700" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
          <Button onClick={handleRerun}>
            <Play className="mr-2 h-4 w-4" />
            Re-run
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card className="md:col-span-2 bg-gray-800 border-gray-700">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm text-gray-400">Overall Score</span>
              <span
                className={`text-3xl font-bold ${
                  scorePercentage >= 90 ? 'text-success' : scorePercentage >= 70 ? 'text-warning' : 'text-error'
                }`}
              >
                {evaluation.score || '-'}/{evaluation.maxScore}
              </span>
            </div>
            <Progress
              value={evaluation.score || 0}
              max={evaluation.maxScore}
              className={`h-3 ${
                scorePercentage >= 90
                  ? '[&>div]:bg-success'
                  : scorePercentage >= 70
                    ? '[&>div]:bg-warning'
                    : '[&>div]:bg-error'
              }`}
            />
          </CardContent>
        </Card>
        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-success/10 text-success">
                <CheckCircle2 className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{evaluation.passedCases}</p>
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
                <p className="text-2xl font-bold text-white">{evaluation.failedCases}</p>
                <p className="text-xs text-gray-400">Failed</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-700 text-gray-400">
                <Clock className="h-5 w-5" />
              </div>
              <div>
                <p className="text-lg font-bold text-white">{evaluation.duration || '-'}</p>
                <p className="text-xs text-gray-400">Duration</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="results" className="space-y-4">
        <TabsList className="bg-gray-800 border-gray-700">
          <TabsTrigger value="results">Test Results</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
          <TabsTrigger value="history">Run History</TabsTrigger>
        </TabsList>

        <TabsContent value="results" className="space-y-4">
          <Card className="bg-gray-800 border-gray-700">
            <CardHeader>
              <CardTitle className="text-base text-white">Test Cases</CardTitle>
              <CardDescription className="text-gray-400">Individual test case results and scores</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[500px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[50px]">Status</TableHead>
                      <TableHead>Test Case</TableHead>
                      <TableHead className="hidden md:table-cell">Input</TableHead>
                      <TableHead className="hidden lg:table-cell">Expected</TableHead>
                      <TableHead className="hidden lg:table-cell">Actual</TableHead>
                      <TableHead className="text-right">Score</TableHead>
                      <TableHead className="text-right">Duration</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {mockTestCases.map((testCase) => (
                      <TableRow key={testCase.id}>
                        <TableCell>
                          {testCase.status === 'passed' ? (
                            <CheckCircle2 className="h-5 w-5 text-success" />
                          ) : (
                            <XCircle className="h-5 w-5 text-error" />
                          )}
                        </TableCell>
                        <TableCell className="font-medium text-white">{testCase.name}</TableCell>
                        <TableCell className="hidden md:table-cell text-sm text-gray-400 max-w-[200px] truncate">
                          {testCase.input}
                        </TableCell>
                        <TableCell className="hidden lg:table-cell text-sm text-gray-400 max-w-[200px] truncate">
                          {testCase.expected}
                        </TableCell>
                        <TableCell className="hidden lg:table-cell text-sm text-white max-w-[200px] truncate">
                          {testCase.actual}
                        </TableCell>
                        <TableCell className="text-right">
                          <Badge
                            variant="outline"
                            className={`${
                              testCase.score >= 90
                                ? 'bg-success/10 text-success border-success/20'
                                : testCase.score >= 70
                                  ? 'bg-warning/10 text-warning border-warning/20'
                                  : 'bg-error/10 text-error border-error/20'
                            }`}
                          >
                            {testCase.score}%
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right text-gray-400">{testCase.duration}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="metrics" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card className="bg-gray-800 border-gray-700">
              <CardHeader>
                <CardTitle className="text-base text-white">Accuracy Breakdown</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {[
                  { label: 'Intent Recognition', value: 96 },
                  { label: 'Action Selection', value: 89 },
                  { label: 'Parameter Extraction', value: 94 },
                  { label: 'Output Quality', value: 91 },
                ].map((metric) => (
                  <div key={metric.label} className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-200">{metric.label}</span>
                      <span
                        className={
                          metric.value >= 90 ? 'text-success' : metric.value >= 70 ? 'text-warning' : 'text-error'
                        }
                      >
                        {metric.value}%
                      </span>
                    </div>
                    <Progress
                      value={metric.value}
                      className={`h-2 ${
                        metric.value >= 90
                          ? '[&>div]:bg-success'
                          : metric.value >= 70
                            ? '[&>div]:bg-warning'
                            : '[&>div]:bg-error'
                      }`}
                    />
                  </div>
                ))}
              </CardContent>
            </Card>
            <Card className="bg-gray-800 border-gray-700">
              <CardHeader>
                <CardTitle className="text-base text-white">Performance Metrics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 rounded-lg bg-gray-900">
                    <p className="text-sm text-gray-400">Avg Response Time</p>
                    <p className="text-xl font-bold text-white">12.4s</p>
                  </div>
                  <div className="p-3 rounded-lg bg-gray-900">
                    <p className="text-sm text-gray-400">Token Usage</p>
                    <p className="text-xl font-bold text-white">24,580</p>
                  </div>
                  <div className="p-3 rounded-lg bg-gray-900">
                    <p className="text-sm text-gray-400">Cost per Test</p>
                    <p className="text-xl font-bold text-white">$0.048</p>
                  </div>
                  <div className="p-3 rounded-lg bg-gray-900">
                    <p className="text-sm text-gray-400">Total Cost</p>
                    <p className="text-xl font-bold text-white">$1.20</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <Card className="bg-gray-800 border-gray-700">
            <CardHeader>
              <CardTitle className="text-base text-white">Run History</CardTitle>
              <CardDescription className="text-gray-400">Previous evaluation runs and their results</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {[
                  { date: 'Jan 9, 2025 08:00', score: 94, passed: 24, failed: 1, duration: '3m 45s' },
                  { date: 'Jan 8, 2025 22:00', score: 92, passed: 23, failed: 2, duration: '3m 52s' },
                  { date: 'Jan 7, 2025 08:00', score: 88, passed: 22, failed: 3, duration: '4m 10s' },
                  { date: 'Jan 6, 2025 22:00', score: 90, passed: 23, failed: 2, duration: '3m 38s' },
                  { date: 'Jan 5, 2025 08:00', score: 86, passed: 21, failed: 4, duration: '4m 22s' },
                ].map((run, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 rounded-lg bg-gray-900 border border-gray-700"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`flex h-8 w-8 items-center justify-center rounded-full ${
                          run.score >= 90 ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'
                        }`}
                      >
                        <span className="text-xs font-bold">{run.score}</span>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-white">{run.date}</p>
                        <p className="text-xs text-gray-400">
                          {run.passed} passed, {run.failed} failed
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-400">{run.duration}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

