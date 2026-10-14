<script setup>
/**
 * 相似球员探索
 * ============
 * 数据来源：
 *   GET /api/players?search=xxx  远程联想选球员
 *   GET /api/similar?player=xxx&n=10&position=FW  相似球员完整数据
 *
 * 说明：初版前端完全没有使用 /api/similar（详情页用的是详情接口内嵌的
 * similar_players 简版字段）。本页启用该接口，把相似关系做成"中心 + 环绕"
 * 的散点图，并展示完整指标明细，便于做同类型球员的横纵向比较。
 */
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import request from '../api/request'
import BaseChart from '../components/BaseChart.vue'
import PageHeader from '../components/PageHeader.vue'
import ErrorState from '../components/ErrorState.vue'
import AppIcon from '../components/AppIcon.vue'
import { fmt, fmtScore, scoreColor, flagUrl } from '../utils/format'
import { CHART_COLORS, CHART_PALETTE } from '../theme/echarts'

const route = useRoute()
const router = useRouter()

const player = ref('')
const position = ref('')
const topN = ref(10)

const options = ref([])
const searching = ref(false)

const loading = ref(false)
const error = ref('')
const data = ref(null)

const positions = [
  { value: '', label: '全部位置' },
  { value: 'FW', label: '前锋' },
  { value: 'MF', label: '中场' },
  { value: 'DF', label: '后卫' },
  { value: 'GK', label: '门将' },
]

/** 远程联想 */
async function search(query) {
  if (!query) {
    options.value = []
    return
  }
  searching.value = true
  try {
    const res = await request.get('/players', {
      params: { search: query, page_size: 10, order: 'Min', direction: 'desc' },
    })
    options.value = (res?.items || []).map((p) => ({
      value: p.Player,
      label: `${p.Player}（${p.Pos || '—'} · ${p.Squads || '未知'}）`,
    }))
  } catch {
    options.value = []
  } finally {
    searching.value = false
  }
}

async function load() {
  if (!player.value) {
    error.value = '请先选择一名球员'
    return
  }

  loading.value = true
  error.value = ''
  try {
    const params = { player: player.value, n: topN.value }
    if (position.value) params.position = position.value
    data.value = await request.get('/similar', { params })
    router.replace({ query: { player: player.value, ...(position.value ? { pos: position.value } : {}) } })
  } catch (e) {
    error.value = e.message
    data.value = null
  } finally {
    loading.value = false
  }
}

/* ---------------- 相似度散点图 ---------------- */

/** 后端可能用不同字段名承载相似球员列表，这里做兼容 */
const similarList = computed(() => {
  const d = data.value
  if (!d) return []
  return d.similar_players || d.players || d.items || []
})

/** 中心球员信息 */
const centerPlayer = computed(() => ({
  player: data.value?.player || player.value,
  position: data.value?.position,
  squads: data.value?.squads,
  score: data.value?.score,
}))

/**
 * 散点图：X = 相似度，Y = 综合评分
 * 右上角 = 又像又强，是最有参考价值的区域
 */
const scatterOption = computed(() => {
  const list = similarList.value
  if (!list.length) return {}

  // 只用有效相似度（后端相似度是 0–1 小数）
  const points = list.map((p) => ({
    value: [Number(p.similarity ?? 0) * 100, Number(p.score ?? 0), p.player],
    player: p.player,
    squads: p.squads,
    position: p.position,
  }))

  const valid = points.map((p) => p.value[0])
  const minX = Math.max(0, Math.min(...valid) - 4)
  const maxX = Math.min(100, Math.max(...valid) + 2)

  return {
    tooltip: {
      trigger: 'item',
      formatter: (p) => {
        const it = p.data || {}
        return [
          `<b>${it.player || '—'}</b>`,
          `相似度：<b>${fmt(it.value?.[0], 1)}%</b>`,
          `综合评分：<b>${fmt(it.value?.[1], 2)}</b>`,
          `俱乐部：${it.squads || '—'}`,
        ].join('<br/>')
      },
    },
    grid: { top: 20, left: 8, right: 24, bottom: 30, containLabel: true },
    xAxis: {
      type: 'value',
      name: '相似度 (%)',
      min: minX,
      max: maxX,
      nameGap: 24,
    },
    yAxis: { type: 'value', name: '综合评分', scale: true, nameGap: 12 },
    series: [
      {
        type: 'scatter',
        symbolSize: (val) => {
          // 相似度越高点越大
          const sim = Number(val?.[0]) || 0
          return Math.max(10, Math.min(30, 8 + sim / 4))
        },
        itemStyle: {
          color: (p) => {
            // 评分越高颜色越绿
            const score = p.data?.value?.[1]
            return scoreColor(score)
          },
          opacity: 0.85,
        },
        label: {
          show: true,
          position: 'right',
          formatter: (p) => p.data?.player || '',
          color: '#5a6a82',
          fontSize: 10.5,
        },
        data: points,
      },
    ],
  }
})

