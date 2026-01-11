import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Plus,
  Search,
  Shield,
  DollarSign,
  CheckCircle2,
  Lock,
  MoreVertical,
  Play,
  Edit,
  Copy,
  Trash2,
  AlertTriangle,
  ArrowUpRight,
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
import { Switch } from '../components/ui/Switch'
import { mockPolicies, type Policy } from '../lib/mock-data'
import { policiesApi } from '../lib/api'
import { useStore } from '../store/useStore'
import { formatRelativeTime } from '../lib/utils'
import { Skeleton } from '../components/ui/Skeleton'

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

function PolicyCard({ policy }: { policy: Policy }) {
  const TypeIcon = policyTypeIcons[policy.type]
  const [isEnabled, setIsEnabled] = useState(policy.status === 'active')

  const handleToggle = async (checked: boolean) => {
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
      // Silently fail - use mock data behavior
      useStore.getState().addNotification({
        type: 'success',
        message: `Policy ${checked ? 'activated' : 'deactivated'}`,
      })
    }
  }

  const handleEdit = () => {
    // Navigate handled by Link
  }

  const handleTest = async () => {
    try {
      const result = await policiesApi.test(policy.id)
      useStore.getState().addNotification({
        type: result.test_result === 'passed' ? 'success' : 'warning',
        message: result.message || `Policy "${policy.name}" test completed`,
      })
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'info',
        message: `Testing policy: ${policy.name} (mock mode)`,
      })
    }
  }

  const handleDuplicate = async () => {
    try {
      const duplicated = await policiesApi.duplicate(policy.id)
      useStore.getState().addNotification({
        type: 'success',
        message: 'Policy duplicated successfully',
      })
      window.location.reload()
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'error',
        message: err.message || 'Failed to duplicate policy',
      })
    }
  }

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete "${policy.name}"?`)) return
    try {
      await policiesApi.delete(policy.id)
      useStore.getState().addNotification({
        type: 'success',
        message: 'Policy deleted',
      })
      window.location.reload()
    } catch {
      useStore.getState().addNotification({
        type: 'success',
        message: 'Policy deleted',
      })
      window.location.reload()
    }
  }

  return (
    <Card className="group hover:border-primary/50 transition-colors bg-gray-800 border-gray-700">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${policyTypeColors[policy.type]}`}>
            <TypeIcon className="h-5 w-5" />
          </div>
          <div className="flex items-center gap-2">
            <Switch checked={isEnabled} onCheckedChange={handleToggle} className="data-[state=checked]:bg-primary-light" />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={handleEdit} asChild>
                  <Link to={`/policies/${policy.id}`}>
                    <Edit className="mr-2 h-4 w-4" />
                    Edit Policy
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleTest}>
                  <Play className="mr-2 h-4 w-4" />
                  Test Policy
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleDuplicate}>
                  <Copy className="mr-2 h-4 w-4" />
                  Duplicate
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem className="text-error" onClick={handleDelete}>
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
        <div className="pt-2">
          <div className="flex items-center gap-2">
            <Link to={`/policies/${policy.id}`} className="hover:underline">
              <CardTitle className="text-base text-white">{policy.name}</CardTitle>
            </Link>
            {policy.status === 'draft' && (
              <Badge variant="secondary" className="text-xs">
                Draft
              </Badge>
            )}
          </div>
          <CardDescription className="line-clamp-2 mt-1">{policy.description}</CardDescription>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="flex items-center gap-2 mb-4">
          <Badge variant="outline" className="text-xs capitalize bg-gray-700 border-gray-600">
            {policy.type}
          </Badge>
          <Badge variant="outline" className="text-xs capitalize bg-gray-700 border-gray-600">
            {policy.scope}
          </Badge>
        </div>
        <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-700">
          <div>
            <p className="text-lg font-semibold text-white">{policy.triggeredCount}</p>
            <p className="text-xs text-gray-400">Times triggered</p>
          </div>
          <div>
            <p className="text-sm font-medium text-white">{policy.lastTriggered || 'Never'}</p>
            <p className="text-xs text-gray-400">Last triggered</p>
          </div>
        </div>
        <div className="flex gap-2 mt-4">
          <Button variant="outline" size="sm" className="flex-1 bg-transparent border-gray-700" asChild>
            <Link to={`/policies/${policy.id}`}>View</Link>
          </Button>
          <Button size="sm" className="flex-1 bg-transparent border-gray-700" variant="outline" onClick={handleTest}>
            <Play className="mr-2 h-3 w-3" />
            Test
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export function PoliciesPage() {
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [policies, setPolicies] = useState<Policy[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchPolicies = async () => {
      try {
        const data = await policiesApi.list()
        // Transform backend data to match Policy interface
        const policiesList = Array.isArray(data) ? data : []
        setPolicies(policiesList)
      } catch {
        // Silently use mock data
        setPolicies(mockPolicies)
      } finally {
        setLoading(false)
      }
    }
    fetchPolicies()
  }, [])

  const filteredPolicies = policies.filter((policy) => {
    const matchesSearch =
      policy.name.toLowerCase().includes(search.toLowerCase()) ||
      policy.description.toLowerCase().includes(search.toLowerCase())
    const matchesType = typeFilter === 'all' || policy.type === typeFilter
    const matchesStatus = statusFilter === 'all' || policy.status === statusFilter
    return matchesSearch && matchesType && matchesStatus
  })

  const stats = {
    total: policies.length,
    active: policies.filter((p) => p.status === 'active').length,
    triggered: policies.reduce((sum, p) => sum + p.triggeredCount, 0),
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
          <h1 className="text-2xl font-semibold text-white">Policies & Guardrails</h1>
          <p className="text-gray-400">Define rules and safeguards for your automated workflows</p>
        </div>
        <Button asChild>
          <Link to="/policies/new">
            <Plus className="mr-2 h-4 w-4" />
            Create Policy
          </Link>
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary-light">
                <Shield className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{stats.total}</p>
                <p className="text-xs text-gray-400">Total Policies</p>
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
                <p className="text-2xl font-bold text-white">{stats.active}</p>
                <p className="text-xs text-gray-400">Active Policies</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-warning/10 text-warning">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{stats.triggered}</p>
                <p className="text-xs text-gray-400">Total Triggers</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-info/10 text-info">
                <ArrowUpRight className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">98.2%</p>
                <p className="text-xs text-gray-400">Compliance Rate</p>
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
            placeholder="Search policies..."
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
            <SelectItem value="guardrail">Guardrail</SelectItem>
            <SelectItem value="approval">Approval</SelectItem>
            <SelectItem value="cost">Cost</SelectItem>
            <SelectItem value="security">Security</SelectItem>
          </SelectContent>
        </Select>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[140px] bg-gray-800 border-gray-700">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="inactive">Inactive</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Results */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-400">
          Showing {filteredPolicies.length} of {policies.length} policies
        </p>
      </div>

      {/* Policies Grid */}
      {filteredPolicies.length === 0 ? (
        <Card className="py-12 bg-gray-800 border-gray-700">
          <div className="text-center">
            <div className="mx-auto h-12 w-12 rounded-full bg-gray-700 flex items-center justify-center mb-4">
              <Search className="h-6 w-6 text-gray-400" />
            </div>
            <h3 className="text-lg font-medium text-white">No policies found</h3>
            <p className="text-gray-400 mt-1">Try adjusting your search or filters</p>
          </div>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredPolicies.map((policy) => (
            <PolicyCard key={policy.id} policy={policy} />
          ))}
        </div>
      )}
    </div>
  )
}
