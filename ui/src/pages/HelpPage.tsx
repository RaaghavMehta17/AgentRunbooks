import { useState } from 'react'
import { HelpCircle, Book, FileText, ExternalLink, Search } from 'lucide-react'
import { Card } from '../components/ui/Card'
import Button from '../components/ui/Button'

const documentation = [
  {
    category: 'Getting Started',
    items: [
      { title: 'Quickstart Guide', description: 'Get up and running in 5 minutes' },
      { title: 'Creating Your First Runbook', description: 'Learn the basics of runbook creation' },
      { title: 'Running a Runbook', description: 'Execute your first runbook' },
    ],
  },
  {
    category: 'Runbook Authoring',
    items: [
      { title: 'Runbook Schema Reference', description: 'Complete YAML schema documentation' },
      { title: 'Step Types', description: 'Available step types and their usage' },
      { title: 'Tool Adapters', description: 'Integrate with external services' },
      { title: 'Best Practices', description: 'Tips for writing effective runbooks' },
    ],
  },
  {
    category: 'Policies & Guardrails',
    items: [
      { title: 'Policy Syntax', description: 'How to write policy rules' },
      { title: 'Approval Rules', description: 'Configure approval workflows' },
      { title: 'Testing Policies', description: 'Validate your policies' },
    ],
  },
  {
    category: 'Integrations',
    items: [
      { title: 'GitHub Setup', description: 'Connect to GitHub repositories' },
      { title: 'Kubernetes Setup', description: 'Configure Kubernetes access' },
      { title: 'PagerDuty Setup', description: 'Integrate with PagerDuty' },
    ],
  },
]

export function HelpPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)

  const filteredDocs = documentation.filter((doc) => {
    if (selectedCategory && doc.category !== selectedCategory) return false
    if (!searchQuery) return true
    return (
      doc.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.items.some((item) =>
        item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.description.toLowerCase().includes(searchQuery.toLowerCase())
      )
    )
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-100 mb-2">Help & Documentation</h1>
        <p className="text-gray-400">Find answers and learn how to use the platform</p>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          placeholder="Search documentation..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-light"
        />
      </div>

      {/* Categories */}
      <div className="flex items-center gap-2 flex-wrap">
        <Button
          variant={selectedCategory === null ? 'primary' : 'ghost'}
          size="sm"
          onClick={() => setSelectedCategory(null)}
        >
          All
        </Button>
        {documentation.map((doc) => (
          <Button
            key={doc.category}
            variant={selectedCategory === doc.category ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setSelectedCategory(doc.category)}
          >
            {doc.category}
          </Button>
        ))}
      </div>

      {/* Documentation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredDocs.map((doc) => (
          <Card key={doc.category} hover>
            <div className="flex items-center gap-2 mb-4">
              <Book className="w-5 h-5 text-primary-light" />
              <h2 className="text-lg font-semibold text-gray-100">{doc.category}</h2>
            </div>
            <div className="space-y-2">
              {doc.items.map((item, i) => (
                <div
                  key={i}
                  className="p-3 bg-gray-900 rounded-lg hover:bg-gray-800 transition-colors cursor-pointer"
                >
                  <div className="font-medium text-gray-200 mb-1">{item.title}</div>
                  <div className="text-sm text-gray-400">{item.description}</div>
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>

      {/* Quick Links */}
      <Card header={<h2 className="text-lg font-semibold text-gray-100">Quick Links</h2>}>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <a
            href="#"
            className="flex items-center gap-3 p-4 bg-gray-900 rounded-lg hover:bg-gray-800 transition-colors"
          >
            <FileText className="w-5 h-5 text-primary-light" />
            <div>
              <div className="font-medium text-gray-100">API Reference</div>
              <div className="text-sm text-gray-400">Complete API documentation</div>
            </div>
            <ExternalLink className="w-4 h-4 text-gray-500 ml-auto" />
          </a>
          <a
            href="#"
            className="flex items-center gap-3 p-4 bg-gray-900 rounded-lg hover:bg-gray-800 transition-colors"
          >
            <HelpCircle className="w-5 h-5 text-primary-light" />
            <div>
              <div className="font-medium text-gray-100">FAQ</div>
              <div className="text-sm text-gray-400">Frequently asked questions</div>
            </div>
            <ExternalLink className="w-4 h-4 text-gray-500 ml-auto" />
          </a>
          <a
            href="#"
            className="flex items-center gap-3 p-4 bg-gray-900 rounded-lg hover:bg-gray-800 transition-colors"
          >
            <FileText className="w-5 h-5 text-primary-light" />
            <div>
              <div className="font-medium text-gray-100">Troubleshooting</div>
              <div className="text-sm text-gray-400">Common issues and solutions</div>
            </div>
            <ExternalLink className="w-4 h-4 text-gray-500 ml-auto" />
          </a>
        </div>
      </Card>
    </div>
  )
}