/** 相似度条颜色（越高越绿） */
function simColor(sim) {
  const v = Number(sim) * 100
  if (v >= 90) return CHART_COLORS.accent
  if (v >= 80) return CHART_COLORS.info
  if (v >= 70) return CHART_COLORS.gold
  return CHART_COLORS.danger
}

function goPlayer(name) {
  if (name) router.push(`/players/${encodeURIComponent(name)}`)
}

onMounted(() => {
  const q = route.query.player
  const pos = route.query.pos
  if (q) {
    player.value = String(q)
    if (pos) position.value = String(pos)
    load()
  }
})
</script>

<template>
  <div>
    <PageHeader
      title="相似球员探索"
      desc="基于比赛风格向量（Z-Score 标准化 + 余弦相似度）找出风格最接近的球员"
    />

    <!-- ============ 查询条件 ============ -->
    <el-card>
      <div class="query-bar">
        <el-select
          v-model="player"
          filterable
          remote
          clearable
          reserve-keyword
          placeholder="搜索球员姓名"
          :remote-method="search"
          :loading="searching"
          class="player-select"
        >
          <template #prefix><AppIcon name="search" :size="14" /></template>
          <el-option
            v-for="item in options"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>

        <el-select v-model="position" style="width: 132px">
          <el-option
            v-for="p in positions"
            :key="p.value"
            :label="p.label"
            :value="p.value"
          />
        </el-select>

        <el-select v-model="topN" style="width: 122px">
          <el-option :value="5" label="TOP 5" />
          <el-option :value="10" label="TOP 10" />
          <el-option :value="20" label="TOP 20" />
        </el-select>

        <el-button type="primary" :loading="loading" @click="load">
          <AppIcon name="network" :size="15" style="margin-right: 5px" />
          查找相似球员
        </el-button>
      </div>

      <p class="query-note">
        不限定位置时，会在全体合格球员中跨位置检索风格相似的球员。
      </p>
    </el-card>

    <ErrorState v-if="error" class="block" :message="error" :retryable="!!player" @retry="load" />

    <template v-else-if="data && similarList.length">
      <!-- ============ 中心球员 ============ -->
      <div class="center-card block">
        <div class="center-badge">目标球员</div>
        <div class="center-main">
          <h2 class="center-name">{{ centerPlayer.player }}</h2>
          <div class="center-meta">
            <span v-if="centerPlayer.position" class="pos-chip">{{ centerPlayer.position }}</span>
            <span v-if="centerPlayer.squads">{{ centerPlayer.squads }}</span>
          </div>
        </div>
        <div v-if="centerPlayer.score !== undefined && centerPlayer.score !== null" class="center-score">
          <span class="cs-value num" :style="{ color: scoreColor(centerPlayer.score) }">
            {{ fmtScore(centerPlayer.score) }}
          </span>
          <span class="cs-label">综合评分</span>
        </div>
      </div>

      <!-- ============ 相似度 / 评分分布 ============ -->
      <el-card class="block">
        <template #header>
          <span>相似度与实力分布</span>
          <span class="card-sub">点越靠右上，风格越像且实力越强</span>
        </template>
        <BaseChart :option="scatterOption" height="380px" :loading="loading" />
      </el-card>

      <!-- ============ 相似球员明细 ============ -->
      <el-card class="block">
        <template #header>
          <span>相似球员明细（TOP {{ similarList.length }}）</span>
        </template>

        <el-table
          v-loading="loading"
          :data="similarList"
          stripe
          class="clickable-rows"
          @row-click="(row) => goPlayer(row.player)"
        >
          <el-table-column label="#" type="index" width="60" align="center" />

          <el-table-column label="球员" min-width="170" fixed>
            <template #default="{ row }">
              <span class="player-cell">
                <img
                  v-if="row.nation_flag && row.nation_flag.startsWith('http')"
                  :src="row.nation_flag"
                  class="flag"
                  :alt="row.nation"
                  loading="lazy"
                  @error="(e) => (e.target.style.display = 'none')"
                />
                <img
                  v-else-if="row.nation"
                  :src="flagUrl(row.nation)"
                  class="flag"
                  :alt="row.nation"
                  loading="lazy"
                  @error="(e) => (e.target.style.display = 'none')"
                />
                <span class="player-link">{{ row.player }}</span>
              </span>
            </template>
          </el-table-column>

          <el-table-column label="位置" width="82" align="center">
            <template #default="{ row }">
              <span class="pos-chip sm">{{ row.position || '—' }}</span>
            </template>
          </el-table-column>

          <el-table-column prop="squads" label="俱乐部" min-width="150" show-overflow-tooltip />

          <el-table-column label="综合评分" width="108" align="center">
            <template #default="{ row }">
              <span class="num" :style="{ color: scoreColor(row.score), fontWeight: 700 }">
                {{ fmtScore(row.score) }}
              </span>
            </template>
          </el-table-column>

          <el-table-column label="相似度" min-width="190">
            <template #default="{ row }">
              <div class="sim-cell">
                <el-progress
                  :percentage="Math.round((row.similarity || 0) * 100)"
                  :stroke-width="8"
                  :show-text="false"
                  :color="simColor(row.similarity)"
                />
                <span class="sim-text num" :style="{ color: simColor(row.similarity) }">
                  {{ fmt((row.similarity || 0) * 100, 1) }}%
                </span>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <el-empty
      v-else-if="data && !similarList.length"
      class="block"
      description="未找到相似球员（可能出场时间不足或风格独特性过强）"
      :image-size="100"
    />

    <el-empty
      v-else-if="!error"
      class="block"
      description="搜索并选择一名球员，开始探索风格相似的同类型球员"
      :image-size="100"
    />
  </div>
