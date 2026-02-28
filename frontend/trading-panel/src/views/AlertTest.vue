<script setup lang="ts">
import { ref, watch } from 'vue'
import { NCard, NButton, NSpace, NGrid, NGridItem, NSwitch, NSlider, NSelect, NText, NDivider, useNotification } from 'naive-ui'
import { useAlertSettings, SOUND_TYPE_NAMES, type SoundType } from '../composables/useAlertSettings'

const { settings, playAlertSound } = useAlertSettings()
const notification = useNotification()

// 测试状态
const testDuration = ref(5)
const testSoundType = ref<SoundType>('beep')

// 音效选项
const soundTypeOptions = [
  { label: '短促蜂鸣', value: 'beep' },
  { label: '柔和叮咚', value: 'ding' },
  { label: '警报声', value: 'alert' },
]

// 时长选项
const durationOptions = [
  { label: '5秒', value: 5 },
  { label: '15秒', value: 15 },
  { label: '30秒', value: 30 },
  { label: '60秒', value: 60 },
]

// 播放测试音效
function handlePlaySound() {
  playAlertSound(testDuration.value, testSoundType.value)
}

// 播放当前设置的音效
function handlePlayCurrentSound() {
  playAlertSound(settings.value.soundDuration, settings.value.soundType)
}

// 触发测试弹窗 - 左下角，不自动消失，最多10个（由 NNotificationProvider 控制）
function handleTestPopup() {
  notification.info({
    title: '交易信号 - 测试策略',
    content: 'BTC 1小时 建仓',
    duration: 0,
  })
}

// 当前设置
const currentSettingsText = ref('')
function updateSettingsText() {
  const duration = settings.value.soundDuration
  const type = SOUND_TYPE_NAMES[settings.value.soundType]
  currentSettingsText.value = `时长: ${duration >= 60 ? '1分钟' : duration + '秒'}, 音效: ${type}`
}

// 监听设置变化
watch(
  () => [settings.value.soundDuration, settings.value.soundType],
  () => updateSettingsText(),
  { immediate: true }
)
</script>

<template>
  <div class="alert-test">
    <n-card title="告警测试" size="small">
      <n-space vertical :size="16">
        <!-- 当前设置显示 -->
        <div class="current-settings">
          <n-text depth="3">当前告警设置:</n-text>
          <n-text strong>{{ currentSettingsText }}</n-text>
        </div>

        <n-divider />

        <!-- 测试音效 -->
        <div class="test-section">
          <n-text strong>测试音效</n-text>
          <n-grid :cols="2" :x-gap="16" :y-gap="12">
            <n-grid-item>
              <div class="control-item">
                <n-text depth="3">音效类型</n-text>
                <n-select
                  v-model:value="testSoundType"
                  :options="soundTypeOptions"
                  size="small"
                />
              </div>
            </n-grid-item>
            <n-grid-item>
              <div class="control-item">
                <n-text depth="3">播放时长</n-text>
                <n-select
                  v-model:value="testDuration"
                  :options="durationOptions"
                  size="small"
                />
              </div>
            </n-grid-item>
          </n-grid>
          <n-space :size="12" style="margin-top: 12px">
            <n-button type="primary" @click="handlePlaySound">
              播放测试音效
            </n-button>
            <n-button @click="handlePlayCurrentSound">
              播放当前设置
            </n-button>
          </n-space>
        </div>

        <n-divider />

        <!-- 测试弹窗 -->
        <div class="test-section test-popup">
          <n-space vertical :size="8" align="center">
            <n-text strong>测试弹窗</n-text>
            <n-space :size="12">
              <n-button type="warning" @click="handleTestPopup">
                触发测试弹窗
              </n-button>
            </n-space>
            <n-text depth="3">
              弹窗显示在左下角，不自动消失，最多累积10个
            </n-text>
          </n-space>
        </div>

        <n-divider />

        <!-- 说明 -->
        <div class="help-text">
          <n-text depth="3">
            提示: 可以在"告警列表"页面点击音效类型和时长来切换设置
          </n-text>
        </div>
      </n-space>
    </n-card>
  </div>
</template>

<style scoped>
.alert-test {
  padding: 16px;
  height: 100%;
  overflow-y: auto;
}

.current-settings {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: var(--n-color-hover);
  border-radius: 6px;
}

.test-section {
  padding: 8px 0;
}

.test-popup {
  display: flex;
  justify-content: center;
  padding: 24px 0;
}

.test-popup :deep(.n-space) {
  align-items: center;
}

.control-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.help-text {
  padding: 12px;
  background: var(--n-color-hover);
  border-radius: 6px;
}
</style>
