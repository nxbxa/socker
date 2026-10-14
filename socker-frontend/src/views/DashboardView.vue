<script setup>
/**
 * 数据仪表盘
 * ==========
 * 数据来源：GET /api/dashboard
 * 板块：KPI 总览 → 各位置 TOP5 → 位置分布 / 评分分布 → 模型性能与聚类概览
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '../api/request'
import BaseChart from '../components/BaseChart.vue'
import StatCard from '../components/StatCard.vue'
import PageHeader from '../components/PageHeader.vue'
import ErrorState from '../components/ErrorState.vue'
import AppIcon from '../components/AppIcon.vue'
import { fmt, fmtScore, fmtInt, flagUrl } from '../utils/format'
import { CHART_COLORS, CHART_PALETTE } from '../theme/echarts'

const router = useRouter()

const loading = ref(true)
const dash = ref(null)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    dash.value = await request.get('/dashboard')
  } catch (e) {
    error.value = e.message
    dash.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)

/* ---------------- KPI ---------------- */

// 合格率：合格球员 / 球员总数。任一为 0 时返回 null 而非 NaN
const qualifiedRate = computed(() => {
  const total = dash.value?.players_total
  const qualified = dash.value?.qualified_total
  if (!total) return null
  return (qualified / total) * 100
})

const avgQualified = computed(() => {
  const total = dash.value?.qualified_total
  const positions = dash.value?.position_distribution?.length
  if (!total || !positions) return null
  return total / positions
})

/* ---------------- 图表 ---------------- */

// 位置分布环形图
const pieOption = computed(() => {
  const dist = dash.value?.position_distribution
  if (!dist?.length) return {}

  return {
    title: {
      text: '合格球员位置分布',
      subtext: `出场时间 ≥ 门槛值 · 共 ${fmtInt(dash.value.qualified_total)} 人`,
      left: 'center',
      // 显式定位：不设 top 时 ECharts 取 'auto'，标题会贴到画布顶边被裁切
      top: 0,
      textStyle: { fontSize: 14 },
      subtextStyle: { fontSize: 11.5 },
    },
    tooltip: {
      trigger: 'item',
      formatter: (p) => `${p.marker} ${p.name}<br/>人数：<b>${p.value}</b>（${p.percent}%）`,
    },
    legend: {
      bottom: 0,
      icon: 'circle',
      itemWidth: 9,
      itemHeight: 9,
      itemGap: 16,
    },
    series: [
      {
        type: 'pie',
        // 半径略收窄并下移中心点：为顶部标题与底部图例同时留出安全间距
        radius: ['42%', '62%'],
        center: ['50%', '58%'],
        avoidLabelOverlap: true,
        label: {
          show: true,
          formatter: '{b}\n{c} 人',
          color: '#5a6a82',
          fontSize: 12,
          lineHeight: 16,
        },
        labelLine: { length: 10, length2: 12 },
        emphasis: {
          scaleSize: 6,
          label: { color: '#1a2332', fontWeight: 600 },
        },
        data: dist.map((p, i) => ({
          name: p.position_label,
          value: p.count,
          itemStyle: {
            color: [CHART_COLORS.accent, CHART_COLORS.info, CHART_COLORS.gold, CHART_COLORS.purple][i % 4],
          },
        })),
      },
    ],
  }
})

// 各位置评分分布（分箱直方图）
const barOption = computed(() => {
  const dist = dash.value?.score_distribution
  if (!dist?.length) return {}

  // 各位置分箱边界一致（同一评分尺度），取第一组生成标签
  const first = dist[0]
  const labels = (first.bins || []).slice(0, -1).map((v, i) => {
    const next = first.bins[i + 1]
    return `${fmt(v, 0)}–${fmt(next, 0)}`
  })

  return {
    title: {
      text: '各位置综合评分分布',
      subtext: '横轴为评分区间，纵轴为人数',
      left: 'center',
      top: 0,
      textStyle: { fontSize: 14 },
      subtextStyle: { fontSize: 11.5 },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      valueFormatter: (v) => `${v} 人`,
    },
    legend: { bottom: 0, icon: 'roundRect', itemWidth: 11, itemHeight: 8 },
    grid: { top: 64, left: 8, right: 12, bottom: 40, containLabel: true },
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: { fontSize: 11, interval: 0 },
    },
    yAxis: { type: 'value', name: '人数', nameGap: 14 },
    series: dist.map((p, i) => ({
      name: p.position_label,
      type: 'bar',
      barMaxWidth: 16,
      itemStyle: {
        borderRadius: [3, 3, 0, 0],
        color: CHART_PALETTE[i % CHART_PALETTE.length],
      },
      data: p.counts,
    })),
  }
})