</template>

<style scoped>
.query-bar {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.player-select {
  width: 300px;
  flex: 0 1 300px;
}

.query-note {
  margin-top: 10px;
  font-size: 12px;
  color: var(--t-3);
}

.card-sub {
  font-size: 12px;
  font-weight: 400;
  color: var(--t-3);
}

/* ============ 中心球员卡 ============ */
.center-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--sp-4);
  padding: 20px 24px;
  border-radius: var(--r-lg);
  background:
    linear-gradient(135deg, rgba(0, 224, 122, 0.08), transparent 60%),
    var(--bg-panel);
  border: 1px solid var(--c-accent-line);
}

.center-badge {
  position: absolute;
  top: -9px;
  left: 22px;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.06em;
  padding: 2px 9px;
  border-radius: var(--r-full);
  color: #04160d;
  background: var(--c-accent);
}

.center-main {
  flex: 1;
  min-width: 0;
}

.center-name {
  font-size: 22px;
  font-weight: 700;
}

.center-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
  font-size: 13px;
  color: var(--t-2);
}

.center-score {
  text-align: right;
  flex-shrink: 0;
}

.cs-value {
  display: block;
  font-size: 34px;
  font-weight: 700;
  line-height: 1;
}

.cs-label {
  font-size: 11.5px;
  color: var(--t-3);
}

/* ============ 表格 ============ */
.player-cell {
  display: flex;
  align-items: center;
  font-size: 13.5px;
}

.pos-chip {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: var(--r-sm);
  color: var(--c-accent);
  background: var(--c-accent-soft);
  border: 1px solid var(--c-accent-line);
}

.pos-chip.sm {
  font-size: 10.5px;
  padding: 1px 6px;
  color: var(--t-2);
  background: var(--bg-panel-2);
  border-color: var(--line-strong);
}

.sim-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sim-cell :deep(.el-progress) {
  flex: 1;
}

.sim-text {
  width: 46px;
  text-align: right;
  font-size: 12.5px;
  font-weight: 600;
}

@media (max-width: 768px) {
  .player-select {
    width: 100%;
    flex: 1 1 100%;
  }
}
</style>
