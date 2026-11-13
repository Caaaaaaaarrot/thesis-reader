/// <reference types="vite/client" />

export {}

declare global {
  interface ElectronAPI {
    getBackendUrl: () => Promise<string>
    openFileDialog: (options?: { multiple?: boolean }) => Promise<string[]>
    notify: (title: string, body: string) => Promise<void>
    minimizeWindow: () => Promise<void>
    maximizeWindow: () => Promise<void>
    closeWindow: () => Promise<void>
    getAutoLaunch: () => Promise<boolean>
    setAutoLaunch: (enabled: boolean) => Promise<void>
    getFilePath: (file: File) => string
    onNavigatePaper: (callback: (paperId: string) => void) => void
    updateTrayPapers: () => Promise<void>
    onMenuImport: (callback: () => void) => void
    toggleDevTools: () => Promise<void>
    showAbout: () => Promise<void>
    quitApp: () => Promise<void>
  }

  interface Window {
    electronAPI?: ElectronAPI
  }
}
