import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Search, Folder } from 'lucide-react'
import { projectsApi } from '../lib/api'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Skeleton } from '../components/ui/Skeleton'
import Button from '../components/ui/Button'
import { Modal } from '../components/ui/Modal'
import { formatRelativeTime } from '../lib/utils'
import { useStore } from '../store/useStore'

export function ProjectsPage() {
  const [projects, setProjects] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const data = await projectsApi.list()
        setProjects(Array.isArray(data) ? data : [])
      } catch (err) {
        console.error('Failed to fetch projects:', err)
        useStore.getState().addNotification({
          type: 'error',
          message: 'Failed to load projects',
        })
      } finally {
        setLoading(false)
      }
    }
    fetchProjects()
  }, [])

  const handleCreate = async () => {
    if (!newProjectName.trim()) return
    setCreating(true)
    try {
      const project = await projectsApi.create({ name: newProjectName })
      setProjects([...projects, project])
      useStore.getState().addNotification({
        type: 'success',
        message: 'Project created successfully',
      })
      setShowCreateModal(false)
      setNewProjectName('')
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'error',
        message: err.message || 'Failed to create project',
      })
    } finally {
      setCreating(false)
    }
  }

  const filteredProjects = projects.filter((p) =>
    p.name?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton variant="text" lines={1} className="h-8 w-48" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} variant="rectangular" className="h-48" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-100 mb-2">Projects</h1>
          <p className="text-gray-400">Manage your projects and workspaces</p>
        </div>
        <Button icon={<Plus className="w-4 h-4" />} onClick={() => setShowCreateModal(true)}>
          Create Project
        </Button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="Search projects..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-light"
        />
      </div>

      {/* Projects Grid */}
      {filteredProjects.length === 0 ? (
        <Card className="text-center py-12">
          <Folder className="w-12 h-12 mx-auto mb-4 text-gray-600" />
          <p className="text-gray-400 mb-4">No projects found</p>
          <Button onClick={() => setShowCreateModal(true)}>Create your first project</Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredProjects.map((project) => (
            <Link key={project.id} to={`/projects/${project.id}`}>
              <Card hover className="h-full">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                    <Folder className="w-5 h-5 text-primary-light" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-gray-100 truncate">{project.name}</h3>
                    <p className="text-xs text-gray-400">Project</p>
                  </div>
                </div>
                <div className="text-xs text-gray-500">
                  Created {project.created_at ? formatRelativeTime(project.created_at) : 'Unknown'}
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}

      {/* Create Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create Project"
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
            <label className="block text-sm font-medium text-gray-300 mb-2">Project Name</label>
            <input
              type="text"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              placeholder="Enter project name"
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-light"
              autoFocus
            />
          </div>
        </div>
      </Modal>
    </div>
  )
}

