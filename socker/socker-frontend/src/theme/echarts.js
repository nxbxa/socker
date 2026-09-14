/**
 * ECharts 统一主题
 * ================
 * 全站图表共用一套深色主题：统一色板、轴网、tooltip、图例样式。
 *
 * 使用方式（必须走 echarts/core 的按需引入体系）：
 *   import { use } from 'echarts/core'
 *   import { CHART_THEME_NAME, chartTheme } from '../theme/echarts'
 *   use([...])                       // 先注册所需组件
 *   echarts.registerTheme(CHART_THEME_NAME, chartTheme)
 *   echarts.init(el, CHART_THEME_NAME)
 *
 * 色板顺序与 CSS 设计令牌保持一致（见 styles/theme.css）。
 */

export const CHART_THEME_NAME = 'football-dark'

/** 图表色板：主强调绿 → 信息蓝 → 金 → 紫 → 青 → 粉 */
export const CHART_PALETTE = [
  '#00e07a',
  '#3aa0ff',
  '#f2b73d',
  '#a06bff',
  '#22d3ee',
  '#ff7ab6',
  '#00b862',
  '#ff5c6c',
]

/** 常用语义色（供组件直接引用，避免散落硬编码） */
export const CHART_COLORS = {
  accent: '#00e07a',
  gold: '#f2b73d',
  info: '#3aa0ff',
  danger: '#ff5c6c',
  purple: '#a06bff',
  cyan: '#22d3ee',
  text1: '#e8edf5',
  text2: '#9aa7bd',
  text3: '#5f6b80',
  line: '#222c3c',
  panel: '#10151f',
}

const AXIS_LABEL = { color: '#9aa7bd', fontSize: 12 }
const AXIS_NAME = { color: '#5f6b80', fontSize: 12 }
const SPLIT_LINE = { lineStyle: { color: '#222c3c', type: 'dashed' } }

const TOOLTIP = {
  backgroundColor: 'rgba(16, 21, 31, 0.96)',
  borderColor: '#2e3a4d',
  borderWidth: 1,
  padding: [10, 14],
  textStyle: { color: '#e8edf5', fontSize: 12.5 },
  extraCssText:
    'border-radius:10px;box-shadow:0 8px 28px rgba(0,0,0,.5);backdrop-filter:blur(6px);',
}

export const chartTheme = {
  color: CHART_PALETTE,
  backgroundColor: 'transparent',

  textStyle: {
    fontFamily:
      "'Inter','HarmonyOS Sans SC','PingFang SC','Microsoft YaHei',system-ui,sans-serif",
    color: '#9aa7bd',
  },

  title: {
    textStyle: { color: '#e8edf5', fontSize: 14, fontWeight: 600 },
    subtextStyle: { color: '#5f6b80', fontSize: 12 },
  },

  legend: {
    textStyle: { color: '#9aa7bd', fontSize: 12 },
    inactiveColor: '#3d4c63',
    itemWidth: 12,
    itemHeight: 8,
    itemGap: 14,
  },

  tooltip: TOOLTIP,
  // 坐标轴触发的 tooltip 需要单独配置，否则不会继承上面的深色样式
  axisPointer: {
    lineStyle: { color: '#3d4c63' },
    crossStyle: { color: '#3d4c63' },
    label: {
      backgroundColor: '#2e3a4d',
      color: '#e8edf5',
      borderColor: '#3d4c63',
    },
  },

  grid: {
    left: 12,
    right: 16,
    top: 48,
    bottom: 12,
    containLabel: true,
    borderColor: '#222c3c',
  },

  categoryAxis: {
    axisLine: { lineStyle: { color: '#2e3a4d' } },
    axisTick: { show: false },
    axisLabel: AXIS_LABEL,
    nameTextStyle: AXIS_NAME,
    splitLine: { show: false },
  },

  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: AXIS_LABEL,
    nameTextStyle: AXIS_NAME,
    splitLine: SPLIT_LINE,
  },

  logAxis: {
    axisLine: { lineStyle: { color: '#2e3a4d' } },
    axisLabel: AXIS_LABEL,
    splitLine: SPLIT_LINE,
  },

  radar: {
    axisName: { color: '#9aa7bd', fontSize: 12 },
    axisLine: { lineStyle: { color: '#222c3c' } },
    splitLine: { lineStyle: { color: '#222c3c' } },
    splitArea: {
      show: true,
      areaStyle: { color: ['rgba(255,255,255,0.012)', 'transparent'] },
    },
  },

  // 饼图 / 环形图的默认描边用面板底色，形成分割感
  pie: {
    itemStyle: { borderColor: '#10151f', borderWidth: 2 },
    label: { color: '#9aa7bd' },
    labelLine: { lineStyle: { color: '#2e3a4d' } },
  },

  bar: {
    itemStyle: { borderRadius: [4, 4, 0, 0] },
    label: { color: '#e8edf5' },
  },

  line: {
    symbolSize: 6,
    smooth: true,
    lineStyle: { width: 2 },
  },

  scatter: {
    itemStyle: { opacity: 0.88 },
  },

  visualMap: {
    textStyle: { color: '#9aa7bd' },
  },

  dataZoom: {
    borderColor: '#2e3a4d',
    textStyle: { color: '#9aa7bd' },
    handleStyle: { color: '#3d4c63' },
    fillerColor: 'rgba(0,224,122,0.08)',
  },
}

export default chartTheme
