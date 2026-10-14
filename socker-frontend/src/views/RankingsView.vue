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
      axisLabel: { color: '#1a2332', fontSize: 12 },
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
          color: '#5a6a82',
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
  padding: var(--sp-4) 0 var(--sp-2);
  position: relative;
}

/* 冠军上方的金色氛围光 */
.podium::before {
  content: '';
  position: absolute;
  top: -10px;
  left: 50%;
  transform: translateX(-50%);
  width: 260px;
  height: 120px;
  background: radial-gradient(ellipse, rgba(217, 154, 32, 0.12), transparent 70%);
  pointer-events: none;
}

.podium-slot {
  flex: 0 1 190px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  transition: transform 0.25s cubic-bezier(0.22, 1, 0.36, 1);
}

.podium-slot:hover {
  transform: translateY(-4px);
}

.podium-slot.is-empty {
  visibility: hidden;
}

.podium-medal {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: var(--r-full);
  font-size: 15px;
  font-weight: 800;
  margin-bottom: 2px;
}

.place-1 .podium-medal {
  background: linear-gradient(135deg, #ffd76e, #e8a020);
  color: #4a3200;
  box-shadow: 0 4px 12px rgba(217, 154, 32, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.4);
}

.place-2 .podium-medal {
  background: linear-gradient(135deg, #e8eef5, #b0bccf);
  color: #2b3340;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.5);
}

.place-3 .podium-medal {
  background: linear-gradient(135deg, #e8b080, #c07840);
  color: #3a2010;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

.podium-name {
  font-size: 15px;
  font-weight: 700;
  text-align: center;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--t-1);
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
  padding-top: 12px;
  border-radius: var(--r-md) var(--r-md) 0 0;
  border: 1px solid var(--line);
  border-bottom: none;
  transition: height 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  position: relative;
}

/* 领奖台顶部高光 */
.podium-bar::after {
  content: '';
  position: absolute;
  top: 0;
  left: 10%;
  right: 10%;
  height: 1px;
  background: linear-gradient(90deg, transparent, currentColor, transparent);
  opacity: 0.4;
}

.place-1 .podium-bar {
  background: linear-gradient(180deg, rgba(217, 154, 32, 0.12), rgba(217, 154, 32, 0.02));
  border-color: rgba(217, 154, 32, 0.3);
  color: var(--c-gold);
  box-shadow: 0 -4px 20px rgba(217, 154, 32, 0.08);
}

.place-2 .podium-bar {
  background: linear-gradient(180deg, rgba(176, 188, 207, 0.12), rgba(176, 188, 207, 0.02));
  border-color: rgba(176, 188, 207, 0.25);
  color: #94a3b8;
}

.place-3 .podium-bar {
  background: linear-gradient(180deg, rgba(192, 120, 64, 0.12), rgba(192, 120, 64, 0.02));
  border-color: rgba(192, 120, 64, 0.25);
  color: #c07840;
}

.podium-score {
  font-size: 20px;
  font-weight: 800;
  color: var(--t-1);
  font-variant-numeric: tabular-nums;
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
