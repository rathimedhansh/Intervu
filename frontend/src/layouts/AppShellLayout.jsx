import { Outlet } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import MobileNav from '../components/MobileNav'
import PageTransition from '../components/PageTransition'

// Application shell for every authenticated page: fixed desktop sidebar +
// mobile top bar/drawer, wrapping a consistent max-width content column.
// ProtectedRoute still gates each individual route element, so an
// unauthenticated visitor never sees this shell render around a redirect.
function AppShellLayout() {
  return (
    <div className="min-h-screen bg-canvas">
      <Sidebar />
      <MobileNav />
      <main className="md:pl-60">
        <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 md:px-8 md:py-8">
          <PageTransition>
            <Outlet />
          </PageTransition>
        </div>
      </main>
    </div>
  )
}

export default AppShellLayout
