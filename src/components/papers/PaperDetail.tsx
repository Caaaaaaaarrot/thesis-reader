import { usePapersStore, Paper } from '../../stores/papers'
import { useState } from 'react'
import SpeedReadView from '../speedread/SpeedReadView'

export default function PaperDetail() {
  const papers = usePapersStore((s) => s.papers)
  const selectedId = usePapersStore((s) => s.selectedId)
  const updatePaper = usePapersStore((s) => s.updatePaper)
  const deletePaper = usePapersStore((s) => s.deletePaper)
  const selectPaper = usePapersStore((s) => s.selectPaper)
  const reindexPaper = usePapersStore((s) => s.reindexPaper)
  const [editing, setEditing] = useState(false)
  const [reindexing, setReindexing] = useState(false)

  const paper = papers.find((p) => p.id === selectedId)
  if (!paper) return null

  const handleSave = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const form = e.currentTarget
    const formData = new FormData(form)
    const data: Partial<Paper> = {
      title: formData.get('title') as string,
      authors: formData.get('authors') as string,
      venue: formData.get('venue') as string,
      year: formData.get('year') ? Number(formData.get('year')) : null,
      tags: (formData.get('tags') as string).split(',').map((t) => t.trim()).filter(Boolean),
      note: formData.get('note') as string,
    }
    await updatePaper(paper.id, data)
    setEditing(false)
  }

  const handleDelete = async () => {
    if (confirm(`确认删除 "${paper.title}" ?\n删除后可到回收站恢复。`)) {
      await deletePaper(paper.id)
    }
  }

  const sr = paper.speed_read

  return (
    <div className="p-4">
      {/* 头部操作栏 */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-gray-400">论文详情</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setEditing(!editing)}
            className="text-xs px-2 py-1 rounded border border-gray-300 hover:bg-gray-50"
          >
            {editing ? '取消' : '编辑'}
          </button>
          <button
            onClick={handleDelete}
            className="text-xs px-2 py-1 rounded border border-red-300 text-red-500 hover:bg-red-50"
          >
            删除
          </button>
          <button
            onClick={() => selectPaper(null)}
            className="text-xs px-2 py-1 rounded text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
        </div>
      </div>

      {editing ? (
        <form onSubmit={handleSave} className="space-y-3">
          <div>
            <label className="text-xs text-gray-400">标题</label>
            <input name="title" defaultValue={paper.title} className="w-full border rounded px-2 py-1 text-sm" />
          </div>
          <div>
            <label className="text-xs text-gray-400">作者</label>
            <input name="authors" defaultValue={paper.authors} className="w-full border rounded px-2 py-1 text-sm" />
          </div>
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="text-xs text-gray-400">会议</label>
              <input name="venue" defaultValue={paper.venue} className="w-full border rounded px-2 py-1 text-sm" />
            </div>
            <div className="w-20">
              <label className="text-xs text-gray-400">年份</label>
              <input name="year" type="number" defaultValue={paper.year || ''} className="w-full border rounded px-2 py-1 text-sm" />
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-400">标签 (逗号分隔)</label>
            <input name="tags" defaultValue={paper.tags.join(', ')} className="w-full border rounded px-2 py-1 text-sm" />
          </div>
          <div>
            <label className="text-xs text-gray-400">备注</label>
            <textarea name="note" defaultValue={paper.note} rows={3} className="w-full border rounded px-2 py-1 text-sm" />
          </div>
          <button type="submit" className="w-full py-1.5 bg-blue-500 text-white text-sm rounded hover:bg-blue-600">
            保存
          </button>
        </form>
      ) : (
        <>
          {/* 显示模式 */}
          <h1 className="text-lg font-semibold text-gray-900 mb-1 leading-snug">
            {paper.title || '(无标题)'}
          </h1>
          {paper.authors && (
            <p className="text-sm text-gray-500 mb-3">{paper.authors}</p>
          )}
          <div className="flex items-center gap-2 mb-4">
            {paper.venue ? (
              <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">{paper.venue}</span>
            ) : (
              <button
                onClick={async () => {
                  setReindexing(true)
                  await reindexPaper(paper.id)
                  setReindexing(false)
                }}
                disabled={reindexing}
                className="px-2 py-0.5 text-xs bg-orange-100 text-orange-500 rounded hover:bg-orange-200 disabled:opacity-50"
              >
                {reindexing ? '识别中...' : '重新识别'}
              </button>
            )}
            {paper.year && (
              <span className="text-xs text-gray-400">{paper.year}</span>
            )}
            <span className="text-xs text-gray-300">|</span>
            <span className={`text-xs ${paper.read ? 'text-green-500' : 'text-gray-400'}`}>
              {paper.read ? '已读' : '未读'}
            </span>
            {paper.page_count > 0 && (
              <>
                <span className="text-xs text-gray-300">|</span>
                <span className="text-xs text-gray-400">{paper.page_count} 页</span>
              </>
            )}
          </div>
          {paper.tags.length > 0 && (
            <div className="flex gap-1 flex-wrap mb-4">
              {paper.tags.map((t) => (
                <span key={t} className="px-2 py-0.5 text-xs bg-blue-50 text-blue-500 rounded-full">{t}</span>
              ))}
            </div>
          )}
          {paper.note && (
            <div className="bg-yellow-50 border border-yellow-100 rounded p-3 mb-4">
              <div className="text-xs text-gray-600 whitespace-pre-wrap">{paper.note}</div>
            </div>
          )}

          {/* AI 速读 */}
          <SpeedReadView
            key={paper.id}
            paperId={paper.id}
            cachedResult={sr && sr.status === 'success' ? sr : null}
            onGenerated={(result) => {
              usePapersStore.getState().updateSpeedRead(paper.id, result)
            }}
          />
        </>
      )}
    </div>
  )
}
