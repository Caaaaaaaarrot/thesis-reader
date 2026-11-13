import { useState, useCallback } from 'react'
import { usePapersStore } from '../stores/papers'

export function useFileDrop() {
  const [isDragging, setIsDragging] = useState(false)
  const importPaper = usePapersStore((s) => s.importPaper)

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.dataTransfer.types.includes('Files')) {
      setIsDragging(true)
    }
  }, [])

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    // 只在离开最外层容器时取消高亮
    if (e.currentTarget === e.target) {
      setIsDragging(false)
    }
  }, [])

  const onDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    const files = Array.from(e.dataTransfer.files).filter(
      (f) => f.name.toLowerCase().endsWith('.pdf')
    )
    if (files.length === 0) return

    for (const file of files) {
      try {
        let path: string
        if (window.electronAPI?.getFilePath) {
          path = window.electronAPI.getFilePath(file)
        } else {
          // 浏览器环境回退
          continue
        }
        await importPaper(path)
      } catch (err) {
        console.error('导入失败:', file.name, err)
      }
    }

    // 通知
    if (window.electronAPI?.notify) {
      window.electronAPI.notify('导入完成', `成功导入 ${files.length} 篇论文`)
    }
  }, [importPaper])

  return { isDragging, onDragOver, onDragLeave, onDrop }
}
