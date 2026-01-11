export default function StepTimeline({ steps }: { steps: any[] }) {
  const statusColors: Record<string, string> = {
    pending: 'bg-gray-100 text-gray-800',
    running: 'bg-blue-100 text-blue-800',
    succeeded: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    skipped: 'bg-yellow-100 text-yellow-800',
    compensated: 'bg-purple-100 text-purple-800',
  }

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <h2 className="text-xl font-bold mb-4">Step Timeline</h2>
      <div className="space-y-4">
        {steps.map((step, idx) => (
          <div key={idx} className="flex items-start space-x-4">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
              {idx + 1}
            </div>
            <div className="flex-1">
              <div className="flex items-center space-x-2">
                <span className="font-medium">{step.name}</span>
                <span className={`px-2 py-1 text-xs rounded-full ${statusColors[step.status] || statusColors.pending}`}>
                  {step.status}
                </span>
                <span className="text-sm text-gray-500">{step.tool}</span>
              </div>
              {step.error && (
                <div className="mt-2 text-sm text-red-600">
                  Error: {JSON.stringify(step.error)}
                </div>
              )}
              {step.output?.usage && (
                <div className="mt-2 text-sm text-gray-600">
                  Usage: {step.output.usage.tokens_in + step.output.usage.tokens_out} tokens, $
                  {step.output.usage.cost_usd?.toFixed(6)}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

