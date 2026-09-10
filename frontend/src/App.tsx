import { Navigate, Route, Routes } from 'react-router-dom'
import Navbar from './components/Navbar'
import ProtectedRoute from './components/ProtectedRoute'
import DashboardPage from './pages/DashboardPage'
import GroupDetailPage from './pages/GroupDetailPage'
import GroupFormPage from './pages/GroupFormPage'
import GroupsPage from './pages/GroupsPage'
import LoginPage from './pages/LoginPage'
import NoteDetailPage from './pages/NoteDetailPage'
import NoteFormPage from './pages/NoteFormPage'
import NotesPage from './pages/NotesPage'
import RegisterPage from './pages/RegisterPage'

export default function App() {
  return (
    <div className="app">
      <Navbar />
      <main className="content">
        <Routes>
          <Route path="/" element={<Navigate to="/notes" replace />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          <Route path="/notes" element={<NotesPage />} />
          <Route
            path="/notes/new"
            element={
              <ProtectedRoute>
                <NoteFormPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/notes/:id/edit"
            element={
              <ProtectedRoute>
                <NoteFormPage />
              </ProtectedRoute>
            }
          />
          <Route path="/notes/:id" element={<NoteDetailPage />} />

          <Route path="/groups" element={<GroupsPage />} />
          <Route
            path="/groups/new"
            element={
              <ProtectedRoute>
                <GroupFormPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/groups/:id/edit"
            element={
              <ProtectedRoute>
                <GroupFormPage />
              </ProtectedRoute>
            }
          />
          <Route path="/groups/:id" element={<GroupDetailPage />} />

          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />

          <Route path="*" element={<p className="center muted">Page not found.</p>} />
        </Routes>
      </main>
      <footer className="footer">
        StudyHub — FastAPI + React.{' '}
        <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">
          Interactive API docs
        </a>
      </footer>
    </div>
  )
}
