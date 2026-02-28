/**
 * 告警设置管理
 *
 * 管理弹窗和声音告警的开关配置，支持 localStorage 持久化
 */

import { ref, watch } from 'vue'

// 音效类型
export type SoundType = 'beep' | 'ding' | 'alert'

// 音效类型名称映射
export const SOUND_TYPE_NAMES: Record<SoundType, string> = {
  beep: '短促蜂鸣',
  ding: '柔和叮咚',
  alert: '警报声',
}

// 配置项接口
export interface AlertSettings {
  popupEnabled: boolean    // 弹窗开关
  soundEnabled: boolean    // 声音开关
  soundDuration: number    // 声音播放时长（秒）
  soundType: SoundType     // 音效类型
}

// 默认配置
const DEFAULT_SETTINGS: AlertSettings = {
  popupEnabled: true,
  soundEnabled: true,
  soundDuration: 5,
  soundType: 'beep',
}

// localStorage 键名
const STORAGE_KEY = 'alert-settings'

/**
 * 加载保存的设置
 */
function loadSettings(): AlertSettings {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) }
    }
  } catch (error) {
    console.error('[AlertSettings] 加载设置失败:', error)
  }
  return { ...DEFAULT_SETTINGS }
}

/**
 * 保存设置到 localStorage
 */
function saveSettings(settings: AlertSettings): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
  } catch (error) {
    console.error('[AlertSettings] 保存设置失败:', error)
  }
}

// 全局设置实例
const settings = ref<AlertSettings>(loadSettings())

// 监听设置变化，自动保存
watch(settings, (newSettings) => {
  saveSettings(newSettings)
}, { deep: true })

/**
 * 播放告警声音
 * 使用 Web Audio API 生成提示音
 * @param durationSeconds - 播放时长（秒），支持 5, 15, 30, 60
 * @param soundType - 音效类型：beep(短促蜂鸣)、ding(柔和叮咚)、alert(警报声)
 */
export function playAlertSound(durationSeconds: number = 5, soundType: SoundType = 'beep'): void {
  try {
    const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof window.AudioContext }).webkitAudioContext

    if (!AudioContextClass) {
      console.warn('[AlertSound] 浏览器不支持 Web Audio API')
      return
    }

    const audioContext = new AudioContextClass()

    // 根据音效类型选择播放模式
    if (soundType === 'beep') {
      playBeepSound(audioContext, durationSeconds)
    } else if (soundType === 'ding') {
      playDingSound(audioContext, durationSeconds)
    } else if (soundType === 'alert') {
      playAlertSound2(audioContext, durationSeconds)
    }

    // 清理资源
    setTimeout(() => {
      audioContext.close()
    }, durationSeconds * 1000 + 2000)
  } catch {
    // 忽略音频播放错误，不影响用户体验
  }
}

/**
 * 短促蜂鸣 - 短促有力的双音提示
 */
function playBeepSound(audioContext: AudioContext, durationSeconds: number): void {
  const segmentDuration = 1.2
  const segmentCount = Math.ceil(durationSeconds / segmentDuration)

  const playSegment = (startTime: number, freq1: number, freq2: number) => {
    const osc1 = audioContext.createOscillator()
    const gain1 = audioContext.createGain()
    const osc2 = audioContext.createOscillator()
    const gain2 = audioContext.createGain()

    osc1.connect(gain1)
    gain1.connect(audioContext.destination)
    osc1.type = 'sine'
    osc1.frequency.setValueAtTime(freq1, startTime)
    gain1.gain.setValueAtTime(0.3, startTime)
    gain1.gain.exponentialRampToValueAtTime(0.01, startTime + 0.5)
    osc1.start(startTime)
    osc1.stop(startTime + 0.5)

    osc2.connect(gain2)
    gain2.connect(audioContext.destination)
    osc2.type = 'sine'
    osc2.frequency.setValueAtTime(freq2, startTime + 0.6)
    gain2.gain.setValueAtTime(0.3, startTime + 0.6)
    gain2.gain.exponentialRampToValueAtTime(0.01, startTime + 1.1)
    osc2.start(startTime + 0.6)
    osc2.stop(startTime + 1.1)
  }

  const frequencies = [
    [880, 660],
    [660, 880],
    [880, 880],
  ]

  for (let i = 0; i < segmentCount; i++) {
    const startTime = audioContext.currentTime + i * segmentDuration
    const freqPair = frequencies[i % frequencies.length]
    playSegment(startTime, freqPair[0], freqPair[1])
  }
}

/**
 * 柔和叮咚 - 使用更高频的纯音，更柔和
 */
function playDingSound(audioContext: AudioContext, durationSeconds: number): void {
  const segmentDuration = 2.0
  const segmentCount = Math.ceil(durationSeconds / segmentDuration)

  const playSegment = (startTime: number) => {
    // 主音 - 高频纯音
    const osc1 = audioContext.createOscillator()
    const gain1 = audioContext.createGain()

    osc1.connect(gain1)
    gain1.connect(audioContext.destination)
    osc1.type = 'sine'
    osc1.frequency.setValueAtTime(1200, startTime) // 更高频率
    gain1.gain.setValueAtTime(0.2, startTime) // 较低音量
    gain1.gain.exponentialRampToValueAtTime(0.01, startTime + 1.5) // 更长的衰减
    osc1.start(startTime)
    osc1.stop(startTime + 1.5)

    // 泛音 - 添加轻微的和声
    const osc2 = audioContext.createOscillator()
    const gain2 = audioContext.createGain()

    osc2.connect(gain2)
    gain2.connect(audioContext.destination)
    osc2.type = 'sine'
    osc2.frequency.setValueAtTime(1800, startTime) // 主音的1.5倍
    gain2.gain.setValueAtTime(0.1, startTime)
    gain2.gain.exponentialRampToValueAtTime(0.01, startTime + 1.0)
    osc2.start(startTime)
    osc2.stop(startTime + 1.0)
  }

  for (let i = 0; i < segmentCount; i++) {
    const startTime = audioContext.currentTime + i * segmentDuration
    playSegment(startTime)
  }
}

/**
 * 警报声 - 快速的交替频率，产生警报效果
 */
function playAlertSound2(audioContext: AudioContext, durationSeconds: number): void {
  const beepDuration = 0.15 // 每个 beep 的时长
  const pauseDuration = 0.1  // 每个 beep 之间的停顿
  const totalBeepCycle = beepDuration + pauseDuration
  const beepCount = Math.floor(durationSeconds / totalBeepCycle)

  for (let i = 0; i < beepCount; i++) {
    const startTime = audioContext.currentTime + i * totalBeepCycle
    const osc = audioContext.createOscillator()
    const gain = audioContext.createGain()

    osc.connect(gain)
    gain.connect(audioContext.destination)
    osc.type = 'square' // 方波更有警报感

    // 交替频率
    const freq = i % 2 === 0 ? 800 : 600
    osc.frequency.setValueAtTime(freq, startTime)

    gain.gain.setValueAtTime(0.2, startTime)
    gain.gain.exponentialRampToValueAtTime(0.01, startTime + beepDuration)

    osc.start(startTime)
    osc.stop(startTime + beepDuration)
  }
}

export function useAlertSettings() {
  return {
    settings,
    playAlertSound,
  }
}
