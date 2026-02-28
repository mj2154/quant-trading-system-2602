<template>
  <div class="alert-config-form">
    <div class="form-header">
      <h3 class="form-title">{{ isEdit ? '编辑告警' : '新建告警' }}</h3>
      <n-button quaternary circle size="small" @click="handleCancel">
        <template #icon>
          <n-icon><CloseOutline /></n-icon>
        </template>
      </n-button>
    </div>

    <div class="form-content">
      <n-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-placement="top"
        require-mark-placement="right-hanging"
      >
        <!-- 基本信息 -->
        <n-form-item label="告警名称" path="name">
          <n-input v-model:value="formData.name" placeholder="请输入告警名称" />
        </n-form-item>

        <n-form-item label="描述" path="description">
          <n-input
            v-model:value="formData.description"
            type="textarea"
            placeholder="请输入告警描述（可选）"
            :rows="2"
          />
        </n-form-item>

        <!-- 交易对和周期 -->
        <n-space vertical :size="16">
          <n-grid :cols="2" :x-gap="16">
            <n-gi>
              <n-form-item label="交易对" path="symbol">
                <n-select
                  v-model:value="formData.symbol"
                  placeholder="选择交易对"
                  :options="symbolOptions"
                  filterable
                />
              </n-form-item>
            </n-gi>
            <n-gi>
              <n-form-item label="K线周期" path="interval">
                <n-select
                  v-model:value="formData.interval"
                  placeholder="选择周期"
                  :options="intervalOptions"
                />
              </n-form-item>
            </n-gi>
          </n-grid>

          <!-- 触发类型 -->
          <n-form-item label="触发类型" path="trigger_type">
            <n-select
              v-model:value="formData.trigger_type"
              :options="triggerTypeOptions"
            />
          </n-form-item>

          <!-- 策略类型 -->
          <n-form-item label="策略类型" path="strategy_type">
            <n-select
              v-model:value="formData.strategy_type"
              :options="strategyOptions"
              placeholder="请选择策略"
              @update:value="handleStrategyChange"
            />
          </n-form-item>
        </n-space>

        <!-- 动态参数表单 -->
        <template v-if="currentParams.length > 0">
          <n-divider title-placement="left">策略参数</n-divider>

          <n-space vertical :size="16">
            <!-- MACD策略：显示为两个卡片 -->
            <template v-if="hasMacdParams">
              <n-grid :cols="2" :x-gap="16" :y-gap="16">
                <!-- MACD1 参数组 -->
                <n-gi>
                  <n-card title="MACD 1" size="small">
                    <n-space vertical :size="12">
                      <n-form-item
                        v-for="param in macd1Params"
                        :key="param.name"
                        :label="param.description"
                        :path="`params.${param.name}`"
                      >
                        <n-input-number
                          v-model:value="(formData.params[param.name] as number)"
                          :min="param.min"
                          :max="param.max"
                          :step="1"
                          style="width: 100%"
                        />
                      </n-form-item>
                    </n-space>
                  </n-card>
                </n-gi>

                <!-- MACD2 参数组 -->
                <n-gi>
                  <n-card title="MACD 2" size="small">
                    <n-space vertical :size="12">
                      <n-form-item
                        v-for="param in macd2Params"
                        :key="param.name"
                        :label="param.description"
                        :path="`params.${param.name}`"
                      >
                        <n-input-number
                          v-model:value="(formData.params[param.name] as number)"
                          :min="param.min"
                          :max="param.max"
                          :step="1"
                          style="width: 100%"
                        />
                      </n-form-item>
                    </n-space>
                  </n-card>
                </n-gi>
              </n-grid>
            </template>

            <!-- 非MACD策略：显示为简单列表 -->
            <template v-else>
              <n-form-item
                v-for="param in currentParams"
                :key="param.name"
                :label="param.description"
                :path="`params.${param.name}`"
              >
                <n-input-number
                  v-if="param.type === 'int'"
                  v-model:value="(formData.params[param.name] as number)"
                  :min="param.min"
                  :max="param.max"
                  :step="1"
                  style="width: 100%"
                />
                <n-input-number
                  v-else-if="param.type === 'float'"
                  v-model:value="(formData.params[param.name] as number)"
                  :min="param.min"
                  :max="param.max"
                  :step="0.01"
                  style="width: 100%"
                />
                <n-switch
                  v-else-if="param.type === 'bool'"
                  v-model:value="formData.params[param.name]"
                />
              </n-form-item>
            </template>
          </n-space>
        </template>

        <!-- 启用状态 -->
        <n-form-item label="状态" path="is_enabled">
          <n-switch v-model:value="formData.is_enabled">
            <template #checked>启用</template>
            <template #unchecked>禁用</template>
          </n-switch>
        </n-form-item>
      </n-form>
    </div>

    <!-- 操作按钮 -->
    <div class="form-footer">
      <n-button @click="handleCancel">取消</n-button>
      <n-button type="primary" :loading="submitting" @click="handleSubmit">
        {{ isEdit ? '保存' : '创建' }}
      </n-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import {
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NSelect,
  NSwitch,
  NButton,
  NSpace,
  NGrid,
  NGi,
  NDivider,
  NCard,
  NIcon,
  type FormInst,
  type FormRules,
} from 'naive-ui'
import { CloseOutline } from '@vicons/ionicons5'
import {
  useAlertStore,
  type AlertConfig,
  ALERT_TRIGGER_TYPE_OPTIONS,
  DEFAULT_PARAMS,
} from '../../stores/alert-store'
import { useStrategyStore } from '../../stores/strategy-store'

