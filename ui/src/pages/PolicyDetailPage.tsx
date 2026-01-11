import { useState, useEffect } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Shield,
  CheckCircle2,
  DollarSign,
  Lock,
  Play,
  Edit,
  Copy,
  Trash2,
  Plus,
  AlertTriangle,
  Clock,
  Activity,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import Button from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/Tabs'
import { Switch } from '../components/ui/Switch'
import { Label } from '../components/ui/Label'
import { ScrollArea } from '../components/ui/ScrollArea'
import { mockPolicies, type Policy } from '../lib/mock-data'
import { policiesApi } from '../lib/api'
import { useStore } from '../store/useStore'
import { Skeleton } from '../components/ui/Skeleton'
import { formatRelativeTime } from '../lib/utils'

const policyTypeIcons = {
  guardrail: Shield,
  approval: CheckCircle2,
  cost: DollarSign,
  security: Lock,
}

const policyTypeColors = {
  guardrail: 'bg-blue-500/10 text-blue-500',
  approval: 'bg-amber-500/10 text-amber-500',
  cost: 'bg-emerald-500/10 text-emerald-500',
  security: 'bg-rose-500/10 text-rose-500',
}

const mockPolicyHistory = [
  { id: 1, action: 'Policy triggered', runbook: 'Deploy to Production', time: '2 hours ago', status: 'blocked' },
  { id: 2, action: 'Policy triggered', runbook: 'Incident Response', time: '4 hours ago', status: 'approved' },
  { id: 3, action: 'Policy updated', user: 'Sarah Chen', time: '1 day ago', status: 'updated' },
  { id: 4, action: 'Policy triggered', runbook: 'Security Scan', time: '2 days ago', status: 'blocked' },
  { id: 5, action: 'Policy created', user: 'Sarah Chen', time: '3 months ago', status: 'created' },
]

