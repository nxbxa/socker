<script setup>
/**
 * 错误状态占位
 * ============
 * 替换原先"请求失败只 console.error、页面一片空白"的行为。
 */
import AppIcon from './AppIcon.vue'

defineProps({
  title: { type: String, default: '数据加载失败' },
  message: { type: String, default: '' },
  /** 是否显示重试按钮 */
  retryable: { type: Boolean, default: true },
})

defineEmits(['retry'])
</script>

<template>
  <div class="err">
    <div class="err-icon"><AppIcon name="alert" :size="26" /></div>
    <h3 class="err-title">{{ title }}</h3>
    <p v-if="message" class="err-msg">{{ message }}</p>
    <p class="err-hint">
      请确认 Flask 分析服务（5000）与 Spring Boot 网关（8080）均已启动。
    </p>
    <el-button v-if="retryable" type="primary" plain @click="$emit('retry')">
      重新加载
    </el-button>
  </div>
</template>

<style scoped>
.err {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 48px 24px;
  text-align: center;
  border-radius: var(--r-lg);
  background: var(--bg-panel);
  border: 1px solid var(--line);
}

.err-icon {
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  border-radius: var(--r-full);
  color: var(--c-danger);
  background: var(--c-danger-soft);
  border: 1px solid rgba(255, 92, 108, 0.28);
}

.err-title {
  font-size: 16px;
  font-weight: 600;
}

.err-msg {
  color: var(--c-danger);
  font-size: 13px;
  max-width: 520px;
}

.err-hint {
  color: var(--t-3);
  font-size: 12.5px;
  max-width: 520px;
  margin-bottom: 6px;
}
</style>
