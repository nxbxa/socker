<script setup>
/**
 * KPI 统计卡片
 * ============
 * 深色数据大屏的核心视觉单元：左侧色条 + 图标 + 大号等宽数字 + 说明文字。
 * 数值为 null 时显示占位符而不是 0，避免"假数据"误导。
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
      {{ display }}<em v-if="unit && !isEmpty" class="stat-unit">{{ unit }}</em>
    </div>
    <div v-if="hint" class="stat-hint">{{ hint }}</div>
  </div>
</template>

<style scoped>
.stat {
  position: relative;
  overflow: hidden;
  padding: 16px 18px;
  border-radius: var(--r-lg);
  background: var(--bg-panel);
  border: 1px solid var(--line);
  transition: border-color 0.2s, transform 0.2s;
}

.stat:hover {
  border-color: var(--line-strong);
  transform: translateY(-1px);
}

/* 左侧主题色条 */
.stat::before {
  content: '';
  position: absolute;
  left: 0;
  top: 14px;
  bottom: 14px;
  width: 3px;
  border-radius: 0 var(--r-full) var(--r-full) 0;
  background: var(--tone-color);
}

.stat-glow {
  position: absolute;
  right: -30px;
  top: -30px;
  width: 110px;
  height: 110px;
  border-radius: 50%;
  background: var(--tone-soft);
  filter: blur(6px);
  pointer-events: none;
}

.stat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.stat-label {
  font-size: 12.5px;
  color: var(--t-2);
  font-weight: 500;
}

.stat-icon {
  color: var(--tone-color);
  opacity: 0.75;
}

.stat-value {
  font-size: 30px;
  font-weight: 700;
  line-height: 1.15;
  color: var(--tone-color);
}

.stat-value.is-empty {
  color: var(--t-3);
}

.stat-unit {
  font-size: 13px;
  font-style: normal;
  font-weight: 500;
  color: var(--t-2);
  margin-left: 4px;
}

.stat-hint {
  margin-top: 4px;
  font-size: 11.5px;
  color: var(--t-3);
}

/* 主题色 */
.tone-accent {
  --tone-color: var(--c-accent);
  --tone-soft: var(--c-accent-soft);
}

.tone-gold {
  --tone-color: var(--c-gold);
  --tone-soft: var(--c-gold-soft);
}

.tone-info {
  --tone-color: var(--c-info);
  --tone-soft: var(--c-info-soft);
}

.tone-danger {
  --tone-color: var(--c-danger);
  --tone-soft: var(--c-danger-soft);
}

.tone-purple {
  --tone-color: var(--c-purple);
  --tone-soft: rgba(160, 107, 255, 0.12);
}
</style>
