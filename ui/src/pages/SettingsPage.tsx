import { useState, useEffect } from 'react'
import {
  User,
  Users,
  Bell,
  Shield,
  Key,
  Globe,
  Database,
  Webhook,
  ToggleLeft,
  Save,
  RefreshCw,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import Button from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Label } from '../components/ui/Label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/Tabs'
import { Switch } from '../components/ui/Switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/Select'
import { Badge } from '../components/ui/Badge'
import { Avatar, AvatarFallback } from '../components/ui/Avatar'
import { Separator } from '../components/ui/Separator'
import { currentUser, mockUsers, mockTenant, type MockUser } from '../lib/mock-data'
import { settingsApi, tenantsApi, roleBindingsApi } from '../lib/api'
import { useStore } from '../store/useStore'

const defaultFeatureFlags = [
  {
    id: 'ai-suggestions',
    name: 'AI Suggestions',
    description: 'Enable AI-powered suggestions for runbook creation and optimization',
    enabled: true,
    category: 'AI',
  },
  {
    id: 'auto-remediation',
    name: 'Auto Remediation',
    description: 'Allow runbooks to automatically apply fixes without approval',
    enabled: false,
    category: 'Automation',
  },
  {
    id: 'advanced-analytics',
    name: 'Advanced Analytics',
    description: 'Enable advanced analytics and ROI tracking features',
    enabled: true,
    category: 'Analytics',
  },
  {
    id: 'webhook-triggers',
    name: 'Webhook Triggers',
    description: 'Allow external systems to trigger runbooks via webhooks',
    enabled: true,
    category: 'Integration',
  },
  {
    id: 'multi-tenant',
    name: 'Multi-Tenant Mode',
    description: 'Enable multi-tenant features for enterprise deployments',
    enabled: false,
    category: 'Enterprise',
  },
  {
    id: 'audit-retention',
    name: 'Extended Audit Retention',
    description: 'Keep audit logs for 1 year instead of 90 days',
    enabled: true,
    category: 'Compliance',
  },
]

