<script setup>
/**
 * ECharts 图表包装组件
 * ====================
 * - 按需引入：只注册项目实际用到的图表与组件，避免打包整个 echarts
 * - 统一主题：注册 football-dark 主题，图表配色与页面设计令牌一致
 * - 自适应：用 ResizeObserver 监听容器尺寸（侧边栏折叠、栅格重排都能触发）
 * - 加载态：数据未到达时显示骨架屏，而不是一片空白
 */
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import {
  BarChart,
  LineChart,
  PieChart,
  RadarChart,
  ScatterChart,
} from 'echarts/charts'
import {
  DataZoomComponent,
  DatasetComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  RadarComponent,
  TitleComponent,
  TooltipComponent,
  TransformComponent,
  VisualMapComponent,
} from 'echarts/components'
import { LabelLayout, UniversalTransition } from 'echarts/features'
import { CanvasRenderer } from 'echarts/renderers'

import { CHART_THEME_NAME, chartTheme } from '../theme/echarts'

// 模块级只注册一次（组件多次实例化不会重复注册）
let registered = false
if (!registered) {
  echarts.use([
    BarChart,
    LineChart,
    PieChart,
    RadarChart,
    ScatterChart,
    DataZoomComponent,
    DatasetComponent,
    GridComponent,
    LegendComponent,
    MarkLineComponent,
    RadarComponent,
    TitleComponent,
    TooltipComponent,
    TransformComponent,
    VisualMapComponent,
    LabelLayout,
    UniversalTransition,
    CanvasRenderer,
  ])
  echarts.registerTheme(CHART_THEME_NAME, chartTheme)
  registered = true
}

const props = defineProps({
  /** ECharts option，直接透传 */
  option: { type: Object, required: true },
  height: { type: String, default: '320px' },
  /** 是否显示加载骨架 */
  loading: { type: Boolean, default: false },
})

const el = ref(null)
let chart = null
let observer = null

function render() {
  if (!chart) return
  // notMerge = true：切换位置/球员时彻底替换旧配置，避免残留系列
  chart.setOption(props.option || {}, true)
}

onMounted(async () => {
  await nextTick()
  if (!el.value) return

  chart = echarts.init(el.value, CHART_THEME_NAME, { renderer: 'canvas' })
  render()

  // 监听容器自身尺寸变化，比 window.resize 更可靠
  if (typeof ResizeObserver !== 'undefined') {
    observer = new ResizeObserver(() => chart && chart.resize())
    observer.observe(el.value)
  } else {
    window.addEventListener('resize', handleWindowResize)
  }
})

function handleWindowResize() {
  chart && chart.resize()
}

onBeforeUnmount(() => {
  if (observer && el.value) {
    observer.unobserve(el.value)
    observer.disconnect()
  }
  observer = null
  window.removeEventListener('resize', handleWindowResize)
  chart && chart.dispose()
  chart = null
})

watch(
  () => props.option,
  () => render(),
  { deep: true }
)

// 骨架屏 -> 图表切换后容器尺寸会变化，需要重算
watch(
  () => props.loading,
  async () => {
    await nextTick()
    chart && chart.resize()
  }
)
</script>

<template>
  <div class="chart-wrap" :style="{ height }">
    <div v-show="!loading" ref="el" class="chart-canvas" />
    <div v-if="loading" class="chart-skeleton">
      <div class="sk-bar" />
      <div class="sk-bar sk-bar--short" />
      <div class="sk-bar" />
    </div>
  </div>
</template>

<style scoped>
.chart-wrap {
  position: relative;
  width: 100%;
}

.chart-canvas {
  width: 100%;
  height: 100%;
}

.chart-skeleton {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 10px;
  padding: 20px 12px 32px;
}

.sk-bar {
  height: 55%;
  border-radius: var(--r-sm);
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0.035) 25%,
    rgba(255, 255, 255, 0.075) 37%,
    rgba(255, 255, 255, 0.035) 63%
  );
  background-size: 400% 100%;
  animation: sk-shimmer 1.4s ease infinite;
}

.sk-bar--short {
  height: 35%;
}

@keyframes sk-shimmer {
  0% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0 50%;
  }
}
</style>
