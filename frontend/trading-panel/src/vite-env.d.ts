/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, unknown>
  export default component
}

interface WindowControlAPI {
  minimize(): Promise<void>
  maximize(): Promise<void>
  restore(): Promise<void>
  close(): Promise<void>
  getSize(): Promise<[number, number]>
  setSize(width: number, height: number): Promise<void>
  getPosition(): Promise<[number, number]>
  setPosition(x: number, y: number): Promise<void>
  isMinimized(): Promise<boolean>
  isMaximized(): Promise<boolean>
  isFocused(): Promise<boolean>
  onResized(callback: (size: [number, number]) => void): void
  onMoved(callback: (position: [number, number]) => void): void
  onFocusChanged(callback: (focused: boolean) => void): void
  onMaximizeChanged(callback: (maximized: boolean) => void): void
}

interface Window {
  ipcRenderer: import('electron').IpcRenderer
  /** Electron window control API (exposed via preload contextBridge) */
  electronWindow: WindowControlAPI
}
