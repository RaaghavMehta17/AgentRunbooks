import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import { ToastContainer } from '../ui/Toast'

export function AppLayout() {
  return (
    <div className="flex h-screen bg-[#0f172a]">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-y-auto bg-[#0f172a]">
          <Outlet />
        </main>
      </div>
      <ToastContainer />
    </div>
  )
}

