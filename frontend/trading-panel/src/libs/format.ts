/**
 * 币安订单参数格式化工具
 *
 * 根据币安过滤器规则，对订单参数进行舍入处理
 * 确保数量和价格满足 stepSize 和 tickSize 的要求
 */

/**
 * 将数值舍入到指定步长的整数倍
 * 用于满足 LOT_SIZE (stepSize) 和 PRICE_FILTER (tickSize) 要求
 *
 * @param value - 要舍入的值
 * @param stepSize - 步长（如 0.00001 for BTCUSDT quantity）
 * @param direction - 舍入方向：'floor'（向下）|'round'（四舍五入）|'ceil'（向上）
 * @returns 舍入后的值
 *
 * @example
 * roundToStep(0.04397598, 0.00001, 'floor')  // 0.04397
 * roundToStep(0.04397598, 0.00001, 'round')  // 0.04398
 * roundToStep(70000.001, 0.01, 'floor')      // 70000.00
 */
export function roundToStep(
  value: number,
  stepSize: number,
  direction: 'floor' | 'round' | 'ceil' = 'floor'
): number {
  if (stepSize <= 0) {
    throw new Error('stepSize must be positive')
  }

  const quotient = value / stepSize
  let result: number

  switch (direction) {
    case 'floor':
      result = Math.floor(quotient) * stepSize
      break
    case 'ceil':
      result = Math.ceil(quotient) * stepSize
      break
    case 'round':
      result = Math.round(quotient) * stepSize
      break
  }

  // 修复浮点数精度问题：确保结果精确到 stepSize 对应的小数位数
  // 例如: 0.0010500000000000002 → 0.00105
  const precision = getDecimalPlaces(stepSize)
  return parseFloat(result.toFixed(precision))
}

/**
 * 检查数值是否满足步长要求
 *
 * @param value - 要检查的值
 * @param stepSize - 步长
 * @returns 是否满足要求
 *
 * @example
 * isValidStep(0.04397, 0.00001)   // true
 * isValidStep(0.04397598, 0.00001) // false
 */
export function isValidStep(value: number, stepSize: number): boolean {
  if (stepSize <= 0) {
    return false
  }
  const remainder = value % stepSize
  // 使用小的容差来处理浮点数精度问题
  const tolerance = 1e-10
  return remainder < tolerance || (stepSize - remainder) < tolerance
}

/**
 * 格式化订单数量
 * 向下舍入到 stepSize 的整数倍（确保不超过用户输入值）
 *
 * @param quantity - 原始数量
 * @param stepSize - 步长
 * @returns 格式化后的数量字符串
 *
 * @example
 * formatQuantity(0.04397598, 0.00001)  // "0.04397"
 * formatQuantity(0.04461714, 0.00001)   // "0.04461"
 */
export function formatQuantity(quantity: number, stepSize: number): string {
  const rounded = roundToStep(quantity, stepSize, 'floor')
  // 转换为字符串，保持合理的精度
  return rounded.toFixed(getDecimalPlaces(stepSize))
}

/**
 * 格式化订单价格
 * 向下舍入到 tickSize 的整数倍（确保不超过用户输入值）
 *
 * @param price - 原始价格
 * @param tickSize - 价格步长
 * @returns 格式化后的价格字符串
 *
 * @example
 * formatPrice(70000.001, 0.01)  // "70000.00"
 * formatPrice(70000.999, 0.01)  // "70000.99"
 */
export function formatPrice(price: number, tickSize: number): string {
  const rounded = roundToStep(price, tickSize, 'floor')
  return rounded.toFixed(getDecimalPlaces(tickSize))
}

/**
 * 获取小数位数
 *
 * @param step - 步长值
 * @returns 小数位数
 *
 * @example
 * getDecimalPlaces(0.00001)  // 5
 * getDecimalPlaces(0.01)      // 2
 * getDecimalPlaces(1)         // 0
 */
export function getDecimalPlaces(step: number): number {
  if (step >= 1) {
    return 0
  }
  // 计算小数位数
  const str = step.toString()
  const decimalIndex = str.indexOf('.')
  if (decimalIndex === -1) {
    return 0
  }
  return str.length - decimalIndex - 1
}

/**
 * 验证订单数量是否满足币安 LOT_SIZE 过滤器要求
 *
 * @param quantity - 数量
 * @param minQty - 最小数量
 * @param maxQty - 最大数量
 * @param stepSize - 步长
 * @returns 验证结果和错误信息
 */
export function validateQuantity(
  quantity: number,
  minQty: number,
  maxQty: number,
  stepSize: number
): { valid: boolean; error?: string } {
  if (quantity < minQty) {
    return { valid: false, error: `数量低于最小值 ${minQty}` }
  }
  if (quantity > maxQty) {
    return { valid: false, error: `数量超过最大值 ${maxQty}` }
  }
  if (!isValidStep(quantity, stepSize)) {
    const rounded = roundToStep(quantity, stepSize, 'floor')
    return {
      valid: false,
      error: `数量必须是 ${stepSize} 的整数倍，可调整为 ${rounded}`,
    }
  }
  return { valid: true }
}

/**
 * 验证订单价格是否满足币安 PRICE_FILTER 要求
 *
 * @param price - 价格
 * @param minPrice - 最小价格
 * @param maxPrice - 最大价格
 * @param tickSize - 步长
 * @returns 验证结果和错误信息
 */
export function validatePrice(
  price: number,
  minPrice: number,
  maxPrice: number,
  tickSize: number
): { valid: boolean; error?: string } {
  if (price < minPrice) {
    return { valid: false, error: `价格低于最小值 ${minPrice}` }
  }
  if (price > maxPrice) {
    return { valid: false, error: `价格超过最大值 ${maxPrice}` }
  }
  if (!isValidStep(price, tickSize)) {
    const rounded = roundToStep(price, tickSize, 'floor')
    return {
      valid: false,
      error: `价格必须是 ${tickSize} 的整数倍，可调整为 ${rounded}`,
    }
  }
  return { valid: true }
}

/**
 * 验证订单名义价值是否满足最低要求
 *
 * @param quantity - 数量
 * @param price - 价格
 * @param minNotional - 最小名义价值
 * @returns 验证结果和错误信息
 */
export function validateNotional(
  quantity: number,
  price: number,
  minNotional: number
): { valid: boolean; error?: string } {
  const notional = quantity * price
  if (notional < minNotional) {
    return {
      valid: false,
      error: `订单名义价值 ${notional.toFixed(2)} 低于最低要求 ${minNotional}`,
    }
  }
  return { valid: true }
}
