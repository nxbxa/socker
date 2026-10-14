/**
 * ECharts 统一主题
 * ================
 * 全站图表共用一套浅色主题：统一色板、轴网、tooltip、图例样式。
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

export const CHART_THEME_NAME = 'football-light'

/** 图表色板：主强调绿 → 信息蓝 → 金 → 紫 → 青 → 粉 */
export const CHART_PALETTE = [
  '#00b862',
  '#2589e8',
  '#d99a20',
  '#7c3aed',
  '#0891b2',
  '#db2777',
  '#009a52',
  '#e53e4d',
]

/** 常用语义色（供组件直接引用，避免散落硬编码） */
export const CHART_COLORS = {
  accent: '#00b862',
  gold: '#d99a20',
  info: '#2589e8',
  danger: '#e53e4d',
  purple: '#7c3aed',
  cyan: '#0891b2',
  text1: '#1a2332',
  text2: '#5a6a82',
  text3: '#94a3b8',
  line: '#e2e8f0',
  panel: '#ffffff',
}

const AXIS_LABEL = { color: '#5a6a82', fontSize: 12 }
const AXIS_NAME = { color: '#94a3b8', fontSize: 12 }
const SPLIT_LINE = { lineStyle: { color: '#e2e8f0', type: 'dashed' } }

const TOOLTIP = {
  backgroundColor: 'rgba(255, 255, 255, 0.98)',
  borderColor: '#e2e8f0',
  borderWidth: 1,
  padding: [10, 14],
  textStyle: { color: '#1a2332', fontSize: 12.5 },
  extraCssText:
    'border-radius:10px;box-shadow:0 4px 16px rgba(0,0,0,.08);backdrop-filter:blur(6px);',
}

export const chartTheme = {
  color: CHART_PALETTE,
  backgroundColor: 'transparent',

  textStyle: {
    fontFamily:
      "'Inter','HarmonyOS Sans SC','PingFang SC','Microsoft YaHei',system-ui,sans-serif",
    color: '#5a6a82',
  },

  title: {
    textStyle: { color: '#1a2332', fontSize: 14, fontWeight: 600 },
    subtextStyle: { color: '#94a3b8', fontSize: 12 },
  },

  legend: {
    textStyle: { color: '#5a6a82', fontSize: 12 },
    inactiveColor: '#cbd5e1',
    itemWidth: 12,
    itemHeight: 8,
    itemGap: 14,
  },

  tooltip: TOOLTIP,
  // 坐标轴触发的 tooltip 需要单独配置，否则不会继承上面的浅色样式
  axisPointer: {
    lineStyle: { color: '#cbd5e1' },
    crossStyle: { color: '#cbd5e1' },
    label: {
      backgroundColor: '#1a2332',
      color: '#ffffff',
      borderColor: '#1a2332',
    },
  },

  grid: {
    left: 12,
    right: 16,
    top: 48,
    bottom: 12,
    containLabel: true,
    borderColor: '#e2e8f0',
  },

  categoryAxis: {
    axisLine: { lineStyle: { color: '#cbd5e1' } },
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
    axisLine: { lineStyle: { color: '#cbd5e1' } },
    axisLabel: AXIS_LABEL,
    splitLine: SPLIT_LINE,
  },

  radar: {
    axisName: { color: '#5a6a82', fontSize: 12 },
    axisLine: { lineStyle: { color: '#e2e8f0' } },
    splitLine: { lineStyle: { color: '#e2e8f0' } },
    splitArea: {
      show: true,
      areaStyle: { color: ['rgba(0,0,0,0.02)', 'transparent'] },
    },
  },

  // 饼图 / 环形图的默认描边用面板底色，形成分割感
  pie: {
    itemStyle: { borderColor: '#ffffff', borderWidth: 2 },
    label: { color: '#5a6a82' },
    labelLine: { lineStyle: { color: '#cbd5e1' } },
  },

  bar: {
    itemStyle: { borderRadius: [4, 4, 0, 0] },
    label: { color: '#1a2332' },
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
    textStyle: { color: '#5a6a82' },
  },

  dataZoom: {
    borderColor: '#e2e8f0',
    textStyle: { color: '#5a6a82' },
    handleStyle: { color: '#cbd5e1' },
    fillerColor: 'rgba(0, 184, 98, 0.08)',
  },
}

export default chartTheme
