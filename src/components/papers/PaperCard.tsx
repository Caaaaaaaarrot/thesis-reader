import { Paper, usePapersStore } from '../../stores/papers'

interface Props {
  paper: Paper
}

export default function PaperCard({ paper }: Props) {
  const selectPaper = usePapersStore((s) => s.selectPaper)
  const updatePaper = usePapersStore((s) => s.updatePaper)
  const selectedId = usePapersStore((s) => s.selectedId)

  const isSelected = selectedId === paper.id
  const hasSpeedRead = paper.speed_read?.status === 'success'

  const toggleRead = (e: React.MouseEvent) => {
    e.stopPropagation()
    updatePaper(paper.id, { read: !paper.read } as Partial<Paper>)
  }

  return (
    <div
      onClick={() => selectPaper(isSelected ? null : paper.id)}
      className={`bg-white rounded-lg border p-3 cursor-pointer transition-all hover:shadow-md ${isSelected ? 'border-blue-400 ring-2 ring-blue-200 shadow-md' : 'border-gray-200'}`}
    >
      {/* 顶部：venue + year + read */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {paper.venue && (
            <span className="px-1.5 py-0.5 text-[10px] font-medium bg-gray-100 text-gray-600 rounded">
              {paper.venue}
            </span>
          )}
          {paper.year && (
            <span className="text-[10px] text-gray-400">{paper.year}</span>
          )}
        </div>
        <button
          onClick={toggleRead}
          className={`w-2.5 h-2.5 rounded-full ${paper.read ? 'bg-green-400' : 'bg-gray-300 hover:bg-gray-400'}`}
          title={paper.read ? '已读' : '未读'}
        />
      </div>

      {/* 标题 */}
      <h3 className="text-sm font-medium text-gray-800 line-clamp-2 mb-1.5 leading-snug">
        {paper.title || '(无标题)'}
      </h3>

      {/* 作者 */}
      {paper.authors && (
        <p className="text-[11px] text-gray-400 line-clamp-1 mb-2">{paper.authors}</p>
      )}

      {/* 底部：tags + badge */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1 flex-wrap">
          {paper.tags.slice(0, 3).map((t) => (
            <span key={t} className="px-1.5 py-0.5 text-[10px] bg-blue-50 text-blue-500 rounded">
              {t}
            </span>
          ))}
          {paper.tags.length > 3 && (
            <span className="text-[10px] text-gray-400">+{paper.tags.length - 3}</span>
          )}
        </div>
        {hasSpeedRead && (
          <span className="text-[10px] text-purple-500 font-medium">AI 已读</span>
        )}
      </div>

      {/* 页数 */}
      {paper.page_count > 0 && (
        <div className="mt-2 text-[10px] text-gray-300">{paper.page_count} 页</div>
      )}
    </div>
  )
}
