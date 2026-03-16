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
          <n-form-item label="触发类型" path="triggerType">
            <n-select
              v-model:value="formData.triggerType"
              :options="triggerTypeOptions"
            />
          </n-form-item>

          <!-- 策略类型 -->
          <n-form-item label="策略类型" path="strategyType">
            <n-select
              v-model:value="formData.strategyType"
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
                          v-model:value="paramsData[param.name]"
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
                          v-model:value="paramsData[param.name]"
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
                <input
                  v-if="param.type === 'int'"
                  type="number"
                  :value="paramsData[param.name]"
                  @input="(e) => paramsData[param.name] = Number((e.target as HTMLInputElement).value)"
                  :min="param.min"
                  :max="param.max"
                  style="width: 100%; padding: 8px; border: 1px solid #333; border-radius: 4px; background: #1a1a1a; color: #fff;"
                />
                <input
                  v-else-if="param.type === 'float'"
                  type="number"
                  :value="paramsData[param.name]"
                  @input="(e) => paramsData[param.name] = Number((e.target as HTMLInputElement).value)"
                  :min="param.min"
                  :max="param.max"
                  step="0.01"
                  style="width: 100%; padding: 8px; border: 1px solid #333; border-radius: 4px; background: #1a1a1a; color: #fff;"
                />
                <n-switch
                  v-else-if="param.type === 'bool'"
                  :value="(paramsData[param.name] as boolean)"
                  @update:value="(val) => paramsData[param.name] = (val as boolean)"
                />
              </n-form-item>
            </template>
          </n-space>
        </template>

        <!-- 启用状态 -->
        <n-form-item label="状态" path="isEnabled">
          <n-switch v-model:value="formData.isEnabled">
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
  ALERT_STRATEGY_TYPE_OPTIONS,
  formatParamName,
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
  // 确保 DataService 已连接后再获取策略
  await store.initialize()
  strategyStore.fetchStrategies()
})

// 监听策略列表加载完成，自动初始化当前策略的参数
watch(
  () => strategyStore.strategies,
  (newStrategies) => {
    if (newStrategies.length > 0) {
      // 如果当前没有选择策略，使用第一个可用策略
      if (!formData.strategyType) {
        formData.strategyType = newStrategies[0].type
      }

      // 根据当前策略类型初始化参数
      const strategy = strategyStore.getStrategyByType(formData.strategyType)
      if (strategy && strategy.params.length > 0) {
        // 使用策略的默认参数
        const defaultParams: Record<string, number | boolean> = {}
        strategy.params.forEach(param => {
          defaultParams[param.name] = param.default
        })
        paramsData.value = defaultParams
      } else {
        // 无参数策略（如随机策略），清空参数
        paramsData.value = {}
      }
    }
  },
  { immediate: true }
)

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
  triggerType: 'each_kline_close',
  symbol: 'BINANCE:BTCUSDT',
  interval: '60',
  isEnabled: true,
  // 默认使用第一个可用策略，如果没有则使用 MACD 共振策略
  strategyType: '',
})

// 使用 ref 来存储参数，确保响应性
// 初始值使用 strategyStore.getDefaultParams 获取，会根据 strategyType 返回正确的默认值
const paramsData = ref<Record<string, number | boolean>>(
  strategyStore.getDefaultParams(formData.strategyType)
)

// 计算属性访问 params
const formDataWithParams = computed(() => ({
  ...formData,
  params: paramsData.value
}))

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

