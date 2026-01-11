import { Area, AreaChart, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip } from 'recharts'

interface ChartData {
  time: string
  successful: number
  failed: number
  total: number
}

interface RunsChartProps {
  data?: ChartData[]
}

// Generate chart data for last 24 hours
const generateChartData = (): ChartData[] => {
  const data: ChartData[] = []
  const now = new Date()

  for (let i = 23; i >= 0; i--) {
    const hour = new Date(now.getTime() - i * 60 * 60 * 1000)
    const hourStr = hour.toLocaleTimeString('en-US', { hour: '2-digit', hour12: true })

    // Simulate varying run counts
    const baseRuns = Math.floor(Math.random() * 5) + 2
    const successRuns = Math.floor(baseRuns * (0.85 + Math.random() * 0.15))
    const failedRuns = baseRuns - successRuns

    data.push({
      time: hourStr,
      successful: successRuns,
      failed: failedRuns,
      total: baseRuns,
    })
  }

  return data
}

export function RunsChart({ data }: RunsChartProps) {
  const chartData = data || generateChartData()

  return (
    <div className="h-[250px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="successGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="failedGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
          <XAxis
            dataKey="time"
            axisLine={false}
            tickLine={false}
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            interval="preserveStartEnd"
          />
          <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
              color: '#e2e8f0',
            }}
            labelStyle={{ color: '#e2e8f0' }}
          />
          <Area
            type="monotone"
            dataKey="successful"
            stackId="1"
            stroke="#10b981"
            fill="url(#successGradient)"
            strokeWidth={2}
          />
          <Area
            type="monotone"
            dataKey="failed"
            stackId="1"
            stroke="#ef4444"
            fill="url(#failedGradient)"
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

