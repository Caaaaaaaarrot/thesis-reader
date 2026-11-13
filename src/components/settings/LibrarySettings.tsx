import { useState } from 'react'
import { apiPost } from '../../api/client'
import { useLibraryStore } from '../../stores/library'

export default function LibrarySettings() {
  const status = useLibraryStore((s) => s.status)
  const error = useLibraryStore((s) => s.error)
  const [message, setMessage] = useState('')
  const [pending, setPending] = useState(false)
  return (
    <section className="border-t border-gray-100 pt-4">
      <div className="text-xs font-semibold text-gray-400 mb-3">论文库与目录监听</div>
      <p className="text-xs text-gray-500 mb-2">将 PDF 放入以下目录或子目录，论文库和图谱会自动更新。</p>
      <div className="text-xs text-gray-600 bg-gray-50 rounded p-2 select-text break-all">{status?.directory || '连接中…'}</div>
      <div className="flex items-center justify-between mt-3 text-xs text-gray-500">
        <span>{status?.running ? '监听已开启' : '监听未连接'} · {status?.paper_count ?? 0} 篇论文</span>
        <button disabled={pending} className="text-blue-500 disabled:opacity-50" onClick={async () => {
          setPending(true)
          try { await apiPost('/api/library/rescan'); setMessage('已安排重新扫描') }
          catch { setMessage('重新扫描失败，请检查后端连接') }
          finally { setPending(false) }
        }}>重新扫描</button>
      </div>
      <p className="text-xs text-gray-500 mt-2">速读页面评分：{status?.scorer.engine === 'cpp' ? 'C++ 加速已启用' : 'Python'}</p>
      {status?.scorer.engine === 'python' && <p className="text-[11px] text-gray-400 mt-1">可运行 npm run native:build 编译 C++ 模块，然后重启应用。</p>}
      {(error || message) && <p role="status" className="text-xs text-gray-500 mt-2">{error || message}</p>}
      {!!status?.errors.length && <div className="mt-2 max-h-24 overflow-auto text-xs text-amber-600">{status.errors.map((item, i) => <p key={i}>{item}</p>)}</div>}
    </section>
  )
}
