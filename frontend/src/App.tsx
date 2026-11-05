import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import AdminLayout from './components/AdminLayout'
import Layout from './components/Layout'
import { RequireAdmin } from './session/AdminContext'
import { RequireStudent } from './session/StudentContext'
import { Spinner } from './components/ui'
import Home from './pages/Home'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Practice from './pages/Practice'
import ProgressPage from './pages/Progress'
import SubjectPage from './pages/Subject'
import TopicPage from './pages/Topic'

// Admin pages load only when an admin opens them (pupils never download them).
const BooksPage = lazy(() => import('./pages/admin/Books'))
const EvaluationPage = lazy(() => import('./pages/Evaluation'))

const guard = (el: React.ReactNode) => <RequireStudent>{el}</RequireStudent>
const admin = (el: React.ReactNode) => <Suspense fallback={<Spinner />}>{el}</Suspense>

export default function App() {
  return (
    <Routes>
      {/* Public pages: full-screen, without the sidebar */}
      <Route path="/landing" element={<Landing />} />
      <Route path="/login" element={<Login />} />

      {/* Admin: its own sign-in and layout (English, for teachers and the researcher) */}
      <Route
        path="/admin"
        element={
          <RequireAdmin>
            <AdminLayout />
          </RequireAdmin>
        }
      >
        <Route index element={<Navigate to="penilaian" replace />} />
        <Route path="penilaian" element={admin(<EvaluationPage />)} />
        <Route path="buku" element={admin(<BooksPage />)} />
      </Route>
      <Route path="/penilaian" element={<Navigate to="/admin/penilaian" replace />} />

      <Route element={<Layout />}>
        <Route path="/" element={guard(<Home />)} />
        <Route path="/subjek/:subjectId" element={guard(<SubjectPage />)} />
        <Route path="/topik/:topicId" element={guard(<TopicPage />)} />
        <Route path="/latihan/:topicId/:level" element={guard(<Practice />)} />
        <Route path="/kemajuan" element={guard(<ProgressPage />)} />
        <Route path="*" element={guard(<Home />)} />
      </Route>
    </Routes>
  )
}
