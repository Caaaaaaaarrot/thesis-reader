import { usePapersStore } from '../../stores/papers'
import { useLibraryStore } from '../../stores/library'

interface Props {
  onSettingsClick: () => void
}

export default function Sidebar({ onSettingsClick }: Props) {
  const venues = usePapersStore((s) => s.venues)
  const tags = usePapersStore((s) => s.tags)
  const filter = usePapersStore((s) => s.filter)
  const setFilter = usePapersStore((s) => s.setFilter)
  const papers = usePapersStore((s) => s.papers)
  const view = usePapersStore((s) => s.view)
  const setView = usePapersStore((s) => s.setView)
  const library = useLibraryStore((s) => s.status)
  const libraryError = useLibraryStore((s) => s.error)

  const total = papers.length
  const unread = papers.filter((p) => !p.read).length
  const read = papers.filter((p) => p.read).length

  return (
    <div className="w-56 bg-white border-r border-gray-200 flex flex-col overflow-hidden shrink-0">
      {/* 概览 */}
      <div className="p-3 border-b border-gray-100">
        <div className="text-xs font-semibold text-gray-400 uppercase mb-2">概览</div>
        <div className="grid grid-cols-2 gap-2 text-center">
          <div className="bg-gray-50 rounded p-1.5">
            <div className="text-lg font-bold text-gray-800">{library?.paper_count ?? total}</div>
            <div className="text-[10px] text-gray-400">全部</div>
          </div>
          <div className="bg-blue-50 rounded p-1.5">
            <div className="text-lg font-bold text-blue-600">{unread}</div>
            <div className="text-[10px] text-blue-400">未读</div>
          </div>
        </div>
      </div>

      <nav className="px-3 pt-3 space-y-1" aria-label="论文视图">
        {(['list', 'graph'] as const).map((mode) => (
          <button key={mode} onClick={() => setView(mode)}
            className={`w-full text-left px-3 py-2 text-sm rounded-md ${view === mode ? 'bg-blue-50 text-blue-600 font-medium' : 'text-gray-500 hover:bg-gray-50'}`}>
            {mode === 'list' ? '▤  论文列表' : '⌘  知识图谱'}
          </button>
        ))}
      </nav>

      {/* 会议 */}
      <div className="flex-1 overflow-auto p-3">
        <div className="text-xs font-semibold text-gray-400 uppercase mb-2">会议/期刊</div>
        <div className="space-y-0.5">
          <button
            onClick={() => setFilter({ venue: '' })}
            className={`w-full text-left px-2 py-1 text-xs rounded ${!filter.venue ? 'bg-blue-50 text-blue-600 font-medium' : 'text-gray-600 hover:bg-gray-50'}`}
          >
            全部 ({total})
          </button>
          {venues.map((v) => (
            <button
              key={v.name}
              onClick={() => setFilter({ venue: filter.venue === v.name ? '' : v.name })}
              className={`w-full text-left px-2 py-1 text-xs rounded flex justify-between ${filter.venue === v.name ? 'bg-blue-50 text-blue-600 font-medium' : 'text-gray-600 hover:bg-gray-50'}`}
            >
              <span className="truncate">{v.name}</span>
              <span className="text-gray-400 ml-1">{v.count}</span>
            </button>
          ))}
        </div>

        {/* 标签 */}
        {tags.length > 0 && (
          <>
            <div className="text-xs font-semibold text-gray-400 uppercase mt-4 mb-2">标签</div>
            <div className="space-y-0.5">
              <button
                onClick={() => setFilter({ tag: '' })}
                className={`w-full text-left px-2 py-1 text-xs rounded ${!filter.tag ? 'bg-blue-50 text-blue-600 font-medium' : 'text-gray-600 hover:bg-gray-50'}`}
              >
                全部
              </button>
              {tags.map((t) => (
                <button
                  key={t.name}
                  onClick={() => setFilter({ tag: filter.tag === t.name ? '' : t.name })}
                  className={`w-full text-left px-2 py-1 text-xs rounded flex justify-between ${filter.tag === t.name ? 'bg-blue-50 text-blue-600 font-medium' : 'text-gray-600 hover:bg-gray-50'}`}
                >
                  <span className="truncate">{t.name}</span>
                  <span className="text-gray-400 ml-1">{t.count}</span>
                </button>
              ))}
            </div>
          </>
        )}
      </div>

      {/* 设置 */}
      <div className="p-3 border-t border-gray-100">
        <div className="px-2 mb-2 text-[11px] text-gray-400" title={libraryError || library?.errors.join('\n') || library?.directory}>
          <span className={`inline-block w-1.5 h-1.5 rounded-full mr-1.5 ${libraryError || library?.errors.length ? 'bg-amber-400' : library?.running ? 'bg-green-400' : 'bg-gray-300'}`} />
          {libraryError ? '目录连接中断' : library?.syncing ? '正在同步论文目录…' : library?.errors.length ? '部分文件等待重试' : library?.running ? '论文目录自动同步中' : '正在连接论文目录…'}
        </div>
        <button
          onClick={onSettingsClick}
          className="w-full text-left px-2 py-1.5 text-xs text-gray-500 hover:bg-gray-50 rounded flex items-center gap-1.5"
        >
          <span className="text-gray-400">⚙</span>
          设置
        </button>
      </div>
    </div>
  )
}
