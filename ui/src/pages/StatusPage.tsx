import { useState, useEffect } from 'react'
import { CheckCircle, XCircle, AlertTriangle, Activity } from 'lucide-react'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { healthApi } from '../lib/api'
import { formatRelativeTime } from '../lib/utils'

const services = [
  { name: 'API Server', status: 'operational', uptime: '99.9%', latency: '12ms' },
  { name: 'Database', status: 'operational', uptime: '99.95%', latency: '5ms' },
  { name: 'Temporal', status: 'operational', uptime: '99.8%', latency: '8ms' },
  { name: 'Log Aggregator', status: 'degraded', uptime: '98.5%', latency: '45ms' },
  { name: 'GitHub Adapter', status: 'operational', uptime: '99.9%', latency: '120ms' },
  { name: 'Kubernetes Adapter', status: 'operational', uptime: '99.9%', latency: '85ms' },
]

export function StatusPage() {
  const [overallStatus, setOverallStatus] = useState<'operational' | 'degraded' | 'down'>('operational')
  const [lastCheck, setLastCheck] = useState<Date>(new Date())

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await healthApi.check()
        setOverallStatus('operational')
      } catch {
        setOverallStatus('down')
      }
      setLastCheck(new Date())
    }
    checkHealth()
    const interval = setInterval(checkHealth, 30000) // Every 30s
    return () => clearInterval(interval)
  }, [])

  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'operational':
        return 'success'
      case 'degraded':
        return 'warning'
      case 'down':
        return 'error'
      default:
        return 'neutral'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'operational':
        return <CheckCircle className="w-5 h-5 text-success" />
      case 'degraded':
        return <AlertTriangle className="w-5 h-5 text-warning" />
      case 'down':
        return <XCircle className="w-5 h-5 text-error" />
      default:
        return <Activity className="w-5 h-5 text-gray-400" />
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-100 mb-2">System Status</h1>
        <p className="text-gray-400">Real-time status of all platform services</p>
      </div>

      {/* Overall Status Banner */}
      <Card>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {getStatusIcon(overallStatus)}
            <div>
              <h2 className="text-xl font-semibold text-gray-100">
                {overallStatus === 'operational'
                  ? 'All Systems Operational'
                  : overallStatus === 'degraded'
                  ? 'Some Services Degraded'
                  : 'System Outage'}
              </h2>
              <p className="text-sm text-gray-400">
                Last updated: {formatRelativeTime(lastCheck.toISOString())}
              </p>
            </div>
          </div>
          <Badge variant={getStatusVariant(overallStatus)} size="lg" pulse={overallStatus !== 'operational'}>
            {overallStatus}
          </Badge>
        </div>
      </Card>

      {/* Service Status Table */}
      <Card header={<h2 className="text-lg font-semibold text-gray-100">Service Status</h2>}>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-300">Service</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-300">Status</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-300">Uptime</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-300">Latency</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-300">Last Incident</th>
              </tr>
            </thead>
            <tbody>
              {services.map((service) => (
                <tr
                  key={service.name}
                  className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors"
                >
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-3">
                      {getStatusIcon(service.status)}
                      <span className="font-medium text-gray-100">{service.name}</span>
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <Badge variant={getStatusVariant(service.status)} size="sm">
                      {service.status}
                    </Badge>
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-400">{service.uptime}</td>
                  <td className="py-3 px-4 text-sm text-gray-400">{service.latency}</td>
                  <td className="py-3 px-4 text-sm text-gray-400">
                    {service.status === 'operational' ? 'None' : '2 hours ago'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Incident History */}
      <Card header={<h2 className="text-lg font-semibold text-gray-100">Recent Incidents</h2>}>
        <div className="space-y-3">
          <div className="p-4 bg-gray-900 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-warning" />
                <span className="font-medium text-gray-100">Increased API Latency</span>
              </div>
              <Badge variant="warning" size="sm">
                Resolved
              </Badge>
            </div>
            <p className="text-sm text-gray-400 mb-2">
              API response times were elevated for approximately 15 minutes. Root cause was identified
              and resolved.
            </p>
            <div className="text-xs text-gray-500">
              Started: 2 hours ago • Resolved: 1 hour ago
            </div>
          </div>
        </div>
      </Card>
    </div>
  )
}

