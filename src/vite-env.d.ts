/// <reference types="vite/client" />

interface ElectronAPI {
  getBackendUrl: () => Promise<string>
  openFileDialog: (options?: { multiple?: boolean }) => Promise<string[]>
  notify: (title: string, body: string) => Promise<void>
  minimizeWindow: () => Promise<void>
  maximizeWindow: () => Promise<void>
  closeWindow: () => Promise<void>
  getAutoLaunch: () => Promise<boolean>
  setAutoLaunch: (enabled: boolean) => Promise<void>
  onFileDrop: (callback: (filePaths: string[]) => void) => void
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI
  }
}
