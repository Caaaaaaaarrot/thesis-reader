import { useState, useEffect } from 'react'

interface MenuItem {
  label: string
  separator?: boolean
  action?: () => void
  accelerator?: string
}

export default function TitleBar() {
  const isElectron = typeof window !== 'undefined' && !!window.electronAPI
  const [openMenu, setOpenMenu] = useState<string | null>(null)

  useEffect(() => {
    if (!openMenu) return
    const close = () => setOpenMenu(null)
    document.addEventListener('click', close)
    return () => document.removeEventListener('click', close)
  }, [openMenu])

  if (!isElectron) return null

  const handleImport = async () => {
    setOpenMenu(null)
    const files = await window.electronAPI!.openFileDialog({ multiple: true })
    if (files?.length) {
      const { usePapersStore } = await import('../../stores/papers')
      for (const f of files) {
        try { await usePapersStore.getState().importPaper(f) } catch { /* ignore */ }
      }
      window.electronAPI!.notify('导入完成', `成功导入 ${files.length} 篇论文`)
    }
  }

  const handleRefresh = async () => {
    setOpenMenu(null)
    const { usePapersStore } = await import('../../stores/papers')
    usePapersStore.getState().fetchPapers()
    usePapersStore.getState().fetchVenues()
    usePapersStore.getState().fetchTags()
  }

  const menus: Record<string, MenuItem[]> = {
    '文件': [
      { label: '导入 PDF...', accelerator: 'Ctrl+O', action: handleImport },
      { label: '', separator: true },
      { label: '退出', accelerator: 'Alt+F4', action: () => { setOpenMenu(null); window.electronAPI?.quitApp() } },
    ],
    '视图': [
      { label: '刷新', accelerator: 'Ctrl+R', action: handleRefresh },
      { label: '', separator: true },
      { label: '开发者工具', accelerator: 'F12', action: () => { setOpenMenu(null); window.electronAPI?.toggleDevTools() } },
    ],
    '帮助': [
      { label: '关于 Thesis-Reader', action: () => { setOpenMenu(null); window.electronAPI?.showAbout() } },
    ],
  }

  const menuLabels = Object.keys(menus)

  return (
    <div
      className="h-9 bg-white border-b border-gray-200 flex items-center shrink-0 select-none"
      style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
    >
      <div className="flex items-center gap-2 px-3">
        <span className="text-xs text-gray-500 font-medium">Thesis-Reader</span>
      </div>

      <div className="flex items-center h-full" style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}>
        {menuLabels.map((label) => {
          const items = menus[label]
          return (
            <div key={label} className="relative h-full">
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setOpenMenu(openMenu === label ? null : label)
                }}
                className={`h-full px-3 text-xs transition-colors ${
                  openMenu === label ? 'bg-blue-50 text-blue-600' : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {label}
              </button>
              {openMenu === label && (
                <div className="absolute top-full left-0 mt-0.5 bg-white border border-gray-200 rounded-md shadow-lg py-1 min-w-[190px] z-[100]">
                  {items.map((item, i) =>
                    item.separator ? (
                      <div key={i} className="my-1 border-t border-gray-100" />
                    ) : (
                      <button
                        key={i}
                        onClick={(e) => { e.stopPropagation(); item.action?.() }}
                        className="w-full text-left px-4 py-1.5 text-xs text-gray-700 hover:bg-blue-50 hover:text-blue-600 flex items-center justify-between"
                      >
                        <span>{item.label}</span>
                        {item.accelerator && (
                          <span className="text-[10px] text-gray-400 ml-6">{item.accelerator}</span>
                        )}
                      </button>
                    )
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
