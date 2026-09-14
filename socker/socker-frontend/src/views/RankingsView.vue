<script setup>
/**
 * 评分排行榜
 * ==========
 * 数据来源：GET /api/rankings?position=FW&limit=20
 * 结构：位置切换 → TOP3 领奖台 → TOP10 横向条形图 → 完整榜单表格
 *
 * 注意：表格列禁用前端 sortable，排序由后端 score 降序保证。
 */
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '../api/request'
import BaseChart from '../components/BaseChart.vue'
import PageHeader from '../components/PageHeader.vue'
import ErrorState from '../components/ErrorState.vue'
import {
  fmt,
  fmtScore,
  fmtInt,
  scoreColor,
  flagUrl,
} from '../utils/format'
import { CHART_COLORS } from '../theme/echarts'

const router = useRouter()

const loading = ref(false)
const error = ref('')
const position = ref('FW')
const limit = ref(20)
const data = ref(null)

const positions = [
  { value: 'FW', label: '前锋' },
  { value: 'MF', label: '中场' },
  { value: 'DF', label: '后卫' },
  { value: 'GK', label: '门将' },
]

const items = computed(() => data.value?.items || [])

/** 领奖台：前 3 名（不足 3 人时自动截断） */
const podium = computed(() => items.value.slice(0, 3))

/** TOP10 横向条形图：从下往上绘制，视觉上第一名在顶部 */
const chartOption = computed(() => {
  const top = items.value.slice(0, 10)
  if (!top.length) return {}

  // ECharts 类目轴从下往上排，所以倒序后第一名才在顶部
  const reversed = [...top].reverse()

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const p = params?.[0]
        if (!p) return ''
        const row = reversed[p.dataIndex]
        if (!row) return ''
        return [
          `<b>${row.player}</b>`,
          `综合评分：<b>${fmtScore(row.score)}</b>`,
          `俱乐部：${row.squads || '—'}`,
          `出场时间：${fmtInt(row.minutes)} 分钟`,
        ].join('<br/>')
      },
    },
    grid: { top: 12, left: 8, right: 56, bottom: 8, containLabel: true },
    xAxis: { type: 'value', show: false, max: 100 },
    yAxis: {
      type: 'category',
      data: reversed.map((p) => p.player),
      axisLabel: { color: '#e8edf5', fontSize: 12 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 15,
        itemStyle: {
          borderRadius: [0, 4, 4, 0],
          color: (p) => {
            // 用评分做色阶，直观区分强弱
            const row = reversed[p.dataIndex]
            return scoreColor(row?.score)
          },
        },
        label: {
          show: true,
          position: 'right',
          formatter: (p) => fmt(p.value, 2),
          color: '#9aa7bd',
          fontSize: 11.5,
          fontWeight: 600,
        },
        data: reversed.map((p) => p.score ?? 0),
      },
    ],
  }
})

async function fetchData() {
  loading.value = true
  error.value = ''
  try {
    data.value = await request.get('/rankings', {
      params: { position: position.value, limit: limit.value },
    })
  } catch (e) {
    error.value = e.message
    data.value = null
  } finally {
    loading.value = false
  }
}

watch([position, limit], fetchData)
onMounted(fetchData)

function goPlayer(name) {
  if (name) router.push(`/players/${encodeURIComponent(name)}`)
}

/** 领奖台高度：第 1 名最高 */
function podiumHeight(index) {
  return ['112px', '88px', '72px'][index] || '72px'
}
</script>

