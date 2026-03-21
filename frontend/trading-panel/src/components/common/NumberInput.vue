<script setup lang="ts">
/**
 * 原生数字输入框组件
 *
 * 特性：
 * - 实时字符过滤（拒绝 e, E, +, -, 等非法字符）
 * - 小数位数限制
 * - 前缀/后缀标签
 * - 支持币安的 tickSize/lotSize 步进验证
 *
 * 注意：步进按钮已从组件中移除，如需步进按钮请使用 StepperButtons 组件
 */
import { ref, computed, watch, nextTick, type Ref } from 'vue'
import { roundToStep, getDecimalPlaces } from '../../libs/format'

// Props 定义
interface Props {
  modelValue?: number | null
  prefix?: string           // 前缀标签，如"价格"、"数量"
  suffix?: string           // 后缀，如"USDT"、"BTC"
  precision?: number        // 小数位数限制（如 2, 8）
  stepSize?: number         // 步进值（用于 +/- 按钮和验证）
  min?: number              // 最小值
  max?: number              // 最大值
  placeholder?: string
  disabled?: boolean
  size?: 'small' | 'medium' | 'large'
  theme?: 'buy' | 'sell' | 'default'  // 主题色
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: null,
  prefix: '',
  suffix: '',
  precision: 2,
  stepSize: 0.01,
  min: 0,
  max: Infinity,
  placeholder: '',
  disabled: false,
  size: 'medium',
  theme: 'default',
})

// Emits
const emit = defineEmits<{
  (e: 'update:modelValue', value: number | null): void
  (e: 'change', value: number | null): void
  (e: 'blur'): void
  (e: 'focus'): void
}>()

// 暴露方法给父组件
defineExpose({
  stepIncrement,
  stepDecrement,
  focus: () => inputRef.value?.focus(),
  blur: () => inputRef.value?.blur(),
})

// 内部显示值（可能包含未提交的用户输入）
const displayValue = ref('')
const inputRef = ref<HTMLInputElement | null>(null)
const isFocused = ref(false)

// 记录上次合法值（用于恢复）
const lastValidValue = ref<number | null>(null)

// 计算实际小数位数
const decimalPlaces = computed(() => {
  if (props.precision !== undefined) {
    return props.precision
  }
  if (props.stepSize !== undefined) {
    return getDecimalPlaces(props.stepSize)
  }
  return 8  // 默认 8 位
})

// 初始化显示值
watch(
  () => props.modelValue,
  (val) => {
    // 只有当输入框没有焦点时才格式化显示值（避免在用户输入过程中覆盖）
    if (isFocused.value) {
      return
    }
    if (val !== null && val !== undefined) {
      displayValue.value = val.toFixed(decimalPlaces.value)
      lastValidValue.value = val
    } else {
      displayValue.value = ''
    }
  },
  { immediate: true }
)

/**
 * 过滤非法字符，只允许数字和小数点
 */
function filterInput(value: string): string {
  // 移除非数字和小数点外的所有字符
  let filtered = value.replace(/[^0-9.]/g, '')

  // 只能有一个小数点
  const parts = filtered.split('.')
  if (parts.length > 2) {
    filtered = parts[0] + '.' + parts.slice(1).join('')
  }

  // 限制小数位数
  if (parts.length === 2) {
    const intPart = parts[0]
    const fracPart = parts[1].slice(0, decimalPlaces.value)
    filtered = intPart + '.' + fracPart
  }

  return filtered
}

/**
 * 处理输入事件 - 实时过滤
 */
function handleInput(event: Event) {
  const target = event.target as HTMLInputElement
  const rawValue = target.value

  // 过滤非法字符
  const filtered = filterInput(rawValue)

  // 如果过滤后为空，设置显示为空
  if (filtered === '' || filtered === '.') {
    displayValue.value = filtered
    emitUpdate(null)
    return
  }

  // 解析为数字
  const numValue = parseFloat(filtered)

  // 如果无效，恢复到上次合法值
  if (isNaN(numValue)) {
    displayValue.value = lastValidValue.value?.toFixed(decimalPlaces.value) ?? ''
    return
  }

  // 检查是否超出范围
  let finalValue = numValue
  if (numValue > props.max) {
    finalValue = props.max
  } else if (numValue < props.min) {
    finalValue = props.min
  }

  // 更新显示值（保留用户输入的格式）
  displayValue.value = filtered

  // 如果值有效且改变了，发射更新
  if (!isNaN(finalValue) && finalValue >= props.min && finalValue <= props.max) {
    emitUpdate(finalValue)
  }
}

/**
 * 处理 blur 事件 - 规范化值
 */
function handleBlur() {
  isFocused.value = false
  const current = parseFloat(displayValue.value)

  if (isNaN(current) || current < props.min) {
    // 恢复到上次合法值或最小值
    const val = lastValidValue.value ?? props.min
    displayValue.value = val.toFixed(decimalPlaces.value)
    emitUpdate(val)
  } else {
    // 规范化到步进的整数倍（向下取整）
    let normalized = current
    if (props.stepSize && props.stepSize > 0) {
      normalized = roundToStep(current, props.stepSize, 'floor')
    }

    // 确保在范围内
    if (normalized > props.max) normalized = props.max
    if (normalized < props.min) normalized = props.min

    // 如果改变了，更新显示
    if (normalized !== current) {
      displayValue.value = normalized.toFixed(decimalPlaces.value)
    }

    lastValidValue.value = normalized
    emitUpdate(normalized)
  }

  emit('blur')
}

