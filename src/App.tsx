import { useEffect, useState } from 'react'
import { usePapersStore } from './stores/papers'
import { initApiClient } from './api/client'
import { useFileDrop } from './hooks/useFileDrop'
import TitleBar from './components/layout/TitleBar'
import Sidebar from './components/layout/Sidebar'
import Toolbar from './components/layout/Toolbar'
import PaperList from './components/papers/PaperList'
import PaperDetail from './components/papers/PaperDetail'
import SettingsModal from './components/settings/SettingsModal'
import KnowledgeGraph from './components/graph/KnowledgeGraph'
import { useLibrarySync } from './hooks/useLibrarySync'

export default function App() {
  const [backendReady, setBackendReady] = useState(false)
  const [initError, setInitError] = useState('')
  const [settingsOpen, setSettingsOpen] = useState(false)
  const fetchPapers = usePapersStore((s) => s.fetchPapers)
  const fetchVenues = usePapersStore((s) => s.fetchVenues)
  const fetchTags = usePapersStore((s) => s.fetchTags)
  const selectedId = usePapersStore((s) => s.selectedId)
  const view = usePapersStore((s) => s.view)

  useLibrarySync(backendReady)

  const { isDragging, onDragOver, onDragLeave, onDrop } = useFileDrop()

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

  // 托盘导航
  useEffect(() => {
    if (window.electronAPI?.onNavigatePaper) {
      window.electronAPI.onNavigatePaper((paperId: string) => {
        usePapersStore.getState().selectPaper(paperId)
        fetchPapers()
      })
    }
  }, [fetchPapers])

  // 菜单导入
  useEffect(() => {
    if (window.electronAPI?.onMenuImport) {
      window.electronAPI.onMenuImport(async () => {
        const files = await window.electronAPI!.openFileDialog({ multiple: true })
        if (files && files.length > 0) {
          for (const f of files) {
            try { await usePapersStore.getState().importPaper(f) } catch { /* ignore */ }
          }
          window.electronAPI!.notify('导入完成', `成功导入 ${files.length} 篇论文`)
        }
      })
    }
  }, [])

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
    <div
      className="flex flex-col h-screen bg-gray-50"
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      {/* 拖放视觉反馈 */}
      {isDragging && (
        <div className="fixed inset-0 z-50 bg-blue-500/10 border-4 border-dashed border-blue-500 pointer-events-none flex items-center justify-center">
          <div className="bg-white rounded-xl shadow-lg px-8 py-6 text-center">
            <svg className="w-12 h-12 mx-auto mb-3 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4v16m8-8H4" />
            </svg>
            <p className="text-sm font-medium text-gray-700">释放以导入 PDF</p>
            <p className="text-xs text-gray-400 mt-1">支持同时导入多篇论文</p>
          </div>
        </div>
      )}
      <TitleBar />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar onSettingsClick={() => setSettingsOpen(true)} />
        <div className="flex-1 flex flex-col overflow-hidden">
          <Toolbar />
          <div className="flex-1 flex overflow-hidden">
            <div className={`flex-1 min-w-0 ${view === 'graph' ? 'overflow-hidden' : 'overflow-auto p-4'}`}>
              {view === 'graph' ? <KnowledgeGraph /> : <PaperList />}
            </div>
            {selectedId && (
              <div className="w-[420px] border-l border-gray-200 bg-white overflow-auto">
                <PaperDetail />
              </div>
            )}
          </div>
        </div>
      </div>
      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  )
}
