import { useState, useEffect, useCallback } from 'react'

export function useElectron() {
  const [isElectron, setIsElectron] = useState(false)

  useEffect(() => {
    setIsElectron(typeof window !== 'undefined' && !!window.electronAPI)
  }, [])

  const notify = useCallback((title: string, body: string) => {
    if (window.electronAPI?.notify) {
      window.electronAPI.notify(title, body)
    }
  }, [])

  const getAutoLaunch = useCallback(async (): Promise<boolean> => {
    if (window.electronAPI?.getAutoLaunch) {
      return window.electronAPI.getAutoLaunch()
    }
    return false
  }, [])

  const setAutoLaunch = useCallback(async (enabled: boolean) => {
    if (window.electronAPI?.setAutoLaunch) {
      await window.electronAPI.setAutoLaunch(enabled)
    }
  }, [])

  return { isElectron, notify, getAutoLaunch, setAutoLaunch }
}