/**
 * 处理 focus 事件 - 选中文本
 */
function handleFocus() {
  isFocused.value = true
  // 选中输入框内容
  nextTick(() => {
    inputRef.value?.select()
  })
  emit('focus')
}

/**
 * 发射更新事件
 */
function emitUpdate(value: number | null) {
  // 检查值是否改变
  if (value !== lastValidValue.value) {
    lastValidValue.value = value
    emit('update:modelValue', value)
    emit('change', value)
  }
}

/**
 * 步进 - 增加
 * 使用 Math.round 来避免浮点精度问题
 * 例如 70385.9 + 0.01 = 70385.90999999999，直接除法会有精度问题
 * 使用 round 可以将 7038590.999999999 正确舍入到 7038591
 */
function stepIncrement() {
  let current = parseFloat(displayValue.value) || 0
  let newValue: number

  if (props.stepSize && props.stepSize > 0) {
    // 步进操作：先将 (current + stepSize) / stepSize 四舍五入到整数
    // 然后乘以 stepSize 得到新的步进值
    const quotient = (current + props.stepSize) / props.stepSize
    const roundedQuotient = Math.round(quotient)
    newValue = roundedQuotient * props.stepSize
  } else {
    newValue = current + 1
  }

  // 确保不超过最大值
  if (newValue > props.max) {
    newValue = props.max
  }

  displayValue.value = newValue.toFixed(decimalPlaces.value)
  lastValidValue.value = newValue
  emitUpdate(newValue)

  // 聚焦以显示光标
  inputRef.value?.focus()
}

/**
 * 步进 - 减少
 * 使用 Math.round 来避免浮点精度问题
 */
function stepDecrement() {
  let current = parseFloat(displayValue.value) || 0
  let newValue: number

  if (props.stepSize && props.stepSize > 0) {
    // 步进操作：先将 (current - stepSize) / stepSize 四舍五入到整数
    const quotient = (current - props.stepSize) / props.stepSize
    const roundedQuotient = Math.round(quotient)
    newValue = roundedQuotient * props.stepSize
  } else {
    newValue = current - 1
  }

  // 确保不小于最小值
  if (newValue < props.min) {
    newValue = props.min
  }

  displayValue.value = newValue.toFixed(decimalPlaces.value)
  lastValidValue.value = newValue
  emitUpdate(newValue)

  // 聚焦以显示光标
  inputRef.value?.focus()
}

/**
 * 获取输入框类名
 */
const inputClass = computed(() => {
  const classes = ['native-input']
  classes.push(`size-${props.size}`)
  return classes.join(' ')
})

/**
 * 获取容器类名
 */
const wrapperClass = computed(() => {
  const classes = ['number-input-wrapper']
  if (props.disabled) classes.push('disabled')
  if (props.theme !== 'default') classes.push(`theme-${props.theme}`)
  return classes.join(' ')
})
</script>

<template>
  <div :class="wrapperClass">
    <!-- 前缀 -->
    <span v-if="prefix" class="input-prefix">{{ prefix }}</span>

    <!-- 输入框 -->
    <input
      ref="inputRef"
      type="text"
      inputmode="decimal"
      :class="inputClass"
      v-model="displayValue"
      :placeholder="placeholder"
      :disabled="disabled"
      autocomplete="off"
      @input="handleInput"
      @blur="handleBlur"
      @focus="handleFocus"
    />

    <!-- 后缀 -->
    <span v-if="suffix" class="currency-suffix">{{ suffix }}</span>
  </div>
</template>

<style scoped>
/* 容器 */
.number-input-wrapper {
  display: flex;
  align-items: center;
  background: #0f0f1a;
  border: 1px solid #2a2a4a;
  border-radius: 4px;
  height: 52px;
  padding: 0 12px;
  transition: border-color 0.2s;
  flex: 1;
  gap: 8px;
}

.number-input-wrapper:focus-within {
  border-color: #00c087;
}

/* 主题色 */
.number-input-wrapper.theme-buy:focus-within {
  border-color: #00c087;
}

.number-input-wrapper.theme-sell:focus-within {
  border-color: #ef4444;
}

/* 禁用状态 */
.number-input-wrapper.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 前缀 */
.input-prefix {
  font-size: 12px;
  color: #8b8b9e;
  white-space: nowrap;
  flex-shrink: 0;
}

/* 输入框 */
.native-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  text-align: right;
  height: 100%;
  padding: 0;
  min-width: 0;
}

.native-input::placeholder {
  color: #4a4a5a;
  text-align: right;
}

/* 输入框尺寸 */
.native-input.size-small {
  font-size: 12px;
}

.native-input.size-medium {
  font-size: 14px;
}

.native-input.size-large {
  font-size: 16px;
}

/* 后缀 */
.currency-suffix {
  font-size: 14px;
  color: #fff;
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
}
</style>
