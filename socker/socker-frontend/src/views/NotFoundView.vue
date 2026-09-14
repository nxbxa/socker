<script setup>
/**
 * 404 页面
 * ========
 * 初版缺少兜底路由，访问错误地址会渲染空白页。
 */
import { useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'

const router = useRouter()
</script>

<template>
  <div class="nf">
    <div class="nf-code num">404</div>
    <div class="nf-ball"><AppIcon name="ball" :size="34" /></div>
    <h2 class="nf-title">这个页面不在场上</h2>
    <p class="nf-desc">
      你访问的地址不存在，可能是链接输入有误，或者页面已被移除。
    </p>
    <div class="nf-actions">
      <el-button type="primary" @click="router.push('/dashboard')">
        返回仪表盘
      </el-button>
      <el-button @click="router.back()">返回上一页</el-button>
    </div>
  </div>
</template>

<style scoped>
.nf {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 68vh;
  text-align: center;
  gap: 6px;
}

.nf-code {
  font-size: 108px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.05em;
  color: transparent;
  -webkit-text-stroke: 1.5px var(--line-strong);
  user-select: none;
}

.nf-ball {
  width: 64px;
  height: 64px;
  display: grid;
  place-items: center;
  margin: 4px 0 10px;
  border-radius: var(--r-full);
  color: var(--c-accent);
  background: var(--c-accent-soft);
  border: 1px solid var(--c-accent-line);
  box-shadow: var(--glow-accent);
}

.nf-title {
  font-size: 22px;
  font-weight: 700;
}

.nf-desc {
  max-width: 420px;
  font-size: 13px;
  color: var(--t-2);
  line-height: 1.8;
}

.nf-actions {
  display: flex;
  gap: var(--sp-3);
  margin-top: var(--sp-5);
}
</style>
