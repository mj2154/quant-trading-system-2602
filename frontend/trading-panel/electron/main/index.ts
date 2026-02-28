import { app, BrowserWindow, shell } from 'electron'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

// ESM 环境下获取 __dirname
const __dirname = path.dirname(fileURLToPath(import.meta.url))

// 环境变量设置
process.env.APP_ROOT = path.join(__dirname, '../..')
const VITE_DEV_SERVER_URL = process.env['VITE_DEV_SERVER_URL']
const RENDERER_DIST = path.join(process.env.APP_ROOT, 'dist')

// 创建全局窗口引用
let mainWindow: BrowserWindow | null = null

// 创建窗口函数
async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  })

  if (VITE_DEV_SERVER_URL) {
    await mainWindow.loadURL(VITE_DEV_SERVER_URL)
    mainWindow.webContents.openDevTools()
  } else {
    await mainWindow.loadFile(path.join(RENDERER_DIST, 'index.html'))
  }
}

// 应用准备就绪时创建窗口
app.whenReady().then(() => {
  createWindow().catch(() => {
    app.quit()
  })
})

// 所有窗口关闭时退出应用（macOS 除外）
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
  mainWindow = null
})

// 应用激活时重新创建窗口（macOS）
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow()
  }
})

// 阻止新窗口创建，外链用默认浏览器打开
app.on('web-contents-created', (_, contents) => {
  contents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https:')) {
      shell.openExternal(url)
    }
    return { action: 'deny' }
  })
})

export { mainWindow }
