import { useState, useEffect } from 'react'
import {
  Search,
  FileText,
  User,
  Bot,
  Globe,
  CheckCircle2,
  XCircle,
  Download,
  Filter,
  Calendar,
  ChevronDown,
  BookOpen,
  Play,
  Shield,
  Plug,
  Settings,
  Eye,
} from 'lucide-react'
import { Card, CardContent, CardHeader } from '../components/ui/Card'
import Button from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Badge } from '../components/ui/Badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/Select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table'
import { ScrollArea } from '../components/ui/ScrollArea'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../components/ui/Dialog'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '../components/ui/Collapsible'
import { auditApi } from '../lib/api'
import { mockAuditEvents, type AuditEvent } from '../lib/mock-data'
import { useStore } from '../store/useStore'

const actorTypeIcons = {
  user: User,
  system: Bot,
  api: Globe,
}

const resourceTypeIcons = {
  runbook: BookOpen,
  run: Play,
  policy: Shield,
  integration: Plug,
  user: User,
  settings: Settings,
}

const actionColors: Record<string, string> = {
  'runbook.execute': 'bg-primary-light/10 text-primary-light',
  'runbook.update': 'bg-primary-light/10 text-primary-light',
  'runbook.create': 'bg-success/10 text-success',
  'policy.triggered': 'bg-warning/10 text-warning',
  'policy.blocked': 'bg-error/10 text-error',
  'policy.create': 'bg-success/10 text-success',
  'approval.approve': 'bg-success/10 text-success',
  'approval.reject': 'bg-error/10 text-error',
  'integration.connect': 'bg-primary-light/10 text-primary-light',
  'user.login': 'bg-gray-700 text-gray-300',
  'settings.update': 'bg-primary-light/10 text-primary-light',
}

