<script setup>
/**
 * 球员列表
 * ========
 * 数据来源：GET /api/players（分页 + 筛选 + 排序全部在 Python 端完成）
 *
 * 注意：表格列刻意不加 el-table 的 sortable —— 那是前端排序，只会排当前页的
 * N 条数据，与后端全库排序结果冲突且用户无感知。排序统一走 order/direction 参数。
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '../api/request'
import PageHeader from '../components/PageHeader.vue'
import ErrorState from '../components/ErrorState.vue'
import AppIcon from '../components/AppIcon.vue'
import {
  fmt,
  fmtScore,
  fmtInt,
  scoreColor,
  flagUrl,
} from '../utils/format'

const router = useRouter()

const loading = ref(true)
const error = ref('')
const rows = ref([])
const total = ref(0)

const query = ref({
  page: 1,
  page_size: 20,
  position: '',
  club: '',
  search: '',
  order: 'Best_Score',
  direction: 'desc',
})

const positionOptions = [
  { label: '全部位置', value: '' },
  { label: '前锋 FW', value: 'FW' },
  { label: '中场 MF', value: 'MF' },
  { label: '后卫 DF', value: 'DF' },
  { label: '门将 GK', value: 'GK' },
]

/** 可选排序字段（与后端 SORTABLE_COLUMNS 保持一致） */
const orderOptions = [
  { label: '综合评分', value: 'Best_Score' },
  { label: '出场时间', value: 'Min' },
  { label: '出场场次', value: 'MP' },
  { label: '进球', value: 'Gls' },
  { label: '助攻', value: 'Ast' },
  { label: '进球+助攻', value: 'G+A' },
  { label: '年龄', value: 'Age' },
]

/** 升序时这些字段的"更好"方向相反（年龄越小越好） */
const ASC_IS_BETTER = new Set(['Age'])