// 组件属性
interface Props {
  alert?: AlertConfig | null
}

const props = withDefaults(defineProps<Props>(), {
  alert: null,
})

// 组件事件
const emit = defineEmits<{
  (e: 'submit', data: AlertConfig): void
  (e: 'cancel'): void
}>()

// Store
const store = useAlertStore()
const strategyStore = useStrategyStore()

// 组件挂载时获取策略列表
onMounted(async () => {
  // 确保 WebSocket 已连接后再获取策略
  await store.connectWebSocket()
  strategyStore.fetchStrategies()
})

// 表单引用
const formRef = ref<FormInst | null>(null)

// 提交状态
const submitting = ref(false)

// 判断是否为编辑模式
const isEdit = computed(() => !!props.alert)

// 表单数据
const formData = reactive({
  name: '',
  description: '',
  trigger_type: 'each_kline_close',
  symbol: 'BINANCE:BTCUSDT',
  interval: '60',
  is_enabled: true,
  strategy_type: 'MACDResonanceStrategyV5',
  params: { ...DEFAULT_PARAMS },
} as {
  name: string
  description: string
  trigger_type: string
  symbol: string
  interval: string
  is_enabled: boolean
  strategy_type: string
  params: Record<string, number | boolean>
})

// 表单验证规则
const formRules: FormRules = {
  name: {
    required: true,
    message: '请输入告警名称',
    trigger: 'blur',
  },
  symbol: {
    required: true,
    message: '请选择交易对',
    trigger: 'change',
  },
  interval: {
    required: true,
    message: '请选择K线周期',
    trigger: 'change',
  },
  trigger_type: {
    required: true,
    message: '请选择触发类型',
    trigger: 'change',
  },
  'params.fast1': {
    required: true,
    type: 'number',
    message: '请输入快速EMA',
    trigger: 'blur',
  },
  'params.slow1': {
    required: true,
    type: 'number',
    message: '请输入慢速EMA',
    trigger: 'blur',
  },
  'params.signal1': {
    required: true,
    type: 'number',
    message: '请输入信号线',
    trigger: 'blur',
  },
  'params.fast2': {
    required: true,
    type: 'number',
    message: '请输入快速EMA',
    trigger: 'blur',
  },
  'params.slow2': {
    required: true,
    type: 'number',
    message: '请输入慢速EMA',
    trigger: 'blur',
  },
  'params.signal2': {
    required: true,
    type: 'number',
    message: '请输入信号线',
    trigger: 'blur',
  },
}

// 交易对选项
const symbolOptions = [
  { label: 'BTC/USDT', value: 'BINANCE:BTCUSDT' },
  { label: 'ETH/USDT', value: 'BINANCE:ETHUSDT' },
  { label: 'BNB/USDT', value: 'BINANCE:BNBUSDT' },
  { label: 'SOL/USDT', value: 'BINANCE:SOLUSDT' },
  { label: 'XRP/USDT', value: 'BINANCE:XRPUSDT' },
  { label: 'ADA/USDT', value: 'BINANCE:ADAUSDT' },
  { label: 'DOGE/USDT', value: 'BINANCE:DOGEUSDT' },
  { label: 'AVAX/USDT', value: 'BINANCE:AVAXUSDT' },
  { label: 'DOT/USDT', value: 'BINANCE:DOTUSDT' },
  { label: 'MATIC/USDT', value: 'BINANCE:MATICUSDT' },
]

