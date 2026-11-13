import { useEffect } from 'react'
import { getBaseUrl } from '../api/client'
import { LibraryStatus, useLibraryStore } from '../stores/library'
import { usePapersStore } from '../stores/papers'

export function useLibrarySync(ready: boolean) {
  useEffect(() => {
    if (!ready) return
    const controller = new AbortController()
    let revision: number | null = null
    let busy = false
    const poll = async () => {
      if (busy || document.hidden) return
      busy = true
      try {
        const response = await fetch(`${getBaseUrl()}/api/library/status`, { signal: controller.signal })
        if (!response.ok) throw new Error('无法获取目录同步状态')
        const status: LibraryStatus = await response.json()
        if (controller.signal.aborted) return
        useLibraryStore.getState().update(status)
        if (revision !== status.revision) {
          revision = status.revision
          const store = usePapersStore.getState()
          await Promise.all([store.fetchPapers(), store.fetchTags(), store.fetchVenues()])
          window.electronAPI?.updateTrayPapers()
        }
      } catch (error) {
        if (!controller.signal.aborted) {
          useLibraryStore.getState().fail(error instanceof Error ? error.message : '目录连接中断')
        }
      } finally {
        busy = false
      }
    }
    void poll()
    const timer = window.setInterval(poll, 2000)
    document.addEventListener('visibilitychange', poll)
    return () => {
      controller.abort()
      window.clearInterval(timer)
      document.removeEventListener('visibilitychange', poll)
    }
  }, [ready])
}
