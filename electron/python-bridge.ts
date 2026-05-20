import { spawn, ChildProcess } from 'child_process'
import path from 'path'
import { app } from 'electron'
import http from 'http'

export class PythonBridge {
  private process: ChildProcess | null = null
  private port: number = 0
  private restartCount = 0
  private maxRestarts = 5

  async start(): Promise<number> {
    const isDev = !app.isPackaged

    const pythonCmd = process.platform === 'win32'
      ? 'F:/anaconda/python.exe'
      : 'python3'
    const rootDir = isDev
      ? path.join(__dirname, '..')
      : process.resourcesPath

    const args = ['-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '0']

    return new Promise((resolve, reject) => {
      this.process = spawn(pythonCmd, args, {
        cwd: rootDir,
        stdio: ['ignore', 'pipe', 'pipe'],
        env: { ...process.env, PYTHONUNBUFFERED: '1' },
      })

      // 从 stdout 解析实际端口号
      let startupOutput = ''
      const timeout = setTimeout(() => {
        reject(new Error('Python 后端启动超时'))
      }, 30000)

      this.process.stdout?.on('data', (data: Buffer) => {
        startupOutput += data.toString()
        // Uvicorn 输出格式: "Uvicorn running on http://127.0.0.1:PORT"
        const match = startupOutput.match(/Uvicorn running on http:\/\/127\.0\.0\.1:(\d+)/)
        if (match) {
          this.port = parseInt(match[1], 10)
          clearTimeout(timeout)
          resolve(this.port)
        }
      })

      this.process.stderr?.on('data', (data: Buffer) => {
        // Uvicorn 输出到 stderr
        const msg = data.toString()
        if (msg.includes('running on')) {
          const match = msg.match(/http:\/\/127\.0\.0\.1:(\d+)/)
          if (match) {
            this.port = parseInt(match[1], 10)
            clearTimeout(timeout)
            resolve(this.port)
          }
        }
      })

      this.process.on('error', (err) => {
        clearTimeout(timeout)
        reject(err)
      })

      this.process.on('exit', (code) => {
        clearTimeout(timeout)
        if (code !== 0 && this.restartCount < this.maxRestarts) {
          this.restartCount++
          console.log(`Python 后端崩溃，第 ${this.restartCount} 次重启...`)
          setTimeout(() => this.start(), 2000)
        }
      })
    })
  }

  getPort(): number {
    return this.port
  }

  async healthCheck(): Promise<boolean> {
    if (!this.port) return false
    return new Promise((resolve) => {
      const req = http.get(`http://127.0.0.1:${this.port}/api/ping`, (res) => {
        resolve(res.statusCode === 200)
      })
      req.on('error', () => resolve(false))
      req.setTimeout(3000, () => {
        req.destroy()
        resolve(false)
      })
    })
  }

  stop(): void {
    if (this.process) {
      if (process.platform === 'win32') {
        spawn('taskkill', ['/pid', String(this.process.pid), '/f', '/t'])
      } else {
        this.process.kill('SIGTERM')
      }
      this.process = null
    }
  }
}
