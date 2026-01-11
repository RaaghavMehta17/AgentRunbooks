import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Search, Building2 } from 'lucide-react'
import { tenantsApi } from '../lib/api'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Skeleton } from '../components/ui/Skeleton'
import Button from '../components/ui/Button'
import { Modal } from '../components/ui/Modal'
import { formatRelativeTime } from '../lib/utils'
import { useStore } from '../store/useStore'

export function TenantsPage() {
  const [tenants, setTenants] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newTenantName, setNewTenantName] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    const fetchTenants = async () => {
      try {
        const data = await tenantsApi.list()
        setTenants(Array.isArray(data) ? data : [])
      } catch (err) {
        console.error('Failed to fetch tenants:', err)
        useStore.getState().addNotification({
          type: 'error',
          message: 'Failed to load tenants',
        })
      } finally {
        setLoading(false)
      }
    }
    fetchTenants()
  }, [])

  const handleCreate = async () => {
    if (!newTenantName.trim()) return
    setCreating(true)
    try {
      const tenant = await tenantsApi.create({ name: newTenantName })
      setTenants([...tenants, tenant])
      useStore.getState().addNotification({
        type: 'success',
        message: 'Tenant created successfully',
      })
      setShowCreateModal(false)
      setNewTenantName('')
      // Refresh list
      const updated = await tenantsApi.list()
      setTenants(Array.isArray(updated) ? updated : [])
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to create tenant'
      useStore.getState().addNotification({
        type: 'error',
        message: errorMsg,
      })
    } finally {
      setCreating(false)
    }
  }

  const filteredTenants = tenants.filter((t) =>
    t.name?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton variant="text" lines={1} className="h-8 w-48" />
        <Skeleton variant="rectangular" className="h-96" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-100 mb-2">Tenants</h1>
          <p className="text-gray-400">Manage your tenants and organizations</p>
        </div>
        <Button icon={<Plus className="w-4 h-4" />} onClick={() => setShowCreateModal(true)}>
          Create Tenant
        </Button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="Search tenants..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-light"
        />
      </div>

      {/* Tenants Table */}
      <Card>
        {filteredTenants.length === 0 ? (
          <div className="text-center py-12">
            <Building2 className="w-12 h-12 mx-auto mb-4 text-gray-600" />
            <p className="text-gray-400 mb-4">No tenants found</p>
            <Button onClick={() => setShowCreateModal(true)}>Create your first tenant</Button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-300">Name</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-300">ID</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-300">Created</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-300">Status</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-300">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredTenants.map((tenant) => (
                  <tr
                    key={tenant.id}
                    className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors"
                  >
                    <td className="py-3 px-4">
                      <Link
                        to={`/tenants/${tenant.id}`}
                        className="font-medium text-gray-100 hover:text-primary-light transition-colors"
                      >
                        {tenant.name}
                      </Link>
                    </td>
                    <td className="py-3 px-4">
                      <code className="text-xs text-gray-400 font-mono">{tenant.id?.slice(0, 8)}</code>
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-400">
                      {tenant.created_at ? formatRelativeTime(tenant.created_at) : 'Unknown'}
                    </td>
                    <td className="py-3 px-4">
                      <Badge variant="success" size="sm">Active</Badge>
                    </td>
                    <td className="py-3 px-4">
                      <Link
                        to={`/tenants/${tenant.id}`}
                        className="text-primary-light hover:text-primary text-sm transition-colors"
                      >
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Create Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create Tenant"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowCreateModal(false)}>
              Cancel
            </Button>
            <Button loading={creating} onClick={handleCreate}>
              Create
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Tenant Name</label>
            <input
              type="text"
              value={newTenantName}
              onChange={(e) => setNewTenantName(e.target.value)}
              placeholder="Enter tenant name"
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-light"
              autoFocus
            />
          </div>
        </div>
      </Modal>
    </div>
  )
}

