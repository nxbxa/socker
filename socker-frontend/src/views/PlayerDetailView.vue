<script setup>
/**
 * 球员详情
 * ========
 * 数据来源：
 *   GET /api/players/<name>  基础信息 + 指标明细 + 各位置评分 + 聚类 + 相似球员
 *   GET /api/compare         六维雷达（单人 = 自己与自己对比，取一侧数据）
 *
 * ⚠️ 关键修复：路由 /players/:name 前后是同一个组件实例，Vue 会复用它。
 * 因此 playerName 必须是 computed，且用 watch 监听变化重新取数；
 * 否则从"球员 A"跳到"球员 B"时 URL 变了但页面数据不变。
 */
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import request from '../api/request'
import BaseChart from '../components/BaseChart.vue'
import ErrorState from '../components/ErrorState.vue'
import AppIcon from '../components/AppIcon.vue'
import {
  fmt,
  fmtScore,
  fmtInt,
  positionLabel,
  flagUrl,
  scoreColor,
} from '../utils/format'
import { CHART_COLORS } from '../theme/echarts'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref('')
const detail = ref(null)
const radarDims = ref([])

// ✅ computed：路由参数变化时自动重新计算
const playerName = computed(() => {
  const raw = route.params.name
  try {
    return decodeURIComponent(String(raw ?? ''))
  } catch {
    return String(raw ?? '')
  }
})

