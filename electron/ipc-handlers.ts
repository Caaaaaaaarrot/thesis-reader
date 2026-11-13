import { ipcMain, BrowserWindow, dialog, Notification, app } from 'electron'

export function registerIpcHandlers(): void {
  // DevTools
  ipcMain.handle('toggle-devtools', () => {
    BrowserWindow.getFocusedWindow()?.webContents.toggleDevTools()
  })

  // 关于对话框
  ipcMain.handle('show-about', () => {
    dialog.showMessageBox(BrowserWindow.getFocusedWindow()!, {
      type: 'info',
      title: '关于 Thesis-Reader',
      message: 'Thesis-Reader',
      detail: `版本: ${app.getVersion()}\n智能论文管理与阅读助手\n\n基于 Electron + Python FastAPI + React`,
    })
  })

  // 彻底退出
  ipcMain.handle('quit-app', () => {
    app.quit()
  })

  // 文件选择对话框
  ipcMain.handle('open-file-dialog', async (_event, options?: { multiple?: boolean }) => {
    const win = BrowserWindow.getFocusedWindow()
    if (!win) return []
    const result = await dialog.showOpenDialog(win, {
      properties: ['openFile'],
      filters: [{ name: 'PDF 文件', extensions: ['pdf'] }],
    })
    return result.filePaths
  })

  // 系统通知
  ipcMain.handle('notify', (_event, title: string, body: string) => {
    if (Notification.isSupported()) {
      new Notification({ title, body }).show()
    }
  })

  // 窗口控制
  ipcMain.handle('minimize-window', () => {
    BrowserWindow.getFocusedWindow()?.minimize()
  })
  ipcMain.handle('maximize-window', () => {
    const win = BrowserWindow.getFocusedWindow()
    if (win?.isMaximized()) {
      win.unmaximize()
    } else {
      win?.maximize()
    }
  })
  ipcMain.handle('close-window', () => {
    BrowserWindow.getFocusedWindow()?.close()
  })

  // 开机自启
  ipcMain.handle('get-auto-launch', () => {
    return require('electron').app.getLoginItemSettings().openAtLogin
  })
  ipcMain.handle('set-auto-launch', (_event, enabled: boolean) => {
    require('electron').app.setLoginItemSettings({
      openAtLogin: enabled,
      path: require('electron').app.getPath('exe'),
    })
  })

  // 拖放文件事件（在主进程监听并转发到渲染进程）
  ipcMain.handle('on-file-drop', () => {
    // 文件拖放在 renderer 端通过 dragover/drop 事件直接处理
    // 这里做备用通道
  })
}
