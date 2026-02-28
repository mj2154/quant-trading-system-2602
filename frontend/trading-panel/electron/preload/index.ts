import { ipcRenderer, contextBridge } from 'electron'

// --------- Expose some API to the Renderer process ---------
contextBridge.exposeInMainWorld('ipcRenderer', {
  on(...args: Parameters<typeof ipcRenderer.on>) {
    const [channel, listener] = args
    return ipcRenderer.on(channel, (event, ...args) => listener(event, ...args))
  },
  off(...args: Parameters<typeof ipcRenderer.off>) {
    const [channel, ...omit] = args
    return ipcRenderer.off(channel, ...omit)
  },
  send(...args: Parameters<typeof ipcRenderer.send>) {
    const [channel, ...omit] = args
    return ipcRenderer.send(channel, ...omit)
  },
  invoke(...args: Parameters<typeof ipcRenderer.invoke>) {
    const [channel, ...omit] = args
    return ipcRenderer.invoke(channel, ...omit)
  },
})

// --------- Expose Tab API to the Renderer process ---------
contextBridge.exposeInMainWorld('tabs', {
  // 创建新标签页
  create(url: string, title?: string) {
    return ipcRenderer.invoke('tab:create', url, title)
  },

  // 关闭标签页
  close(tabId: string) {
    return ipcRenderer.invoke('tab:close', tabId)
  },

  // 切换标签页
  switch(tabId: string) {
    return ipcRenderer.invoke('tab:switch', tabId)
  },

  // 获取所有标签页
  getAll() {
    return ipcRenderer.invoke('tab:getAll')
  },

  // 获取当前激活标签页
  getActive() {
    return ipcRenderer.invoke('tab:getActive')
  },

  // 更新标签页标题
  updateTitle(tabId: string, title: string) {
    return ipcRenderer.invoke('tab:updateTitle', tabId, title)
  },

  // 更新标签页URL
  updateUrl(tabId: string, url: string) {
    return ipcRenderer.invoke('tab:updateUrl', tabId, url)
  },

  // 获取标签页数量
  getCount() {
    return ipcRenderer.invoke('tab:getCount')
  },

  // 清空所有标签页
  clear() {
    return ipcRenderer.invoke('tab:clear')
  },

  // 监听标签页事件
  onTabCreated(callback: (tab: any) => void) {
    ipcRenderer.on('tab:created', (_, tab) => callback(tab))
  },

  onTabClosed(callback: (data: { tabId: string }) => void) {
    ipcRenderer.on('tab:closed', (_, data) => callback(data))
  },

  onTabSwitched(callback: (data: { tabId: string }) => void) {
    ipcRenderer.on('tab:switched', (_, data) => callback(data))
  },

  onTabUpdated(callback: (data: { type: string; tab: any }) => void) {
    ipcRenderer.on('tab:updated', (_, data) => callback(data))
  },
})

// --------- Expose Window API to the Renderer process ---------
contextBridge.exposeInMainWorld('window', {
  // 窗口控制
  minimize() {
    return ipcRenderer.invoke('window:minimize')
  },

  maximize() {
    return ipcRenderer.invoke('window:maximize')
  },

  restore() {
    return ipcRenderer.invoke('window:restore')
  },

  close() {
    return ipcRenderer.invoke('window:close')
  },

  // 获取窗口信息
  getSize() {
    return ipcRenderer.invoke('window:getSize')
  },

  setSize(width: number, height: number) {
    return ipcRenderer.invoke('window:setSize', width, height)
  },

  getPosition() {
    return ipcRenderer.invoke('window:getPosition')
  },

  setPosition(x: number, y: number) {
    return ipcRenderer.invoke('window:setPosition', x, y)
  },

  // 窗口状态
  isMinimized() {
    return ipcRenderer.invoke('window:isMinimized')
  },

  isMaximized() {
    return ipcRenderer.invoke('window:isMaximized')
  },

  isFocused() {
    return ipcRenderer.invoke('window:isFocused')
  },

  // 窗口事件
  onResized(callback: (size: [number, number]) => void) {
    ipcRenderer.on('window:resized', (_, size) => callback(size))
  },

  onMoved(callback: (position: [number, number]) => void) {
    ipcRenderer.on('window:moved', (_, position) => callback(position))
  },

  onFocusChanged(callback: (focused: boolean) => void) {
    ipcRenderer.on('window:focus-changed', (_, focused) => callback(focused))
  },
})

// --------- Expose App API to the Renderer process ---------
contextBridge.exposeInMainWorld('app', {
  // 应用信息
  getVersion() {
    return ipcRenderer.invoke('app:getVersion')
  },

  getName() {
    return ipcRenderer.invoke('app:getName')
  },

  // 应用控制
  quit() {
    return ipcRenderer.invoke('app:quit')
  },

  // 事件监听
  onReady(callback: () => void) {
    ipcRenderer.on('app:ready', () => callback())
  },
})

// --------- Preload scripts loading ---------
function domReady(condition: DocumentReadyState[] = ['complete', 'interactive']) {
  return new Promise((resolve) => {
    if (condition.includes(document.readyState)) {
      resolve(true)
    } else {
      document.addEventListener('readystatechange', () => {
        if (condition.includes(document.readyState)) {
          resolve(true)
        }
      })
    }
  })
}

const safeDOM = {
  append(parent: HTMLElement, child: HTMLElement) {
    if (!Array.from(parent.children).find(e => e === child)) {
      return parent.appendChild(child)
    }
  },
  remove(parent: HTMLElement, child: HTMLElement) {
    if (Array.from(parent.children).find(e => e === child)) {
      return parent.removeChild(child)
    }
  },
}

/**
 * https://tobiasahlin.com/spinkit
 * https://connoratherton.com/loaders
 * https://projects.lukehaas.me/css-loaders
 * https://matejkustec.github.io/SpinThatShit
 */
function useLoading() {
  const className = `loaders-css__square-spin`
  const styleContent = `
@keyframes square-spin {
  25% { transform: perspective(100px) rotateX(180deg) rotateY(0); }
  50% { transform: perspective(100px) rotateX(180deg) rotateY(180deg); }
  75% { transform: perspective(100px) rotateX(0) rotateY(180deg); }
  100% { transform: perspective(100px) rotateX(0) rotateY(0); }
}
.${className} > div {
  animation-fill-mode: both;
  width: 50px;
  height: 50px;
  background: #fff;
  animation: square-spin 3s 0s cubic-bezier(0.09, 0.57, 0.49, 0.9) infinite;
}
.app-loading-wrap {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #282c34;
  z-index: 9;
}
    `
  const oStyle = document.createElement('style')
  const oDiv = document.createElement('div')

  oStyle.id = 'app-loading-style'
  oStyle.innerHTML = styleContent
  oDiv.className = 'app-loading-wrap'
  oDiv.innerHTML = `<div class="${className}"><div></div></div>`

  return {
    appendLoading() {
      safeDOM.append(document.head, oStyle)
      safeDOM.append(document.body, oDiv)
    },
    removeLoading() {
      safeDOM.remove(document.head, oStyle)
      safeDOM.remove(document.body, oDiv)
    },
  }
}

// ----------------------------------------------------------------------

const { appendLoading, removeLoading } = useLoading()
domReady().then(appendLoading)

window.onmessage = (ev) => {
  ev.data.payload === 'removeLoading' && removeLoading()
}

setTimeout(removeLoading, 4999)
