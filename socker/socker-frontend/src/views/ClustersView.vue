<script setup>
/**
 * 聚类分型
 * ========
 * 数据来源：GET /api/clusters?position=FW
 * 结构：位置切换 → 聚类质量 KPI → PCA 散点图 + K 值选择曲线 → 簇画像 → 成员明细
 *
 * 说明：散点图点的面积映射综合评分，颜色映射所属簇；
 * tooltip 直接使用 ECharts 回调提供的原始数据，避免按下标反查导致错位。
 */
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '../api/request'
import BaseChart from '../components/BaseChart.vue'
import StatCard from '../components/StatCard.vue'
import PageHeader from '../components/PageHeader.vue'
import ErrorState from '../components/ErrorState.vue'
import { fmt, fmtScore, fmtInt, scoreColor } from '../utils/format'
import { CHART_PALETTE } from '../theme/echarts'

const router = useRouter()

const loading = ref(false)
const error = ref('')
const position = ref('FW')
const data = ref(null)
const clusterFilter = ref('')

const positions = [
  { value: 'FW', label: '前锋' },
  { value: 'MF', label: '中场' },
  { value: 'DF', label: '后卫' },
  { value: 'GK', label: '门将' },
]

/** 簇配色：与图表色板保持一致 */
const colorOf = (cluster) =>
  CHART_PALETTE[Number(cluster) % CHART_PALETTE.length] || CHART_PALETTE[0]

/* ---------------- PCA 散点图 ---------------- */

const scatterOption = computed(() => {
  const d = data.value
  if (!d?.points?.length) return {}

  const ev = d.explained_variance || [0, 0]

  // 每个簇一个 series，便于图例单独开关
  const series = (d.profiles || []).map((p) => {
    const points = d.points.filter((pt) => pt.cluster === p.cluster)
    return {
      name: `${p.name}（${p.size}人）`,
      type: 'scatter',
      // data 项形如 { value: [pc1, pc2, score], player, squads }
      data: points.map((pt) => ({
        value: [pt.pc1, pt.pc2, pt.score ?? 0],
        player: pt.player,
        squads: pt.squads,
        minutes: pt.minutes,
        clusterName: pt.cluster_name,
      })),
      symbolSize: (val) => {
        const score = Number(val?.[2]) || 0
        return Math.max(7, Math.min(22, 6 + score / 7))
      },
      itemStyle: { color: colorOf(p.cluster), opacity: 0.82 },
      emphasis: { itemStyle: { opacity: 1, borderColor: '#fff', borderWidth: 1 } },
    }
  })

  return {
    title: {
      text: `${d.position_label}球员风格分布（PCA 降维）`,
      left: 'center',
      // 显式定位：不设 top 时 ECharts 取 'auto'，标题会贴到画布顶边被裁切
      top: 0,
      textStyle: { fontSize: 14 },
    },
    tooltip: {
      trigger: 'item',
      formatter: (p) => {
        const it = p.data || {}
        return [
          `<b>${it.player || p.name || '—'}</b>`,
          `类型：${it.clusterName || '—'}`,
          `俱乐部：${it.squads || '—'}`,
          `综合评分：<b>${fmt(it.value?.[2], 2)}</b>`,
          `出场时间：${fmtInt(it.minutes)} 分钟`,
        ].join('<br/>')
      },
    },
    legend: { bottom: 0, type: 'scroll', icon: 'circle', itemWidth: 9, itemHeight: 9 },
    grid: { top: 70, left: 8, right: 20, bottom: 52, containLabel: true },
    xAxis: {
      type: 'value',
      name: `PC1 (${fmt((ev[0] || 0) * 100, 1)}%)`,
      nameLocation: 'middle',
      nameGap: 28,
      scale: true,
    },
    yAxis: {
      type: 'value',
      name: `PC2 (${fmt((ev[1] || 0) * 100, 1)}%)`,
      nameGap: 16,
      scale: true,
    },
    series,
  }
})

/* ---------------- K 值选择曲线（肘部法） ---------------- */

