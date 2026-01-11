import { useEffect, useState } from 'react'
import { runbooksApi, runsApi, policiesApi, approvalsApi, projectsApi, tenantsApi, evalsApi, healthApi } from '../lib/api'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import Button from '../components/ui/Button'
import { useStore } from '../store/useStore'

export function TestPage() {
  const [results, setResults] = useState<Record<string, any>>({})
  const [testing, setTesting] = useState(false)

  const runTests = async () => {
    setTesting(true)
    const testResults: Record<string, any> = {}

    try {
      // Test health
      testResults.health = await healthApi.check()
    } catch (err: any) {
      testResults.health = { error: err.message }
    }

    try {
      // Test runbooks
      testResults.runbooks = await runbooksApi.list()
    } catch (err: any) {
      testResults.runbooks = { error: err.message }
    }

    try {
      // Test runs
      testResults.runs = await runsApi.list({ limit: 5 })
    } catch (err: any) {
      testResults.runs = { error: err.message }
    }

    try {
      // Test policies
      testResults.policies = await policiesApi.list()
    } catch (err: any) {
      testResults.policies = { error: err.message }
    }

    try {
      // Test approvals
      testResults.approvals = await approvalsApi.list()
    } catch (err: any) {
      testResults.approvals = { error: err.message }
    }

    try {
      // Test projects
      testResults.projects = await projectsApi.list()
    } catch (err: any) {
      testResults.projects = { error: err.message }
    }

    try {
      // Test tenants
      testResults.tenants = await tenantsApi.list()
    } catch (err: any) {
      testResults.tenants = { error: err.message }
    }

    try {
      // Test evals
      testResults.evals = await evalsApi.list()
    } catch (err: any) {
      testResults.evals = { error: err.message }
    }

    setResults(testResults)
    setTesting(false)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-100 mb-2">API Integration Test</h1>
        <p className="text-gray-400">Test all backend API endpoints</p>
      </div>

      <Button onClick={runTests} loading={testing}>
        Run All Tests
      </Button>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(results).map(([key, value]) => (
          <Card key={key}>
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-gray-100">{key}</h3>
              <Badge variant={value.error ? 'error' : 'success'} size="sm">
                {value.error ? 'Error' : 'OK'}
              </Badge>
            </div>
            <pre className="bg-gray-900 p-3 rounded text-xs font-mono text-gray-300 overflow-x-auto max-h-48 overflow-y-auto">
              {JSON.stringify(value, null, 2)}
            </pre>
          </Card>
        ))}
      </div>
    </div>
  )
}