async function load() {
  const name = playerName.value
  if (!name) return

  loading.value = true
  error.value = ''
  detail.value = null
  radarDims.value = []

  try {
    // 并行：详情 + 雷达（对比接口同名调用 = 取单人六维数据）
    const [d, cmp] = await Promise.all([
      request.get(`/players/${encodeURIComponent(name)}`),
      request.get('/compare', {
        params: { player1: name, player2: name },
      }),
    ])
    detail.value = d
    radarDims.value = cmp?.dimensions || []
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

// ✅ 监听参数变化重新取数，并用 immediate 覆盖首次挂载
watch(playerName, load, { immediate: true })

/* ---------------- 派生数据 ---------------- */

const basic = computed(() => detail.value?.basic || null)

/** 最佳位置的中文名 */
const bestPositionLabel = computed(() =>
  positionLabel(detail.value?.best_position)
)

/** 六维雷达数据 */
const radarOption = computed(() => {
  const dims = radarDims.value
  if (!dims.length) return {}

  const values = dims.map((d) => {
    const v = d.player1_score
    return v === null || v === undefined ? 0 : Number(v)
  })

  return {
    title: {
      text: '六维能力雷达',
      subtext: '各指标在同群体中的百分位均值（0–100）',
      left: 'center',
      top: 4,
    },
    tooltip: {
      trigger: 'item',
      formatter: () => {
        const lines = dims.map(
          (d, i) => `${d.name}：<b>${fmt(values[i], 1)}</b>`
        )
        return `<b>${playerName.value}</b><br/>${lines.join('<br/>')}`
      },
    },
    radar: {
      indicator: dims.map((d) => ({ name: d.name, max: 100 })),
      radius: '62%',
      center: ['50%', '56%'],
      splitNumber: 4,
      axisName: { color: '#5a6a82', fontSize: 12 },
    },
    series: [
      {
        type: 'radar',
        symbolSize: 5,
        data: [
          {
            name: playerName.value,
            value: values,
            areaStyle: { opacity: 0.28, color: CHART_COLORS.accent },
            lineStyle: { color: CHART_COLORS.accent, width: 2 },
            itemStyle: { color: CHART_COLORS.accent },
          },
        ],
      },
    ],
  }
})

/** 位置评分排序（按评分降序，最佳位置置顶） */
const sortedScores = computed(() => {
  const list = detail.value?.scores || []
  return [...list].sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
})

/** 每个维度的得分（用于明细区着色） */
function dimScore(dim) {
  const v = dim?.player1_score
  return v === null || v === undefined ? null : Number(v)
}

/** 指标明细：把 player1_metrics 对象转成数组 */
function metricList(dim) {
  const metrics = dim?.player1_metrics || {}
  return Object.entries(metrics).map(([key, m]) => ({
    key,
    label: m?.label || key,
    value: m?.value,
    percentile: m?.percentile,
  }))
}

function goPlayer(name) {
  if (name) router.push(`/players/${encodeURIComponent(name)}`)
}
</script>

<template>
  <div v-loading="loading">
    <ErrorState v-if="error" :message="error" @retry="load" />

    <template v-else-if="detail">
      <!-- ============ 返回 + 球员信息头 ============ -->
      <el-button text class="back-btn" @click="router.push('/players')">
        <AppIcon name="back" :size="15" style="margin-right: 4px" />返回球员列表
      </el-button>

      <div class="hero block">
        <div class="hero-avatar" :style="{ '--ring': scoreColor(detail.scores?.[0]?.score) }">
          <span class="hero-initial">{{ (basic?.player || '?').charAt(0) }}</span>
        </div>

        <div class="hero-main">
          <div class="hero-name-row">
            <h1 class="hero-name">{{ basic?.player }}</h1>
            <span class="pos-chip">{{ basic?.position || '—' }}</span>
            <span v-if="detail.best_position" class="best-chip">
              <AppIcon name="crosshair" :size="13" />
              最佳位置 {{ bestPositionLabel }}
            </span>
          </div>

          <div class="hero-meta">
            <span v-if="basic?.nation" class="meta-item">
              <img
                v-if="basic.nation_flag"
                :src="flagUrl(basic.nation_flag)"
                class="flag"
                :alt="basic.nation"
                @error="(e) => (e.target.style.display = 'none')"
              />
              {{ basic.nation }}
            </span>
            <span v-if="basic?.age !== null && basic?.age !== undefined" class="meta-item">
              {{ fmt(basic.age, 0) }} 岁
            </span>
            <span v-if="basic?.born" class="meta-item">生于 {{ fmt(basic.born, 0) }}</span>
            <span v-if="basic?.squads" class="meta-item squad">{{ basic.squads }}</span>
          </div>

          <div class="hero-tags">
            <el-tag v-if="detail.cluster" effect="dark" class="cluster-tag">
              {{ detail.cluster.cluster_name }}
            </el-tag>
            <el-tag
              v-if="detail.cluster"
              type="info"
              effect="plain"
              size="small"
            >
              聚类 #{{ detail.cluster.cluster }}
            </el-tag>
          </div>
        </div>

        <!-- 最佳位置评分大数字 -->
        <div v-if="sortedScores.length" class="hero-score">
          <div class="hero-score-value num" :style="{ color: scoreColor(sortedScores[0].score) }">
            {{ fmtScore(sortedScores[0].score) }}
          </div>
          <div class="hero-score-label">{{ sortedScores[0].position_label }}综合评分</div>
          <div class="hero-score-rank">
            第 {{ sortedScores[0].rank }} / {{ sortedScores[0].total }} 名
          </div>
        </div>
      </div>

      <!-- ============ 雷达 + 各位置评分 ============ -->
      <el-row :gutter="16" class="block">
        <el-col :xs="24" :lg="10">
          <el-card class="chart-card">
            <BaseChart :option="radarOption" height="360px" />
          </el-card>
        </el-col>

        <el-col :xs="24" :lg="14">
          <el-card class="chart-card">
            <template #header>
              <span>各位置评分与排名</span>
              <span class="card-sub">排名统计范围为合格球员</span>
            </template>

            <div v-if="!sortedScores.length" class="empty-hint">
              该球员出场时间不足，暂无位置评分
            </div>

            <div v-for="s in sortedScores" :key="s.position" class="score-row">
              <div class="score-label">
                <span class="pos-chip sm">{{ s.position }}</span>
                <span>{{ s.position_label }}</span>
              </div>
              <div class="score-track">
                <div
                  class="score-fill"
                  :style="{
                    width: `${Math.max(0, Math.min(100, Number(s.score) || 0))}%`,
                    background: `linear-gradient(90deg, ${scoreColor(s.score)}88, ${scoreColor(s.score)})`,
                  }"
                />
              </div>
              <div class="score-value num" :style="{ color: scoreColor(s.score) }">
                {{ fmtScore(s.score) }}
              </div>
              <div class="score-rank num">
                {{ s.rank }} <em>/ {{ s.total }}</em>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- ============ 相似球员 ============ -->
      <el-card class="block">
        <template #header>
          <span>相似球员推荐</span>
          <span class="card-sub">基于比赛风格向量（Z-Score + 余弦相似度）</span>
        </template>

        <el-table
          v-if="detail.similar_players?.length"
          :data="detail.similar_players"
          stripe
          class="clickable-rows"
          @row-click="(row) => goPlayer(row.player)"
        >
          <el-table-column label="球员" min-width="150">
            <template #default="{ row }">
              <span class="player-link">{{ row.player }}</span>
            </template>
          </el-table-column>
          <el-table-column label="位置" width="80" align="center">
            <template #default="{ row }">
              <span class="pos-chip sm">{{ row.position || '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="squads" label="俱乐部" min-width="150" show-overflow-tooltip />
          <el-table-column label="综合评分" width="106" align="center">
            <template #default="{ row }">
              <span class="num" :style="{ color: scoreColor(row.score) }">
                {{ fmtScore(row.score) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="相似度" width="190">
            <template #default="{ row }">
              <div class="sim-cell">
                <el-progress
                  :percentage="Math.round((row.similarity || 0) * 100)"
                  :stroke-width="8"
                  :show-text="false"
                  :color="CHART_COLORS.accent"
                />
                <span class="sim-text num">{{ fmt((row.similarity || 0) * 100, 1) }}%</span>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-else description="暂无相似球员数据（可能出场时间不足）" :image-size="70" />
      </el-card>

      <!-- ============ 六维明细 ============ -->
      <el-card v-if="radarDims.length" class="block">
        <template #header>
          <span>六维能力明细</span>
          <span class="card-sub">各项指标在同群体中的百分位</span>
        </template>

        <div class="dim-grid">
          <div v-for="dim in radarDims" :key="dim.name" class="dim-card">
            <div class="dim-head">
              <span class="dim-name">{{ dim.name }}</span>
              <span
                class="dim-score num"
                :style="{ color: scoreColor(dimScore(dim)) }"
              >
                {{ fmt(dimScore(dim), 1) }}
              </span>
            </div>
            <div
              v-for="m in metricList(dim)"
              :key="m.key"
              class="dim-row"
            >
              <span class="dim-row-label">{{ m.label }}</span>
              <span class="dim-row-val num">{{ fmt(m.value, 2) }}</span>
              <span class="dim-row-pct num">{{ fmt(m.percentile, 0) }}</span>
            </div>
          </div>
        </div>
      </el-card>

      <!-- ============ 比赛数据明细 ============ -->
      <el-card v-if="detail.metric_groups?.length" class="block">
        <template #header>
          <span>比赛数据明细</span>
          <span class="card-sub">按指标类别分组</span>
        </template>

        <el-tabs>
          <el-tab-pane
            v-for="g in detail.metric_groups"
            :key="g.group"
            :label="g.group"
          >
            <el-table :data="g.metrics" size="small" stripe max-height="420">
              <el-table-column prop="label" label="指标" min-width="170" />
              <el-table-column prop="name" label="原始字段" min-width="130">
                <template #default="{ row }">
                  <code class="code-chip">{{ row.name }}</code>
                </template>
              </el-table-column>
              <el-table-column label="数值" width="150" align="right">
                <template #default="{ row }">
                  <span class="num" :class="{ 'is-na': row.value === null }">
                    {{ row.value === null ? '—' : fmt(row.value, 2) }}
                  </span>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </template>

    <!-- 加载完成但无数据且无错误（理论上不会出现） -->
    <el-empty
      v-else-if="!loading"
      description="未找到该球员"
      :image-size="90"
    >
      <el-button type="primary" @click="router.push('/players')">返回列表</el-button>
    </el-empty>
  </div>
</template>

<style scoped>
.back-btn {
  margin-bottom: var(--sp-3);
  color: var(--t-2);
}

.back-btn:hover {
  color: var(--c-accent);
}

/* ============ 球员信息头 ============ */
.hero {
  display: flex;
  align-items: center;
  gap: var(--sp-5);
  padding: 22px 24px;
  border-radius: var(--r-lg);
  background:
    linear-gradient(135deg, rgba(0, 224, 122, 0.07), transparent 55%),
    var(--bg-panel);
  border: 1px solid var(--line);
}

.hero-avatar {
  width: 76px;
  height: 76px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: var(--r-full);
  background: var(--bg-panel-2);
  border: 2px solid var(--ring, var(--c-accent));
  box-shadow: 0 0 22px -4px var(--ring, var(--c-accent));
}

.hero-initial {
  font-size: 30px;
  font-weight: 700;
  font-family: var(--font-num);
  color: var(--ring, var(--c-accent));
  text-transform: uppercase;
}

.hero-main {
  flex: 1;
  min-width: 0;
}

.hero-name-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.hero-name {
  font-size: 25px;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.pos-chip {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 9px;
  border-radius: var(--r-sm);
  color: var(--t-2);
  background: var(--bg-panel-2);
  border: 1px solid var(--line-strong);
}

.pos-chip.sm {
  font-size: 10.5px;
  padding: 1px 6px;
}

.best-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: var(--r-sm);
  color: var(--c-accent);
  background: var(--c-accent-soft);
  border: 1px solid var(--c-accent-line);
}

.hero-meta {
  display: flex;
  align-items: center;
  gap: var(--sp-4);
  flex-wrap: wrap;
  margin-top: 10px;
  font-size: 13px;
  color: var(--t-2);
}

.meta-item {
  display: inline-flex;
  align-items: center;
}

.meta-item.squad {
  color: var(--t-1);
}

.hero-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.cluster-tag {
  background: var(--c-purple);
  border-color: var(--c-purple);
  color: #fff;
}

.hero-score {
  text-align: center;
  padding-left: var(--sp-5);
  border-left: 1px solid var(--line);
  flex-shrink: 0;
}

.hero-score-value {
  font-size: 42px;
  font-weight: 700;
  line-height: 1;
}

.hero-score-label {
  margin-top: 6px;
  font-size: 12.5px;
  color: var(--t-2);
}

.hero-score-rank {
  margin-top: 3px;
  font-size: 11.5px;
  color: var(--t-3);
}

/* ============ 位置评分 ============ */
.score-row {
  display: grid;
  grid-template-columns: 132px 1fr 64px 88px;
  align-items: center;
  gap: var(--sp-3);
  padding: 9px 0;
  border-bottom: 1px dashed var(--line);
}

.score-row:last-child {
  border-bottom: none;
}

.score-label {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  color: var(--t-2);
}

.score-track {
  height: 10px;
  border-radius: var(--r-full);
  background: var(--bg-hover);
  overflow: hidden;
}

.score-fill {
  height: 100%;
  border-radius: var(--r-full);
  transition: width 0.5s cubic-bezier(0.22, 1, 0.36, 1);
}

.score-value {
  text-align: right;
  font-size: 15px;
  font-weight: 700;
}

.score-rank {
  text-align: right;
  font-size: 12.5px;
  color: var(--t-2);
}

.score-rank em {
  font-style: normal;
  color: var(--t-3);
}

.empty-hint {
  padding: 24px;
  text-align: center;
  color: var(--t-3);
  font-size: 13px;
}

/* ============ 相似球员 ============ */
.sim-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sim-cell :deep(.el-progress) {
  flex: 1;
}

.sim-text {
  font-size: 12.5px;
  color: var(--c-accent);
  width: 46px;
  text-align: right;
}

/* ============ 六维明细 ============ */
.dim-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--sp-4);
}

.dim-card {
  padding: 14px 16px;
  border-radius: var(--r-md);
  background: var(--bg-panel-2);
  border: 1px solid var(--line);
}

.dim-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 9px;
  margin-bottom: 6px;
  border-bottom: 1px solid var(--line);
}

.dim-name {
  font-size: 13.5px;
  font-weight: 600;
}

.dim-score {
  font-size: 17px;
  font-weight: 700;
}

.dim-row {
  display: grid;
  grid-template-columns: 1fr auto 42px;
  align-items: center;
  gap: 10px;
  padding: 4px 0;
  font-size: 12.5px;
}

.dim-row-label {
  color: var(--t-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dim-row-val {
  color: var(--t-1);
}

.dim-row-pct {
  text-align: right;
  color: var(--t-3);
  font-size: 11.5px;
}

/* ============ 明细表 ============ */
.code-chip {
  font-family: var(--font-num);
  font-size: 11.5px;
  padding: 1px 6px;
  border-radius: 4px;
  color: var(--t-2);
  background: var(--bg-panel-2);
  border: 1px solid var(--line);
}

.is-na {
  color: var(--t-3);
}

.card-sub {
  font-size: 12px;
  font-weight: 400;
  color: var(--t-3);
}

.chart-card {
  height: 100%;
}

/* ============ 响应式 ============ */
@media (max-width: 1100px) {
  .dim-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .hero {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--sp-4);
  }

  .hero-score {
    padding-left: 0;
    padding-top: var(--sp-4);
    border-left: none;
    border-top: 1px solid var(--line);
    width: 100%;
  }

  .score-row {
    grid-template-columns: 100px 1fr 58px;
  }

  .score-rank {
    display: none;
  }

  .dim-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
