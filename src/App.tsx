import { useEffect, useState } from 'react'
import { usePapersStore } from './stores/papers'
import { initApiClient } from './api/client'
import Sidebar from './components/layout/Sidebar'
import Toolbar from './components/layout/Toolbar'
import PaperList from './components/papers/PaperList'
import PaperDetail from './components/papers/PaperDetail'
import SettingsModal from './components/settings/SettingsModal'

export default function App() {
  const [backendReady, setBackendReady] = useState(false)
  const [initError, setInitError] = useState('')
  const [settingsOpen, setSettingsOpen] = useState(false)
  const fetchPapers = usePapersStore((s) => s.fetchPapers)
  const fetchVenues = usePapersStore((s) => s.fetchVenues)
  const fetchTags = usePapersStore((s) => s.fetchTags)
  const selectedId = usePapersStore((s) => s.selectedId)

  useEffect(() => {
    initApiClient()
      .then(() => {
        setBackendReady(true)
        fetchPapers()
        fetchVenues()
        fetchTags()
      })
      .catch((err) => setInitError(`后端连接失败: ${err.message}`))
  }, [fetchPapers, fetchVenues, fetchTags])

  if (initError) {
    return (
      <div className="flex items-center justify-center h-screen text-red-500">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-2">无法连接到后端</h1>
          <p className="text-gray-500">{initError}</p>
        </div>
      </div>
    )
  }

  if (!backendReady) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center text-gray-400">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p>正在连接后端服务...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar onSettingsClick={() => setSettingsOpen(true)} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Toolbar />
        <div className="flex-1 flex overflow-hidden">
          <div className={`${selectedId ? 'flex-1' : 'flex-1'} overflow-auto p-4`}>
            <PaperList />
          </div>
          {selectedId && (
            <div className="w-[420px] border-l border-gray-200 bg-white overflow-auto">
              <PaperDetail />
            </div>
          )}
        </div>
      </div>
      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  )
}
