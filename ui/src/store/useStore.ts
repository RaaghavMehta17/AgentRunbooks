import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  email: string
  name?: string
  roles: string[]
}

interface AppState {
  // Auth
  user: User | null
  token: string | null
  setUser: (user: User | null) => void
  setToken: (token: string | null) => void

  // Theme
  theme: 'dark' | 'light'
  toggleTheme: () => void

  // Context
  currentTenant: string | null
  currentProject: string | null
  setCurrentTenant: (tenant: string | null) => void
  setCurrentProject: (project: string | null) => void

  // Notifications
  notifications: Array<{
    id: string
    type: 'success' | 'error' | 'warning' | 'info'
    message: string
    timestamp: Date
  }>
  addNotification: (notification: Omit<AppState['notifications'][0], 'id' | 'timestamp'>) => void
  removeNotification: (id: string) => void

  // Feature flags
  featureFlags: Record<string, boolean>
  setFeatureFlag: (flag: string, value: boolean) => void
}

export const useStore = create<AppState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      theme: 'dark',
      currentTenant: null,
      currentProject: null,
      notifications: [],
      featureFlags: {},

      setUser: (user) => set({ user }),
      setToken: (token) => set({ token }),
      toggleTheme: () => set((state) => ({ theme: state.theme === 'dark' ? 'light' : 'dark' })),
      setCurrentTenant: (tenant) => set({ currentTenant: tenant }),
      setCurrentProject: (project) => set({ currentProject: project }),
      addNotification: (notification) =>
        set((state) => ({
          notifications: [
            ...state.notifications,
            { ...notification, id: Date.now().toString(), timestamp: new Date() },
          ],
        })),
      removeNotification: (id) =>
        set((state) => ({
          notifications: state.notifications.filter((n) => n.id !== id),
        })),
      setFeatureFlag: (flag, value) =>
        set((state) => ({
          featureFlags: { ...state.featureFlags, [flag]: value },
        })),
    }),
    {
      name: 'ops-agents-storage',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        theme: state.theme,
        currentTenant: state.currentTenant,
        currentProject: state.currentProject,
      }),
    }
  )
)