// 将驼峰策略类型转换为可读显示格式
function formatStrategyTypeForSelect(strategyType: string): string {
  if (!strategyType) return ''
  return strategyType
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2')
    .replace(/([A-Z])(\d+)(?=[A-Z]|$)/g, '$1$2')
    .replace(/(\d+)(?=[A-Z])/g, '$1 ')
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

// 策略选项（从 store 获取，使用转换后的 strategyType 作为显示）
const strategyOptions = computed(() =>
  strategyStore.strategies.map(s => ({
    label: formatStrategyTypeForSelect(s.type),
    value: s.type
  }))
)

// 当前策略的参数定义
// 优先使用表单中已存储的参数（编辑模式），否则使用策略默认参数
const currentParams = computed(() => {
  // 如果 paramsData 有内容，说明是编辑模式，使用实际存储的参数
  if (paramsData.value && Object.keys(paramsData.value).length > 0) {
    return Object.entries(paramsData.value).map(([name, value]) => ({
      name,
      // 使用 formatParamName 将参数名转换为友好显示格式
      description: formatParamName(name),
      type: typeof value === 'number' ? (Number.isInteger(value) ? 'int' : 'float') : typeof value === 'boolean' ? 'bool' : 'int',
      default: value,
      min: 0,
      max: 9999,
    }))
  }

  // 创建模式：使用策略默认参数
  const strategy = strategyStore.getStrategyByType(formData.strategyType)
  if (strategy?.params && strategy.params.length > 0) {
    return strategy.params
  }

  // 无参数策略（如随机策略），返回空数组
  return []
})

// 处理策略变更，重置参数为默认值
function handleStrategyChange(strategyType: string) {
  const strategy = strategyStore.getStrategyByType(strategyType)
  if (strategy && strategy.params.length > 0) {
    // 完全替换参数为新策略的默认值
    const newParams: Record<string, number | boolean> = {}
    strategy.params.forEach(param => {
      newParams[param.name] = param.default
    })
    paramsData.value = newParams
  } else {
    // 无参数策略（如随机策略），清空参数
    paramsData.value = {}
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
      formData.triggerType = newAlert.triggerType
      formData.symbol = newAlert.symbol
      formData.interval = newAlert.interval
      formData.isEnabled = newAlert.isEnabled
      formData.strategyType = newAlert.strategyType
      // 加载 params（如果存在）
      if (newAlert.params && Object.keys(newAlert.params).length > 0) {
        paramsData.value = { ...newAlert.params } as Record<string, number | boolean>
      } else {
        paramsData.value = { ...DEFAULT_PARAMS }
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
  formData.triggerType = 'each_kline_close'
  formData.symbol = 'BINANCE:BTCUSDT'
  formData.interval = '60'
  formData.isEnabled = true
  // 使用第一个可用的策略类型，如果没有则使用默认值
  formData.strategyType = strategyStore.strategies[0]?.type || 'MACDResonanceStrategyV5'

  // 使用策略的默认参数，而不是硬编码的 DEFAULT_PARAMS
  const strategy = strategyStore.getStrategyByType(formData.strategyType)
  if (strategy && strategy.params.length > 0) {
    const newParams: Record<string, number | boolean> = {}
    strategy.params.forEach(param => {
      newParams[param.name] = param.default
    })
    paramsData.value = newParams
  } else {
    // 无参数策略（如随机策略），清空参数
    paramsData.value = {}
  }
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
      description: formData.description || undefined,
      triggerType: formData.triggerType,
      symbol: formData.symbol,
      interval: formData.interval,
      isEnabled: formData.isEnabled,
      strategyType: formData.strategyType,
      params: { ...paramsData.value },
      createdAt: props.alert?.createdAt || '',
      updatedAt: props.alert?.updatedAt || '',
      createdBy: props.alert?.createdBy || undefined,
    }

    emit('submit', submitData)
  } finally {
    submitting.value = false
  }
}

// 获取参数值的辅助函数
function getParamValue(name: string): number | undefined {
  const val = paramsData.value[name]
  return typeof val === 'number' ? val : undefined
}

// 设置参数值的辅助函数
function setParamValue(name: string, value: number | boolean | null) {
  if (value !== null) {
    paramsData.value[name] = value as number | boolean
  }
}

// 创建动态参数的计算属性
function createParamModel(name: string) {
  return computed({
    get: () => getParamValue(name),
    set: (val: number | boolean | null) => setParamValue(name, val)
  })
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
