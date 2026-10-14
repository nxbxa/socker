<script setup>
/**
 * 统一图标组件
 * ============
 * 用法：<AppIcon name="dashboard" :size="18" />
 * 颜色继承父元素 currentColor，可通过 CSS 的 color 控制。
 */
import { computed } from 'vue'
import { icons } from '../icons'

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 18 },
  /** 描边粗细 */
  stroke: { type: [Number, String], default: 1.7 },
})

const paths = computed(() => icons[props.name] || [])
</script>

<template>
  <svg
    class="app-icon"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    :stroke-width="stroke"
    stroke="currentColor"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path v-for="(d, i) in paths" :key="i" :d="d" />
  </svg>
</template>

<style scoped>
.app-icon {
  display: inline-block;
  flex-shrink: 0;
  vertical-align: -0.15em;
}
</style>