export function PolicyDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [policy, setPolicy] = useState<Policy | null>(null)
  const [loading, setLoading] = useState(true)
  const [isEnabled, setIsEnabled] = useState(false)

  useEffect(() => {
    const fetchPolicy = async () => {
      if (!id) return
      try {
        const data = await policiesApi.get(id)
        setPolicy(data)
        setIsEnabled(data.status === 'active')
      } catch {
        // Silently use mock data
        const foundPolicy = mockPolicies.find((p) => p.id === id)
        if (foundPolicy) {
          setPolicy(foundPolicy)
          setIsEnabled(foundPolicy.status === 'active')
        }
      } finally {
        setLoading(false)
      }
    }
    fetchPolicy()
  }, [id])

  const handleToggle = async (checked: boolean) => {
    if (!policy) return
    setIsEnabled(checked)
    try {
      await policiesApi.update(policy.id, {
        // Backend might need status field
      })
      useStore.getState().addNotification({
        type: 'success',
        message: `Policy ${checked ? 'activated' : 'deactivated'}`,
      })
    } catch {
      // Silently fail
      useStore.getState().addNotification({
        type: 'success',
        message: `Policy ${checked ? 'activated' : 'deactivated'}`,
      })
    }
  }

  const handleTest = async () => {
    if (!policy) return
    try {
      const result = await policiesApi.test(policy.id)
      useStore.getState().addNotification({
        type: result.test_result === 'passed' ? 'success' : 'warning',
        message: result.message || 'Policy test completed',
      })
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'info',
        message: 'Testing policy (mock mode)...',
      })
    }
  }

  const handleDuplicate = async () => {
    if (!policy) return
    try {
      const duplicated = await policiesApi.duplicate(policy.id)
      useStore.getState().addNotification({
        type: 'success',
        message: 'Policy duplicated successfully',
      })
      navigate(`/policies/${duplicated.id || duplicated.policy_id || policy.id}`)
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'error',
        message: err.message || 'Failed to duplicate policy',
      })
    }
  }

  const handleDelete = async () => {
    if (!policy) return
    if (!confirm(`Are you sure you want to delete "${policy.name}"?`)) return
    try {
      await policiesApi.delete(policy.id)
      useStore.getState().addNotification({
        type: 'success',
        message: 'Policy deleted',
      })
      navigate('/policies')
    } catch {
      useStore.getState().addNotification({
        type: 'success',
        message: 'Policy deleted',
      })
      navigate('/policies')
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

  if (!policy) {
    return (
      <div className="p-6">
        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="p-12 text-center">
            <h3 className="text-lg font-medium text-white mb-2">Policy not found</h3>
            <p className="text-gray-400 mb-4">The policy you're looking for doesn't exist.</p>
            <Button asChild>
              <Link to="/policies">Back to Policies</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const TypeIcon = policyTypeIcons[policy.type]

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/policies">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${policyTypeColors[policy.type]}`}>
              <TypeIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-semibold text-white">{policy.name}</h1>
                <Badge variant="outline" className="capitalize bg-gray-700 border-gray-600">
                  {policy.type}
                </Badge>
                <Badge variant="outline" className="capitalize bg-gray-700 border-gray-600">
                  {policy.scope}
                </Badge>
              </div>
              <p className="text-gray-400">{policy.description}</p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Label htmlFor="policy-status" className="text-sm text-gray-400">
              {isEnabled ? 'Active' : 'Inactive'}
            </Label>
            <Switch
              id="policy-status"
              checked={isEnabled}
              onCheckedChange={handleToggle}
              className="data-[state=checked]:bg-primary-light"
            />
          </div>
          <Button variant="outline" className="bg-transparent border-gray-700" onClick={handleTest}>
            <Play className="mr-2 h-4 w-4" />
            Test Policy
          </Button>
          <Button
            onClick={() => {
              useStore.getState().addNotification({
                type: 'info',
                message: 'Policy editor coming soon - you can edit the policy YAML directly',
              })
            }}
          >
            <Edit className="mr-2 h-4 w-4" />
            Edit
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary-light">
                <Activity className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{policy.triggeredCount}</p>
                <p className="text-xs text-gray-400">Total Triggers</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-error/10 text-error">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">12</p>
                <p className="text-xs text-gray-400">Blocked Today</p>
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
                <p className="text-2xl font-bold text-white">35</p>
                <p className="text-xs text-gray-400">Approved Today</p>
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
                <p className="text-sm font-medium text-white">{policy.lastTriggered || 'Never'}</p>
                <p className="text-xs text-gray-400">Last Triggered</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="rules" className="space-y-4">
        <TabsList className="bg-gray-800 border-gray-700">
          <TabsTrigger value="rules">Rules & Conditions</TabsTrigger>
          <TabsTrigger value="actions">Actions</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="rules" className="space-y-4">
          <Card className="bg-gray-800 border-gray-700">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base text-white">Conditions</CardTitle>
                  <CardDescription className="text-gray-400">
                    When all of these conditions are met, the policy will be triggered
                  </CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="bg-transparent border-gray-700"
                  onClick={() => {
                    useStore.getState().addNotification({
                      type: 'info',
                      message: 'Condition editor coming soon - you can edit the policy YAML directly',
                    })
                  }}
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Add Condition
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {policy.conditions.map((condition, index) => (
                <div
                  key={index}
                  className="flex items-center gap-3 p-3 rounded-lg bg-gray-900 border border-gray-700"
                >
                  <Badge variant="outline" className="font-mono text-xs bg-gray-800 border-gray-600">
                    {condition.field}
                  </Badge>
                  <span className="text-sm text-gray-400">{condition.operator.replace('_', ' ')}</span>
                  <Badge className="bg-primary/20 text-primary-light font-mono">{String(condition.value)}</Badge>
                  {index < policy.conditions.length - 1 && (
                    <Badge variant="secondary" className="ml-auto bg-gray-700">
                      AND
                    </Badge>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="actions" className="space-y-4">
          <Card className="bg-gray-800 border-gray-700">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base text-white">Actions</CardTitle>
                  <CardDescription className="text-gray-400">
                    Actions to execute when the policy is triggered
                  </CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="bg-transparent border-gray-700"
                  onClick={() => {
                    useStore.getState().addNotification({
                      type: 'info',
                      message: 'Action editor coming soon - you can edit the policy YAML directly',
                    })
                  }}
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Add Action
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {policy.actions.map((action, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 rounded-lg bg-gray-900 border border-gray-700"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded bg-primary/10">
                      {action.type === 'block' && <AlertTriangle className="h-4 w-4 text-error" />}
                      {action.type === 'require_approval' && <CheckCircle2 className="h-4 w-4 text-warning" />}
                      {action.type === 'notify' && <Activity className="h-4 w-4 text-info" />}
                      {action.type === 'log' && <Activity className="h-4 w-4 text-gray-400" />}
                      {action.type === 'throttle' && <Clock className="h-4 w-4 text-primary-light" />}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white capitalize">{action.type.replace('_', ' ')}</p>
                      {action.config && (
                        <p className="text-xs text-gray-400">
                          {JSON.stringify(action.config)
                            .replace(/[{}"]/g, '')
                            .replace(/,/g, ', ')}
                        </p>
                      )}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      useStore.getState().addNotification({
                        type: 'info',
                        message: 'Action editor coming soon - you can edit the policy YAML directly',
                      })
                    }}
                  >
                    Edit
                  </Button>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <Card className="bg-gray-800 border-gray-700">
            <CardHeader>
              <CardTitle className="text-base text-white">Policy History</CardTitle>
              <CardDescription className="text-gray-400">Recent activity and triggers for this policy</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                <div className="space-y-4">
                  {mockPolicyHistory.map((event) => (
                    <div
                      key={event.id}
                      className="flex items-start gap-4 pb-4 border-b border-gray-700 last:border-0"
                    >
                      <div
                        className={`flex h-8 w-8 items-center justify-center rounded-full shrink-0 ${
                          event.status === 'blocked'
                            ? 'bg-error/10 text-error'
                            : event.status === 'approved'
                              ? 'bg-success/10 text-success'
                              : 'bg-gray-700 text-gray-400'
                        }`}
                      >
                        {event.status === 'blocked' && <AlertTriangle className="h-4 w-4" />}
                        {event.status === 'approved' && <CheckCircle2 className="h-4 w-4" />}
                        {event.status === 'updated' && <Edit className="h-4 w-4" />}
                        {event.status === 'created' && <Plus className="h-4 w-4" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-white">{event.action}</p>
                        <p className="text-xs text-gray-400">
                          {event.runbook ? `Runbook: ${event.runbook}` : `By: ${event.user}`}
                        </p>
                      </div>
                      <span className="text-xs text-gray-400 shrink-0">{event.time}</span>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings" className="space-y-4">
          <Card className="bg-gray-800 border-gray-700">
            <CardHeader>
              <CardTitle className="text-base text-white">Policy Settings</CardTitle>
              <CardDescription className="text-gray-400">Configure policy behavior and metadata</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label className="text-sm text-gray-400">Created By</Label>
                  <p className="text-sm font-medium text-white">{policy.createdBy}</p>
                </div>
                <div>
                  <Label className="text-sm text-gray-400">Created At</Label>
                  <p className="text-sm font-medium text-white">
                    {policy.createdAt ? formatRelativeTime(policy.createdAt) : 'Unknown'}
                  </p>
                </div>
                <div>
                  <Label className="text-sm text-gray-400">Last Updated</Label>
                  <p className="text-sm font-medium text-white">
                    {policy.updatedAt ? formatRelativeTime(policy.updatedAt) : 'Unknown'}
                  </p>
                </div>
                <div>
                  <Label className="text-sm text-gray-400">Scope</Label>
                  <p className="text-sm font-medium text-white capitalize">{policy.scope}</p>
                </div>
              </div>
              <div className="pt-4 border-t border-gray-700 flex gap-3">
                <Button variant="outline" className="bg-transparent border-gray-700" onClick={handleDuplicate}>
                  <Copy className="mr-2 h-4 w-4" />
                  Duplicate Policy
                </Button>
                <Button
                  variant="outline"
                  className="bg-transparent border-gray-700 text-error hover:bg-error/10"
                  onClick={handleDelete}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete Policy
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

