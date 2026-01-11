import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft,
  Play,
  Edit,
  Copy,
  MoreVertical,
  Clock,
  CheckCircle,
  Calendar,
  User,
  GitBranch,
  Webhook,
  Sparkles,
  Activity,
  Settings,
  AlertTriangle,
  ExternalLink,
  ChevronRight,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import Button from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/Tabs'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../components/ui/DropdownMenu'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../components/ui/Dialog'
import { Label } from '../components/ui/Label'
import { Input } from '../components/ui/Input'
import { Textarea } from '../components/ui/Textarea'
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

export function RunbookDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [runbook, setRunbook] = useState<any>(null)
  const [runbookRuns, setRunbookRuns] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [isRunDialogOpen, setIsRunDialogOpen] = useState(false)
  const [runName, setRunName] = useState('')
  const [inputParams, setInputParams] = useState('')
  const [executing, setExecuting] = useState(false)

  useEffect(() => {
    if (!id) return

    const fetchData = async () => {
      try {
        const [runbookData, runsData] = await Promise.all([
          runbooksApi.get(id).catch(async () => {
            // Fallback to mock data
            const { mockRunbooks } = await import('../lib/mock-data')
            return mockRunbooks.find((rb) => rb.id === id) || null
          }),
          runsApi.list({ limit: 50 }).catch(async () => {
            const { mockRuns } = await import('../lib/mock-data')
            return mockRuns
          }),
        ])

        setRunbook(runbookData)

        // Filter runs for this runbook
        const runs = Array.isArray(runsData) ? runsData : []
        const filteredRuns = runs.filter((r: any) => r.runbook_id === id)
        setRunbookRuns(filteredRuns)
      } catch (err) {
        console.error('Failed to fetch runbook:', err)
        // Try to use mock data
        const { mockRunbooks, mockRuns } = await import('../lib/mock-data')
        const mockRunbook = mockRunbooks.find((rb) => rb.id === id)
        if (mockRunbook) {
          setRunbook(mockRunbook)
          const filteredRuns = mockRuns.filter((r: any) => r.runbook_id === id)
          setRunbookRuns(filteredRuns)
        }
        // Silently use mock data - no notifications
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [id])

  const handleRun = async () => {
    if (!id) return
    setExecuting(true)
    try {
      let context = {}
      if (inputParams.trim()) {
        try {
          context = JSON.parse(inputParams)
        } catch {
          useStore.getState().addNotification({
            type: 'error',
            message: 'Invalid JSON in input parameters',
          })
          setExecuting(false)
          return
        }
      }

      const run = await runsApi.create({
        runbook_id: id,
        mode: 'execute',
        context,
      })

      useStore.getState().addNotification({
        type: 'success',
        message: 'Run started successfully',
      })
      setIsRunDialogOpen(false)
      setRunName('')
      setInputParams('')
      navigate(`/runs/${run.id || run.run_id || id}`)
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to start run'
      useStore.getState().addNotification({
        type: 'error',
        message: errorMsg,
      })
    } finally {
      setExecuting(false)
    }
  }

  const handleDelete = async () => {
    if (!id || !confirm('Are you sure you want to delete this runbook?')) return
    try {
      await runbooksApi.delete(id)
      useStore.getState().addNotification({
        type: 'success',
        message: 'Runbook deleted successfully',
      })
      navigate('/runbooks')
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'error',
        message: err.message || 'Failed to delete runbook',
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

  if (!runbook) {
    return (
      <div className="p-6 text-center py-12">
        <p className="text-gray-400 mb-4">Runbook not found</p>
        <Link to="/runbooks">
          <Button>Back to Runbooks</Button>
        </Link>
      </div>
    )
  }

  // Determine trigger type from runbook data
  const triggerType = runbook.trigger || 'manual'
  const TriggerIcon = triggerIcons[triggerType as keyof typeof triggerIcons] || Play

  // Calculate stats
  const successfulRuns = runbookRuns.filter((r: any) => r.status === 'succeeded' || r.status === 'completed').length
  const successRate = runbookRuns.length > 0 ? Math.round((successfulRuns / runbookRuns.length) * 100) : 0
  const avgDuration = runbookRuns.length > 0
    ? runbookRuns
        .filter((r: any) => r.duration)
        .reduce((acc: number, r: any) => acc + (parseInt(r.duration) || 0), 0) / runbookRuns.length
    : 0
  const lastRun = runbookRuns.length > 0
    ? new Date(runbookRuns[0].created_at).toLocaleDateString()
    : 'Never'

  // Mock workflow steps - in real app, parse from YAML
  const workflowSteps = [
    { id: 1, name: 'Trigger', type: 'trigger', description: `${triggerType} trigger` },
    { id: 2, name: 'Pre-checks', type: 'tool', description: 'Validate prerequisites' },
    { id: 3, name: 'Analyze Context', type: 'llm', description: 'AI analysis of situation' },
    { id: 4, name: 'Execute Action', type: 'tool', description: 'Primary automation action' },
    { id: 5, name: 'Human Review', type: 'human', description: 'Optional approval gate' },
    { id: 6, name: 'Finalize', type: 'tool', description: 'Complete and notify' },
  ]

  return (
    <div className="p-6 space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <Link to="/runbooks" className="text-gray-400 hover:text-white flex items-center gap-1">
          <ArrowLeft className="h-4 w-4" />
          Runbooks
        </Link>
        <ChevronRight className="h-4 w-4 text-gray-400" />
        <span className="text-white">{runbook.name}</span>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-[#3b82f6]/10 text-[#3b82f6]">
              <TriggerIcon className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-white flex items-center gap-3">
                {runbook.name}
                <StatusBadge status={runbook.status || 'active'} />
              </h1>
              <p className="text-gray-400">{runbook.description || 'No description'}</p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Dialog open={isRunDialogOpen} onOpenChange={setIsRunDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Play className="mr-2 h-4 w-4" />
                Run Now
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Run {runbook.name}</DialogTitle>
                <DialogDescription>Configure and execute this runbook</DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label>Run Name (Optional)</Label>
                  <Input
                    placeholder="e.g., Production deployment v2.4.1"
                    value={runName}
                    onChange={(e) => setRunName(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Input Parameters</Label>
                  <Textarea
                    placeholder='{"environment": "production", "version": "latest"}'
                    className="font-mono text-sm"
                    rows={4}
                    value={inputParams}
                    onChange={(e) => setInputParams(e.target.value)}
                  />
                </div>
                <div className="flex items-center gap-2 p-3 rounded-lg bg-[#f59e0b]/10 border border-[#f59e0b]/20">
                  <AlertTriangle className="h-4 w-4 text-[#f59e0b]" />
                  <p className="text-sm text-[#f59e0b]">This runbook may require human approval during execution</p>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsRunDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleRun} loading={executing}>
                  <Play className="mr-2 h-4 w-4" />
                  Start Run
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          <Button
            variant="outline"
            onClick={() => {
              useStore.getState().addNotification({
                type: 'info',
                message: 'Runbook editor coming soon - use the YAML editor in the configuration tab',
              })
            }}
          >
            <Edit className="mr-2 h-4 w-4" />
            Edit
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={async () => {
                try {
                  const duplicated = await runbooksApi.duplicate(id!)
                  useStore.getState().addNotification({
                    type: 'success',
                    message: 'Runbook duplicated successfully',
                  })
                  navigate(`/runbooks/${duplicated.id || duplicated.runbook_id || id}`)
                } catch (err: any) {
                  useStore.getState().addNotification({
                    type: 'error',
                    message: err.message || 'Failed to duplicate runbook',
                  })
                }
              }}>
                <Copy className="mr-2 h-4 w-4" />
                Duplicate
              </DropdownMenuItem>
              <DropdownMenuItem onClick={async () => {
                try {
                  const { downloadJSON } = await import('../lib/utils')
                  const data = { ...runbook, exported_at: new Date().toISOString() }
                  downloadJSON(data, `runbook-${runbook.name}-${new Date().toISOString().split('T')[0]}.json`)
                  useStore.getState().addNotification({
                    type: 'success',
                    message: 'Runbook exported successfully',
                  })
                } catch (err: any) {
                  useStore.getState().addNotification({
                    type: 'error',
                    message: err.message || 'Failed to export runbook',
                  })
                }
              }}>
                <ExternalLink className="mr-2 h-4 w-4" />
                Export
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-[#ef4444]" onClick={handleDelete}>
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Tags */}
      {runbook.tags && runbook.tags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {runbook.tags.map((tag: string) => (
            <Badge key={tag} variant="secondary">
              {tag}
            </Badge>
          ))}
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400">Success Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-[#10b981]">{successRate}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400">Avg Duration</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{avgDuration > 0 ? `${Math.round(avgDuration)}s` : '-'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400">Last Run</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{lastRun}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400">Version</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">v{runbook.version || '1.0'}</div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview" className="gap-2">
            <Activity className="h-4 w-4" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="runs" className="gap-2">
            <Play className="h-4 w-4" />
            Runs
          </TabsTrigger>
          <TabsTrigger value="config" className="gap-2">
            <Settings className="h-4 w-4" />
            Configuration
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* Workflow Visualization */}
          <Card>
            <CardHeader>
              <CardTitle>Workflow</CardTitle>
              <CardDescription>Visual representation of the runbook steps</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 overflow-x-auto pb-4">
                {workflowSteps.map((step, index) => (
                  <div key={step.id} className="flex items-center gap-2">
                    <div className="flex flex-col items-center">
                      <div
                        className={`flex h-12 w-12 items-center justify-center rounded-lg border-2 ${
                          step.type === 'trigger'
                            ? 'bg-[#3b82f6]/10 border-[#3b82f6] text-[#3b82f6]'
                            : step.type === 'llm'
                              ? 'bg-[#10b981]/10 border-[#10b981] text-[#10b981]'
                              : step.type === 'human'
                                ? 'bg-[#f59e0b]/10 border-[#f59e0b] text-[#f59e0b]'
                                : 'bg-[#334155] border-[#475569] text-white'
                        }`}
                      >
                        {step.type === 'trigger' && <Sparkles className="h-5 w-5" />}
                        {step.type === 'tool' && <Settings className="h-5 w-5" />}
                        {step.type === 'llm' && <Sparkles className="h-5 w-5" />}
                        {step.type === 'human' && <User className="h-5 w-5" />}
                      </div>
                      <p className="text-xs font-medium mt-2 text-center max-w-[80px] text-white">{step.name}</p>
                      <p className="text-[10px] text-gray-400 text-center max-w-[80px]">{step.description}</p>
                    </div>
                    {index < workflowSteps.length - 1 && <div className="h-0.5 w-8 bg-[#334155]" />}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Metadata */}
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400 flex items-center gap-2">
                    <TriggerIcon className="h-4 w-4" />
                    Trigger Type
                  </span>
                  <span className="text-sm font-medium text-white capitalize">{triggerType}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400 flex items-center gap-2">
                    <User className="h-4 w-4" />
                    Created By
                  </span>
                  <span className="text-sm font-medium text-white">{runbook.created_by || 'System'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400 flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Created
                  </span>
                  <span className="text-sm font-medium text-white">
                    {runbook.created_at ? new Date(runbook.created_at).toLocaleDateString() : 'Unknown'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400 flex items-center gap-2">
                    <Clock className="h-4 w-4" />
                    Updated
                  </span>
                  <span className="text-sm font-medium text-white">
                    {runbook.updated_at ? new Date(runbook.updated_at).toLocaleDateString() : 'Unknown'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400 flex items-center gap-2">
                    <GitBranch className="h-4 w-4" />
                    Version
                  </span>
                  <span className="text-sm font-medium text-white">v{runbook.version || '1.0'}</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Recent Activity</CardTitle>
              </CardHeader>
              <CardContent>
                {runbookRuns.length === 0 ? (
                  <p className="text-sm text-gray-400 text-center py-4">No runs yet</p>
                ) : (
                  <div className="space-y-3">
                    {runbookRuns.slice(0, 4).map((run: any) => (
                      <Link
                        key={run.id}
                        to={`/runs/${run.id}`}
                        className="flex items-center justify-between hover:bg-[#1e293b]/50 rounded p-2 -mx-2 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          {run.status === 'completed' || run.status === 'succeeded' ? (
                            <CheckCircle className="h-4 w-4 text-[#10b981]" />
                          ) : run.status === 'failed' ? (
                            <AlertTriangle className="h-4 w-4 text-[#ef4444]" />
                          ) : run.status === 'running' ? (
                            <Play className="h-4 w-4 text-[#3b82f6]" />
                          ) : (
                            <Clock className="h-4 w-4 text-[#f59e0b]" />
                          )}
                          <span className="text-sm text-white">{run.created_by || 'System'}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-400">{run.duration || 'In progress'}</span>
                          <StatusBadge status={run.status} />
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="runs" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Execution History</CardTitle>
              <CardDescription>All runs of this runbook</CardDescription>
            </CardHeader>
            <CardContent>
              {runbookRuns.length === 0 ? (
                <div className="text-center py-8">
                  <Play className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-white">No runs yet</h3>
                  <p className="text-gray-400">Run this runbook to see execution history</p>
                  <Button className="mt-4" onClick={() => setIsRunDialogOpen(true)}>
                    <Play className="mr-2 h-4 w-4" />
                    Run Now
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  {runbookRuns.map((run: any) => (
                    <Link
                      key={run.id}
                      to={`/runs/${run.id}`}
                      className="flex items-center justify-between rounded-lg border border-[#334155] px-4 py-3 hover:bg-[#1e293b]/50 transition-colors"
                    >
                      <div className="flex items-center gap-4">
                        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#334155]">
                          {run.status === 'completed' || run.status === 'succeeded' ? (
                            <CheckCircle className="h-4 w-4 text-[#10b981]" />
                          ) : run.status === 'failed' ? (
                            <AlertTriangle className="h-4 w-4 text-[#ef4444]" />
                          ) : run.status === 'running' ? (
                            <Play className="h-4 w-4 text-[#3b82f6]" />
                          ) : (
                            <Clock className="h-4 w-4 text-[#f59e0b]" />
                          )}
                        </div>
                        <div>
                          <p className="font-medium text-sm text-white">Run #{run.id.split('-')[1] || run.id.slice(0, 8)}</p>
                          <p className="text-xs text-gray-400">
                            {run.created_by || 'System'} • {new Date(run.created_at).toLocaleString()}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        {run.duration && <span className="text-sm text-gray-400">{run.duration}</span>}
                        {run.metrics?.cost_usd !== undefined && (
                          <span className="text-sm text-gray-400">${run.metrics.cost_usd.toFixed(3)}</span>
                        )}
                        <StatusBadge status={run.status} />
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="config" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Trigger Configuration</CardTitle>
              <CardDescription>How this runbook is triggered</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-4 p-4 rounded-lg bg-[#334155]/50">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#3b82f6]/10 text-[#3b82f6]">
                  <TriggerIcon className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-medium text-white capitalize">{triggerType} Trigger</p>
                  <p className="text-sm text-gray-400">
                    {triggerType === 'manual' && 'Manually triggered by users'}
                    {triggerType === 'scheduled' && 'Runs on a defined schedule'}
                    {triggerType === 'webhook' && 'Triggered via HTTP webhook'}
                    {triggerType === 'event' && 'Triggered by external events'}
                  </p>
                </div>
              </div>
              {triggerType === 'webhook' && (
                <div className="space-y-2">
                  <Label>Webhook URL</Label>
                  <div className="flex gap-2">
                    <Input
                      readOnly
                      value={`https://api.runbookos.io/webhooks/${id}/trigger`}
                      className="font-mono text-sm"
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={async () => {
                        try {
                          const { copyToClipboard } = await import('../lib/utils')
                          await copyToClipboard(`https://api.runbookos.io/webhooks/${id}/trigger`)
                          useStore.getState().addNotification({
                            type: 'success',
                            message: 'Webhook URL copied to clipboard',
                          })
                        } catch (err: any) {
                          useStore.getState().addNotification({
                            type: 'error',
                            message: 'Failed to copy webhook URL',
                          })
                        }
                      }}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Policies & Guardrails</CardTitle>
              <CardDescription>Rules applied to this runbook</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 rounded-lg border border-[#334155]">
                  <div className="flex items-center gap-3">
                    <CheckCircle className="h-4 w-4 text-[#10b981]" />
                    <span className="text-sm text-white">Require approval for destructive actions</span>
                  </div>
                  <Badge variant="secondary">Enabled</Badge>
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg border border-[#334155]">
                  <div className="flex items-center gap-3">
                    <CheckCircle className="h-4 w-4 text-[#10b981]" />
                    <span className="text-sm text-white">Cost limit per run: $5.00</span>
                  </div>
                  <Badge variant="secondary">Enabled</Badge>
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg border border-[#334155]">
                  <div className="flex items-center gap-3">
                    <CheckCircle className="h-4 w-4 text-[#10b981]" />
                    <span className="text-sm text-white">Timeout: 30 minutes</span>
                  </div>
                  <Badge variant="secondary">Enabled</Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