const kSelectionOption = computed(() => {
  const records = data.value?.k_selection
  if (!records?.length) return {}

  // 兼容后端可能使用的字段名
  const getK = (r) => r.k ?? r.n_clusters ?? r.clusters
  const getScore = (r) =>
    r.silhouette ?? r.score ?? r.inertia ?? r.sse ?? null

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params?.[0]
        if (!p) return ''
        return `K = <b>${p.axisValue}</b><br/>指标值：<b>${fmt(p.value, 4)}</b>`
      },
    },
    grid: { top: 16, left: 8, right: 20, bottom: 8, containLabel: true },
    xAxis: {
      type: 'category',
      data: records.map((r) => getK(r)),
      name: 'K',
      nameGap: 6,
    },
    yAxis: { type: 'value', scale: true },
    series: [
      {
        type: 'line',
        symbolSize: 8,
        data: records.map((r) => getScore(r)),
        itemStyle: { color: CHART_PALETTE[2] },
        lineStyle: { color: CHART_PALETTE[2], width: 2 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(242,183,61,0.22)' },
              { offset: 1, color: 'rgba(242,183,61,0)' },
            ],
          },
        },
        // 标出选中的 K
        markLine: data.value
          ? {
              silent: true,
              symbol: 'none',
              lineStyle: { color: CHART_PALETTE[0], type: 'dashed' },
              label: { formatter: `最优 K=${data.value.k}`, color: CHART_PALETTE[0] },
              data: [{ xAxis: String(data.value.k) }],
            }
          : undefined,
      },
    ],
  }
})

/* ---------------- 成员明细表 ---------------- */

const tableData = computed(() => {
  const points = data.value?.points || []
  const rows = [...points].sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
  return clusterFilter.value === '' || clusterFilter.value === null
    ? rows
    : rows.filter((r) => r.cluster === clusterFilter.value)
})

async function fetchData() {
  loading.value = true
  error.value = ''
  clusterFilter.value = ''
  try {
    data.value = await request.get('/clusters', {
      params: { position: position.value },
    })
  } catch (e) {
    error.value = e.message
    data.value = null
  } finally {
    loading.value = false
  }
}

watch(position, fetchData)
onMounted(fetchData)

function goPlayer(name) {
  if (name) router.push(`/players/${encodeURIComponent(name)}`)
}

/** 轮廓系数优劣的评价文案 */
function silhouetteHint(v) {
  const n = Number(v)
  if (Number.isNaN(n)) return '—'
  if (n >= 0.4) return '分型结构清晰'
  if (n >= 0.25) return '分型结构合理'
  if (n >= 0.15) return '分型结构偏弱'
  return '分型结构不明显'
}
</script>

