import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Shield, LogIn } from 'lucide-react'
import { authApi } from '../lib/api'
import { useStore } from '../store/useStore'
import Button from '../components/ui/Button'

export function LoginPage() {
  const navigate = useNavigate()
  const setToken = useStore((state) => state.setToken)
  const addNotification = useStore((state) => state.addNotification)
  const [email, setEmail] = useState('admin@example.com')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      // Use dev-login for local development
      const result = await authApi.devLogin(email, ['admin', 'sre'])
      if (result.access_token) {
        setToken(result.access_token)
        useStore.getState().setUser({
          email: result.email || email,
          roles: result.roles || ['Admin'],
        })
        addNotification({ type: 'success', message: 'Logged in successfully' })
        navigate('/')
      } else {
        throw new Error('No access token received')
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Login failed'
      setError(errorMsg)
      addNotification({ type: 'error', message: errorMsg })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900 p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/20 mb-4">
            <Shield className="w-8 h-8 text-primary-light" />
          </div>
          <h1 className="text-3xl font-bold text-gray-100 mb-2">OpsGenie-for-Agents</h1>
          <p className="text-gray-400">Enterprise Agentic Runbook Platform</p>
        </div>

        <div className="bg-gray-800 rounded-lg border border-gray-700 shadow-xl p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-light focus:border-transparent"
                required
                autoFocus
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-light focus:border-transparent"
                required
              />
            </div>

            {error && (
              <div className="px-4 py-3 bg-error/20 border border-error/30 rounded-lg text-error text-sm">
                {error}
              </div>
            )}

            <Button
              type="submit"
              loading={loading}
              icon={<LogIn className="w-4 h-4" />}
              className="w-full"
              size="lg"
            >
              Sign In
            </Button>
          </form>
        </div>

        <p className="text-center text-gray-500 text-sm mt-6">
          Enterprise-grade runbook automation platform
        </p>
      </div>
    </div>
  )
}

