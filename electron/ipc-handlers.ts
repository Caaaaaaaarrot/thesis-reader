import { ipcMain, BrowserWindow, dialog, Notification } from 'electron'

export function registerIpcHandlers(): void {
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
