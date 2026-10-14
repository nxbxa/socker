<script setup>
/**
 * 页面标题区
 * ==========
 * 统一各视图的标题、说明文字与右侧操作区排版。
 */
defineProps({
  title: { type: String, required: true },
  desc: { type: String, default: '' },
})
</script>

<template>
  <div class="page-head">
    <div class="head-left">
      <h2 class="page-title">{{ title }}</h2>
      <p v-if="desc" class="page-desc">{{ desc }}</p>
    </div>
    <div class="head-right">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.head-left {
  min-width: 0;
}

.head-right {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  flex-wrap: wrap;
}
</style>
