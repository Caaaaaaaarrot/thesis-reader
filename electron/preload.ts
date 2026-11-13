import { contextBridge, ipcRenderer, webUtils } from 'electron'

contextBridge.exposeInMainWorld('electronAPI', {
  // 获取后端 API 基础 URL
  getBackendUrl: () => ipcRenderer.invoke('get-backend-port').then(
    (port: number) => `http://127.0.0.1:${port}`
  ),

  // 文件对话框
  openFileDialog: (options?: { multiple?: boolean }) =>
    ipcRenderer.invoke('open-file-dialog', options),

  // 系统通知
  notify: (title: string, body: string) =>
    ipcRenderer.invoke('notify', title, body),

  // 窗口控制
  minimizeWindow: () => ipcRenderer.invoke('minimize-window'),
  maximizeWindow: () => ipcRenderer.invoke('maximize-window'),
  closeWindow: () => ipcRenderer.invoke('close-window'),

  // 开机自启
  getAutoLaunch: () => ipcRenderer.invoke('get-auto-launch'),
  setAutoLaunch: (enabled: boolean) =>
    ipcRenderer.invoke('set-auto-launch', enabled),

  // 拖放文件路径提取
  getFilePath: (file: File) => webUtils.getPathForFile(file),

  // 托盘论文导航
  onNavigatePaper: (callback: (paperId: string) => void) => {
    ipcRenderer.on('navigate-paper', (_event, paperId: string) => callback(paperId))
  },

  // 刷新托盘论文列表
  updateTrayPapers: () => ipcRenderer.invoke('update-tray-papers'),

  // 菜单事件
  onMenuImport: (callback: () => void) => {
    ipcRenderer.on('menu-import', () => callback())
  },

  // 菜单专用动作
  toggleDevTools: () => ipcRenderer.invoke('toggle-devtools'),
  showAbout: () => ipcRenderer.invoke('show-about'),
  quitApp: () => ipcRenderer.invoke('quit-app'),
})
