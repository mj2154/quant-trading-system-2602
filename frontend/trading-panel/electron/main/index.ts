import { app, BrowserWindow, ipcMain, shell } from 'electron'
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
  const preloadPath = path.join(__dirname, '../preload/index.mjs')

  // Linux (WSLg) 使用系统框架，Windows/macOS 使用无边框暗色风格
  const useFrameless = process.platform !== 'linux'

  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    frame: !useFrameless,
    title: 'QuantTrading',
    ...(useFrameless && { backgroundColor: '#1e1e1e' }),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: preloadPath,
    },
  })

  // 注册窗口控制 IPC handlers
  registerWindowControlHandlers()

  if (VITE_DEV_SERVER_URL) {
    await mainWindow.loadURL(VITE_DEV_SERVER_URL)
  } else {
    await mainWindow.loadFile(path.join(RENDERER_DIST, 'index.html'))
  }
}

// 注册窗口控制相关的 IPC handlers
function registerWindowControlHandlers() {
  ipcMain.handle('window:minimize', () => {
    mainWindow?.minimize()
  })

  ipcMain.handle('window:maximize', () => {
    if (mainWindow?.isMaximized()) {
      mainWindow.unmaximize()
    } else {
      mainWindow?.maximize()
    }
  })

  ipcMain.handle('window:restore', () => {
    mainWindow?.unmaximize()
  })

  ipcMain.handle('window:close', () => {
    mainWindow?.close()
  })

  ipcMain.handle('window:isMaximized', () => {
    return mainWindow?.isMaximized() ?? false
  })

  ipcMain.handle('window:getSize', () => {
    if (!mainWindow) return [0, 0]
    const [width, height] = mainWindow.getSize()
    return [width, height]
  })

  ipcMain.handle('window:getPosition', () => {
    if (!mainWindow) return [0, 0]
    const [x, y] = mainWindow.getPosition()
    return [x, y]
  })

  ipcMain.handle('window:setSize', (_event, width: number, height: number) => {
    mainWindow?.setSize(width, height)
  })

  ipcMain.handle('window:setPosition', (_event, x: number, y: number) => {
    mainWindow?.setPosition(x, y)
  })

  ipcMain.handle('window:isMinimized', () => {
    return mainWindow?.isMinimized() ?? false
  })

  ipcMain.handle('window:isFocused', () => {
    return mainWindow?.isFocused() ?? false
  })

  ipcMain.handle('app:getVersion', () => {
    return app.getVersion()
  })

  ipcMain.handle('app:getName', () => {
    return app.getName()
  })

  ipcMain.handle('app:quit', () => {
    app.quit()
  })

  // 窗口状态变化事件 -> 推送给渲染进程
  mainWindow?.on('resize', () => {
    if (mainWindow) {
      const [width, height] = mainWindow.getSize()
      mainWindow.webContents.send('window:resized', [width, height])
    }
  })

  mainWindow?.on('move', () => {
    if (mainWindow) {
      const [x, y] = mainWindow.getPosition()
      mainWindow.webContents.send('window:moved', [x, y])
    }
  })

  mainWindow?.on('focus', () => {
    mainWindow?.webContents.send('window:focus-changed', true)
  })

  mainWindow?.on('blur', () => {
    mainWindow?.webContents.send('window:focus-changed', false)
  })

  mainWindow?.on('maximize', () => {
    mainWindow?.webContents.send('window:maximize-changed', true)
  })

  mainWindow?.on('unmaximize', () => {
    mainWindow?.webContents.send('window:maximize-changed', false)
  })
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
