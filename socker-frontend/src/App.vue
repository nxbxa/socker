<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from './components/AppIcon.vue'
import request from './api/request'
import { fmtInt } from './utils/format'

const route = useRoute()

/**
 * 侧边导航
 * ========
 * 按分析层次分组，避免 8 个平铺条目难以扫读。
 */
const menuGroups = [
  {
    label: '总览',
    items: [{ path: '/dashboard', title: '数据仪表盘', icon: 'dashboard' }],
  },
  {
    label: '球员分析',
    items: [
      { path: '/players', title: '球员列表', icon: 'list' },
      { path: '/compare', title: '球员对比', icon: 'compare' },
      { path: '/rankings', title: '评分排行榜', icon: 'trophy' },
    ],
  },
  {
    label: '模型与分型',
    items: [
      { path: '/clusters', title: '聚类分型', icon: 'clusters' },
      { path: '/similar', title: '相似球员探索', icon: 'network' },
      { path: '/predict', title: '评分预测', icon: 'target' },
    ],
  },
]

// 详情页（/players/:name）需要让「球员列表」保持高亮
const activePath = computed(() => {
  if (route.path.startsWith('/players/')) return '/players'
  return route.path
})

// 当前页面标题（写入顶栏面包屑）
const currentTitle = computed(() => route.meta?.title || '')

const collapsed = ref(false)

/** 移动端抽屉式导航 */
const mobileOpen = ref(false)

function toggleSidebar() {
  if (window.innerWidth <= 900) {
    mobileOpen.value = !mobileOpen.value
  } else {
    collapsed.value = !collapsed.value
  }
}

function closeMobile() {
  mobileOpen.value = false
}

// 顶栏服务状态：反映 Flask 分析服务是否可用
const health = ref(null)
const healthError = ref(false)

onMounted(async () => {
  try {
    health.value = await request.get('/health')
  } catch {
    healthError.value = true
  }
})

const statusText = computed(() => {
  if (healthError.value) return '分析服务未连接'
  if (!health.value) return '连接中…'
  return `${fmtInt(health.value.players_total, '—')} 名球员`
})
</script>

<template>
  <div class="layout" :class="{ 'is-collapsed': collapsed }">
    <!-- ============ 侧边导航 ============ -->
    <aside class="sidebar" :class="{ 'is-open': mobileOpen }">
      <div class="brand" @click="closeMobile">
        <span class="brand-mark"><AppIcon name="ball" :size="22" /></span>
        <transition name="fade">
          <span v-if="!collapsed" class="brand-text">
            <strong>球员表现分析</strong>
            <em>Football Analytics</em>
          </span>
        </transition>
      </div>

      <nav class="nav">
        <div v-for="group in menuGroups" :key="group.label" class="nav-group">
          <div v-if="!collapsed" class="nav-group-label">{{ group.label }}</div>
          <router-link
            v-for="m in group.items"
            :key="m.path"
            :to="m.path"
            class="nav-item"
            :class="{ 'is-active': activePath === m.path }"
            :title="collapsed ? m.title : ''"
            @click="closeMobile"
          >
            <AppIcon :name="m.icon" :size="17" />
            <span v-if="!collapsed" class="nav-item-text">{{ m.title }}</span>
          </router-link>
        </div>
      </nav>

      <!-- 侧栏底部：分析服务状态 -->
      <div class="sidebar-foot">
        <div class="status" :class="{ 'is-down': healthError }">
          <span class="dot" />
          <span v-if="!collapsed" class="status-text">{{ statusText }}</span>
        </div>
      </div>
    </aside>

    <!-- 移动端遮罩 -->
    <div v-if="mobileOpen" class="scrim" @click="closeMobile" />

    <!-- ============ 主区域 ============ -->
    <div class="body">
      <header class="topbar">
        <button class="icon-btn" type="button" :title="collapsed ? '展开菜单' : '收起菜单'" @click="toggleSidebar">
          <AppIcon name="menu" :size="18" />
        </button>

        <div class="crumb">
          <span class="crumb-root">总览</span>
          <span class="crumb-sep">/</span>
          <span class="crumb-cur">{{ currentTitle }}</span>
        </div>

        <div class="topbar-right">
          <span class="chip" :class="{ 'is-down': healthError }">
            <span class="dot" />
            {{ healthError ? '分析服务离线' : '分析服务在线' }}
          </span>
        </div>
      </header>

      <main class="main">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  position: relative;
  z-index: 1;
}

