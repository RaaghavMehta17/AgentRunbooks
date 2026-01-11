import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Save, Play, CheckCircle } from 'lucide-react'
import Editor from '@monaco-editor/react'
import { runbooksApi } from '../lib/api'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import Button from '../components/ui/Button'
import { useStore } from '../store/useStore'

const defaultYAML = `name: my-runbook
description: A sample runbook
steps:
  - name: step1
    tool: github.get_repo
    args:
      owner: org
      repo: repo
`

export function RunbookCreatePage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [yaml, setYaml] = useState(defaultYAML)
  const [validating, setValidating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [validationErrors, setValidationErrors] = useState<string[]>([])

  const handleValidate = async () => {
    setValidating(true)
    setValidationErrors([])
    // TODO: Call validation endpoint
    setTimeout(() => {
      setValidating(false)
      useStore.getState().addNotification({
        type: 'success',
        message: 'Runbook YAML is valid',
      })
    }, 500)
  }

  const handleSave = async () => {
    if (!name.trim()) {
      useStore.getState().addNotification({
        type: 'error',
        message: 'Please enter a runbook name',
      })
      return
    }

    setSaving(true)
    try {
      const runbook = await runbooksApi.create({ name, yaml })
      useStore.getState().addNotification({
        type: 'success',
        message: 'Runbook created successfully',
      })
      navigate(`/runbooks/${runbook.id || runbook.runbook_id}`)
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to create runbook'
      useStore.getState().addNotification({
        type: 'error',
        message: errorMsg,
      })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            icon={<ArrowLeft className="w-4 h-4" />}
            onClick={() => navigate('/runbooks')}
          >
            Back
          </Button>
          <div>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter runbook name"
              className="text-3xl font-bold bg-transparent border-none text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-light rounded px-2"
            />
            <Badge variant="warning" size="sm" className="ml-3">
              Draft
            </Badge>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            icon={<CheckCircle className="w-4 h-4" />}
            loading={validating}
            onClick={handleValidate}
          >
            Validate
          </Button>
          <Button
            variant="secondary"
            icon={<Save className="w-4 h-4" />}
            loading={saving}
            onClick={handleSave}
          >
            Save Draft
          </Button>
          <Button icon={<Play className="w-4 h-4" />} onClick={handleSave}>
            Publish
          </Button>
        </div>
      </div>

      {/* Editor and Preview */}
      <div className="grid grid-cols-2 gap-6">
        {/* YAML Editor */}
        <Card header={<h2 className="text-lg font-semibold text-gray-100">YAML Editor</h2>}>
          <div className="h-[600px]">
            <Editor
              height="100%"
              defaultLanguage="yaml"
              value={yaml}
              onChange={(value) => setYaml(value || '')}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                automaticLayout: true,
              }}
            />
          </div>
        </Card>

        {/* Preview/Validation */}
        <Card header={<h2 className="text-lg font-semibold text-gray-100">Preview & Validation</h2>}>
          <div className="space-y-4">
            {validationErrors.length > 0 ? (
              <div className="p-4 bg-error/20 border border-error/30 rounded-lg">
                <h3 className="font-semibold text-error mb-2">Validation Errors</h3>
                <ul className="list-disc list-inside text-sm text-error space-y-1">
                  {validationErrors.map((error, i) => (
                    <li key={i}>{error}</li>
                  ))}
                </ul>
              </div>
            ) : (
              <div className="p-4 bg-success/20 border border-success/30 rounded-lg">
                <div className="flex items-center gap-2 text-success">
                  <CheckCircle className="w-5 h-5" />
                  <span className="font-medium">YAML is valid</span>
                </div>
              </div>
            )}

            <div>
              <h3 className="font-semibold text-gray-100 mb-2">Runbook Preview</h3>
              <pre className="bg-gray-900 p-4 rounded-lg overflow-x-auto text-sm font-mono text-gray-300">
                {yaml || 'No content'}
              </pre>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}

