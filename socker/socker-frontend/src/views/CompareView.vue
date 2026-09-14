<script setup>
/**
 * 球员对比
 * ========
 * 数据来源：
 *   GET /api/players?search=xxx  远程联想候选球员
 *   GET /api/compare             双人六维雷达 + 维度胜负统计
 *
 * 增强点：
 * - 对比双方写入 URL query（?a=xxx&b=yyy），刷新/分享后结果不丢失
 * - 切换任一球员即清空旧结果，避免出现"标题是新人、图表是旧数据"的错位
 * - 一键交换 A/B
 */
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import request from '../api/request'
import BaseChart from '../components/BaseChart.vue'
import PageHeader from '../components/PageHeader.vue'
import AppIcon from '../components/AppIcon.vue'
import { fmt, fmtScore, positionLabel, scoreColor } from '../utils/format'
import { CHART_COLORS } from '../theme/echarts'

const route = useRoute()
const router = useRouter()

const player1 = ref('')
const player2 = ref('')
const options1 = ref([])
const options2 = ref([])
const searching = ref(false)

const comparing = ref(false)
const result = ref(null)
const error = ref('')

/** 远程联想：输入片段 -> 调 /players 搜索候选 */
function makeSearch(optionsRef) {
  return async (query) => {
    if (!query) {
      optionsRef.value = []
      return
    }
    searching.value = true
    try {
      const data = await request.get('/players', {
        params: { search: query, page_size: 10, order: 'Min', direction: 'desc' },
      })
      optionsRef.value = (data?.items || []).map((p) => ({
        value: p.Player,
        label: `${p.Player}（${p.Pos || '—'} · ${p.Squads || '未知'}）`,
      }))
    } catch {
      // 联想失败不打扰用户（网络抖动时静默降级为手动输入）
      optionsRef.value = []
    } finally {
      searching.value = false
    }
  }
}

const search1 = makeSearch(options1)
const search2 = makeSearch(options2)

async function doCompare() {
  if (!player1.value || !player2.value) {
    error.value = '请选择两名球员'
    return
  }
  if (player1.value === player2.value) {
    error.value = '请选择两名不同的球员'
    return
  }

  error.value = ''
  comparing.value = true
  try {
    result.value = await request.get('/compare', {
      params: { player1: player1.value, player2: player2.value },
    })
    // 结果写入 URL，支持刷新与分享
    router.replace({
      query: { a: player1.value, b: player2.value },
    })
  } catch (e) {
    error.value = e.message
    result.value = null
  } finally {
    comparing.value = false
  }
}

function swapPlayers() {
  const tmp = player1.value
  player1.value = player2.value
  player2.value = tmp
  const tmpOpts = options1.value
  options1.value = options2.value
  options2.value = tmpOpts
  if (player1.value && player2.value) doCompare()
}

function reset() {
  player1.value = ''
  player2.value = ''
  result.value = null
  error.value = ''
  options1.value = []
  options2.value = []
  router.replace({ query: {} })
}

// 任一球员被改动 -> 旧结果立即失效
watch([player1, player2], () => {
  if (result.value) result.value = null
  error.value = ''
})

/* ---------------- 雷达图 ---------------- */

const radarOption = computed(() => {
  const dims = result.value?.dimensions
  if (!dims?.length) return {}

  const nameA = result.value.player1?.player || 'A'
  const nameB = result.value.player2?.player || 'B'

  const toValues = (key) =>
    dims.map((d) => {
      const v = d[key]
      return v === null || v === undefined ? 0 : Number(v)
    })

  return {
    tooltip: { trigger: 'item' },
    legend: {
      bottom: 0,
      icon: 'roundRect',
      itemWidth: 12,
      itemHeight: 8,
      data: [nameA, nameB],
    },
    radar: {
      indicator: dims.map((d) => ({ name: d.name, max: 100 })),
      radius: '62%',
      center: ['50%', '52%'],
      splitNumber: 4,
      axisName: { color: '#9aa7bd', fontSize: 12 },
    },
    series: [
      {
        type: 'radar',
        symbolSize: 5,
        data: [
          {
            name: nameA,
            value: toValues('player1_score'),
            areaStyle: { opacity: 0.22, color: CHART_COLORS.info },
            lineStyle: { color: CHART_COLORS.info, width: 2 },
            itemStyle: { color: CHART_COLORS.info },
          },
          {
            name: nameB,
            value: toValues('player2_score'),
            areaStyle: { opacity: 0.22, color: CHART_COLORS.danger },
            lineStyle: { color: CHART_COLORS.danger, width: 2 },
            itemStyle: { color: CHART_COLORS.danger },
          },
        ],
      },
    ],
  }
})