/* ============ 侧边栏 ============ */
.sidebar {
  width: var(--aside-w);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-panel);
  border-right: 1px solid var(--line);
  transition: width 0.22s ease;
  box-shadow: 1px 0 4px rgba(0, 0, 0, 0.02);
}

.is-collapsed .sidebar {
  width: var(--aside-w-collapsed);
}

.brand {
  height: var(--header-h);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  border-bottom: 1px solid var(--line);
  overflow: hidden;
  cursor: pointer;
}

.brand-mark {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: var(--r-md);
  color: #ffffff;
  background: linear-gradient(135deg, var(--c-accent), var(--c-accent-deep));
  box-shadow: 0 4px 12px rgba(0, 184, 98, 0.25);
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
  white-space: nowrap;
}

.brand-text strong {
  font-size: 14px;
  font-weight: 700;
  color: var(--t-1);
}

.brand-text em {
  font-size: 10px;
  font-style: normal;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--t-3);
}

.nav {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px 10px;
}

.nav-group + .nav-group {
  margin-top: 16px;
}

.nav-group-label {
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--t-3);
  padding: 0 10px 6px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 38px;
  padding: 0 10px;
  margin-bottom: 2px;
  border-radius: var(--r-md);
  color: var(--t-2);
  font-size: 13.5px;
  font-weight: 500;
  white-space: nowrap;
  transition: all 0.16s;
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--t-1);
}

.nav-item.is-active {
  background: var(--c-accent-soft);
  color: var(--c-accent);
  font-weight: 600;
}

.is-collapsed .nav-item {
  justify-content: center;
  padding: 0;
}

.sidebar-foot {
  padding: 12px;
  border-top: 1px solid var(--line);
}

.status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--t-2);
  padding: 0 4px;
  white-space: nowrap;
}

.is-collapsed .status {
  justify-content: center;
}

.dot {
  width: 7px;
  height: 7px;
  flex-shrink: 0;
  border-radius: var(--r-full);
  background: var(--c-accent);
  box-shadow: 0 0 0 3px var(--c-accent-soft);
}

.is-down .dot,
.status.is-down .dot {
  background: var(--c-danger);
  box-shadow: 0 0 0 3px var(--c-danger-soft);
}

/* ============ 主区域 ============ */
.body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.topbar {
  height: var(--header-h);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 20px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--line);
}

.icon-btn {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: var(--r-sm);
  color: var(--t-2);
  background: transparent;
  border: 1px solid var(--line);
  cursor: pointer;
  transition: all 0.16s;
}

.icon-btn:hover {
  color: var(--c-accent);
  border-color: var(--c-accent-line);
  background: var(--c-accent-soft);
}

.crumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13.5px;
  min-width: 0;
}

.crumb-root {
  color: var(--t-3);
}

.crumb-sep {
  color: var(--line-strong);
}

.crumb-cur {
  color: var(--t-1);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.topbar-right {
  margin-left: auto;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 28px;
  padding: 0 12px;
  border-radius: var(--r-full);
  font-size: 12px;
  font-weight: 500;
  color: var(--c-accent);
  background: var(--c-accent-soft);
  border: 1px solid var(--c-accent-line);
}

.chip.is-down {
  color: var(--c-danger);
  background: var(--c-danger-soft);
  border-color: rgba(229, 62, 77, 0.3);
}

.main {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

/* ============ 过渡动画 ============ */
.page-enter-active,
.page-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.page-leave-to {
  opacity: 0;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.16s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ============ 移动端 ============ */
.scrim {
  position: fixed;
  inset: 0;
  z-index: 40;
  background: rgba(4, 7, 12, 0.6);
  backdrop-filter: blur(2px);
}

@media (max-width: 900px) {
  .sidebar {
    position: fixed;
    top: 0;
    bottom: 0;
    left: 0;
    z-index: 50;
    width: var(--aside-w);
    transform: translateX(-100%);
    transition: transform 0.24s ease;
  }

  .sidebar.is-open {
    transform: translateX(0);
  }

  /* 移动端忽略折叠态，统一显示完整导航 */
  .is-collapsed .sidebar {
    width: var(--aside-w);
  }

  .is-collapsed .nav-item {
    justify-content: flex-start;
    padding: 0 10px;
  }

  .main {
    padding: 14px;
  }

  .crumb-root,
  .crumb-sep {
    display: none;
  }
}

@media (max-width: 640px) {
  .topbar {
    padding: 0 12px;
  }

  .chip {
    padding: 0 9px;
    font-size: 11px;
  }
}
</style>
