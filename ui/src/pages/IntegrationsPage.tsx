import { useState } from 'react'
import {
  Plus,
  Search,
  Plug,
  Github,
  Bell,
  Cloud,
  MessageSquare,
  Activity,
  Clipboard,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Settings,
  Trash2,
} from 'lucide-react'
import { Card, CardContent } from '../components/ui/Card'
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
import { mockIntegrations, type Integration } from '../lib/mock-data'
import { useStore } from '../store/useStore'

const integrationIcons: Record<string, typeof Github> = {
  github: Github,
  bell: Bell,
  cloud: Cloud,
  'message-square': MessageSquare,
  activity: Activity,
  clipboard: Clipboard,
}

const statusConfig = {
  connected: { icon: CheckCircle2, color: 'text-success', bg: 'bg-success/10' },
  disconnected: { icon: XCircle, color: 'text-gray-400', bg: 'bg-gray-700' },
  error: { icon: AlertTriangle, color: 'text-error', bg: 'bg-error/10' },
}

function IntegrationCard({ integration }: { integration: Integration }) {
  const Icon = integrationIcons[integration.icon] || Plug
  const status = statusConfig[integration.status]
  const StatusIcon = status.icon

  const handleConfigure = async () => {
    try {
      const { integrationsApi } = await import('../lib/api')
      await integrationsApi.configure(integration.id, {})
      useStore.getState().addNotification({
        type: 'success',
        message: `${integration.name} configuration updated`,
      })
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'info',
        message: `Configure ${integration.name} (mock mode)`,
      })
    }
  }

  const handleSync = async () => {
    try {
      const { integrationsApi } = await import('../lib/api')
      await integrationsApi.sync(integration.id)
      // Update last sync time
      setIntegrations((prev) =>
        prev.map((i) =>
          i.id === integration.id ? { ...i, lastSync: new Date().toLocaleString() } : i
        )
      )
      useStore.getState().addNotification({
        type: 'success',
        message: `Syncing ${integration.name}...`,
      })
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'info',
        message: `Syncing ${integration.name}... (mock mode)`,
      })
    }
  }

  const handleDisconnect = async () => {
    if (!confirm(`Are you sure you want to disconnect ${integration.name}?`)) return
    try {
      const { integrationsApi } = await import('../lib/api')
      await integrationsApi.disconnect(integration.id)
      setIntegrations((prev) => prev.filter((i) => i.id !== integration.id))
      useStore.getState().addNotification({
        type: 'success',
        message: `${integration.name} disconnected successfully`,
      })
    } catch (err: any) {
      setIntegrations((prev) => prev.filter((i) => i.id !== integration.id))
      useStore.getState().addNotification({
        type: 'success',
        message: `${integration.name} disconnected successfully`,
      })
    }
  }

  return (
    <Card className="group hover:border-primary/50 transition-colors bg-gray-800 border-gray-700">
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className={`flex h-12 w-12 items-center justify-center rounded-lg ${status.bg}`}>
              <Icon className={`h-6 w-6 ${status.color}`} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-medium text-white">{integration.name}</h3>
                <Badge
                  variant="outline"
                  className={`capitalize ${
                    integration.status === 'connected'
                      ? 'bg-success/10 text-success border-success/20'
                      : integration.status === 'error'
                        ? 'bg-error/10 text-error border-error/20'
                        : 'bg-gray-700 text-gray-400 border-gray-600'
                  }`}
                >
                  <StatusIcon className="mr-1 h-3 w-3" />
                  {integration.status}
                </Badge>
              </div>
              <p className="text-sm text-gray-400">{integration.type}</p>
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100">
                <Settings className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={handleConfigure}>
                <Settings className="mr-2 h-4 w-4" />
                Configure
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleSync}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Sync Now
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-error" onClick={handleDisconnect}>
                <Trash2 className="mr-2 h-4 w-4" />
                Disconnect
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        {integration.lastSync && (
          <p className="text-xs text-gray-400 mt-4">Last synced: {integration.lastSync}</p>
        )}
      </CardContent>
    </Card>
  )
}

