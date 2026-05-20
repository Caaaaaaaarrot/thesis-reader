import { app, BrowserWindow, ipcMain } from 'electron'
import path from 'path'
import { PythonBridge } from './python-bridge'
import { createTray } from './tray'
import { registerIpcHandlers } from './ipc-handlers'

let mainWindow: BrowserWindow | null = null
let pythonBridge: PythonBridge | null = null
let isQuitting = false

const isDev = !app.isPackaged

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 900,
    minHeight: 600,
    title: 'Thesis-Reader',
    icon: path.join(__dirname, '../resources/icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  mainWindow.on('close', (e) => {
    if (!isQuitting) {
      e.preventDefault()
      mainWindow?.hide()
    }
  })
}

app.whenReady().then(async () => {
  // 启动 Python 后端
  pythonBridge = new PythonBridge()
  const port = await pythonBridge.start()

  // 把端口号传给渲染进程
  ipcMain.handle('get-backend-port', () => port)

  // 注册 IPC handlers
  registerIpcHandlers()

  // 创建窗口
  createWindow()

  // 创建系统托盘
  createTray(mainWindow!)

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    } else if (mainWindow) {
      mainWindow.show()
    }
  })
})

app.on('before-quit', () => {
  isQuitting = true
  if (pythonBridge) {
    pythonBridge.stop()
  }
})

app.on('window-all-closed', () => {
  // 不退出，留在托盘运行
})
