import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/Card'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Line,
  LineChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'

// More vibrant colors for better visibility
const successColor = '#22c55e' // Brighter green
const failedColor = '#ef4444' // Red
const primaryColor = '#3b82f6' // Blue
const costColor = '#8b5cf6' // Purple
const p50Color = '#06b6d4' // Cyan
const p90Color = '#f59e0b' // Orange
const p99Color = '#ef4444' // Red

interface AnalyticsChartsProps {
  runsData?: Array<{ date: string; runs: number; success: number; failed: number }>
  costData?: Array<{ date: string; cost: number; tokens: number }>
  latencyData?: Array<{ date: string; p50: number; p90: number; p99: number }>
}

// Custom tooltip component
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 shadow-lg">
        <p className="text-white font-medium mb-2">{label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} className="text-sm" style={{ color: entry.color }}>
            {entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
          </p>
        ))}
      </div>
    )
  }
  return null
}

export function AnalyticsCharts({ runsData, costData, latencyData }: AnalyticsChartsProps) {
  // Default mock data if not provided
  const defaultRunsData = [
    { date: 'Mon', runs: 145, success: 140, failed: 5 },
    { date: 'Tue', runs: 168, success: 162, failed: 6 },
    { date: 'Wed', runs: 192, success: 186, failed: 6 },
    { date: 'Thu', runs: 178, success: 172, failed: 6 },
    { date: 'Fri', runs: 203, success: 198, failed: 5 },
    { date: 'Sat', runs: 89, success: 87, failed: 2 },
    { date: 'Sun', runs: 72, success: 70, failed: 2 },
  ]

  const defaultCostData = [
    { date: 'Mon', cost: 42.5, tokens: 380000 },
    { date: 'Tue', cost: 48.2, tokens: 420000 },
    { date: 'Wed', cost: 51.8, tokens: 450000 },
    { date: 'Thu', cost: 45.3, tokens: 395000 },
    { date: 'Fri', cost: 52.1, tokens: 455000 },
    { date: 'Sat', cost: 22.4, tokens: 190000 },
    { date: 'Sun', cost: 18.9, tokens: 160000 },
  ]

  const defaultLatencyData = [
    { date: 'Mon', p50: 135, p90: 380, p99: 720 },
    { date: 'Tue', p50: 142, p90: 395, p99: 745 },
    { date: 'Wed', p50: 128, p90: 365, p99: 690 },
    { date: 'Thu', p50: 138, p90: 375, p99: 710 },
    { date: 'Fri', p50: 145, p90: 400, p99: 780 },
    { date: 'Sat', p50: 120, p90: 340, p99: 650 },
    { date: 'Sun', p50: 115, p90: 325, p99: 620 },
  ]

  const finalRunsData = runsData && runsData.length > 0 ? runsData : defaultRunsData
  const finalCostData = costData && costData.length > 0 ? costData : defaultCostData
  const finalLatencyData = latencyData && latencyData.length > 0 ? latencyData : defaultLatencyData

  return (
    <div className="space-y-4">
      {/* Runs Chart */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base text-white">Run Activity</CardTitle>
          <CardDescription className="text-gray-400">Daily runs breakdown</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[250px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={finalRunsData}
                margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                barCategoryGap="20%"
              >
                <defs>
                  <linearGradient id="successGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={successColor} stopOpacity={0.9} />
                    <stop offset="95%" stopColor={successColor} stopOpacity={0.6} />
                  </linearGradient>
                  <linearGradient id="failedGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={failedColor} stopOpacity={0.9} />
                    <stop offset="95%" stopColor={failedColor} stopOpacity={0.6} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis
                  dataKey="date"
                  stroke="#94a3b8"
                  fontSize={12}
                  tick={{ fill: '#94a3b8' }}
                  axisLine={{ stroke: '#475569' }}
                  tickLine={{ stroke: '#475569' }}
                />
                <YAxis
                  stroke="#94a3b8"
                  fontSize={12}
                  tick={{ fill: '#94a3b8' }}
                  axisLine={{ stroke: '#475569' }}
                  tickLine={{ stroke: '#475569' }}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  wrapperStyle={{ color: '#e2e8f0', paddingTop: '20px' }}
                  iconType="rect"
                  formatter={(value) => (
                    <span style={{ color: '#e2e8f0', fontSize: '12px' }}>{value}</span>
                  )}
                />
                <Bar
                  dataKey="success"
                  name="Success"
                  stackId="a"
                  fill="url(#successGradient)"
                  radius={[0, 0, 0, 0]}
                  animationDuration={1000}
                  animationBegin={0}
                />
                <Bar
                  dataKey="failed"
                  name="Failed"
                  stackId="a"
                  fill="url(#failedGradient)"
                  radius={[4, 4, 0, 0]}
                  animationDuration={1000}
                  animationBegin={100}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Cost Chart */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base text-white">Cost Trend</CardTitle>
          <CardDescription className="text-gray-400">Daily spending</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[250px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={finalCostData}
                margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={costColor} stopOpacity={0.4} />
                    <stop offset="95%" stopColor={costColor} stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis
                  dataKey="date"
                  stroke="#94a3b8"
                  fontSize={12}
                  tick={{ fill: '#94a3b8' }}
                  axisLine={{ stroke: '#475569' }}
                  tickLine={{ stroke: '#475569' }}
                />
                <YAxis
                  stroke="#94a3b8"
                  fontSize={12}
                  tick={{ fill: '#94a3b8' }}
                  axisLine={{ stroke: '#475569' }}
                  tickLine={{ stroke: '#475569' }}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="cost"
                  name="Cost ($)"
                  stroke={costColor}
                  strokeWidth={3}
                  fill="url(#costGradient)"
                  animationDuration={1000}
                  animationBegin={0}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Latency Chart */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base text-white">Latency Percentiles</CardTitle>
          <CardDescription className="text-gray-400">Response time in milliseconds</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[250px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={finalLatencyData}
                margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis
                  dataKey="date"
                  stroke="#94a3b8"
                  fontSize={12}
                  tick={{ fill: '#94a3b8' }}
                  axisLine={{ stroke: '#475569' }}
                  tickLine={{ stroke: '#475569' }}
                />
                <YAxis
                  stroke="#94a3b8"
                  fontSize={12}
                  tick={{ fill: '#94a3b8' }}
                  axisLine={{ stroke: '#475569' }}
                  tickLine={{ stroke: '#475569' }}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  wrapperStyle={{ color: '#e2e8f0', paddingTop: '20px' }}
                  iconType="line"
                  formatter={(value) => (
                    <span style={{ color: '#e2e8f0', fontSize: '12px' }}>{value}</span>
                  )}
                />
                <Line
                  type="monotone"
                  dataKey="p50"
                  name="P50"
                  stroke={p50Color}
                  strokeWidth={3}
                  dot={{ fill: p50Color, r: 4 }}
                  activeDot={{ r: 6 }}
                  animationDuration={1000}
                  animationBegin={0}
                />
                <Line
                  type="monotone"
                  dataKey="p90"
                  name="P90"
                  stroke={p90Color}
                  strokeWidth={3}
                  dot={{ fill: p90Color, r: 4 }}
                  activeDot={{ r: 6 }}
                  animationDuration={1000}
                  animationBegin={150}
                />
                <Line
                  type="monotone"
                  dataKey="p99"
                  name="P99"
                  stroke={p99Color}
                  strokeWidth={3}
                  dot={{ fill: p99Color, r: 4 }}
                  activeDot={{ r: 6 }}
                  animationDuration={1000}
                  animationBegin={300}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