/** 维度明细表数据：补一个利于排序的 winner 字段 */
const dimensionRows = computed(() => {
  const dims = result.value?.dimensions || []
  return dims.map((d) => ({
    ...d,
    winner:
      d.diff === null || d.diff === undefined
        ? 'tie'
        : d.diff > 0
          ? 'a'
          : d.diff < 0
            ? 'b'
            : 'tie',
  }))
})

/** 总体优势：按维度胜出数判断 */
const overallWinner = computed(() => {
  const s = result.value?.summary
  if (!s) return null
  if (s.player1_wins > s.player2_wins) return 'a'
  if (s.player2_wins > s.player1_wins) return 'b'
  return 'tie'
})

/** 是否是门将对比（维度模型不同） */
const isGk = computed(() => !!result.value?.is_goalkeeper_comparison)

function goPlayer(name) {
  if (name) router.push(`/players/${encodeURIComponent(name)}`)
}

/* ---------------- 初始化：从 URL 还原对比 ---------------- */

onMounted(() => {
  const a = route.query.a
  const b = route.query.b
  if (a && b) {
    player1.value = String(a)
    player2.value = String(b)
    doCompare()
  }
})
</script>

<template>
  <div>
    <PageHeader
      title="球员对比"
      desc="任选两名球员，按六维能力模型逐维度对比（百分位基准为同群体合格球员）"
    >
      <el-tag v-if="isGk" type="warning" effect="plain" size="small">
        门将专用维度模型
      </el-tag>
    </PageHeader>

    <!-- ============ 选择区 ============ -->
    <el-card>
      <div class="picker">
        <div class="picker-side">
          <span class="picker-tag tag-a">A</span>
          <el-select
            v-model="player1"
            filterable
            remote
            clearable
            reserve-keyword
            placeholder="搜索并选择球员 A"
            :remote-method="search1"
            :loading="searching"
            class="picker-select"
          >
            <el-option
              v-for="item in options1"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </div>

        <div class="picker-center">
          <button class="swap-btn" type="button" title="交换双方" @click="swapPlayers">
            <AppIcon name="compare" :size="17" />
          </button>
          <span class="vs-label">VS</span>
        </div>

        <div class="picker-side">
          <span class="picker-tag tag-b">B</span>
          <el-select
            v-model="player2"
            filterable
            remote
            clearable
            reserve-keyword
            placeholder="搜索并选择球员 B"
            :remote-method="search2"
            :loading="searching"
            class="picker-select"
          >
            <el-option
              v-for="item in options2"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </div>

        <div class="picker-actions">
          <el-button type="primary" :loading="comparing" @click="doCompare">
            开始对比
          </el-button>
          <el-button v-if="result || error" text @click="reset">清空</el-button>
        </div>
      </div>

      <el-alert
        v-if="error"
        :title="error"
        type="warning"
        show-icon
        :closable="false"
        class="err"
      />
    </el-card>

    <!-- ============ 对比结果 ============ -->
    <template v-if="result">
      <!-- 双方信息卡 + 胜负统计 -->
      <el-row :gutter="16" class="block">
        <el-col :xs="24" :md="10">
          <div
            class="p-card side-a"
            :class="{ 'is-winner': overallWinner === 'a' }"
            @click="goPlayer(result.player1.player)"
          >
            <div v-if="overallWinner === 'a'" class="winner-badge">综合占优</div>
            <div class="p-card-top">
              <span class="p-avatar">A</span>
              <div>
                <h3 class="p-name">{{ result.player1.player }}</h3>
                <p class="p-sub">
                  {{ result.player1.position }} ·
                  {{ positionLabel(result.player1.position) }}
                </p>
              </div>
            </div>
            <div class="p-stats">
              <div class="p-stat">
                <span class="p-stat-v num">{{ fmt(result.player1.age, 0) }}</span>
                <span class="p-stat-l">年龄</span>
              </div>
              <div class="p-stat">
                <span class="p-stat-v num">{{ fmt(result.player1.minutes, 0) }}</span>
                <span class="p-stat-l">出场时间</span>
              </div>
              <div class="p-stat">
                <span class="p-stat-v num">{{ fmt(result.player1.goals, 0) }}</span>
                <span class="p-stat-l">进球</span>
              </div>
              <div class="p-stat">
                <span class="p-stat-v num">{{ fmt(result.player1.assists, 0) }}</span>
                <span class="p-stat-l">助攻</span>
              </div>
            </div>
            <p class="p-club">{{ result.player1.squads || '俱乐部未知' }}</p>
          </div>
        </el-col>

        <el-col :xs="24" :md="4">
          <div class="win-box">
            <div class="win-num num" :class="{ 'is-win': overallWinner === 'a' }">
              {{ result.summary.player1_wins }}
            </div>
            <div class="win-mid">
              <span class="win-label">维度胜出</span>
              <span class="win-total num">
                共 {{ result.summary.total_dimensions }} 维
              </span>
            </div>
            <div class="win-num num" :class="{ 'is-win': overallWinner === 'b' }">
              {{ result.summary.player2_wins }}
            </div>
          </div>
        </el-col>

        <el-col :xs="24" :md="10">
          <div
            class="p-card side-b"
            :class="{ 'is-winner': overallWinner === 'b' }"
            @click="goPlayer(result.player2.player)"
          >
            <div v-if="overallWinner === 'b'" class="winner-badge">综合占优</div>
            <div class="p-card-top">
              <span class="p-avatar">B</span>
              <div>
                <h3 class="p-name">{{ result.player2.player }}</h3>
                <p class="p-sub">
                  {{ result.player2.position }} ·
                  {{ positionLabel(result.player2.position) }}
                </p>
              </div>
            </div>
            <div class="p-stats">
              <div class="p-stat">
                <span class="p-stat-v num">{{ fmt(result.player2.age, 0) }}</span>
                <span class="p-stat-l">年龄</span>
              </div>
              <div class="p-stat">
                <span class="p-stat-v num">{{ fmt(result.player2.minutes, 0) }}</span>
                <span class="p-stat-l">出场时间</span>
              </div>
              <div class="p-stat">
                <span class="p-stat-v num">{{ fmt(result.player2.goals, 0) }}</span>
                <span class="p-stat-l">进球</span>
              </div>
              <div class="p-stat">
                <span class="p-stat-v num">{{ fmt(result.player2.assists, 0) }}</span>
                <span class="p-stat-l">助攻</span>
              </div>
            </div>
            <p class="p-club">{{ result.player2.squads || '俱乐部未知' }}</p>
          </div>
        </el-col>
      </el-row>

      <!-- 雷达 + 维度明细 -->
      <el-row :gutter="16" class="block">
        <el-col :xs="24" :lg="12">
          <el-card class="chart-card">
            <BaseChart :option="radarOption" height="400px" />
          </el-card>
        </el-col>

        <el-col :xs="24" :lg="12">
          <el-card class="chart-card">
            <template #header>
              <span>六维得分对比</span>
              <span class="card-sub">差值 = A − B</span>
            </template>

            <el-table :data="dimensionRows" size="small">
              <el-table-column label="维度" width="86">
                <template #default="{ row }">
                  <span class="dim-name">{{ row.name }}</span>
                </template>
              </el-table-column>

              <el-table-column label="A" width="86" align="center">
                <template #default="{ row }">
                  <span
                    class="num cell-score"
                    :class="{ 'is-win': row.winner === 'a' }"
                  >
                    {{ fmt(row.player1_score, 1) }}
                  </span>
                </template>
              </el-table-column>

              <el-table-column label="B" width="86" align="center">
                <template #default="{ row }">
                  <span
                    class="num cell-score"
                    :class="{ 'is-win': row.winner === 'b' }"
                  >
                    {{ fmt(row.player2_score, 1) }}
                  </span>
                </template>
              </el-table-column>

              <el-table-column label="差值" align="center">
                <template #default="{ row }">
                  <span v-if="row.diff === null || row.diff === undefined" class="dim-na">—</span>
                  <span
                    v-else
                    class="num diff-tag"
                    :class="row.winner === 'a' ? 'to-a' : row.winner === 'b' ? 'to-b' : 'tie'"
                  >
                    {{ row.winner === 'a' ? 'A +' : row.winner === 'b' ? 'B +' : '' }}{{
                      fmt(Math.abs(row.diff), 1)
                    }}
                  </span>
                </template>
              </el-table-column>
            </el-table>

            <p class="table-note">
              得分口径：该维度内各指标在<strong>同群体合格球员</strong>中的百分位均值（0–100）。
            </p>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <el-empty
      v-else-if="!error"
      description="选择两名球员开始对比"
      :image-size="100"
    />
  </div>
