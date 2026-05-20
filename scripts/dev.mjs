/**
 * 开发环境启动脚本
 * 同时启动: Python 后端 + Vite 前端 + Electron
 */
import { spawn } from 'child_process'
import { createServer } from 'vite'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, '..')

async function main() {
  console.log('=== Thesis-Reader 开发模式 ===\n')

  // 1. 启动 Python 后端
  console.log('[1/3] 启动 Python 后端...')
  const backendDir = path.join(ROOT, 'backend')
  const pythonCmd = process.platform === 'win32'
    ? 'F:/anaconda/python.exe'
    : 'python3'

  const pythonProc = spawn(pythonCmd, [
    '-m', 'uvicorn', 'backend.main:app',
    '--host', '127.0.0.1',
    '--port', '17384',
    '--reload',
  ], {
    cwd: ROOT,
    stdio: 'inherit',
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
  })

  // 2. 启动 Vite 开发服务器
  console.log('[2/3] 启动 Vite 开发服务器...')
  const viteServer = await createServer({
    root: ROOT,
    server: {
      port: 5173,
      strictPort: true,
    },
  })
  await viteServer.listen()
  console.log('  Vite → http://localhost:5173')

  // 3. 启动 Electron
  console.log('[3/3] 启动 Electron...')
  const isWin = process.platform === 'win32'
  const binDir = path.join(ROOT, 'node_modules', '.bin')
  const electronPath = path.join(binDir, isWin ? 'electron.cmd' : 'electron')

  // 先编译 electron TS（用 node 直接跑 tsc.js，避免 Windows .cmd spawn 问题）
  const compileElectron = spawn('node', [
    path.join(ROOT, 'node_modules', 'typescript', 'bin', 'tsc'),
    '-p', 'tsconfig.electron.json',
  ], { cwd: ROOT, stdio: 'inherit' })

  compileElectron.on('close', () => {
    const electronProc = spawn(electronPath, ['.'], {
      cwd: ROOT,
      stdio: 'inherit',
      shell: true,
      env: {
        ...process.env,
        VITE_DEV_SERVER_URL: 'http://localhost:5173',
      },
    })

    electronProc.on('close', () => {
      pythonProc.kill()
      viteServer.close()
      process.exit(0)
    })
  })

  // 清理
  const cleanup = () => {
    pythonProc.kill()
    viteServer.close()
    process.exit(0)
  }

  process.on('SIGINT', cleanup)
  process.on('SIGTERM', cleanup)
}

main().catch((err) => {
  console.error('启动失败:', err)
  process.exit(1)
})
