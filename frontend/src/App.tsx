import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { RequireStudent } from './session/StudentContext'
import Home from './pages/Home'
import Login from './pages/Login'
import Practice from './pages/Practice'
import ProgressPage from './pages/Progress'
import SubjectPage from './pages/Subject'
import TopicPage from './pages/Topic'

const guard = (el: React.ReactNode) => <RequireStudent>{el}</RequireStudent>

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/login" element={<Login />} />
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