<template>
  <div>
    <PageHeader
      title="聚类分型"
      desc="K-Means + PCA 无监督分型：把同位置球员按比赛风格自动划分为若干类型"
    >
      <el-tag v-if="data" effect="plain" size="small">
        最优聚类数 K = {{ data.k }}
      </el-tag>
    </PageHeader>

    <el-card class="filter-card">
      <el-radio-group v-model="position">
        <el-radio-button v-for="p in positions" :key="p.value" :value="p.value">
          {{ p.label }}
        </el-radio-button>
      </el-radio-group>
    </el-card>

    <ErrorState v-if="error" class="block" :message="error" @retry="fetchData" />

    <template v-else-if="data">
      <!-- ============ 质量指标 ============ -->
      <div class="kpi-grid block">
        <StatCard
          label="最佳聚类数 K"
          :value="data.k"
          icon="clusters"
          tone="accent"
          hint="由轮廓系数自动选择"
        />
        <StatCard
          label="轮廓系数"
          :value="data.silhouette"
          :digits="3"
          icon="zap"
          tone="gold"
          :hint="silhouetteHint(data.silhouette)"
        />
        <StatCard
          label="主成分解释方差"
          :value="(data.explained_variance || []).reduce((s, v) => s + (v || 0), 0) * 100"
          :digits="1"
          unit="%"
          icon="layers"
          tone="info"
          hint="前两个主成分合计"
        />
        <StatCard
          label="参与分型球员"
          :value="data.points?.length"
          unit="人"
          icon="users"
          tone="purple"
          :hint="`${data.position_label} · 合格球员`"
        />
      </div>

      <!-- ============ PCA 散点 ============ -->
      <el-card class="block">
        <template #header>
          <span>{{ data.position_label }}球员风格分布（PCA 降维）</span>
          <span class="card-sub">点面积代表综合评分，颜色代表所属类型</span>
        </template>
        <BaseChart :option="scatterOption" height="460px" :loading="loading" />
      </el-card>

      <!-- ============ K 值选择 + 簇画像 ============ -->
      <el-row :gutter="16" class="block">
        <el-col :xs="24" :lg="8">
          <el-card class="chart-card">
            <template #header>
              <span>K 值选择</span>
              <span class="card-sub">轮廓系数随 K 变化</span>
            </template>
            <BaseChart :option="kSelectionOption" height="260px" :loading="loading" />
          </el-card>
        </el-col>

        <el-col :xs="24" :lg="16">
          <el-card class="chart-card">
            <template #header>
              <span>球员类型画像</span>
              <span class="card-sub">σ 为簇内均值相对全体的标准差偏移</span>
            </template>

            <div class="profile-grid" :style="{ '--cols': Math.min((data.profiles || []).length, 3) }">
              <div
                v-for="p in data.profiles"
                :key="p.cluster"
                class="profile-card"
                :style="{ '--cc': colorOf(p.cluster) }"
              >
                <div class="profile-head">
                  <span class="cluster-dot" />
                  <span class="profile-name">{{ p.name }}</span>
                  <span class="profile-count num">{{ p.size }} 人</span>
                </div>

                <div class="profile-score">
                  <span class="ps-label">平均评分</span>
                  <span class="ps-value num" :style="{ color: scoreColor(p.avg_score) }">
                    {{ fmt(p.avg_score, 2) }}
                  </span>
                </div>

                <div class="metric-list">
                  <div
                    v-for="m in p.top_metrics"
                    :key="m.metric"
                    class="metric-item"
                  >
                    <span class="mi-label">{{ m.label }}</span>
                    <span
                      class="mi-value num"
                      :class="Number(m.z_diff) > 0 ? 'is-high' : 'is-low'"
                    >
                      {{ Number(m.z_diff) > 0 ? '+' : '' }}{{ fmt(m.z_diff, 2) }}σ
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- ============ 成员明细 ============ -->
      <el-card class="block">
        <template #header>
          <span>{{ data.position_label }}球员分型明细</span>
          <el-select
            v-model="clusterFilter"
            placeholder="全部类型"
            clearable
            style="width: 210px"
          >
            <el-option
              v-for="p in data.profiles"
              :key="p.cluster"
              :value="p.cluster"
              :label="`${p.name}（${p.size} 人）`"
            />
          </el-select>
        </template>

        <el-table
          v-loading="loading"
          :data="tableData"
          stripe
          class="clickable-rows"
          max-height="520"
          @row-click="(row) => goPlayer(row.player)"
        >
          <el-table-column label="球员" min-width="170" fixed>
            <template #default="{ row }">
              <span class="player-link">{{ row.player }}</span>
            </template>
          </el-table-column>

          <el-table-column prop="squads" label="俱乐部" min-width="150" show-overflow-tooltip />

          <el-table-column label="出场时间" width="104" align="right">
            <template #default="{ row }">
              <span class="num">{{ fmtInt(row.minutes) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="综合评分" width="110" align="right">
            <template #default="{ row }">
              <span class="num" :style="{ color: scoreColor(row.score), fontWeight: 700 }">
                {{ fmtScore(row.score) }}
              </span>
            </template>
          </el-table-column>

          <el-table-column label="所属类型" min-width="170">
            <template #default="{ row }">
              <span class="type-chip" :style="{ '--cc': colorOf(row.cluster) }">
                <span class="cluster-dot" />
                {{ row.cluster_name }}
              </span>
            </template>
          </el-table-column>

          <template #empty>
            <el-empty description="没有符合条件的球员" :image-size="70" />
          </template>
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.filter-card :deep(.el-card__body) {
  padding: 14px 18px;
}

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

.chart-card {
  height: 100%;
}

/* ============ 簇画像 ============ */
.profile-grid {
  display: grid;
  grid-template-columns: repeat(var(--cols, 3), minmax(0, 1fr));
  gap: var(--sp-3);
}

.profile-card {
  padding: 14px 15px;
  border-radius: var(--r-md);
  background: var(--bg-panel-2);
  border: 1px solid var(--line);
  border-top: 2px solid var(--cc);
}

.profile-head {
  display: flex;
  align-items: center;
  gap: 7px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--line);
}

.cluster-dot {
  width: 9px;
  height: 9px;
  flex-shrink: 0;
  border-radius: var(--r-full);
  background: var(--cc, var(--c-accent));
}

.profile-name {
  flex: 1;
  font-size: 13.5px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-count {
  font-size: 11.5px;
  color: var(--t-3);
}

.profile-score {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin: 10px 0 8px;
}

.ps-label {
  font-size: 12px;
  color: var(--t-2);
}

.ps-value {
  font-size: 20px;
  font-weight: 700;
}

.metric-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12.5px;
}

.mi-label {
  color: var(--t-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mi-value {
  font-weight: 600;
  flex-shrink: 0;
}

.mi-value.is-high {
  color: var(--c-accent);
}

.mi-value.is-low {
  color: var(--c-danger);
}

/* ============ 表格 ============ */
.type-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: var(--r-full);
  color: var(--cc);
  background: color-mix(in srgb, var(--cc) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--cc) 34%, transparent);
}

/* ============ 响应式 ============ */
@media (max-width: 1200px) {
  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .profile-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  }
}

@media (max-width: 640px) {
  .kpi-grid,
  .profile-grid {
    grid-template-columns: minmax(0, 1fr) !important;
  }
}
</style>
