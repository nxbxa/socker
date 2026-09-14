import { createRouter, createWebHistory } from 'vue-router'

/**
 * 路由表
 * ======
 * 所有视图均为懒加载（除应用壳），配合 Vite 自动分包。
 * meta.title 由下方 afterEach 守卫写入 document.title。
 */

const APP_NAME = '球员表现智能分析平台'

const routes = [
  { path: '/', redirect: '/dashboard' },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/DashboardView.vue'),
    meta: { title: '数据仪表盘' },
  },
  {
    path: '/players',
    name: 'Players',
    component: () => import('../views/PlayersView.vue'),
    meta: { title: '球员列表' },
  },
  {
    path: '/players/:name',
    name: 'PlayerDetail',
    component: () => import('../views/PlayerDetailView.vue'),
    meta: { title: '球员详情' },
  },
  {
    path: '/compare',
    name: 'Compare',
    component: () => import('../views/CompareView.vue'),
    meta: { title: '球员对比' },
  },
  {
    path: '/rankings',
    name: 'Rankings',
    component: () => import('../views/RankingsView.vue'),
    meta: { title: '评分排行榜' },
  },
  {
    path: '/clusters',
    name: 'Clusters',
    component: () => import('../views/ClustersView.vue'),
    meta: { title: '聚类分型' },
  },
  {
    path: '/similar',
    name: 'Similar',
    component: () => import('../views/SimilarView.vue'),
    meta: { title: '相似球员探索' },
  },
  {
    path: '/predict',
    name: 'Predict',
    component: () => import('../views/PredictView.vue'),
    meta: { title: '评分预测' },
  },
  // 兜底 404：必须放在最后
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('../views/NotFoundView.vue'),
    meta: { title: '页面不存在' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  // 切换路由时回到顶部，否则从长表格进详情页会停在中间
  scrollBehavior: () => ({ top: 0 }),
})

// 同步浏览器标签页标题
router.afterEach((to) => {
  const title = to.meta?.title
  document.title = title ? `${title} · ${APP_NAME}` : APP_NAME
})

export default router