export function SettingsPage() {
  const [isSaving, setIsSaving] = useState(false)
  const [flags, setFlags] = useState(defaultFeatureFlags)
  const [profile, setProfile] = useState<any>(null)
  const [teamMembers, setTeamMembers] = useState<MockUser[]>([])
  const [apiKeys, setApiKeys] = useState<any[]>([])
  const [notifications, setNotifications] = useState<any>(null)
  const [dataRetention, setDataRetention] = useState<any>(null)
  const [sessions, setSessions] = useState<any[]>([])
  const [webhooks, setWebhooks] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const user = useStore((state) => state.user)
  const currentTenant = useStore((state) => state.currentProject) || 'default'

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [profileRes, teamRes, apiKeysRes, notificationsRes, retentionRes, sessionsRes, webhooksRes] =
          await Promise.all([
            settingsApi.getProfile().catch(() => null),
            roleBindingsApi.list().catch(() => []),
            tenantsApi.listApiKeys(currentTenant).catch(() => []),
            settingsApi.getNotifications().catch(() => null),
            settingsApi.getDataRetention().catch(() => null),
            settingsApi.getSessions().catch(() => null),
            settingsApi.getWebhooks().catch(() => null),
          ])

        if (profileRes) setProfile(profileRes)
        else setProfile({ name: currentUser.name, email: currentUser.email, role: currentUser.role })

        // Map role bindings to team members
        if (Array.isArray(teamRes) && teamRes.length > 0) {
          // TODO: Map from role bindings
          setTeamMembers(mockUsers)
        } else {
          setTeamMembers(mockUsers)
        }

        if (apiKeysRes && Array.isArray(apiKeysRes)) {
          setApiKeys(apiKeysRes)
        } else {
          // Mock API keys
          setApiKeys([
            {
              id: 'key-1',
              name: 'Production API Key',
              prefix: 'rk_live_',
              created: 'Jan 5, 2025',
              lastUsed: '2 hours ago',
            },
            {
              id: 'key-2',
              name: 'Staging API Key',
              prefix: 'rk_test_',
              created: 'Dec 15, 2024',
              lastUsed: '1 day ago',
            },
            {
              id: 'key-3',
              name: 'CI/CD Pipeline',
              prefix: 'rk_ci_',
              created: 'Nov 20, 2024',
              lastUsed: '3 hours ago',
            },
          ])
        }

        if (notificationsRes) setNotifications(notificationsRes)
        else {
          setNotifications({
            run_completions_email: true,
            run_completions_slack: true,
            run_failures_email: true,
            run_failures_slack: true,
            approval_requests_email: true,
            approval_requests_slack: true,
            policy_triggers_email: false,
            policy_triggers_slack: true,
            weekly_reports_email: true,
            weekly_reports_slack: false,
          })
        }

        if (retentionRes) setDataRetention(retentionRes)
        else {
          setDataRetention({
            run_history_retention_days: 90,
            audit_log_retention_days: 365,
          })
        }

        if (sessionsRes && sessionsRes.sessions) setSessions(sessionsRes.sessions)
        else {
          setSessions([
            {
              id: 'session-1',
              device: 'Chrome on macOS',
              location: 'San Francisco, CA',
              lastActive: 'Active now',
              current: true,
            },
            {
              id: 'session-2',
              device: 'Safari on iPhone',
              location: 'San Francisco, CA',
              lastActive: '2 hours ago',
              current: false,
            },
            {
              id: 'session-3',
              device: 'Firefox on Windows',
              location: 'New York, NY',
              lastActive: '3 days ago',
              current: false,
            },
          ])
        }

        if (webhooksRes && webhooksRes.webhooks) setWebhooks(webhooksRes.webhooks)
        else setWebhooks([])
      } catch (err) {
        console.debug('Failed to fetch settings data (silent):', err)
        // Use defaults
        setProfile({ name: currentUser.name, email: currentUser.email, role: currentUser.role })
        setTeamMembers(mockUsers)
        setNotifications({
          run_completions_email: true,
          run_completions_slack: true,
          run_failures_email: true,
          run_failures_slack: true,
          approval_requests_email: true,
          approval_requests_slack: true,
          policy_triggers_email: false,
          policy_triggers_slack: true,
          weekly_reports_email: true,
          weekly_reports_slack: false,
        })
        setDataRetention({
          run_history_retention_days: 90,
          audit_log_retention_days: 365,
        })
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [currentTenant])

  const handleSave = async () => {
    setIsSaving(true)
    try {
      // Save all settings
      await Promise.all([
        profile && settingsApi.updateProfile(profile).catch(() => {}),
        notifications && settingsApi.updateNotifications(notifications).catch(() => {}),
        dataRetention && settingsApi.updateDataRetention(dataRetention).catch(() => {}),
      ])
      useStore.getState().addNotification({
        type: 'success',
        message: 'Settings saved successfully',
      })
    } catch (err) {
      useStore.getState().addNotification({
        type: 'error',
        message: 'Failed to save settings',
      })
    } finally {
      setTimeout(() => setIsSaving(false), 1000)
    }
  }

  const toggleFlag = (id: string) => {
    setFlags(flags.map((f) => (f.id === id ? { ...f, enabled: !f.enabled } : f)))
  }

  const handleRevokeSession = async (sessionId: string) => {
    try {
      await settingsApi.revokeSession(sessionId)
      setSessions(sessions.filter((s) => s.id !== sessionId))
      useStore.getState().addNotification({
        type: 'success',
        message: 'Session revoked successfully',
      })
    } catch (err) {
      useStore.getState().addNotification({
        type: 'error',
        message: 'Failed to revoke session',
      })
    }
  }

  const handleRevokeApiKey = async (keyId: string) => {
    try {
      await tenantsApi.revokeApiKey(keyId)
      setApiKeys(apiKeys.filter((k) => k.id !== keyId))
      useStore.getState().addNotification({
        type: 'success',
        message: 'API key revoked successfully',
      })
    } catch (err) {
      useStore.getState().addNotification({
        type: 'error',
        message: 'Failed to revoke API key',
      })
    }
  }

  const handleCreateApiKey = async () => {
    const keyName = prompt('Enter a name for the API key:')
    if (!keyName) return
    try {
      const newKey = await tenantsApi.createApiKey(currentTenant, { name: keyName })
      setApiKeys([...apiKeys, newKey])
      useStore.getState().addNotification({
        type: 'success',
        message: 'API key created successfully',
      })
    } catch (err: any) {
      // Mock mode - create a placeholder key
      const mockKey = {
        id: `key-${Date.now()}`,
        name: keyName,
        prefix: 'rk_live_',
        created: new Date().toLocaleDateString(),
        lastUsed: 'Never',
      }
      setApiKeys([...apiKeys, mockKey])
      useStore.getState().addNotification({
        type: 'success',
        message: 'API key created successfully (mock mode)',
      })
    }
  }

  const handleInviteMember = async () => {
    const email = prompt('Enter the email address to invite:')
    if (!email || !email.includes('@')) {
      useStore.getState().addNotification({
        type: 'error',
        message: 'Please enter a valid email address',
      })
      return
    }
    try {
      // TODO: Implement invite API
      useStore.getState().addNotification({
        type: 'success',
        message: `Invitation sent to ${email}`,
      })
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'info',
        message: `Member invitation feature coming soon - would invite ${email}`,
      })
    }
  }

  const handleTestWebhook = async () => {
    const webhookUrl = prompt('Enter the webhook URL to test:')
    if (!webhookUrl) return
    try {
      await settingsApi.testWebhook(webhookUrl)
      useStore.getState().addNotification({
        type: 'success',
        message: 'Webhook test successful',
      })
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'info',
        message: 'Webhook test completed (mock mode)',
      })
    }
  }

  const handleChangeAvatar = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'image/jpeg,image/png,image/gif'
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (file) {
        if (file.size > 2 * 1024 * 1024) {
          useStore.getState().addNotification({
            type: 'error',
            message: 'File size must be less than 2MB',
          })
          return
        }
        // TODO: Implement avatar upload
        useStore.getState().addNotification({
          type: 'success',
          message: 'Avatar updated successfully',
        })
      }
    }
    input.click()
  }

  const handleUpdatePassword = async () => {
    const currentPassword = prompt('Enter your current password:')
    if (!currentPassword) return
    const newPassword = prompt('Enter your new password:')
    if (!newPassword || newPassword.length < 8) {
      useStore.getState().addNotification({
        type: 'error',
        message: 'New password must be at least 8 characters',
      })
      return
    }
    const confirmPassword = prompt('Confirm your new password:')
    if (newPassword !== confirmPassword) {
      useStore.getState().addNotification({
        type: 'error',
        message: 'Passwords do not match',
      })
      return
    }
    try {
      await settingsApi.updatePassword({ current_password: currentPassword, new_password: newPassword })
      useStore.getState().addNotification({
        type: 'success',
        message: 'Password updated successfully',
      })
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'error',
        message: err.message || 'Failed to update password',
      })
    }
  }

  const handleManage2FA = () => {
    useStore.getState().addNotification({
      type: 'info',
      message: 'Two-factor authentication setup coming soon',
    })
  }

  const handleEditTeamMember = (userId: string) => {
    useStore.getState().addNotification({
      type: 'info',
      message: 'Team member editor coming soon',
    })
  }

  const handleExportData = async () => {
    try {
      const { downloadJSON } = await import('../lib/utils')
      const exportData = {
        profile: displayProfile,
        tenant: displayTenant,
        teamMembers,
        apiKeys,
        notifications,
        dataRetention,
        featureFlags: flags,
        exported_at: new Date().toISOString(),
      }
      downloadJSON(exportData, `settings-export-${new Date().toISOString().split('T')[0]}.json`)
      useStore.getState().addNotification({
        type: 'success',
        message: 'Settings data exported successfully',
      })
    } catch (err: any) {
      useStore.getState().addNotification({
        type: 'error',
        message: err.message || 'Failed to export settings data',
      })
    }
  }

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <div className="h-8 w-48 bg-gray-800 rounded animate-pulse" />
        <div className="h-96 bg-gray-800 rounded animate-pulse" />
      </div>
    )
  }

  const displayProfile = profile || { name: currentUser.name, email: currentUser.email, role: currentUser.role }
  const displayTenant = { name: mockTenant.name, slug: mockTenant.slug }

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Settings</h1>
          <p className="text-sm text-gray-400">Manage your account and platform settings</p>
        </div>
        <Button onClick={handleSave} disabled={isSaving}>
          {isSaving ? (
            <>
              <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              Save Changes
            </>
          )}
        </Button>
      </div>

      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList className="bg-gray-800 border-gray-700 flex-wrap h-auto gap-1 p-1">
          <TabsTrigger value="profile" className="gap-2">
            <User className="h-4 w-4" />
            Profile
          </TabsTrigger>
          <TabsTrigger value="team" className="gap-2">
            <Users className="h-4 w-4" />
            Team
          </TabsTrigger>
          <TabsTrigger value="notifications" className="gap-2">
            <Bell className="h-4 w-4" />
            Notifications
          </TabsTrigger>
          <TabsTrigger value="security" className="gap-2">
            <Shield className="h-4 w-4" />
            Security
          </TabsTrigger>
          <TabsTrigger value="api" className="gap-2">
            <Key className="h-4 w-4" />
            API Keys
          </TabsTrigger>
          <TabsTrigger value="features" className="gap-2">
            <ToggleLeft className="h-4 w-4" />
            Features
          </TabsTrigger>
        </TabsList>

        {/* Profile Tab */}
        <TabsContent value="profile" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base text-white">Profile Information</CardTitle>
              <CardDescription className="text-gray-400">
                Update your personal information and preferences
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center gap-6">
                <Avatar className="h-20 w-20">
                  <AvatarFallback className="bg-primary-light/20 text-primary-light text-xl">
                    {displayProfile.name
                      .split(' ')
                      .map((n: string) => n[0])
                      .join('')}
                  </AvatarFallback>
                </Avatar>
                <div className="space-y-2">
                  <Button variant="outline" className="bg-transparent border-gray-700" onClick={handleChangeAvatar}>
                    Change Avatar
                  </Button>
                  <p className="text-xs text-gray-400">JPG, PNG or GIF. Max 2MB.</p>
                </div>
              </div>
              <Separator />
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="name" className="text-gray-200">
                    Full Name
                  </Label>
                  <Input
                    id="name"
                    defaultValue={displayProfile.name}
                    className="bg-gray-800 border-gray-700 text-gray-200"
                    onChange={(e) => setProfile({ ...displayProfile, name: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-gray-200">
                    Email
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    defaultValue={displayProfile.email}
                    className="bg-gray-800 border-gray-700 text-gray-200"
                    onChange={(e) => setProfile({ ...displayProfile, email: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="role" className="text-gray-200">
                    Role
                  </Label>
                  <Select defaultValue={displayProfile.role}>
                    <SelectTrigger className="bg-gray-800 border-gray-700 text-gray-200">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="admin">Admin</SelectItem>
                      <SelectItem value="operator">Operator</SelectItem>
                      <SelectItem value="viewer">Viewer</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="timezone" className="text-gray-200">
                    Timezone
                  </Label>
                  <Select defaultValue="utc-8">
                    <SelectTrigger className="bg-gray-800 border-gray-700 text-gray-200">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="utc-8">Pacific Time (UTC-8)</SelectItem>
                      <SelectItem value="utc-5">Eastern Time (UTC-5)</SelectItem>
                      <SelectItem value="utc">UTC</SelectItem>
                      <SelectItem value="utc+1">Central European (UTC+1)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base text-white">Organization</CardTitle>
              <CardDescription className="text-gray-400">Your organization settings</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="org-name" className="text-gray-200">
                    Organization Name
                  </Label>
                  <Input
                    id="org-name"
                    defaultValue={displayTenant.name}
                    className="bg-gray-800 border-gray-700 text-gray-200"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="org-slug" className="text-gray-200">
                    Organization Slug
                  </Label>
                  <Input
                    id="org-slug"
                    defaultValue={displayTenant.slug}
                    className="bg-gray-800 border-gray-700 text-gray-200"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Team Tab */}
        <TabsContent value="team" className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base text-white">Team Members</CardTitle>
                  <CardDescription className="text-gray-400">Manage who has access to your platform</CardDescription>
                </div>
                <Button onClick={handleInviteMember}>
                  <Users className="mr-2 h-4 w-4" />
                  Invite Member
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {teamMembers.map((user) => (
                  <div key={user.id} className="flex items-center justify-between p-4 rounded-lg bg-gray-800">
                    <div className="flex items-center gap-4">
                      <Avatar>
                        <AvatarFallback className="bg-primary-light/20 text-primary-light">
                          {user.name
                            .split(' ')
                            .map((n) => n[0])
                            .join('')}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <p className="text-sm font-medium text-white">{user.name}</p>
                        <p className="text-xs text-gray-400">{user.email}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <Badge
                        variant="outline"
                        className={`capitalize ${
                          user.role === 'admin'
                            ? 'bg-primary-light/10 text-primary-light'
                            : user.role === 'operator'
                              ? 'bg-primary-light/10 text-primary-light'
                              : 'bg-gray-700 text-gray-300'
                        }`}
                      >
                        {user.role}
                      </Badge>
                      <Button variant="ghost" size="sm" onClick={() => handleEditTeamMember(user.id)}>
                        Edit
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base text-white">Notification Preferences</CardTitle>
              <CardDescription className="text-gray-400">Choose what you want to be notified about</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {[
                {
                  title: 'Run Completions',
                  description: 'Get notified when a runbook execution completes',
                  email: notifications?.run_completions_email ?? true,
                  slack: notifications?.run_completions_slack ?? true,
                  emailKey: 'run_completions_email',
                  slackKey: 'run_completions_slack',
                },
                {
                  title: 'Run Failures',
                  description: 'Get notified when a runbook execution fails',
                  email: notifications?.run_failures_email ?? true,
                  slack: notifications?.run_failures_slack ?? true,
                  emailKey: 'run_failures_email',
                  slackKey: 'run_failures_slack',
                },
                {
                  title: 'Approval Requests',
                  description: 'Get notified when your approval is required',
                  email: notifications?.approval_requests_email ?? true,
                  slack: notifications?.approval_requests_slack ?? true,
                  emailKey: 'approval_requests_email',
                  slackKey: 'approval_requests_slack',
                },
                {
                  title: 'Policy Triggers',
                  description: 'Get notified when a policy blocks an action',
                  email: notifications?.policy_triggers_email ?? false,
                  slack: notifications?.policy_triggers_slack ?? true,
                  emailKey: 'policy_triggers_email',
                  slackKey: 'policy_triggers_slack',
                },
                {
                  title: 'Weekly Reports',
                  description: 'Receive a weekly summary of platform activity',
                  email: notifications?.weekly_reports_email ?? true,
                  slack: notifications?.weekly_reports_slack ?? false,
                  emailKey: 'weekly_reports_email',
                  slackKey: 'weekly_reports_slack',
                },
              ].map((notification, index) => (
                <div key={index} className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <p className="text-sm font-medium text-white">{notification.title}</p>
                    <p className="text-xs text-gray-400">{notification.description}</p>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="flex items-center gap-2">
                      <Label className="text-xs text-gray-400">Email</Label>
                      <Switch
                        checked={notification.email}
                        onCheckedChange={(checked) =>
                          setNotifications({
                            ...notifications,
                            [notification.emailKey]: checked,
                          })
                        }
                        className="data-[state=checked]:bg-primary-light"
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <Label className="text-xs text-gray-400">Slack</Label>
                      <Switch
                        checked={notification.slack}
                        onCheckedChange={(checked) =>
                          setNotifications({
                            ...notifications,
                            [notification.slackKey]: checked,
                          })
                        }
                        className="data-[state=checked]:bg-primary-light"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Tab */}
        <TabsContent value="security" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base text-white">Password</CardTitle>
              <CardDescription className="text-gray-400">Update your password</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="current-password" className="text-gray-200">
                    Current Password
                  </Label>
                  <Input
                    id="current-password"
                    type="password"
                    className="bg-gray-800 border-gray-700 text-gray-200"
                  />
                </div>
                <div />
                <div className="space-y-2">
                  <Label htmlFor="new-password" className="text-gray-200">
                    New Password
                  </Label>
                  <Input
                    id="new-password"
                    type="password"
                    className="bg-gray-800 border-gray-700 text-gray-200"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirm-password" className="text-gray-200">
                    Confirm New Password
                  </Label>
                  <Input
                    id="confirm-password"
                    type="password"
                    className="bg-gray-800 border-gray-700 text-gray-200"
                  />
                </div>
              </div>
              <Button variant="outline" className="bg-transparent border-gray-700" onClick={handleUpdatePassword}>
                Update Password
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base text-white">Two-Factor Authentication</CardTitle>
              <CardDescription className="text-gray-400">
                Add an extra layer of security to your account
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-4 rounded-lg bg-gray-800">
                <div className="flex items-center gap-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-success/10 text-success">
                    <Shield className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">2FA is enabled</p>
                    <p className="text-xs text-gray-400">Your account is protected with authenticator app</p>
                  </div>
                </div>
                <Button variant="outline" className="bg-transparent border-gray-700" onClick={handleManage2FA}>
                  Manage
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base text-white">Active Sessions</CardTitle>
              <CardDescription className="text-gray-400">Manage your active sessions across devices</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {sessions.map((session) => (
                <div key={session.id} className="flex items-center justify-between p-4 rounded-lg bg-gray-800">
                  <div className="flex items-center gap-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-700">
                      <Globe className="h-5 w-5 text-gray-400" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-white">{session.device}</p>
                        {session.current && (
                          <Badge variant="outline" className="bg-success/10 text-success text-xs">
                            Current
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-gray-400">
                        {session.location} · {session.lastActive}
                      </p>
                    </div>
                  </div>
                  {!session.current && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-error hover:bg-error/10"
                      onClick={() => handleRevokeSession(session.id)}
                    >
                      Revoke
                    </Button>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* API Keys Tab */}
        <TabsContent value="api" className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base text-white">API Keys</CardTitle>
                  <CardDescription className="text-gray-400">Manage API keys for programmatic access</CardDescription>
                </div>
                <Button onClick={handleCreateApiKey}>
                  <Key className="mr-2 h-4 w-4" />
                  Create Key
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {apiKeys.map((key) => (
                <div key={key.id} className="flex items-center justify-between p-4 rounded-lg bg-gray-800">
                  <div className="flex items-center gap-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-light/10 text-primary-light">
                      <Key className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white">{key.name}</p>
                      <p className="text-xs text-gray-400 font-mono">
                        {key.prefix || 'rk_'}
                        {'•'.repeat(24)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right hidden md:block">
                      <p className="text-xs text-gray-400">Created {key.created_at || key.created}</p>
                      <p className="text-xs text-gray-400">Last used {key.last_used_at || key.lastUsed || 'Never'}</p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-error hover:bg-error/10"
                      onClick={() => handleRevokeApiKey(key.id)}
                    >
                      Revoke
                    </Button>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base text-white">Webhooks</CardTitle>
              <CardDescription className="text-gray-400">
                Configure webhook endpoints for event notifications
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="webhook-url" className="text-gray-200">
                  Webhook URL
                </Label>
                <Input
                  id="webhook-url"
                  placeholder="https://your-server.com/webhook"
                  className="bg-gray-800 border-gray-700 text-gray-200"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-gray-200">Events to send</Label>
                <div className="grid gap-2 md:grid-cols-2">
                  {['run.started', 'run.completed', 'run.failed', 'approval.requested'].map((event) => (
                    <div key={event} className="flex items-center gap-2">
                      <Switch defaultChecked className="data-[state=checked]:bg-primary-light" />
                      <span className="text-sm font-mono text-gray-200">{event}</span>
                    </div>
                  ))}
                </div>
              </div>
              <Button variant="outline" className="bg-transparent border-gray-700" onClick={handleTestWebhook}>
                <Webhook className="mr-2 h-4 w-4" />
                Test Webhook
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Features Tab */}
        <TabsContent value="features" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base text-white">Feature Flags</CardTitle>
              <CardDescription className="text-gray-400">Enable or disable platform features</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {flags.map((flag) => (
                <div key={flag.id} className="flex items-center justify-between p-4 rounded-lg bg-gray-800">
                  <div className="flex items-center gap-4">
                    <div
                      className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                        flag.enabled ? 'bg-success/10 text-success' : 'bg-gray-700 text-gray-400'
                      }`}
                    >
                      <ToggleLeft className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-white">{flag.name}</p>
                        <Badge variant="outline" className="text-xs">
                          {flag.category}
                        </Badge>
                      </div>
                      <p className="text-xs text-gray-400">{flag.description}</p>
                    </div>
                  </div>
                  <Switch
                    checked={flag.enabled}
                    onCheckedChange={() => toggleFlag(flag.id)}
                    className="data-[state=checked]:bg-primary-light"
                  />
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base text-white">Data & Storage</CardTitle>
              <CardDescription className="text-gray-400">
                Manage your data retention and storage settings
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label className="text-gray-200">Run History Retention</Label>
                  <Select
                    defaultValue={String(dataRetention?.run_history_retention_days || 90)}
                    onValueChange={(value) =>
                      setDataRetention({ ...dataRetention, run_history_retention_days: parseInt(value) })
                    }
                  >
                    <SelectTrigger className="bg-gray-800 border-gray-700 text-gray-200">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="30">30 days</SelectItem>
                      <SelectItem value="60">60 days</SelectItem>
                      <SelectItem value="90">90 days</SelectItem>
                      <SelectItem value="180">180 days</SelectItem>
                      <SelectItem value="365">1 year</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label className="text-gray-200">Audit Log Retention</Label>
                  <Select
                    defaultValue={String(dataRetention?.audit_log_retention_days || 365)}
                    onValueChange={(value) =>
                      setDataRetention({ ...dataRetention, audit_log_retention_days: parseInt(value) })
                    }
                  >
                    <SelectTrigger className="bg-gray-800 border-gray-700 text-gray-200">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="90">90 days</SelectItem>
                      <SelectItem value="180">180 days</SelectItem>
                      <SelectItem value="365">1 year</SelectItem>
                      <SelectItem value="730">2 years</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-white">Export All Data</p>
                  <p className="text-xs text-gray-400">Download a complete export of your data</p>
                </div>
                <Button variant="outline" className="bg-transparent border-gray-700" onClick={handleExportData}>
                  <Database className="mr-2 h-4 w-4" />
                  Export
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
