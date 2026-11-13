import { usePapersStore } from '../../stores/papers'
import { useState } from 'react'

export default function Toolbar() {
  const filter = usePapersStore((s) => s.filter)
  const setFilter = usePapersStore((s) => s.setFilter)
  const importPaper = usePapersStore((s) => s.importPaper)
  const [importing, setImporting] = useState(false)

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilter({ search: e.target.value })
  }

  const handleImport = async () => {
    if (window.electronAPI) {
      const files = await window.electronAPI.openFileDialog({ multiple: true })
      if (files.length > 0) {
        setImporting(true)
        for (const f of files) {
          try {
            await importPaper(f)
          } catch (err) {
            console.error('导入失败:', f, err)
          }
        }
        setImporting(false)
        window.electronAPI.notify('导入完成', `成功导入 ${files.length} 篇论文`)
      }
    }
  }

  const handleReadFilter = (val: string) => {
    setFilter({ read: val })
  }

  return (
    <div className="h-12 bg-white border-b border-gray-200 flex items-center px-4 gap-3 shrink-0">
      {/* 搜索 */}
      <div className="relative flex-1 max-w-md">
        <svg className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          type="text"
          placeholder="搜索论文标题、作者...  (按 / 聚焦)"
          value={filter.search}
          onChange={handleSearch}
          className="w-full pl-9 pr-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          onKeyDown={(e) => {
            if (e.key === 'Escape') setFilter({ search: '' })
          }}
        />
      </div>

      {/* 排序 */}
      <select
        value={filter.sort}
        onChange={(e) => setFilter({ sort: e.target.value })}
        className="text-sm border border-gray-300 rounded-md px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="date_added">加入时间</option>
        <option value="year">发表年份</option>
        <option value="title">标题</option>
        <option value="venue">会议</option>
      </select>

      {/* 排序方向 */}
      <button
        onClick={() => setFilter({ order: filter.order === 'desc' ? 'asc' : 'desc' })}
        className="text-sm text-gray-500 hover:text-gray-700 p-1"
        title={filter.order === 'desc' ? '降序' : '升序'}
      >
        {filter.order === 'desc' ? '↓' : '↑'}
      </button>

      <div className="w-px h-5 bg-gray-300" />

      {/* 已读筛选 */}
      <div className="flex rounded-md border border-gray-300 overflow-hidden">
        {(['all', 'unread', 'read'] as const).map((v) => (
          <button
            key={v}
            onClick={() => handleReadFilter(v)}
            className={`px-3 py-1 text-xs ${filter.read === v ? 'bg-blue-500 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
          >
            {v === 'all' ? '全部' : v === 'unread' ? '未读' : '已读'}
          </button>
        ))}
      </div>

      <div className="flex-1" />

      {/* 刷新按钮 */}
      <button
        onClick={() => {
          usePapersStore.getState().fetchPapers()
          usePapersStore.getState().fetchVenues()
          usePapersStore.getState().fetchTags()
        }}
        className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md"
        title="刷新"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
      </button>

      {/* 导入按钮 */}
      <button
        onClick={handleImport}
        disabled={importing}
        className="flex items-center gap-1 px-4 py-1.5 bg-blue-500 text-white text-sm rounded-md hover:bg-blue-600 disabled:opacity-50"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
        {importing ? '导入中...' : '导入 PDF'}
      </button>
    </div>
  )
}