</template>

<style scoped>
/* ============ 选择区 ============ */
.picker {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.picker-side {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 240px;
}

.picker-select {
  flex: 1;
}

.picker-tag {
  width: 26px;
  height: 26px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: var(--r-sm);
  font-size: 12px;
  font-weight: 700;
  font-family: var(--font-num);
}

.tag-a {
  color: var(--c-info);
  background: var(--c-info-soft);
  border: 1px solid rgba(58, 160, 255, 0.3);
}

.tag-b {
  color: var(--c-danger);
  background: var(--c-danger-soft);
  border: 1px solid rgba(255, 92, 108, 0.3);
}

.picker-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.swap-btn {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: var(--r-sm);
  color: var(--t-2);
  background: var(--bg-input);
  border: 1px solid var(--line-strong);
  cursor: pointer;
  transition: all 0.18s;
}

.swap-btn:hover {
  color: var(--c-accent);
  border-color: var(--c-accent-line);
  background: var(--c-accent-soft);
  transform: rotate(180deg);
}

.vs-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--t-3);
}

.picker-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.err {
  margin-top: var(--sp-4);
}

/* ============ 球员卡 ============ */
.p-card {
  position: relative;
  height: 100%;
  padding: 18px 20px;
  border-radius: var(--r-lg);
  background: var(--bg-panel);
  border: 1px solid var(--line);
  border-top: 3px solid var(--side-color);
  cursor: pointer;
  transition: border-color 0.2s, transform 0.2s;
}