// 模型 R² 对比（随机森林 vs 线性回归基准）
const modelOption = computed(() => {
  const metrics = dash.value?.model_metrics
  if (!metrics?.length) return {}

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      valueFormatter: (v) => fmt(v, 4),
    },
    legend: { bottom: 0, icon: 'roundRect', itemWidth: 11, itemHeight: 8 },
    grid: { top: 20, left: 8, right: 20, bottom: 40, containLabel: true },
    xAxis: { type: 'category', data: metrics.map((m) => m.position) },
    yAxis: { type: 'value', name: 'R²', max: 1, nameGap: 14 },
    series: [
      {
        name: '随机森林',
        type: 'bar',
        barMaxWidth: 22,
        itemStyle: { color: CHART_COLORS.accent, borderRadius: [4, 4, 0, 0] },
        label: { show: true, position: 'top', formatter: (p) => fmt(p.value, 3), fontSize: 11 },
        data: metrics.map((m) => m.forest_r2),
      },
      {
        name: '线性回归基准',
        type: 'bar',
        barMaxWidth: 22,
        itemStyle: { color: CHART_COLORS.info, borderRadius: [4, 4, 0, 0] },
        label: { show: true, position: 'top', formatter: (p) => fmt(p.value, 3), fontSize: 11 },
        data: metrics.map((m) => m.linear_r2),
      },
    ],
  }
})

/** 排名徽章样式类 */
function rankClass(i) {
  return i < 3 ? `is-${i + 1}` : ''
}

function goPlayer(name) {
  if (name) router.push(`/players/${encodeURIComponent(name)}`)
}
</script>

