import { app, BrowserWindow, ipcMain, Menu, dialog } from 'electron'
import path from 'path'
import { PythonBridge } from './python-bridge'
import { createTray } from './tray'
import { updateTrayPapers } from './tray'
import { registerIpcHandlers } from './ipc-handlers'

let mainWindow: BrowserWindow | null = null
let pythonBridge: PythonBridge | null = null
let isQuitting = false

const isDev = !app.isPackaged

function createMenu() {
  const isMac = process.platform === 'darwin'

  const template: Electron.MenuItemConstructorOptions[] = [
    // macOS 应用菜单
    ...(isMac ? [{
      label: app.getName(),
      submenu: [
        { role: 'about' as const },
        { type: 'separator' as const },
        { role: 'quit' as const },
      ],
    }] : []),
    {
      label: '文件',
      submenu: [
        {
          label: '导入 PDF...',
          accelerator: 'CmdOrCtrl+O',
          click: () => mainWindow?.webContents.send('menu-import'),
        },
        { type: 'separator' },
        ...(isMac ? [] : [{
          label: '退出',
          accelerator: 'Alt+F4',
          click: () => app.quit(),
        }]),
      ],
    },
    {
      label: '视图',
      submenu: [
        {
          label: '刷新',
          accelerator: 'CmdOrCtrl+R',
          click: () => mainWindow?.webContents.reload(),
        },
        { type: 'separator' },
        {
          label: '开发者工具',
          accelerator: 'F12',
          click: () => mainWindow?.webContents.toggleDevTools(),
        },
      ],
    },
    {
      label: '帮助',
      submenu: [
        {
          label: '关于 Thesis-Reader',
          click: () => {
            dialog.showMessageBox(mainWindow!, {
              type: 'info',
              title: '关于 Thesis-Reader',
              message: 'Thesis-Reader',
              detail: `版本: ${app.getVersion()}\n智能论文管理与阅读助手\n\n基于 Electron + Python FastAPI + React`,
            })
          },
        },
      ],
    },
  ]

  const menu = Menu.buildFromTemplate(template)
  Menu.setApplicationMenu(menu)
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 900,
    minHeight: 600,
    title: 'Thesis-Reader',
    icon: path.join(__dirname, '../resources/icon.ico'),
    frame: false,
    autoHideMenuBar: false,
    titleBarStyle: 'hidden',
    titleBarOverlay: {
      color: '#ffffff',
      symbolColor: '#333333',
      height: 36,
    },
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
  // 设置应用菜单
  createMenu()

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
  createTray(mainWindow!, port)

  // 托盘论文导航 → 转发到渲染进程
  ipcMain.on('navigate-paper', (_event, paperId: string) => {
    mainWindow?.webContents.send('navigate-paper', paperId)
  })

  // 前端通知刷新托盘论文列表
  ipcMain.handle('update-tray-papers', () => {
    updateTrayPapers()
  })

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
