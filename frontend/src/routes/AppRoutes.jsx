import { Routes, Route } from 'react-router-dom'
import AppShellLayout from '../layouts/AppShellLayout'
import PublicLayout from '../layouts/PublicLayout'
import ProtectedRoute from '../components/ProtectedRoute'
import LandingPage from '../pages/LandingPage'
import LoginPage from '../pages/LoginPage'
import SignupPage from '../pages/SignupPage'
import ForgotPasswordPage from '../pages/ForgotPasswordPage'
import ResetPasswordPage from '../pages/ResetPasswordPage'
import InterviewSetupPage from '../pages/InterviewSetupPage'
import InterviewPage from '../pages/InterviewPage'
import ResultsPage from '../pages/ResultsPage'
import DashboardPage from '../pages/DashboardPage'
import HistoryPage from '../pages/HistoryPage'
import PracticePage from '../pages/PracticePage'
import PerformancePage from '../pages/PerformancePage'
import ProfilePage from '../pages/ProfilePage'
import SettingsPage from '../pages/SettingsPage'
import NotFoundPage from '../pages/NotFoundPage'

function AppRoutes() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>

      <Route element={<AppShellLayout />}>
        <Route
          path="/setup"
          element={
            <ProtectedRoute>
              <InterviewSetupPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/interview/:interviewId"
          element={
            <ProtectedRoute>
              <InterviewPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/results/:interviewId"
          element={
            <ProtectedRoute>
              <ResultsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/history"
          element={
            <ProtectedRoute>
              <HistoryPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/practice"
          element={
            <ProtectedRoute>
              <PracticePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/performance"
          element={
            <ProtectedRoute>
              <PerformancePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <ProfilePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <SettingsPage />
            </ProtectedRoute>
          }
        />
      </Route>
    </Routes>
  )
}

export default AppRoutes