<template>
  <div>
    <PageHeader
      title="数据仪表盘"
      desc="赛季球员表现总览：数据规模、位置分布、评分分布与模型性能"
    >
      <el-button :loading="loading" @click="load">
        <AppIcon name="trendUp" :size="15" style="margin-right: 5px" />刷新数据
      </el-button>
    </PageHeader>

    <ErrorState v-if="error" :message="error" @retry="load" />

    <template v-else>
      <!-- ============ KPI ============ -->
      <div class="kpi-grid" v-loading="loading">
        <StatCard
          label="球员总数"
          :value="dash?.players_total"
          unit="人"
          icon="users"
          tone="accent"
          hint="本赛季有出场记录的球员"
        />
        <StatCard
          label="合格球员"
          :value="dash?.qualified_total"
          unit="人"
          icon="crosshair"
          tone="info"
          :hint="qualifiedRate !== null ? `占总数 ${fmt(qualifiedRate, 1)}%` : '出场时间达标'"
        />
        <StatCard
          label="转会球员"
          :value="dash?.transfer_players"
          unit="人"
          icon="transfer"
          tone="gold"
          hint="赛季中效力多支俱乐部"
        />
        <StatCard
          label="每位置平均合格人数"
          :value="avgQualified"
          :digits="1"
          unit="人"
          icon="layers"
          tone="purple"
          hint="各位置评分样本规模"
        />
      </div>

      <!-- ============ 各位置 TOP5 ============ -->
      <el-card class="block" v-loading="loading">
        <template #header>
          <span>各位置评分 TOP5</span>
          <span class="card-sub">点击球员姓名查看完整档案</span>
        </template>
        <div class="top5-grid">
          <div
            v-for="pos in dash?.top5_by_position || []"
            :key="pos.position"
            class="top5-col"
          >
            <div class="top5-head">
              <span class="pos-chip">{{ pos.position }}</span>
              <span class="pos-name">{{ pos.position_label }}</span>
            </div>
            <div
              v-for="(p, i) in pos.players"
              :key="p.player"
              class="top-item"
              @click="goPlayer(p.player)"
            >
              <span class="rank-badge" :class="rankClass(i)">{{ i + 1 }}</span>
              <img
                v-if="p.nation_flag"
                :src="flagUrl(p.nation_flag)"
                class="flag"
                :alt="p.nation"
                loading="lazy"
                @error="(e) => (e.target.style.display = 'none')"
              />
              <span class="top-name">{{ p.player }}</span>
              <span class="top-score num">{{ fmtScore(p.score) }}</span>
            </div>
          </div>
        </div>
      </el-card>

      <!-- ============ 位置分布 + 评分分布 ============ -->
      <el-row :gutter="16" class="block">
        <el-col :xs="24" :lg="10">
          <el-card class="chart-card">
            <BaseChart :option="pieOption" height="360px" :loading="loading" />
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="14">
          <el-card class="chart-card">
            <BaseChart :option="barOption" height="360px" :loading="loading" />
          </el-card>
        </el-col>
      </el-row>

      <!-- ============ 模型性能 + 聚类概览 ============ -->
      <el-row :gutter="16" class="block">
        <el-col :xs="24" :lg="10">
          <el-card class="chart-card">
            <template #header>
              <span>评分预测模型性能</span>
              <span class="card-sub">测试集 R²（越高越好）</span>
            </template>
            <BaseChart :option="modelOption" height="280px" :loading="loading" />
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="14">
          <el-card v-loading="loading">
            <template #header>
              <span>聚类分型概览</span>
              <span class="card-sub">K-Means 最优 K 与轮廓系数</span>
            </template>
            <el-table :data="dash?.cluster_overview || []" size="small">
              <el-table-column prop="position" label="位置" width="70" align="center" />
              <el-table-column prop="position_label" label="名称" width="80" />
              <el-table-column label="最佳 K" width="80" align="center">
                <template #default="{ row }">
                  <span class="num accent">{{ row.k }}</span>
                </template>
              </el-table-column>
              <el-table-column label="轮廓系数" width="110" align="center">
                <template #default="{ row }">
                  <span class="num" :style="{ color: row.silhouette >= 0.25 ? '#00b862' : '#d99a20' }">
                    {{ fmt(row.silhouette, 3) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="球员类型构成">
                <template #default="{ row }">
                  <div class="cluster-tags">
                    <el-tag
                      v-for="(c, ci) in row.clusters"
                      :key="c.name"
                      size="small"
                      effect="plain"
                      :style="{
                        borderColor: CHART_PALETTE[ci % CHART_PALETTE.length],
                        color: CHART_PALETTE[ci % CHART_PALETTE.length],
                      }"
                    >
                      {{ c.name }} · {{ c.size }}人
                    </el-tag>
                  </div>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<style scoped>
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--sp-4);
}

.card-sub {
  font-size: 12px;
  font-weight: 400;
  color: var(--t-3);
}

/* ---- 各位置 TOP5 ---- */
.top5-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--sp-4);
}

.top5-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 10px;
  margin-bottom: 6px;
  border-bottom: 1px solid var(--line);
}

.pos-chip {
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 2px 7px;
  border-radius: var(--r-sm);
  color: var(--c-accent);
  background: var(--c-accent-soft);
  border: 1px solid var(--c-accent-line);
}

.pos-name {
  font-size: 13.5px;
  font-weight: 600;
}

.top-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 6px;
  border-radius: var(--r-sm);
  cursor: pointer;
  transition: background 0.16s;
}

.top-item:hover {
  background: var(--bg-hover);
}

.top-name {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.top-score {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--c-accent);
}

/* ---- 图表卡片 ---- */
.chart-card {
  height: 100%;
}

.cluster-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.accent {
  color: var(--c-accent);
  font-weight: 700;
}

/* ---- 响应式 ---- */
@media (max-width: 1200px) {
  .kpi-grid,
  .top5-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .kpi-grid,
  .top5-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