const availableIntegrations = [
  { name: 'Kubernetes', type: 'Container Orchestration', icon: Cloud },
  { name: 'Terraform', type: 'Infrastructure as Code', icon: Cloud },
  { name: 'ServiceNow', type: 'ITSM', icon: Clipboard },
  { name: 'Splunk', type: 'Log Management', icon: Activity },
  { name: 'New Relic', type: 'APM', icon: Activity },
  { name: 'OpsGenie', type: 'Incident Management', icon: Bell },
]

export function IntegrationsPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [integrations, setIntegrations] = useState<Integration[]>(mockIntegrations)

  const filteredIntegrations = integrations.filter((integration) => {
    const matchesSearch =
      integration.name.toLowerCase().includes(search.toLowerCase()) ||
      integration.type.toLowerCase().includes(search.toLowerCase())
    const matchesStatus = statusFilter === 'all' || integration.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const stats = {
    total: integrations.length,
    connected: integrations.filter((i) => i.status === 'connected').length,
    errors: integrations.filter((i) => i.status === 'error').length,
  }

  const handleAddIntegration = async () => {
    try {
      const { integrationsApi } = await import('../lib/api')
      useStore.getState().addNotification({
        type: 'info',
        message: 'Integration setup wizard coming soon - you can configure integrations via API keys',
      })
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'info',
        message: 'Add integration functionality coming soon',
      })
    }
  }

  const handleConnect = async (integrationName: string) => {
    try {
      const { integrationsApi } = await import('../lib/api')
      const result = await integrationsApi.connect(integrationName, {})
      setIntegrations([...integrations, result])
      useStore.getState().addNotification({
        type: 'success',
        message: `Successfully connected to ${integrationName}`,
      })
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'info',
        message: `Connecting to ${integrationName}... (mock mode)`,
      })
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Integrations</h1>
          <p className="text-gray-400">Connect your tools and services</p>
        </div>
        <Button onClick={handleAddIntegration}>
          <Plus className="mr-2 h-4 w-4" />
          Add Integration
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary-light">
                <Plug className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{stats.total}</p>
                <p className="text-xs text-gray-400">Total Integrations</p>
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
                <p className="text-2xl font-bold text-white">{stats.connected}</p>
                <p className="text-xs text-gray-400">Connected</p>
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
                <p className="text-2xl font-bold text-white">{stats.errors}</p>
                <p className="text-xs text-gray-400">Needs Attention</p>
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
            placeholder="Search integrations..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 bg-gray-800 border-gray-700"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[140px] bg-gray-800 border-gray-700">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="connected">Connected</SelectItem>
            <SelectItem value="disconnected">Disconnected</SelectItem>
            <SelectItem value="error">Error</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Connected Integrations */}
      <div className="space-y-4">
        <h2 className="text-lg font-medium text-white">Connected Integrations</h2>
        {filteredIntegrations.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredIntegrations.map((integration) => (
              <IntegrationCard key={integration.id} integration={integration} />
            ))}
          </div>
        ) : (
          <Card className="bg-gray-800 border-gray-700">
            <CardContent className="p-8 text-center">
              <p className="text-gray-400">No integrations found matching your filters</p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Available Integrations */}
      <div className="space-y-4">
        <h2 className="text-lg font-medium text-white">Available Integrations</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {availableIntegrations.map((integration, index) => (
            <Card key={index} className="hover:border-primary/50 transition-colors bg-gray-800 border-gray-700">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-gray-700">
                      <integration.icon className="h-6 w-6 text-gray-400" />
                    </div>
                    <div>
                      <h3 className="font-medium text-white">{integration.name}</h3>
                      <p className="text-sm text-gray-400">{integration.type}</p>
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="bg-transparent border-gray-700"
                    onClick={() => handleConnect(integration.name)}
                  >
                    Connect
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}