// 周期选项
const intervalOptions = [
  { label: '1分钟', value: '1' },
  { label: '5分钟', value: '5' },
  { label: '15分钟', value: '15' },
  { label: '1小时', value: '60' },
  { label: '4小时', value: '240' },
  { label: '日线', value: 'D' },
  { label: '周线', value: 'W' },
]

// 触发类型选项
const triggerTypeOptions = ALERT_TRIGGER_TYPE_OPTIONS

// 策略选项（从 store 获取）
const strategyOptions = computed(() =>
  strategyStore.strategies.map(s => ({
    label: s.name,
    value: s.type
  }))
)

// 当前策略的参数定义
const currentParams = computed(() => {
  const strategy = strategyStore.getStrategyByType(formData.strategy_type)
  return strategy?.params || []
})

// 处理策略变更，重置参数为默认值
function handleStrategyChange(strategyType: string) {
  const strategy = strategyStore.getStrategyByType(strategyType)
  if (strategy) {
    // 重置参数为默认值
    strategy.params.forEach(param => {
      formData.params[param.name] = param.default
    })
  }
}

// 监听 props 变化
watch(
  () => props.alert,
  (newAlert) => {
    if (newAlert) {
      // 编辑模式：填充表单数据
      formData.name = newAlert.name
      formData.description = newAlert.description || ''
      formData.trigger_type = newAlert.trigger_type
      formData.symbol = newAlert.symbol
      formData.interval = newAlert.interval
      formData.is_enabled = newAlert.is_enabled
      formData.strategy_type = newAlert.strategy_type
      // 加载 params（如果存在）
      if (newAlert.params) {
        formData.params = { ...newAlert.params }
      } else {
        formData.params = { ...DEFAULT_PARAMS }
      }
    } else {
      // 创建模式：重置表单
      resetForm()
    }
  },
  { immediate: true }
)

// 重置表单
function resetForm() {
  formData.name = ''
  formData.description = ''
  formData.trigger_type = 'each_kline_close'
  formData.symbol = 'BINANCE:BTCUSDT'
  formData.interval = '60'
  formData.is_enabled = true
  formData.strategy_type = 'macd'
  formData.params = { ...DEFAULT_PARAMS }
}

// 提交表单
async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  submitting.value = true

  try {
    const submitData: AlertConfig = {
      id: props.alert?.id || '',
      name: formData.name,
      description: formData.description || null,
      trigger_type: formData.trigger_type,
      symbol: formData.symbol,
      interval: formData.interval,
      is_enabled: formData.is_enabled,
      strategy_type: formData.strategy_type,
      params: { ...formData.params },
      created_at: props.alert?.created_at || '',
      updated_at: props.alert?.updated_at || '',
      created_by: props.alert?.created_by || null,
    }

    emit('submit', submitData)
  } finally {
    submitting.value = false
  }
}

// 取消
function handleCancel() {
  emit('cancel')
}

// 判断当前策略是否有MACD参数（用于显示共振阈值）
const hasMacdParams = computed(() => {
  return currentParams.value.some(p => p.name.startsWith('macd1_') || p.name.startsWith('macd2_'))
})

// MACD1 参数列表
const macd1Params = computed(() => {
  return currentParams.value.filter(p => p.name.startsWith('macd1_'))
})

// MACD2 参数列表
const macd2Params = computed(() => {
  return currentParams.value.filter(p => p.name.startsWith('macd2_'))
})
</script>

<style scoped>
.alert-config-form {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, rgba(30, 30, 40, 0.5) 0%, rgba(20, 20, 28, 0.8) 100%);
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(255, 180, 0, 0.08);
}

.form-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 180, 0, 0.08);
  background: rgba(255, 180, 0, 0.03);
}

.form-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  letter-spacing: 0.5px;
}

.form-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.form-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid rgba(255, 180, 0, 0.08);
  background: rgba(255, 180, 0, 0.02);
}

</style>
