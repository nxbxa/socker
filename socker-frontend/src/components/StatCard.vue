<script setup>
/**
 * KPI 统计卡片
 * ============
 * 现代浅色数据卡片：左侧色条 + 图标 + 大号渐变数字 + 说明文字。
 * hover 时上浮 + 边框发光。数值为 null 时显示占位符而不是 0。
 */
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'
import { fmt } from '../utils/format'

const props = defineProps({
  label: { type: String, required: true },
  value: { type: [Number, String], default: null },
  /** 说明 / 副标题 */
  hint: { type: String, default: '' },
  /** 图标名（见 src/icons/index.js） */
  icon: { type: String, default: '' },
  /** 单位后缀，如 "人" / "分钟" */
  unit: { type: String, default: '' },
  /** 小数位；传 null 表示原样输出字符串 */
  digits: { type: Number, default: 0 },
  /** 主题色：accent | gold | info | danger | purple */
  tone: { type: String, default: 'accent' },
})

const display = computed(() => {
  if (props.value === null || props.value === undefined || props.value === '') {
    return '—'
  }
  if (typeof props.value === 'number' && props.digits !== null) {
    return fmt(props.value, props.digits)
  }
  return props.value
})

const isEmpty = computed(
  () => props.value === null || props.value === undefined || props.value === ''
)
</script>

<template>
  <div class="stat" :class="`tone-${tone}`">
    <div class="stat-glow" />
    <div class="stat-head">
      <span class="stat-label">{{ label }}</span>
      <span v-if="icon" class="stat-icon"><AppIcon :name="icon" :size="16" /></span>
    </div>
    <div class="stat-value num" :class="{ 'is-empty': isEmpty }">
      <span v-if="!isEmpty" class="value-gradient">{{ display }}</span>
      <template v-else>{{ display }}</template>
      <em v-if="unit && !isEmpty" class="stat-unit">{{ unit }}</em>
    </div>
    <div v-if="hint" class="stat-hint">{{ hint }}</div>
  </div>
</template>

<style scoped>
.stat {
  position: relative;
  overflow: hidden;
  padding: 20px 22px;
  border-radius: var(--r-lg);
  background: var(--bg-panel);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-panel);
  transition: all 0.25s cubic-bezier(0.22, 1, 0.36, 1);
}

.stat:hover {
  border-color: var(--tone-line);
  transform: translateY(-3px);
  box-shadow: var(--shadow-panel-hover);
}

/* 左侧主题色条 */
.stat::before {
  content: '';
  position: absolute;
  left: 0;
  top: 18px;
  bottom: 18px;
  width: 3px;
  border-radius: 0 var(--r-full) var(--r-full) 0;
  background: var(--tone-gradient);
}

.stat-glow {
  position: absolute;
  right: -36px;
  top: -36px;
  width: 130px;
  height: 130px;
  border-radius: 50%;
  background: radial-gradient(circle, var(--tone-soft), transparent 70%);
  pointer-events: none;
  opacity: 0.6;
  transition: opacity 0.25s;
}

.stat:hover .stat-glow {
  opacity: 1;
}

.stat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 13px;
  color: var(--t-2);
  font-weight: 500;
}

.stat-icon {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: var(--r-sm);
  background: var(--tone-soft);
  color: var(--tone-color);
}

.stat-value {
  font-size: 32px;
  font-weight: 800;
  line-height: 1.15;
  color: var(--t-1);
  letter-spacing: -0.02em;
}

.value-gradient {
  background: var(--tone-gradient);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.stat-value.is-empty {
  color: var(--t-3);
}

.stat-unit {
  font-size: 14px;
  font-style: normal;
  font-weight: 500;
  color: var(--t-3);
  margin-left: 4px;
}

.stat-hint {
  margin-top: 6px;
  font-size: 12px;
  color: var(--t-3);
}

/* 主题色 */
.tone-accent {
  --tone-color: var(--c-accent);
  --tone-soft: var(--c-accent-soft);
  --tone-line: var(--c-accent-line);
  --tone-gradient: linear-gradient(135deg, var(--c-accent), #4dd690);
}

.tone-gold {
  --tone-color: var(--c-gold);
  --tone-soft: var(--c-gold-soft);
  --tone-line: rgba(217, 154, 32, 0.3);
  --tone-gradient: linear-gradient(135deg, var(--c-gold), #f0c040);
}

.tone-info {
  --tone-color: var(--c-info);
  --tone-soft: var(--c-info-soft);
  --tone-line: rgba(37, 137, 232, 0.3);
  --tone-gradient: linear-gradient(135deg, var(--c-info), #6db8ff);
}

.tone-danger {
  --tone-color: var(--c-danger);
  --tone-soft: var(--c-danger-soft);
  --tone-line: rgba(229, 62, 77, 0.3);
  --tone-gradient: linear-gradient(135deg, var(--c-danger), #ff7a8a);
}

.tone-purple {
  --tone-color: var(--c-purple);
  --tone-soft: rgba(124, 58, 237, 0.10);
  --tone-line: rgba(124, 58, 237, 0.3);
  --tone-gradient: linear-gradient(135deg, var(--c-purple), #a78bfa);
}
</style>
