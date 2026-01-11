import { useState } from 'react'
import { Download, Upload, Database, FileJson, CheckCircle, AlertTriangle } from 'lucide-react'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import Button from '../components/ui/Button'
import { Modal } from '../components/ui/Modal'
import { useStore } from '../store/useStore'
import { tenantExportApi } from '../lib/api'

export function DataManagementPage() {
  const [exportOptions, setExportOptions] = useState({
    includeRunbooks: true,
    includePolicies: true,
    includeRunHistory: false,
    includeAuditLogs: false,
  })
  const [showExportModal, setShowExportModal] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [importFile, setImportFile] = useState<File | null>(null)
  const [validating, setValidating] = useState(false)
  const [validationResult, setValidationResult] = useState<any>(null)

  const handleExport = async () => {
    setExporting(true)
    try {
      // Get current tenant ID from store or use default
      const tenantId = useStore.getState().currentTenant || 'default'
      const blob = await tenantExportApi.export(tenantId)
      
      // Create download link
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `tenant-export-${new Date().toISOString()}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)

      useStore.getState().addNotification({
        type: 'success',
        message: 'Export bundle generated successfully',
      })
      setShowExportModal(false)
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'error',
        message: err.response?.data?.detail || err.message || 'Failed to export data',
      })
    } finally {
      setExporting(false)
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setImportFile(file)
    }
  }

  const handleValidate = async () => {
    if (!importFile) return
    setValidating(true)
    try {
      // TODO: Call validation API
      await new Promise((resolve) => setTimeout(resolve, 1500))
      setValidationResult({
        valid: true,
        summary: {
          runbooks: 12,
          policies: 5,
          runs: 0,
        },
      })
      useStore.getState().addNotification({
        type: 'success',
        message: 'Bundle validation successful',
      })
    } catch (err: any) {
      setValidationResult({
        valid: false,
        errors: ['Invalid bundle format', 'Missing required fields'],
      })
      useStore.getState().addNotification({
        type: 'error',
        message: 'Bundle validation failed',
      })
    } finally {
      setValidating(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-100 mb-2">Data Management</h1>
        <p className="text-gray-400">Export and import tenant data</p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Export Section */}
        <Card
          header={
            <div className="flex items-center gap-2">
              <Download className="w-5 h-5 text-primary-light" />
              <h2 className="text-lg font-semibold text-gray-100">Export Data</h2>
            </div>
          }
        >
          <div className="space-y-4">
            <p className="text-sm text-gray-400">
              Export your tenant data as a JSON bundle for backup or migration purposes.
            </p>
            <div className="space-y-3">
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={exportOptions.includeRunbooks}
                  onChange={(e) =>
                    setExportOptions({ ...exportOptions, includeRunbooks: e.target.checked })
                  }
                  className="w-4 h-4 rounded border-gray-700"
                />
                <span className="text-sm text-gray-300">Include runbooks</span>
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={exportOptions.includePolicies}
                  onChange={(e) =>
                    setExportOptions({ ...exportOptions, includePolicies: e.target.checked })
                  }
                  className="w-4 h-4 rounded border-gray-700"
                />
                <span className="text-sm text-gray-300">Include policies</span>
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={exportOptions.includeRunHistory}
                  onChange={(e) =>
                    setExportOptions({ ...exportOptions, includeRunHistory: e.target.checked })
                  }
                  className="w-4 h-4 rounded border-gray-700"
                />
                <span className="text-sm text-gray-300">Include run history</span>
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={exportOptions.includeAuditLogs}
                  onChange={(e) =>
                    setExportOptions({ ...exportOptions, includeAuditLogs: e.target.checked })
                  }
                  className="w-4 h-4 rounded border-gray-700"
                />
                <span className="text-sm text-gray-300">Include audit logs</span>
              </label>
            </div>
            <Button
              icon={<Download className="w-4 h-4" />}
              onClick={() => setShowExportModal(true)}
              className="w-full"
            >
              Generate Export Bundle
            </Button>
          </div>
        </Card>

        {/* Import Section */}
        <Card
          header={
            <div className="flex items-center gap-2">
              <Upload className="w-5 h-5 text-primary-light" />
              <h2 className="text-lg font-semibold text-gray-100">Import Data</h2>
            </div>
          }
        >
          <div className="space-y-4">
            <p className="text-sm text-gray-400">
              Import a tenant data bundle to restore or migrate data.
            </p>
            <div className="border-2 border-dashed border-gray-700 rounded-lg p-8 text-center">
              <Upload className="w-12 h-12 mx-auto mb-4 text-gray-600" />
              <input
                type="file"
                accept=".json"
                onChange={handleFileSelect}
                className="hidden"
                id="import-file"
              />
              <label
                htmlFor="import-file"
                className="cursor-pointer text-primary-light hover:text-primary transition-colors"
              >
                {importFile ? importFile.name : 'Click to select file or drag and drop'}
              </label>
            </div>
            {importFile && (
              <div className="space-y-2">
                <Button
                  variant="secondary"
                  icon={<CheckCircle className="w-4 h-4" />}
                  loading={validating}
                  onClick={handleValidate}
                  className="w-full"
                >
                  Validate Bundle
                </Button>
                {validationResult && (
                  <div
                    className={`p-4 rounded-lg ${
                      validationResult.valid
                        ? 'bg-success/20 border border-success/30'
                        : 'bg-error/20 border border-error/30'
                    }`}
                  >
                    {validationResult.valid ? (
                      <div>
                        <div className="flex items-center gap-2 text-success mb-2">
                          <CheckCircle className="w-5 h-5" />
                          <span className="font-medium">Bundle is valid</span>
                        </div>
                        <div className="text-sm text-gray-300 space-y-1">
                          <div>Runbooks: {validationResult.summary.runbooks}</div>
                          <div>Policies: {validationResult.summary.policies}</div>
                        </div>
                        <Button className="w-full mt-3">Import Bundle</Button>
                      </div>
                    ) : (
                      <div>
                        <div className="flex items-center gap-2 text-error mb-2">
                          <AlertTriangle className="w-5 h-5" />
                          <span className="font-medium">Validation failed</span>
                        </div>
                        <ul className="list-disc list-inside text-sm text-error space-y-1">
                          {validationResult.errors?.map((error: string, i: number) => (
                            <li key={i}>{error}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Backup Status */}
      <Card
        header={
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-primary-light" />
            <h2 className="text-lg font-semibold text-gray-100">Backup Status</h2>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-gray-900 rounded-lg">
            <div>
              <div className="font-medium text-gray-100">Last Backup</div>
              <div className="text-sm text-gray-400">2 hours ago</div>
            </div>
            <Badge variant="success" size="sm">
              Success
            </Badge>
          </div>
          <div className="text-sm text-gray-400">
            <strong>Schedule:</strong> Daily at 2:00 AM UTC
          </div>
          <div className="text-sm text-gray-400">
            <strong>Retention:</strong> 14 days
          </div>
        </div>
      </Card>

      {/* Export Modal */}
      <Modal
        isOpen={showExportModal}
        onClose={() => setShowExportModal(false)}
        title="Export Tenant Data"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowExportModal(false)}>
              Cancel
            </Button>
            <Button loading={exporting} onClick={handleExport}>
              Generate Export
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-gray-300">
            This will generate a JSON bundle containing all selected data. The export may take a few
            minutes for large datasets.
          </p>
          <div className="bg-gray-900 p-4 rounded-lg">
            <div className="text-sm font-medium text-gray-300 mb-2">Export Options:</div>
            <div className="space-y-1 text-sm text-gray-400">
              {exportOptions.includeRunbooks && <div>✓ Runbooks</div>}
              {exportOptions.includePolicies && <div>✓ Policies</div>}
              {exportOptions.includeRunHistory && <div>✓ Run History</div>}
              {exportOptions.includeAuditLogs && <div>✓ Audit Logs</div>}
            </div>
          </div>
        </div>
      </Modal>
    </div>
  )
}

