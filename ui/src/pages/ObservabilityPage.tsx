import { useState, useEffect } from 'react'
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Clock,
  Zap,
  Activity,
  CheckCircle2,
  XCircle,
  Calendar,
  Download,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import Button from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/Tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/Select'
import { Progress } from '../components/ui/Progress'
import { AnalyticsCharts } from '../components/Analytics/AnalyticsCharts'
import { analyticsApi } from '../lib/api'
import { useStore } from '../store/useStore'

export function ObservabilityPage() {
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d' | '90d'>('7d')
  const [metrics, setMetrics] = useState<any>(null)
  const [runsData, setRunsData] = useState<any[]>([])
  const [costData, setCostData] = useState<any[]>([])
  const [latencyData, setLatencyData] = useState<any[]>([])
  const [topRunbooks, setTopRunbooks] = useState<any[]>([])
  // Default mock data
  const defaultCostBreakdown = [
    { category: 'LLM Tokens', value: 156.34, percentage: 55 },
    { category: 'Tool Executions', value: 78.45, percentage: 28 },
    { category: 'External APIs', value: 34.12, percentage: 12 },
    { category: 'Storage', value: 15.65, percentage: 5 },
  ]

  const defaultTopRunbooks = [
    { name: 'Incident Response - Database', runs: 312, successRate: 94.5, avgDuration: '4m 32s', cost: 89.45 },
    { name: 'Deploy to Production', runs: 245, successRate: 98.2, avgDuration: '12m 15s', cost: 67.23 },
    { name: 'Customer Onboarding', runs: 198, successRate: 99.1, avgDuration: '2m 45s', cost: 34.12 },
    { name: 'Infrastructure Scaling', runs: 156, successRate: 96.8, avgDuration: '1m 15s', cost: 28.9 },
    { name: 'Security Scan & Remediation', runs: 89, successRate: 91.3, avgDuration: '18m 22s', cost: 64.86 },
  ]

  const [costBreakdown, setCostBreakdown] = useState<any[]>(defaultCostBreakdown)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [metricsRes, runsRes, costRes, latencyRes, topRunbooksRes, costBreakdownRes] = await Promise.all([
          analyticsApi.getMetrics(timeRange).catch(() => null),
          analyticsApi.getRunsData(timeRange).catch(() => []),
          analyticsApi.getCostData(timeRange).catch(() => []),
          analyticsApi.getLatencyData(timeRange).catch(() => []),
          analyticsApi.getTopRunbooks(timeRange, 5).catch(() => []),
          analyticsApi.getCostBreakdown(timeRange).catch(() => []),
        ])

        if (metricsRes) setMetrics(metricsRes)
        if (runsRes && runsRes.length > 0) setRunsData(runsRes)
        if (costRes && costRes.length > 0) setCostData(costRes)
        if (latencyRes && latencyRes.length > 0) setLatencyData(latencyRes)
        if (topRunbooksRes && topRunbooksRes.length > 0) {
          setTopRunbooks(topRunbooksRes)
        } else {
          setTopRunbooks(defaultTopRunbooks)
        }
        if (costBreakdownRes && costBreakdownRes.length > 0) {
          setCostBreakdown(costBreakdownRes)
        } else {
          setCostBreakdown(defaultCostBreakdown)
        }
      } catch (err) {
        console.debug('Failed to fetch analytics data (silent):', err)
        // Use default mock data
        setMetrics({
          totalRuns: { value: 1247, change: 12.5, trend: 'up' },
          successRate: { value: 96.8, change: 2.1, trend: 'up' },
          avgDuration: { value: '4m 12s', change: -15.3, trend: 'down' },
          totalCost: { value: 284.56, change: -8.2, trend: 'down' },
          timeSaved: { value: 142, change: 18.7, trend: 'up' },
          tokensUsed: { value: 2450000, change: 5.2, trend: 'up' },
        })
        setTopRunbooks(defaultTopRunbooks)
        setCostBreakdown(defaultCostBreakdown)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [timeRange])

  const handleExport = async () => {
    try {
      const { downloadJSON } = await import('../lib/utils')
      const exportData = {
        timeRange,
        metrics: mockMetrics,
        runsData,
        costData,
        latencyData,
        topRunbooks,
        costBreakdown,
        exported_at: new Date().toISOString(),
      }
      downloadJSON(exportData, `analytics-export-${timeRange}-${new Date().toISOString().split('T')[0]}.json`)
      useStore.getState().addNotification({
        type: 'success',
        message: 'Analytics data exported successfully',
      })
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'error',
        message: err.message || 'Failed to export analytics data',
      })
    }
  }

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <div className="h-8 w-48 bg-gray-800 rounded animate-pulse" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-32 bg-gray-800 rounded animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  const mockMetrics = metrics || {
    totalRuns: { value: 1247, change: 12.5, trend: 'up' },
    successRate: { value: 96.8, change: 2.1, trend: 'up' },
    avgDuration: { value: '4m 12s', change: -15.3, trend: 'down' },
    totalCost: { value: 284.56, change: -8.2, trend: 'down' },
    timeSaved: { value: 142, change: 18.7, trend: 'up' },
    tokensUsed: { value: 2450000, change: 5.2, trend: 'up' },
  }

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Analytics & ROI</h1>
          <p className="text-sm text-gray-400">Track performance, costs, and business impact</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={timeRange} onValueChange={(v) => setTimeRange(v as any)}>
            <SelectTrigger className="w-[140px] bg-gray-800 border-gray-700 text-gray-200">
              <Calendar className="mr-2 h-4 w-4" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="24h">Last 24 hours</SelectItem>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
              <SelectItem value="90d">Last 90 days</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" className="bg-transparent border-gray-700" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-gray-400">Total Runs</span>
              <Activity className="h-4 w-4 text-gray-400" />
            </div>
            <p className="text-2xl font-bold text-white">{mockMetrics.totalRuns.value.toLocaleString()}</p>
            <div className="flex items-center gap-1 mt-1">
              {mockMetrics.totalRuns.trend === 'up' ? (
                <TrendingUp className="h-3 w-3 text-success" />
              ) : (
                <TrendingDown className="h-3 w-3 text-error" />
              )}
              <span
                className={`text-xs ${mockMetrics.totalRuns.trend === 'up' ? 'text-success' : 'text-error'}`}
              >
                {mockMetrics.totalRuns.change > 0 ? '+' : ''}
                {mockMetrics.totalRuns.change}%
              </span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-gray-400">Success Rate</span>
              <CheckCircle2 className="h-4 w-4 text-success" />
            </div>
            <p className="text-2xl font-bold text-white">{mockMetrics.successRate.value}%</p>
            <div className="flex items-center gap-1 mt-1">
              <TrendingUp className="h-3 w-3 text-success" />
              <span className="text-xs text-success">
                +{mockMetrics.successRate.change > 0 ? '+' : ''}
                {mockMetrics.successRate.change}%
              </span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-gray-400">Avg Duration</span>
              <Clock className="h-4 w-4 text-gray-400" />
            </div>
            <p className="text-2xl font-bold text-white">{mockMetrics.avgDuration.value}</p>
            <div className="flex items-center gap-1 mt-1">
              <TrendingDown className="h-3 w-3 text-success" />
              <span className="text-xs text-success">{mockMetrics.avgDuration.change}%</span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-gray-400">Total Cost</span>
              <DollarSign className="h-4 w-4 text-gray-400" />
            </div>
            <p className="text-2xl font-bold text-white">${mockMetrics.totalCost.value}</p>
            <div className="flex items-center gap-1 mt-1">
              <TrendingDown className="h-3 w-3 text-success" />
              <span className="text-xs text-success">{mockMetrics.totalCost.change}%</span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-gray-400">Time Saved</span>
              <Zap className="h-4 w-4 text-warning" />
            </div>
            <p className="text-2xl font-bold text-white">{mockMetrics.timeSaved.value}h</p>
            <div className="flex items-center gap-1 mt-1">
              <TrendingUp className="h-3 w-3 text-success" />
              <span className="text-xs text-success">
                +{mockMetrics.timeSaved.change > 0 ? '+' : ''}
                {mockMetrics.timeSaved.change}%
              </span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-gray-400">Tokens Used</span>
              <BarChart3 className="h-4 w-4 text-gray-400" />
            </div>
            <p className="text-2xl font-bold text-white">{(mockMetrics.tokensUsed.value / 1000000).toFixed(1)}M</p>
            <div className="flex items-center gap-1 mt-1">
              <TrendingUp className="h-3 w-3 text-gray-400" />
              <span className="text-xs text-gray-400">
                +{mockMetrics.tokensUsed.change > 0 ? '+' : ''}
                {mockMetrics.tokensUsed.change}%
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="bg-gray-800 border-gray-700">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="cost">Cost Analysis</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="roi">ROI</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-3">
            {/* Charts */}
            <div className="lg:col-span-2">
              <AnalyticsCharts runsData={runsData} costData={costData} latencyData={latencyData} />
            </div>

            {/* Top Runbooks */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base text-white">Top Runbooks</CardTitle>
                <CardDescription className="text-gray-400">By execution count</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {topRunbooks.length === 0 ? (
                  <p className="text-sm text-gray-400 text-center py-4">No runbooks found</p>
                ) : (
                  topRunbooks.map((runbook, index) => (
                    <div key={index} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-white truncate max-w-[180px]">
                          {runbook.name}
                        </span>
                        <span className="text-sm text-gray-400">{runbook.runs}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Progress
                          value={(runbook.runs / (topRunbooks[0]?.runs || 1)) * 100}
                          className="h-1.5 flex-1"
                        />
                        <Badge
                          variant={
                            runbook.successRate >= 95
                              ? 'success'
                              : runbook.successRate >= 90
                                ? 'warning'
                                : 'error'
                          }
                          size="sm"
                        >
                          {runbook.successRate}%
                        </Badge>
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="cost" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            {/* Cost Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base text-white">Cost Breakdown</CardTitle>
                <CardDescription className="text-gray-400">Where your money is going</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {(costBreakdown.length === 0 ? defaultCostBreakdown : costBreakdown).map((item) => (
                  <div key={item.category} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-200">{item.category}</span>
                      <span className="text-sm font-medium text-white">${item.value.toFixed(2)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Progress value={item.percentage} className="h-2 flex-1" />
                      <span className="text-xs text-gray-400 w-8">{item.percentage}%</span>
                    </div>
                  </div>
                ))}
                <div className="pt-4 border-t border-gray-700">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-200">Total</span>
                    <span className="text-lg font-bold text-white">${mockMetrics.totalCost.value}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Cost by Runbook */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base text-white">Cost by Runbook</CardTitle>
                <CardDescription className="text-gray-400">Top spending workflows</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {(topRunbooks.length === 0 ? defaultTopRunbooks : topRunbooks).map((runbook, index) => (
                  <div key={index} className="flex items-center justify-between p-3 rounded-lg bg-gray-800">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white truncate">{runbook.name}</p>
                      <p className="text-xs text-gray-400">{runbook.runs} runs</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold text-white">${runbook.cost.toFixed(2)}</p>
                      <p className="text-xs text-gray-400">${(runbook.cost / runbook.runs).toFixed(3)}/run</p>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            {/* Latency Distribution */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base text-white">Response Time Distribution</CardTitle>
                <CardDescription className="text-gray-400">Execution time percentiles</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {[
                  { percentile: 'p50', value: '2m 15s', description: '50% of runs complete within' },
                  { percentile: 'p75', value: '4m 32s', description: '75% of runs complete within' },
                  { percentile: 'p90', value: '8m 45s', description: '90% of runs complete within' },
                  { percentile: 'p99', value: '15m 20s', description: '99% of runs complete within' },
                ].map((item) => (
                  <div key={item.percentile} className="flex items-center justify-between p-3 rounded-lg bg-gray-800">
                    <div>
                      <Badge variant="neutral" size="sm" className="font-mono">
                        {item.percentile}
                      </Badge>
                      <p className="text-xs text-gray-400 mt-1">{item.description}</p>
                    </div>
                    <p className="text-lg font-bold text-white">{item.value}</p>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Error Rate */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base text-white">Error Analysis</CardTitle>
                <CardDescription className="text-gray-400">Common failure reasons</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {[
                  { reason: 'Timeout exceeded', count: 12, percentage: 30 },
                  { reason: 'API rate limit', count: 8, percentage: 20 },
                  { reason: 'Invalid response', count: 7, percentage: 17.5 },
                  { reason: 'Authentication failed', count: 5, percentage: 12.5 },
                  { reason: 'Resource not found', count: 4, percentage: 10 },
                  { reason: 'Other', count: 4, percentage: 10 },
                ].map((error) => (
                  <div key={error.reason} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-200">{error.reason}</span>
                      <div className="flex items-center gap-2">
                        <XCircle className="h-3 w-3 text-error" />
                        <span className="text-sm text-gray-400">{error.count}</span>
                      </div>
                    </div>
                    <Progress value={error.percentage} className="h-1.5 [&>div]:bg-error" />
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="roi" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle className="text-base text-white">ROI Summary</CardTitle>
                <CardDescription className="text-gray-400">Business impact of automation</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-6 md:grid-cols-2">
                  <div className="space-y-4">
                    <div className="p-4 rounded-lg bg-success/10 border border-success/20">
                      <p className="text-sm text-success font-medium">Time Saved</p>
                      <p className="text-3xl font-bold text-success">{mockMetrics.timeSaved.value} hours</p>
                      <p className="text-xs text-gray-400 mt-1">
                        Equivalent to ${(mockMetrics.timeSaved.value * 60).toFixed(0)} in labor costs
                      </p>
                    </div>
                    <div className="p-4 rounded-lg bg-primary-light/10 border border-primary-light/20">
                      <p className="text-sm text-primary-light font-medium">Incidents Resolved</p>
                      <p className="text-3xl font-bold text-primary-light">47</p>
                      <p className="text-xs text-gray-400 mt-1">Automatically without human intervention</p>
                    </div>
                  </div>
                  <div className="space-y-4">
                    <div className="p-4 rounded-lg bg-warning/10 border border-warning/20">
                      <p className="text-sm text-warning font-medium">MTTR Reduction</p>
                      <p className="text-3xl font-bold text-warning">68%</p>
                      <p className="text-xs text-gray-400 mt-1">From 45min to 14min average</p>
                    </div>
                    <div className="p-4 rounded-lg bg-primary-light/10 border border-primary-light/20">
                      <p className="text-sm text-primary-light font-medium">Net ROI</p>
                      <p className="text-3xl font-bold text-primary-light">2,895%</p>
                      <p className="text-xs text-gray-400 mt-1">
                        ${(mockMetrics.timeSaved.value * 60 - mockMetrics.totalCost.value).toFixed(0)} saved / $
                        {mockMetrics.totalCost.value} spent
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base text-white">Quick Stats</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {[
                  { label: 'Automation Rate', value: '78%', sublabel: 'Tasks fully automated' },
                  { label: 'Human Escalations', value: '12', sublabel: 'Required this period' },
                  { label: 'Avg Time to Resolution', value: '14m', sublabel: 'Down from 45m manual' },
                  {
                    label: 'Cost per Resolution',
                    value: `$${(mockMetrics.totalCost.value / mockMetrics.totalRuns.value).toFixed(2)}`,
                    sublabel: 'vs $60 manual average',
                  },
                ].map((stat) => (
                  <div key={stat.label} className="p-3 rounded-lg bg-gray-800">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-400">{stat.label}</span>
                      <span className="text-lg font-bold text-white">{stat.value}</span>
                    </div>
                    <p className="text-xs text-gray-500">{stat.sublabel}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