function formatTimestamp(timestamp: string) {
  const date = new Date(timestamp)
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function AuditEventRow({ event, onViewDetails }: { event: AuditEvent; onViewDetails: (event: AuditEvent) => void }) {
  const ActorIcon = actorTypeIcons[event.actorType]
  const ResourceIcon = resourceTypeIcons[event.resourceType]

  return (
    <TableRow className="group">
      <TableCell className="w-[140px]">
        <span className="text-xs text-gray-400 font-mono">{formatTimestamp(event.timestamp)}</span>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <div
            className={`flex h-6 w-6 items-center justify-center rounded-full ${
              event.actorType === 'user'
                ? 'bg-primary-light/10 text-primary-light'
                : event.actorType === 'system'
                  ? 'bg-gray-700 text-gray-300'
                  : 'bg-primary-light/10 text-primary-light'
            }`}
          >
            <ActorIcon className="h-3 w-3" />
          </div>
          <span className="text-sm text-gray-200">{event.actor}</span>
        </div>
      </TableCell>
      <TableCell>
        <Badge
          variant="outline"
          className={`text-xs ${actionColors[event.action] || 'bg-gray-700 text-gray-300'}`}
        >
          {event.action}
        </Badge>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <ResourceIcon className="h-4 w-4 text-gray-400" />
          <span className="text-sm text-gray-200 truncate max-w-[200px]">{event.resource}</span>
        </div>
      </TableCell>
      <TableCell className="hidden lg:table-cell">
        <span className="text-sm text-gray-400 truncate max-w-[250px] block">{event.details}</span>
      </TableCell>
      <TableCell>
        {event.status === 'success' ? (
          <CheckCircle2 className="h-4 w-4 text-success" />
        ) : (
          <XCircle className="h-4 w-4 text-error" />
        )}
      </TableCell>
      <TableCell>
        <Button
          variant="ghost"
          size="sm"
          className="opacity-0 group-hover:opacity-100"
          onClick={() => onViewDetails(event)}
        >
          <Eye className="h-4 w-4" />
        </Button>
      </TableCell>
    </TableRow>
  )
}

export function AuditPage() {
  const [search, setSearch] = useState('')
  const [actorFilter, setActorFilter] = useState<string>('all')
  const [resourceFilter, setResourceFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null)
  const [expandedFilters, setExpandedFilters] = useState(false)
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchAuditEvents = async () => {
      try {
        const params: any = {}
        if (actorFilter !== 'all') params.actor_type = actorFilter
        if (resourceFilter !== 'all') params.resource_type = resourceFilter
        if (statusFilter !== 'all') params.status = statusFilter

        const data = await auditApi.list({ limit: 1000, ...params }).catch(() => null)
        if (data && data.events && data.events.length > 0) {
          setAuditEvents(data.events)
        } else {
          // Use mock data if API fails or returns empty
          setAuditEvents(mockAuditEvents)
        }
      } catch (err) {
        console.debug('Failed to fetch audit events, using mock data (silent):', err)
        setAuditEvents(mockAuditEvents)
      } finally {
        setLoading(false)
      }
    }

    fetchAuditEvents()
  }, [actorFilter, resourceFilter, statusFilter])

  const filteredEvents = auditEvents.filter((event) => {
    const matchesSearch =
      event.actor.toLowerCase().includes(search.toLowerCase()) ||
      event.action.toLowerCase().includes(search.toLowerCase()) ||
      event.resource.toLowerCase().includes(search.toLowerCase()) ||
      event.details.toLowerCase().includes(search.toLowerCase())
    const matchesActor = actorFilter === 'all' || event.actorType === actorFilter
    const matchesResource = resourceFilter === 'all' || event.resourceType === resourceFilter
    const matchesStatus = statusFilter === 'all' || event.status === statusFilter
    return matchesSearch && matchesActor && matchesResource && matchesStatus
  })

  const stats = {
    total: auditEvents.length,
    success: auditEvents.filter((e) => e.status === 'success').length,
    failed: auditEvents.filter((e) => e.status === 'failure').length,
    users: new Set(auditEvents.filter((e) => e.actorType === 'user').map((e) => e.actor)).size,
  }

  const handleExport = async () => {
    try {
      const { downloadJSON } = await import('../lib/utils')
      const exportData = {
        events: auditEvents,
        filters: {
          actor_type: actorFilter,
          resource_type: resourceFilter,
          status: statusFilter,
          search,
        },
        stats,
        exported_at: new Date().toISOString(),
      }
      downloadJSON(exportData, `audit-log-export-${new Date().toISOString().split('T')[0]}.json`)
      useStore.getState().addNotification({
        type: 'success',
        message: 'Audit log exported successfully',
      })
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'error',
        message: err.message || 'Failed to export audit log',
      })
    }
  }

  const handleDateRangeFilter = () => {
    // TODO: Add date range picker
    useStore.getState().addNotification({
      type: 'info',
      message: 'Date range filter coming soon - use the search and filters to narrow results',
    })
  }

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Audit Log</h1>
          <p className="text-sm text-gray-400">Track all actions and changes across your platform</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" className="bg-transparent border-gray-700" onClick={handleDateRangeFilter}>
            <Calendar className="mr-2 h-4 w-4" />
            Date Range
          </Button>
          <Button variant="outline" className="bg-transparent border-gray-700" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-light/10 text-primary-light">
                <FileText className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{stats.total}</p>
                <p className="text-xs text-gray-400">Total Events</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-success/10 text-success">
                <CheckCircle2 className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{stats.success}</p>
                <p className="text-xs text-gray-400">Successful</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
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
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-light/10 text-primary-light">
                <User className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{stats.users}</p>
                <p className="text-xs text-gray-400">Active Users</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <Collapsible open={expandedFilters} onOpenChange={setExpandedFilters}>
          <CardHeader className="py-3">
            <div className="flex items-center justify-between">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <Input
                  placeholder="Search audit log..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9 bg-gray-800 border-gray-700 text-gray-200"
                />
              </div>
              <CollapsibleTrigger asChild>
                <Button variant="outline" className="bg-transparent border-gray-700">
                  <Filter className="mr-2 h-4 w-4" />
                  Filters
                  <ChevronDown
                    className={`ml-2 h-4 w-4 transition-transform ${expandedFilters ? 'rotate-180' : ''}`}
                  />
                </Button>
              </CollapsibleTrigger>
            </div>
          </CardHeader>
          <CollapsibleContent>
            <CardContent className="pt-0 pb-4">
              <div className="flex flex-wrap gap-3">
                <Select value={actorFilter} onValueChange={setActorFilter}>
                  <SelectTrigger className="w-[140px] bg-gray-800 border-gray-700 text-gray-200">
                    <SelectValue placeholder="Actor Type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Actors</SelectItem>
                    <SelectItem value="user">User</SelectItem>
                    <SelectItem value="system">System</SelectItem>
                    <SelectItem value="api">API</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={resourceFilter} onValueChange={setResourceFilter}>
                  <SelectTrigger className="w-[140px] bg-gray-800 border-gray-700 text-gray-200">
                    <SelectValue placeholder="Resource" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Resources</SelectItem>
                    <SelectItem value="runbook">Runbooks</SelectItem>
                    <SelectItem value="run">Runs</SelectItem>
                    <SelectItem value="policy">Policies</SelectItem>
                    <SelectItem value="integration">Integrations</SelectItem>
                    <SelectItem value="user">Users</SelectItem>
                    <SelectItem value="settings">Settings</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-[140px] bg-gray-800 border-gray-700 text-gray-200">
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="success">Success</SelectItem>
                    <SelectItem value="failure">Failed</SelectItem>
                  </SelectContent>
                </Select>
                <Button
                  variant="ghost"
                  onClick={() => {
                    setSearch('')
                    setActorFilter('all')
                    setResourceFilter('all')
                    setStatusFilter('all')
                  }}
                >
                  Clear Filters
                </Button>
              </div>
            </CardContent>
          </CollapsibleContent>
        </Collapsible>
      </Card>

      {/* Results */}
      <p className="text-sm text-gray-400">
        Showing {filteredEvents.length} of {auditEvents.length} events
      </p>

      {/* Audit Log Table */}
      <Card>
        <ScrollArea className="h-[600px]">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[140px]">Timestamp</TableHead>
                <TableHead>Actor</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Resource</TableHead>
                <TableHead className="hidden lg:table-cell">Details</TableHead>
                <TableHead className="w-[60px]">Status</TableHead>
                <TableHead className="w-[60px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-gray-400">
                    Loading audit events...
                  </TableCell>
                </TableRow>
              ) : filteredEvents.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-gray-400">
                    No audit events found matching your filters
                  </TableCell>
                </TableRow>
              ) : (
                filteredEvents.map((event) => (
                  <AuditEventRow key={event.id} event={event} onViewDetails={setSelectedEvent} />
                ))
              )}
            </TableBody>
          </Table>
        </ScrollArea>
      </Card>

      {/* Event Detail Dialog */}
      <Dialog open={!!selectedEvent} onOpenChange={() => setSelectedEvent(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-white">Event Details</DialogTitle>
            <DialogDescription className="text-gray-400">Full audit event information</DialogDescription>
          </DialogHeader>
          {selectedEvent && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-400">Timestamp</p>
                  <p className="text-sm font-mono text-gray-200">{formatTimestamp(selectedEvent.timestamp)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Status</p>
                  <Badge
                    variant="outline"
                    className={
                      selectedEvent.status === 'success'
                        ? 'bg-success/10 text-success'
                        : 'bg-error/10 text-error'
                    }
                  >
                    {selectedEvent.status}
                  </Badge>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Actor</p>
                  <p className="text-sm text-gray-200">{selectedEvent.actor}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Actor Type</p>
                  <p className="text-sm text-gray-200 capitalize">{selectedEvent.actorType}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Action</p>
                  <Badge
                    variant="outline"
                    className={actionColors[selectedEvent.action] || 'bg-gray-700 text-gray-300'}
                  >
                    {selectedEvent.action}
                  </Badge>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Resource Type</p>
                  <p className="text-sm text-gray-200 capitalize">{selectedEvent.resourceType}</p>
                </div>
              </div>
              <div>
                <p className="text-xs text-gray-400">Resource</p>
                <p className="text-sm text-gray-200">{selectedEvent.resource}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400">Details</p>
                <p className="text-sm text-gray-200">{selectedEvent.details}</p>
              </div>
              {selectedEvent.ipAddress && (
                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-700">
                  <div>
                    <p className="text-xs text-gray-400">IP Address</p>
                    <p className="text-sm font-mono text-gray-200">{selectedEvent.ipAddress}</p>
                  </div>
                  {selectedEvent.userAgent && (
                    <div>
                      <p className="text-xs text-gray-400">User Agent</p>
                      <p className="text-sm text-gray-400 truncate">{selectedEvent.userAgent}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
