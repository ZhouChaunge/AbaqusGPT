import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import ChatPage from './pages/ChatPage'
import DiagnosePage from './pages/DiagnosePage'
import GeneratePage from './pages/GeneratePage'
import KnowledgePage from './pages/KnowledgePage'
import MonitorPage from './pages/MonitorPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<ChatPage />} />
          <Route path="monitor" element={<MonitorPage />} />
          <Route path="diagnose" element={<DiagnosePage />} />
          <Route path="generate" element={<GeneratePage />} />
          <Route path="knowledge" element={<KnowledgePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