<template>
  <div>
    <PageHeader title="评分排行榜" desc="各位置综合评分排名，评分口径为百分位标准化 + 加权求和（0–100）">
      <el-select v-model="limit" style="width: 126px">
        <el-option :value="10" label="TOP 10" />
        <el-option :value="20" label="TOP 20" />
        <el-option :value="50" label="TOP 50" />
        <el-option :value="100" label="TOP 100" />
      </el-select>
    </PageHeader>

    <!-- 位置切换 -->
    <el-card class="filter-card">
      <div class="filter-bar">
        <el-radio-group v-model="position">
          <el-radio-button v-for="p in positions" :key="p.value" :value="p.value">
            {{ p.label }}
          </el-radio-button>
        </el-radio-group>
        <span v-if="data" class="total">
          共 <b class="num">{{ fmtInt(data.total_players) }}</b> 名合格{{ data.position_label }}
        </span>
      </div>
    </el-card>

    <ErrorState v-if="error" class="block" :message="error" @retry="fetchData" />

    <template v-else-if="data">
      <!-- ============ TOP3 领奖台 ============ -->
      <el-card class="block" v-loading="loading">
        <template #header>
          <span>{{ data.position_label }} TOP 3</span>
          <span class="card-sub">点击卡片查看球员档案</span>
        </template>

        <div class="podium">
          <!-- 展示顺序：2 - 1 - 3，形成领奖台视觉 -->
          <div
            v-for="slot in [1, 0, 2]"
            :key="slot"
            class="podium-slot"
            :class="[`place-${slot + 1}`, { 'is-empty': !podium[slot] }]"
            @click="podium[slot] && goPlayer(podium[slot].player)"
          >
            <template v-if="podium[slot]">
              <div class="podium-medal num">{{ slot + 1 }}</div>
              <img
                v-if="podium[slot].nation_flag"
                :src="flagUrl(podium[slot].nation_flag)"
                class="flag"
                :alt="podium[slot].nation"
                @error="(e) => (e.target.style.display = 'none')"
              />
              <div class="podium-name">{{ podium[slot].player }}</div>
              <div class="podium-club">{{ podium[slot].squads || '—' }}</div>
              <div class="podium-bar" :style="{ height: podiumHeight(slot) }">
                <span class="podium-score num">{{ fmtScore(podium[slot].score) }}</span>
              </div>
            </template>
          </div>
        </div>
      </el-card>

      <!-- ============ TOP10 图表 ============ -->
      <el-card class="block">
        <template #header>
          <span>评分 TOP {{ Math.min(10, items.length) }}（{{ data.position_label }}）</span>
          <span class="card-sub">条形颜色代表评分区间</span>
        </template>
        <BaseChart :option="chartOption" :height="`${Math.max(300, Math.min(10, items.length) * 34 + 40)}px`" :loading="loading" />
      </el-card>

      <!-- ============ 完整榜单 ============ -->
      <el-card class="block">
        <template #header>
          <span>{{ data.position_label }}完整榜单（TOP {{ items.length }}）</span>
        </template>

        <el-table
          v-loading="loading"
          :data="items"
          stripe
          class="clickable-rows"
          :max-height="620"
          @row-click="(row) => goPlayer(row.player)"
        >
          <el-table-column label="排名" width="76" align="center">
            <template #default="{ row }">
              <span class="rank-badge" :class="row.rank <= 3 ? `is-${row.rank}` : ''">
                {{ row.rank }}
              </span>
            </template>
          </el-table-column>

          <el-table-column label="球员" min-width="180" fixed>
            <template #default="{ row }">
              <span class="player-cell">
                <img
                  v-if="row.nation_flag"
                  :src="flagUrl(row.nation_flag)"
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
              <span class="pos-chip">{{ row.position || '—' }}</span>
            </template>
          </el-table-column>

          <el-table-column prop="squads" label="俱乐部" min-width="150" show-overflow-tooltip />

          <el-table-column label="年龄" width="74" align="center">
            <template #default="{ row }">
              <span class="num dim">{{ fmt(row.age, 0) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="出场时间" width="104" align="right">
            <template #default="{ row }">
              <span class="num">{{ fmtInt(row.minutes) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="综合评分" width="180" align="center" fixed="right">
            <template #default="{ row }">
              <div class="score-cell">
                <div class="score-track">
                  <div
                    class="score-fill"
                    :style="{
                      width: `${Math.max(0, Math.min(100, Number(row.score) || 0))}%`,
                      background: scoreColor(row.score),
                    }"
                  />
                </div>
                <span class="score-num num" :style="{ color: scoreColor(row.score) }">
                  {{ fmtScore(row.score) }}
                </span>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.filter-card :deep(.el-card__body) {
  padding: 14px 18px;
}

.total {
  font-size: 12.5px;
  color: var(--t-2);
}

.total b {
  color: var(--c-accent);
  font-size: 14px;
  margin: 0 2px;
}

.card-sub {
  font-size: 12px;
  font-weight: 400;
  color: var(--t-3);
}

/* ============ 领奖台 ============ */
.podium {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: var(--sp-5);
  padding: var(--sp-3) 0 var(--sp-2);
}

.podium-slot {
  flex: 0 1 190px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  cursor: pointer;
}

.podium-slot.is-empty {
  visibility: hidden;
}

.podium-medal {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: var(--r-full);
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 2px;
}

.place-1 .podium-medal {
  background: linear-gradient(135deg, #ffd76e, #e8a020);
  color: #4a3200;
  box-shadow: 0 0 20px rgba(242, 183, 61, 0.45);
}

.place-2 .podium-medal {
  background: linear-gradient(135deg, #dfe6ef, #9aa8bb);
  color: #2b3340;
}

.place-3 .podium-medal {
  background: linear-gradient(135deg, #e5a06b, #b87333);
  color: #3a2010;
}

.podium-name {
  font-size: 14.5px;
  font-weight: 700;
  text-align: center;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.podium-club {
  font-size: 11.5px;
  color: var(--t-3);
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.podium-bar {
  width: 100%;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 10px;
  border-radius: var(--r-md) var(--r-md) 0 0;
  border: 1px solid var(--line);
  border-bottom: none;
  transition: height 0.4s cubic-bezier(0.22, 1, 0.36, 1);
}

.place-1 .podium-bar {
  background: linear-gradient(180deg, rgba(242, 183, 61, 0.16), rgba(242, 183, 61, 0.02));
  border-color: rgba(242, 183, 61, 0.30);
}

.place-2 .podium-bar {
  background: linear-gradient(180deg, rgba(223, 230, 239, 0.10), rgba(223, 230, 239, 0.02));
  border-color: rgba(223, 230, 239, 0.18);
}

.place-3 .podium-bar {
  background: linear-gradient(180deg, rgba(229, 160, 107, 0.13), rgba(229, 160, 107, 0.02));
  border-color: rgba(229, 160, 107, 0.24);
}

.podium-score {
  font-size: 19px;
  font-weight: 700;
  color: var(--t-1);
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
  padding: 2px 7px;
  border-radius: var(--r-sm);
  color: var(--t-2);
  background: var(--bg-panel-2);
  border: 1px solid var(--line-strong);
}

.dim {
  color: var(--t-2);
}

.score-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.score-track {
  flex: 1;
  height: 7px;
  border-radius: var(--r-full);
  background: var(--bg-hover);
  overflow: hidden;
}

.score-fill {
  height: 100%;
  border-radius: var(--r-full);
}

.score-num {
  width: 46px;
  text-align: right;
  font-size: 13.5px;
  font-weight: 700;
}

@media (max-width: 768px) {
  .podium {
    gap: var(--sp-3);
  }

  .podium-slot {
    flex: 1 1 0;
  }
}
</style>
