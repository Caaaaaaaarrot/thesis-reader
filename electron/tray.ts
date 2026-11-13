import { Tray, Menu, BrowserWindow, nativeImage, app } from 'electron'
import path from 'path'
import http from 'http'

let tray: Tray | null = null
let backendPort: number = 0
let balloonShown = false

function fetchRecentPapers(): Promise<{ id: string; title: string }[]> {
  return new Promise((resolve) => {
    if (!backendPort) { resolve([]); return }
    const req = http.get(`http://127.0.0.1:${backendPort}/api/papers?sort=date_added&order=desc`, (res) => {
      let body = ''
      res.on('data', (chunk: Buffer) => { body += chunk.toString() })
      res.on('end', () => {
        try {
          const papers = JSON.parse(body)
          resolve(papers.slice(0, 5).map((p: { id: string; title: string }) => ({
            id: p.id,
            title: (p.title || '无标题').slice(0, 40),
          })))
        } catch { resolve([]) }
      })
    })
    req.on('error', () => resolve([]))
    req.setTimeout(3000, () => { req.destroy(); resolve([]) })
  })
}

async function buildMenu(mainWindow: BrowserWindow): Promise<Electron.Menu> {
  const recentPapers = await fetchRecentPapers()

  const template: Electron.MenuItemConstructorOptions[] = [
    {
      label: '显示主窗口',
      click: () => {
        mainWindow.show()
        mainWindow.focus()
      },
    },
    { type: 'separator' },
  ]

  // 最近添加的论文
  if (recentPapers.length > 0) {
    template.push({ label: '最近添加', enabled: false })
    for (const paper of recentPapers) {
      template.push({
        label: `  ${paper.title}`,
        click: () => {
          mainWindow.show()
          mainWindow.focus()
          mainWindow.webContents.send('navigate-paper', paper.id)
        },
      })
    }
    template.push({ type: 'separator' })
  }

  template.push(
    {
      label: '开机自启',
      type: 'checkbox',
      checked: app.getLoginItemSettings().openAtLogin,
      click: (mi) => {
        app.setLoginItemSettings({
          openAtLogin: mi.checked,
          path: app.getPath('exe'),
        })
      },
    },
    { type: 'separator' },
    {
      label: '退出',
      click: () => {
        app.quit()
      },
    },
  )

  return Menu.buildFromTemplate(template)
}

export function createTray(mainWindow: BrowserWindow, port: number): void {
  backendPort = port

  const iconPath = path.join(__dirname, '../resources/tray.png')
  const trayIcon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 })
  tray = new Tray(trayIcon)

  tray.setToolTip('Thesis-Reader - 论文阅读助手')

  // 异步构建初始菜单
  buildMenu(mainWindow).then((menu) => tray?.setContextMenu(menu))

  // 每次右键时刷新菜单
  tray.on('right-click', async () => {
    const menu = await buildMenu(mainWindow)
    tray?.setContextMenu(menu)
    tray?.popUpContextMenu(menu)
  })

  tray.on('double-click', () => {
    mainWindow.show()
    mainWindow.focus()
  })

  // 窗口隐藏时显示气泡（仅首次）
  mainWindow.on('hide', () => {
    if (!balloonShown && tray && !tray.isDestroyed()) {
      balloonShown = true
      tray.displayBalloon({
        title: 'Thesis-Reader',
        content: '应用正在后台运行，双击托盘图标可重新打开',
        iconType: 'info',
      })
    }
  })
}

export function updateTrayPapers(): void {
  if (!tray || tray.isDestroyed()) return
  const mainWindow = BrowserWindow.getAllWindows()[0]
  if (!mainWindow) return
  buildMenu(mainWindow).then((menu) => tray?.setContextMenu(menu))
}

export function getTray(): Tray | null {
  return tray
}
