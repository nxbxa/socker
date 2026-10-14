/**
 * 数据格式化工具
 * ==============
 * 后端（Python）统一用 json_safe() 把 NaN / Inf 转成 JSON null，
 * 因此任何数值字段都可能是 null —— 所有格式化必须先判空，
 * 否则 .toFixed() 会直接抛 TypeError 导致整个表格/图表白屏。
 */

/** 数值是否有效（排除 null / undefined / NaN / 空串） */
export function isNum(value) {
  return value !== null && value !== undefined && value !== '' && !Number.isNaN(Number(value))
}

/**
 * 数值格式化，无效值返回占位符。
 * @param {*} value 原始值
 * @param {number} digits 小数位
 * @param {string} fallback 无效值占位符
 */
export function fmt(value, digits = 1, fallback = '—') {
  if (!isNum(value)) return fallback
  return Number(value).toFixed(digits)
}

/** 评分格式化（默认 2 位小数） */
export function fmtScore(value, fallback = '—') {
  return fmt(value, 2, fallback)
}

/** 整数格式化（千分位） */
export function fmtInt(value, fallback = '—') {
  if (!isNum(value)) return fallback
  return Number(value).toLocaleString('zh-CN')
}

/** 出场时间格式化：1234 -> 1,234 */
export function fmtMinutes(value, fallback = '—') {
  return fmtInt(value, fallback)
}

/** 百分比格式化：0.8231 -> 82.3%（入参为 0-1 小数） */
export function fmtRatio(value, digits = 1, fallback = '—') {
  if (!isNum(value)) return fallback
  return `${(Number(value) * 100).toFixed(digits)}%`
}

/**
 * 已经是百分数尺度的字段（如 SavePct = 72.5）直接加 % 号。
 * 注意：max 超过 1.5 视为已是百分数尺度。
 */
export function fmtPctValue(value, digits = 1, fallback = '—') {
  if (!isNum(value)) return fallback
  return `${Number(value).toFixed(digits)}%`
}

/** 差值格式化：带正负号，如 +3.2 / -1.5 / 0.0 */
export function fmtDiff(value, digits = 1, fallback = '—') {
  if (!isNum(value)) return fallback
  const n = Number(value)
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(digits)}`
}

/** 位置代码 -> 中文名 */
const POSITION_LABELS = {
  FW: '前锋',
  MF: '中场',
  DF: '后卫',
  GK: '门将',
}

export function positionLabel(code) {
  return POSITION_LABELS[code] || code || '—'
}

/** 国旗图片 URL（后端只给三字母代码） */
export function flagUrl(code) {
  return code ? `https://flagcdn.com/w40/${String(code).toLowerCase()}.png` : ''
}

/**
 * 评分对应的色阶（用于表格标签 / 进度条着色）。
 * 返回一个语义级别，交由 CSS 决定具体颜色。
 */
export function scoreLevel(score) {
  if (!isNum(score)) return 'none'
  const n = Number(score)
  if (n >= 85) return 'elite'
  if (n >= 70) return 'good'
  if (n >= 55) return 'mid'
  return 'low'
}

/** 评分色阶对应的十六进制色值（供内联 style / 图表使用） */
export const SCORE_COLORS = {
  elite: '#00b862',
  good: '#2589e8',
  mid: '#d99a20',
  low: '#e53e4d',
  none: '#94a3b8',
}

export function scoreColor(score) {
  return SCORE_COLORS[scoreLevel(score)]
}
