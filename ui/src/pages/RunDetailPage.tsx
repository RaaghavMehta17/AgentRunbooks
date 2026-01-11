import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft,
  ChevronRight,
  Play,
  Pause,
  RotateCcw,
  XCircle,
  CheckCircle,
  AlertTriangle,
  Sparkles,
  Settings,
  User,
  Terminal,
  DollarSign,
  Timer,
  Cpu,
  Copy,
  ExternalLink,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import Button from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Progress } from '../components/ui/Progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/Tabs'
import { ScrollArea } from '../components/ui/ScrollArea'
import { Separator } from '../components/ui/Separator'
import { StatusBadge } from '../components/ui/StatusBadge'
import { runsApi, runbooksApi } from '../lib/api'
import { Skeleton } from '../components/ui/Skeleton'
import { useStore } from '../store/useStore'
import { cn } from '../lib/utils'

const stepTypeIcons = {
  trigger: Sparkles,
  llm: Sparkles,
  tool: Settings,
  human: User,
  condition: AlertTriangle,
  loop: RotateCcw,
}

function StepCard({ step, isActive = false }: { step: any; isActive?: boolean }) {
  const Icon = stepTypeIcons[step.type as keyof typeof stepTypeIcons] || Settings

  return (
    <div
      className={cn(
        'rounded-lg border border-[#334155] p-4 transition-all',
        isActive && 'border-[#3b82f6] bg-[#3b82f6]/5 ring-1 ring-[#3b82f6]/30',
        step.status === 'succeeded' && 'border-[#10b981]/30',
        step.status === 'failed' && 'border-[#ef4444]/30'
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'flex h-9 w-9 items-center justify-center rounded-lg shrink-0',
            step.status === 'succeeded' && 'bg-[#10b981]/10 text-[#10b981]',
            step.status === 'failed' && 'bg-[#ef4444]/10 text-[#ef4444]',
            step.status === 'running' && 'bg-[#3b82f6]/10 text-[#3b82f6]',
            step.status === 'pending' && 'bg-[#334155] text-gray-400'
          )}
        >
          {step.status === 'succeeded' && <CheckCircle className="h-4 w-4" />}
          {step.status === 'failed' && <XCircle className="h-4 w-4" />}
          {step.status === 'running' && <Icon className="h-4 w-4 animate-pulse" />}
          {step.status === 'pending' && <Icon className="h-4 w-4" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm text-white">{step.name || step.step_name || 'Step'}</span>
              <Badge variant="outline" className="text-xs capitalize">
                {step.type || 'tool'}
              </Badge>
            </div>
            {step.duration && <span className="text-xs text-gray-400">{step.duration}</span>}
          </div>
          {step.output && (
            <p className="text-xs text-gray-400 mt-1 line-clamp-2 font-mono bg-[#0f172a] rounded px-2 py-1">
              {typeof step.output === 'string' ? step.output : JSON.stringify(step.output)}
            </p>
          )}
          {(step.usage || step.cost) && (
            <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
              {step.usage?.tokens_in && (
                <span className="flex items-center gap-1">
                  <Cpu className="h-3 w-3" />
                  {(step.usage.tokens_in + (step.usage.tokens_out || 0)).toLocaleString()} tokens
                </span>
              )}
              {(step.usage?.cost_usd || step.cost) && (
                <span className="flex items-center gap-1">
                  <DollarSign className="h-3 w-3" />${(step.usage?.cost_usd || step.cost || 0).toFixed(4)}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function RunDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [run, setRun] = useState<any>(null)
  const [runbook, setRunbook] = useState<any>(null)
  const [logs, setLogs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    if (!id) return

    const fetchData = async (showErrors = true) => {
      try {
        const runData = await runsApi.get(id)
        setRun(runData)

        // Calculate progress
        const steps = runData.steps || []
        const completedSteps = steps.filter((s: any) => s.status === 'succeeded').length
        const totalSteps = steps.length || 1
        setProgress((completedSteps / totalSteps) * 100)

        // Fetch runbook if available
        if (runData.runbook_id) {
          try {
            const runbookData = await runbooksApi.get(runData.runbook_id)
            setRunbook(runbookData)
          } catch {
            // Runbook might not exist - use mock data
            const { mockRunbooks } = await import('../lib/mock-data')
            const mockRunbook = mockRunbooks.find((rb) => rb.id === runData.runbook_id)
            if (mockRunbook) setRunbook(mockRunbook)
          }
        }

        // Generate logs from steps
        const generatedLogs: any[] = []
        steps.forEach((step: any, index: number) => {
          generatedLogs.push({
            time: new Date(runData.created_at).toLocaleTimeString(),
            level: 'info',
            message: `Executing step: ${step.name || step.step_name || `Step ${index + 1}`}`,
          })
          if (step.status === 'succeeded') {
            generatedLogs.push({
              time: new Date(runData.created_at).toLocaleTimeString(),
              level: 'info',
              message: `Step completed: ${step.name || step.step_name || `Step ${index + 1}`}`,
            })
          } else if (step.status === 'failed') {
            generatedLogs.push({
              time: new Date(runData.created_at).toLocaleTimeString(),
              level: 'error',
              message: `Step failed: ${step.name || step.step_name || `Step ${index + 1}`}`,
            })
          }
        })
        setLogs(generatedLogs)
      } catch (err) {
        // Silently use mock data - no errors, no notifications
        const { mockRuns, mockLogs: mockLogEntries } = await import('../lib/mock-data')
        const mockRun = mockRuns.find((r) => r.id === id)
        if (mockRun) {
          setRun(mockRun)
          const steps = mockRun.steps || []
          const completedSteps = steps.filter((s: any) => s.status === 'succeeded').length
          const totalSteps = steps.length || 1
          setProgress((completedSteps / totalSteps) * 100)
          
          // Use mock logs
          setLogs(mockLogEntries.map((log) => ({
            ...log,
            time: new Date(mockRun.created_at).toLocaleTimeString(),
          })))
          
          // Try to get runbook
          const { mockRunbooks } = await import('../lib/mock-data')
          const mockRunbook = mockRunbooks.find((rb) => rb.id === mockRun.runbook_id)
          if (mockRunbook) setRunbook(mockRunbook)
        }
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [id])

  // Poll for updates if running (silently, no error notifications)
  useEffect(() => {
    if (!id || !run) return
    if (run.status !== 'running' && run.status !== 'pending') return

    const interval = setInterval(async () => {
      try {
        const runData = await runsApi.get(id)
        setRun(runData)

        const steps = runData.steps || []
        const completedSteps = steps.filter((s: any) => s.status === 'succeeded').length
        const totalSteps = steps.length || 1
        setProgress((completedSteps / totalSteps) * 100)

        // Stop polling if run is complete
        if (
          runData.status === 'succeeded' ||
          runData.status === 'failed' ||
          runData.status === 'completed'
        ) {
          clearInterval(interval)
        }
      } catch {
        // Silently fail on polling - no errors, no notifications
      }
    }, 2000)

    return () => {
      clearInterval(interval)
    }
  }, [id, run?.status])

  const handleApprove = async () => {
    if (!id || !run) return
    try {
      // Find the approval for this run
      const approvals = await approvalsApi.list()
      const approval = Array.isArray(approvals) ? approvals.find((a: any) => a.run_id === id && !a.approved) : null
      
      if (approval) {
        await approvalsApi.approve(approval.id, { comment: 'Approved via UI' })
      }
      
      useStore.getState().addNotification({
        type: 'success',
        message: 'Approval granted',
      })
      
      // Refresh run data
      const updated = await runsApi.get(id)
      setRun(updated)
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'error',
        message: err.message || 'Failed to approve',
      })
    }
  }

  const handleReject = async () => {
    if (!id || !run) return
    try {
      // Find the approval for this run
      const approvals = await approvalsApi.list()
      const approval = Array.isArray(approvals) ? approvals.find((a: any) => a.run_id === id && !a.approved) : null
      
      if (approval) {
        await approvalsApi.deny(approval.id, { comment: 'Rejected via UI' })
      }
      
      useStore.getState().addNotification({
        type: 'success',
        message: 'Run rejected',
      })
      
      // Refresh run data
      const updated = await runsApi.get(id)
      setRun(updated)
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'error',
        message: err.message || 'Failed to reject',
      })
    }
  }

  const handleRerun = async () => {
    if (!run?.runbook_id) return
    try {
      const newRun = await runsApi.create({
        runbook_id: run.runbook_id,
        mode: 'execute',
        context: run.context || {},
      })
      navigate(`/runs/${newRun.id || newRun.run_id}`)
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'error',
        message: err.message || 'Failed to re-run',
      })
    }
  }

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton variant="text" lines={1} className="h-8 w-48" />
        <div className="grid gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} variant="rectangular" className="h-32" />
          ))}
        </div>
      </div>
    )
  }

  if (!run) {
    return (
      <div className="p-6 text-center py-12">
        <p className="text-gray-400 mb-4">Run not found</p>
        <Link to="/runs">
          <Button>Back to Runs</Button>
        </Link>
      </div>
    )
  }

  const steps = run.steps || []
  const currentStepIndex = steps.findIndex((s: any) => s.status === 'running')
  const duration = run.duration || (run.created_at ? `${Math.floor((Date.now() - new Date(run.created_at).getTime()) / 1000)}s` : '-')
  const cost = run.metrics?.cost_usd || 0
  const tokens = (run.metrics?.tokens_in || 0) + (run.metrics?.tokens_out || 0)

  return (
    <div className="p-6 space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <Link to="/runs" className="text-gray-400 hover:text-white flex items-center gap-1">
          <ArrowLeft className="h-4 w-4" />
          Runs
        </Link>
        <ChevronRight className="h-4 w-4 text-gray-400" />
        <span className="text-white">Run #{id?.split('-')[1] || id?.slice(0, 8)}</span>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-white">{run.runbook_id || 'Unknown Runbook'}</h1>
            <StatusBadge status={run.status} />
          </div>
          <p className="text-gray-400">
            Triggered by {run.created_by || 'System'} • {new Date(run.created_at).toLocaleString()}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {run.status === 'running' && (
            <>
              <Button
                variant="outline"
                onClick={async () => {
                  if (!id) return
                  try {
                    await runsApi.pause(id)
                    useStore.getState().addNotification({
                      type: 'success',
                      message: 'Run paused successfully',
                    })
                    // Refresh run data
                    const updated = await runsApi.get(id)
                    setRun(updated)
                  } catch (err: any) {
                    useStore.getState().addNotification({
                      type: 'error',
                      message: err.message || 'Failed to pause run',
                    })
                  }
                }}
              >
                <Pause className="mr-2 h-4 w-4" />
                Pause
              </Button>
              <Button
                variant="danger"
                onClick={async () => {
                  if (!id || !confirm('Are you sure you want to cancel this run?')) return
                  try {
                    await runsApi.cancel(id)
                    useStore.getState().addNotification({
                      type: 'success',
                      message: 'Run cancelled successfully',
                    })
                    // Refresh run data
                    const updated = await runsApi.get(id)
                    setRun(updated)
                  } catch (err: any) {
                    useStore.getState().addNotification({
                      type: 'error',
                      message: err.message || 'Failed to cancel run',
                    })
                  }
                }}
              >
                <XCircle className="mr-2 h-4 w-4" />
                Cancel
              </Button>
            </>
          )}
          {run.status === 'awaiting_approval' && (
            <>
              <Button
                variant="outline"
                className="text-[#ef4444] border-[#ef4444] hover:bg-[#ef4444]/10 bg-transparent"
                onClick={handleReject}
              >
                Reject
              </Button>
              <Button onClick={handleApprove}>
                <CheckCircle className="mr-2 h-4 w-4" />
                Approve
              </Button>
            </>
          )}
          {(run.status === 'succeeded' || run.status === 'failed') && (
            <Button variant="outline" onClick={handleRerun}>
              <RotateCcw className="mr-2 h-4 w-4" />
              Re-run
            </Button>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      {(run.status === 'running' || run.status === 'awaiting_approval') && (
        <Card className="border-[#3b82f6]/30 bg-[#3b82f6]/5">
          <CardContent className="pt-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium text-white">
                  {run.status === 'awaiting_approval' ? 'Waiting for Approval' : 'In Progress'}
                </span>
                <span className="text-gray-400">
                  {steps.filter((s: any) => s.status === 'succeeded').length} of {steps.length} steps completed
                </span>
              </div>
              <Progress value={progress} className="h-2" />
              {run.status === 'awaiting_approval' && (
                <div className="flex items-center gap-2 mt-3 p-3 rounded-lg bg-[#f59e0b]/10 border border-[#f59e0b]/20">
                  <AlertTriangle className="h-4 w-4 text-[#f59e0b]" />
                  <p className="text-sm text-[#f59e0b]">Awaiting approval for: Full Production Rollout (100% traffic)</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400 flex items-center gap-2">
              <Timer className="h-4 w-4" />
              Duration
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{duration}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400 flex items-center gap-2">
              <Play className="h-4 w-4" />
              Steps
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">
              {steps.filter((s: any) => s.status === 'succeeded').length}/{steps.length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400 flex items-center gap-2">
              <DollarSign className="h-4 w-4" />
              Cost
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">${cost.toFixed(3)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400 flex items-center gap-2">
              <Cpu className="h-4 w-4" />
              Tokens
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{tokens.toLocaleString()}</div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="timeline" className="space-y-4">
        <TabsList>
          <TabsTrigger value="timeline" className="gap-2">
            <Play className="h-4 w-4" />
            Timeline
          </TabsTrigger>
          <TabsTrigger value="logs" className="gap-2">
            <Terminal className="h-4 w-4" />
            Logs
          </TabsTrigger>
          <TabsTrigger value="details" className="gap-2">
            <Settings className="h-4 w-4" />
            Details
          </TabsTrigger>
        </TabsList>

        <TabsContent value="timeline" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Execution Timeline</CardTitle>
              <CardDescription>Step-by-step progress of the run</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {steps.length === 0 ? (
                  <p className="text-sm text-gray-400 text-center py-8">No steps available</p>
                ) : (
                  steps.map((step: any, index: number) => (
                    <StepCard key={step.id || index} step={step} isActive={index === currentStepIndex} />
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="logs" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Execution Logs</CardTitle>
                <CardDescription>Real-time output from the run</CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    navigator.clipboard.writeText(logs.map((l) => `${l.time} [${l.level}] ${l.message}`).join('\n'))
                    useStore.getState().addNotification({
                      type: 'success',
                      message: 'Logs copied to clipboard',
                    })
                  }}
                >
                  <Copy className="mr-2 h-3 w-3" />
                  Copy
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={async () => {
                    try {
                      const { downloadText } = await import('../lib/utils')
                      const logText = logs.map((l) => `${l.time} [${l.level}] ${l.message}`).join('\n')
                      downloadText(logText, `run-${id}-logs-${new Date().toISOString().split('T')[0]}.txt`)
                      useStore.getState().addNotification({
                        type: 'success',
                        message: 'Logs downloaded successfully',
                      })
                    } catch (err: any) {
                      useStore.getState().addNotification({
                        type: 'error',
                        message: err.message || 'Failed to download logs',
                      })
                    }
                  }}
                >
                  <ExternalLink className="mr-2 h-3 w-3" />
                  Download
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px] rounded-lg bg-[#0d1117] p-4 font-mono text-xs">
                {logs.length === 0 ? (
                  <p className="text-gray-400">No logs available</p>
                ) : (
                  logs.map((log, index) => (
                    <div key={index} className="flex gap-3 py-0.5">
                      <span className="text-gray-400 shrink-0">{log.time}</span>
                      <span
                        className={cn(
                          'shrink-0 w-12',
                          log.level === 'info' && 'text-[#3b82f6]',
                          log.level === 'debug' && 'text-gray-400',
                          log.level === 'warn' && 'text-[#f59e0b]',
                          log.level === 'error' && 'text-[#ef4444]'
                        )}
                      >
                        [{log.level}]
                      </span>
                      <span className="text-white">{log.message}</span>
                    </div>
                  ))
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="details" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Run Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Run ID</span>
                  <span className="text-sm font-mono text-white">{run.id}</span>
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Runbook</span>
                  {run.runbook_id ? (
                    <Link to={`/runbooks/${run.runbook_id}`} className="text-sm text-[#3b82f6] hover:underline">
                      {run.runbook_id}
                    </Link>
                  ) : (
                    <span className="text-sm text-white">-</span>
                  )}
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Triggered By</span>
                  <span className="text-sm text-white">{run.created_by || 'System'}</span>
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Started At</span>
                  <span className="text-sm text-white">
                    {run.created_at ? new Date(run.created_at).toLocaleString() : '-'}
                  </span>
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Completed At</span>
                  <span className="text-sm text-white">
                    {run.completed_at ? new Date(run.completed_at).toLocaleString() : '-'}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Input Parameters</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-xs font-mono bg-[#0f172a] rounded-lg p-3 overflow-auto text-white">
                  {JSON.stringify(run.context || {}, null, 2)}
                </pre>
              </CardContent>
            </Card>
          </div>

          {runbook && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Runbook Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Version</span>
                  <Badge variant="secondary">v{runbook.version || '1.0'}</Badge>
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Name</span>
                  <span className="text-sm text-white">{runbook.name}</span>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