async function load() {
  loading.value = true
  error.value = ''
  try {
    // 过滤空字符串参数，避免后端把空串当成筛选条件
    const params = Object.fromEntries(
      Object.entries(query.value).filter(([, v]) => v !== '')
    )
    const data = await request.get('/players', { params })
    rows.value = data?.items || []
    total.value = data?.total || 0
  } catch (e) {
    error.value = e.message
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

/** 筛选条件变化：重置回第 1 页 */
function onFilter() {
  query.value.page = 1
  load()
}

function resetFilters() {
  query.value.position = ''
  query.value.club = ''
  query.value.search = ''
  query.value.order = 'Best_Score'
  query.value.direction = 'desc'
  onFilter()
}

function toggleDirection() {
  query.value.direction = query.value.direction === 'desc' ? 'asc' : 'desc'
  onFilter()
}

function onPageSizeChange(size) {
  query.value.page_size = size
  query.value.page = 1
  load()
}

function goDetail(name) {
  if (name) router.push(`/players/${encodeURIComponent(name)}`)
}

/** 当前排序方向是否对该字段"更优" */
const directionIsGood = computed(() => {
  const isAsc = query.value.direction === 'asc'
  return ASC_IS_BETTER.has(query.value.order) ? isAsc : !isAsc
})

/** 是否有生效中的筛选条件 */
const hasFilter = computed(
  () => !!(query.value.position || query.value.club || query.value.search)
)

onMounted(load)
</script>

<template>
  <div>
    <PageHeader
      title="球员列表"
      desc="全量球员数据，支持位置 / 俱乐部 / 姓名筛选与全库排序"
    >
      <span class="total-chip">
        共 <b class="num">{{ fmtInt(total) }}</b> 名球员
      </span>
    </PageHeader>

    <el-card>
      <!-- ============ 筛选栏 ============ -->
      <div class="filter-bar">
        <el-select
          v-model="query.position"
          placeholder="位置"
          style="width: 132px"
          @change="onFilter"
        >
          <el-option
            v-for="opt in positionOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>

        <el-input
          v-model="query.search"
          placeholder="搜索球员姓名"
          style="width: 180px"
          clearable
          @keyup.enter="onFilter"
          @clear="onFilter"
        >
          <template #prefix><AppIcon name="search" :size="14" /></template>
        </el-input>

        <el-input
          v-model="query.club"
          placeholder="搜索俱乐部"
          style="width: 180px"
          clearable
          @keyup.enter="onFilter"
          @clear="onFilter"
        />

        <el-divider direction="vertical" />

        <el-select v-model="query.order" style="width: 140px" @change="onFilter">
          <el-option
            v-for="opt in orderOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>

        <el-button @click="toggleDirection">
          {{ query.direction === 'desc' ? '降序' : '升序' }}
          <span class="dir-icon" :class="{ 'is-good': directionIsGood }">
            {{ query.direction === 'desc' ? '↓' : '↑' }}
          </span>
        </el-button>

        <el-button v-if="hasFilter" text type="primary" @click="resetFilters">
          清空筛选
        </el-button>
      </div>

      <!-- ============ 错误态 ============ -->
      <ErrorState v-if="error" :message="error" @retry="load" />

      <!-- ============ 表格 ============ -->
      <template v-else>
        <el-table
          v-loading="loading"
          :data="rows"
          stripe
          class="clickable-rows"
          :max-height="560"
          @row-click="(row) => goDetail(row.Player)"
        >
          <el-table-column label="#" width="62" align="center">
            <template #default="{ $index }">
              <span class="row-index num">
                {{ (query.page - 1) * query.page_size + $index + 1 }}
              </span>
            </template>
          </el-table-column>

          <el-table-column label="球员" min-width="170" fixed>
            <template #default="{ row }">
              <span class="player-cell">
                <span class="player-link">{{ row.Player }}</span>
              </span>
            </template>
          </el-table-column>

          <el-table-column label="位置" width="82" align="center">
            <template #default="{ row }">
              <span class="pos-chip">{{ row.Pos || '—' }}</span>
            </template>
          </el-table-column>

          <el-table-column
            prop="Squads"
            label="俱乐部"
            min-width="150"
            show-overflow-tooltip
          />

          <el-table-column label="年龄" width="74" align="center">
            <template #default="{ row }">
              <span class="num dim">{{ fmt(row.Age, 0) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="出场时间" width="104" align="right">
            <template #default="{ row }">
              <span class="num">{{ fmtInt(row.Min) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="进球" width="72" align="right">
            <template #default="{ row }">
              <span class="num">{{ fmt(row.Gls, 0) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="助攻" width="72" align="right">
            <template #default="{ row }">
              <span class="num">{{ fmt(row.Ast, 0) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="综合评分" width="116" align="center" fixed="right">
            <template #default="{ row }">
              <span
                class="score-pill num"
                :style="{
                  color: scoreColor(row.Best_Score),
                  borderColor: scoreColor(row.Best_Score),
                  background: `${scoreColor(row.Best_Score)}1f`,
                }"
              >
                {{ fmtScore(row.Best_Score) }}
              </span>
            </template>
          </el-table-column>

          <template #empty>
            <el-empty description="没有符合条件的球员" :image-size="80" />
          </template>
        </el-table>

        <!-- ============ 分页 ============ -->
        <div class="pager">
          <el-pagination
            v-model:current-page="query.page"
            :page-size="query.page_size"
            :page-sizes="[10, 20, 50, 100]"
            :total="total"
            background
            layout="total, sizes, prev, pager, next, jumper"
            @current-change="load"
            @size-change="onPageSizeChange"
          />
        </div>
      </template>
    </el-card>
  </div>
</template>

<style scoped>
.total-chip {
  font-size: 12.5px;
  color: var(--t-2);
  padding: 5px 12px;
  border-radius: var(--r-full);
  background: var(--bg-panel);
  border: 1px solid var(--line);
}

.total-chip b {
  color: var(--c-accent);
  font-size: 14px;
  margin: 0 2px;
}

.filter-bar {
  margin-bottom: var(--sp-4);
}

.dir-icon {
  margin-left: 4px;
  font-weight: 700;
  color: var(--t-3);
}

.dir-icon.is-good {
  color: var(--c-accent);
}

.row-index {
  color: var(--t-3);
  font-size: 12.5px;
}

.player-cell {
  display: flex;
  align-items: center;
  gap: 8px;
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

.score-pill {
  display: inline-block;
  min-width: 58px;
  padding: 3px 9px;
  border-radius: var(--r-sm);
  border: 1px solid;
  font-size: 13px;
  font-weight: 700;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--sp-4);
}

@media (max-width: 768px) {
  .pager {
    justify-content: center;
  }
}
</style>