.p-card:hover {
  transform: translateY(-2px);
  border-color: var(--side-color);
}

.p-card.is-winner {
  box-shadow: 0 0 0 1px var(--side-color), 0 0 24px -8px var(--side-color);
}

.side-a {
  --side-color: var(--c-info);
}

.side-b {
  --side-color: var(--c-danger);
}

.winner-badge {
  position: absolute;
  top: 14px;
  right: 16px;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.05em;
  padding: 3px 9px;
  border-radius: var(--r-full);
  color: #04160d;
  background: var(--c-accent);
}

.p-card-top {
  display: flex;
  align-items: center;
  gap: 12px;
}

.p-avatar {
  width: 42px;
  height: 42px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: var(--r-md);
  font-size: 17px;
  font-weight: 700;
  font-family: var(--font-num);
  color: var(--side-color);
  background: var(--bg-panel-2);
  border: 1px solid var(--side-color);
}

.p-name {
  font-size: 18px;
  font-weight: 700;
}

.p-sub {
  font-size: 12.5px;
  color: var(--t-2);
  margin-top: 2px;
}

.p-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px dashed var(--line);
}

.p-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.p-stat-v {
  font-size: 16px;
  font-weight: 700;
}

.p-stat-l {
  font-size: 11px;
  color: var(--t-3);
}

.p-club {
  margin-top: 12px;
  font-size: 12px;
  color: var(--t-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ============ 胜负统计 ============ */
.win-box {
  height: 100%;
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 18px 8px;
  border-radius: var(--r-lg);
  background: var(--bg-panel);
  border: 1px solid var(--line);
}

.win-num {
  font-size: 38px;
  font-weight: 700;
  color: var(--t-3);
  transition: color 0.2s;
}

.win-num.is-win {
  color: var(--c-accent);
  text-shadow: 0 0 20px rgba(0, 224, 122, 0.35);
}

.win-mid {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.win-label {
  font-size: 11.5px;
  color: var(--t-2);
}

.win-total {
  font-size: 10.5px;
  color: var(--t-3);
}

/* ============ 维度表 ============ */
.dim-name {
  font-weight: 600;
  font-size: 13px;
}

.cell-score {
  font-size: 13.5px;
  color: var(--t-2);
}

.cell-score.is-win {
  color: var(--c-accent);
  font-weight: 700;
}

.dim-na {
  color: var(--t-3);
}

.diff-tag {
  display: inline-block;
  min-width: 56px;
  padding: 2px 8px;
  border-radius: var(--r-sm);
  font-size: 12.5px;
  font-weight: 700;
  border: 1px solid;
}

.diff-tag.to-a {
  color: var(--c-info);
  background: var(--c-info-soft);
  border-color: rgba(58, 160, 255, 0.32);
}

.diff-tag.to-b {
  color: var(--c-danger);
  background: var(--c-danger-soft);
  border-color: rgba(255, 92, 108, 0.32);
}

.diff-tag.tie {
  color: var(--t-3);
  background: var(--bg-hover);
  border-color: var(--line-strong);
}

.table-note {
  margin-top: var(--sp-4);
  font-size: 12px;
  color: var(--t-3);
  line-height: 1.7;
}

.table-note strong {
  color: var(--t-2);
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
@media (max-width: 992px) {
  .picker-side {
    min-width: 100%;
  }

  .picker-center {
    flex-direction: row;
    width: 100%;
    justify-content: center;
  }
}

@media (max-width: 560px) {
  .p-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
