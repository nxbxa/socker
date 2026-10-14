<script setup>
/**
 * 评分预测
 * ========
 * 数据来源：
 *   GET  /api/models   各位置随机森林模型的评估结果与所需指标
 *   GET  /api/meta     指标中文标签
 *   GET  /api/rankings 当前群体评分分布（用于把预测分换算成百分位）
 *   POST /api/predict  提交指标 -> 预测综合评分
 *
 * 相比初版的关键增强：
 * 1. 每个指标标注「单位 + 参考范围 + 权重」，解决"不知道该填 0.5 还是 50"
 * 2. 前端按范围做校验，减少无意义的请求
 * 3. 支持一键填入示例值 / 清空
 * 4. 预测结果换算成同位置百分位，并显示该分数在群体分布中的位置
 * 5. 展示模型评估全貌（R²/RMSE/MAE/交叉验证/特征重要性）
 */
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../api/request'
import BaseChart from '../components/BaseChart.vue'
import PageHeader from '../components/PageHeader.vue'
import ErrorState from '../components/ErrorState.vue'
import AppIcon from '../components/AppIcon.vue'
import { fmt, fmtScore, fmtRatio, scoreColor } from '../utils/format'
import { CHART_COLORS, CHART_PALETTE } from '../theme/echarts'

const loading = ref(true)
const loadError = ref('')
const submitting = ref(false)

const models = ref(null)
const metaLabels = ref({})
const position = ref('FW')
const form = ref({})
const result = ref(null)

/** 群体评分分布（用于百分位换算） */
const population = ref([])
const populationLoading = ref(false)

const positions = [
  { value: 'FW', label: '前锋' },
  { value: 'MF', label: '中场' },
  { value: 'DF', label: '后卫' },
  { value: 'GK', label: '门将' },
]

/**
 * 指标参考元信息：单位 + 合理取值范围 + 示例值
 * 取值范围用于前端校验，避免把 50 当成"每 90 分钟进球数"提交。
 */
const METRIC_META = {
  // 每 90 分钟进攻产出
  Gls_90: { unit: '球/90分钟', min: 0, max: 2, step: 0.01, sample: 0.65, hint: '顶级前锋约 0.6–1.0' },
  xG_90: { unit: 'xG/90分钟', min: 0, max: 2, step: 0.01, sample: 0.58, hint: '顶级前锋约 0.5–0.9' },
  Ast_90: { unit: '次/90分钟', min: 0, max: 1.5, step: 0.01, sample: 0.28, hint: '组织核心约 0.3–0.6' },
  xAG_90: { unit: 'xAG/90分钟', min: 0, max: 1.5, step: 0.01, sample: 0.25, hint: '创造型球员约 0.2–0.5' },
  SoT_90: { unit: '次/90分钟', min: 0, max: 4, step: 0.01, sample: 1.45, hint: '射正次数，前锋约 1.2–2.0' },
  'G/Sh': { unit: '进球/射门', min: 0, max: 1, step: 0.01, sample: 0.15, hint: '转化率，0.15 以上优秀' },
  Succ_90: { unit: '次/90分钟', min: 0, max: 8, step: 0.01, sample: 1.6, hint: '成功过人次数' },

  // 中场组织
  Cmp_90: { unit: '次/90分钟', min: 0, max: 130, step: 1, sample: 52, hint: '成功传球，中场约 40–80' },
  PrgP_90: { unit: '次/90分钟', min: 0, max: 20, step: 0.1, sample: 5.4, hint: '推进传球' },
  KP_90: { unit: '次/90分钟', min: 0, max: 6, step: 0.01, sample: 1.4, hint: '关键传球' },

  // 防守
  Tkl_90: { unit: '次/90分钟', min: 0, max: 8, step: 0.01, sample: 2.1, hint: '抢断' },
  TklW_90: { unit: '次/90分钟', min: 0, max: 6, step: 0.01, sample: 1.4, hint: '抢断成功' },
  Int_90: { unit: '次/90分钟', min: 0, max: 8, step: 0.01, sample: 1.8, hint: '拦截' },
  Clr_90: { unit: '次/90分钟', min: 0, max: 12, step: 0.01, sample: 3.2, hint: '解围，中卫约 3–6' },
  Won_90: { unit: '次/90分钟', min: 0, max: 15, step: 0.01, sample: 5.5, hint: '对抗成功' },
  Carries_90: { unit: '次/90分钟', min: 0, max: 90, step: 0.1, sample: 42, hint: '持球推进次数' },
  PrgC_90: { unit: '次/90分钟', min: 0, max: 15, step: 0.01, sample: 4.2, hint: '带球推进距离相关次数' },

  // 门将（注意：这几个是百分比尺度，不是 0–1）
  SavePct: { unit: '%（0–100）', min: 0, max: 100, step: 0.1, sample: 72.5, hint: '扑救成功率，优秀门将 ≥ 72' },
  CSPct: { unit: '%（0–100）', min: 0, max: 100, step: 0.1, sample: 30.5, hint: '零封率' },
  StpPct: { unit: '%（0–100）', min: 0, max: 100, step: 0.1, sample: 8.4, hint: '传中拦截率' },
  GKCmpPct: { unit: '%（0–100）', min: 0, max: 100, step: 0.1, sample: 78.2, hint: '门将传球成功率' },
  PSxGD_90: { unit: '球/90分钟', min: -1, max: 1, step: 0.01, sample: 0.12, hint: '每 90 分钟扑救贡献，可为负' },
}

/** 未知指标的兜底元信息（不参与范围校验） */
const DEFAULT_META = { unit: '', hint: '' }

/**
 * 百分比尺度的指标（后端用 0–100 而不是 0–1）
 * 用于提示文案，避免用户误填 0.72
 */
const PERCENT_METRICS = new Set([
  'SavePct',
  'CSPct',
  'StpPct',
  'GKCmpPct',
  'SoT%',
  'Cmp%',
  'Succ%',
])

/** /api/meta 的完整响应（提供指标权重） */
const metaInfo = ref(null)

const currentModel = computed(() => models.value?.[position.value] || null)

/** 当前模型对应的指标配置（含中文名、权重、范围提示） */
const metricFields = computed(() => {
  const model = currentModel.value
  if (!model) return []

  const metaPositions = metaInfo.value?.positions || {}
  const weightMap = {}
  ;(metaPositions[position.value]?.metrics || []).forEach((m) => {
    weightMap[m.name] = m.weight
  })

  return (model.metrics || []).map((name) => {
    const meta = METRIC_META[name] || DEFAULT_META
    return {
      name,
      label: metaLabels.value[name] || name,
      weight: weightMap[name],
      isPercent: PERCENT_METRICS.has(name),
      ...meta,
    }
  })
})

/* ---------------- 数据加载 ---------------- */

async function loadBase() {
  loading.value = true
  loadError.value = ''
  try {
    const [modelsRes, metaRes] = await Promise.all([
      request.get('/models'),
      request.get('/meta'),
    ])
    models.value = modelsRes
    metaInfo.value = metaRes
    metaLabels.value = metaRes?.metric_labels || {}
  } catch (e) {
    loadError.value = e.message
  } finally {
    loading.value = false
  }
}

/** 拉取当前群体评分分布（limit 上限 100，足够做百分位估算） */
async function loadPopulation() {
  populationLoading.value = true
  try {
    const data = await request.get('/rankings', {
      params: { position: position.value, limit: 100 },
    })
    population.value = (data?.items || []).map((i) => i.score).filter((s) => s !== null)
  } catch {
    population.value = []
  } finally {
    populationLoading.value = false
  }
}

onMounted(async () => {
  await loadBase()
  if (!loadError.value) loadPopulation()
})

watch(position, () => {
  loadPopulation()
})

/* ---------------- 表单操作 ---------------- */

const onPositionChange = () => {
  form.value = {}
  result.value = null
}

/** 一键填入示例值（演示 / 快速体验用） */
function fillSample() {
  const next = {}
  metricFields.value.forEach((f) => {
    if (f.sample !== undefined) next[f.name] = f.sample
  })
  form.value = next
  result.value = null
  ElMessage.success(`已填入${currentModel.value?.position_label || ''}示例数据`)
}

function reset() {
  form.value = {}
  result.value = null
}

/* ---------------- 提交预测 ---------------- */

async function submit() {
  const fields = metricFields.value
  if (!fields.length) return

  const missing = []
  const outOfRange = []

  fields.forEach((f) => {
    const raw = form.value[f.name]
    if (raw === undefined || raw === null || raw === '') {
      missing.push(f.label)
      return
    }
    const n = Number(raw)
    if (Number.isNaN(n)) {
      missing.push(f.label)
      return
    }
    // 范围校验：只对配置了范围的指标生效
    if (f.min !== undefined && f.max !== undefined && (n < f.min || n > f.max)) {
      outOfRange.push(`${f.label}（应在 ${f.min}–${f.max} ${f.unit || ''}）`)
    }
  })

  if (missing.length) {
    ElMessage.warning(`还有 ${missing.length} 项未填写：${missing.slice(0, 5).join('、')}${missing.length > 5 ? ' 等' : ''}`)
    return
  }

  if (outOfRange.length) {
    ElMessage.error(`数值超出合理范围：${outOfRange.slice(0, 3).join('；')}${outOfRange.length > 3 ? ' 等' : ''}`)
    return
  }

  const metrics = {}
  fields.forEach((f) => {
    metrics[f.name] = Number(form.value[f.name])
  })

  submitting.value = true
  try {
    result.value = await request.post('/predict', {
      position: position.value,
      metrics,
    })
  } catch (e) {
    ElMessage.error(e.message || '预测失败')
    result.value = null
  } finally {
    submitting.value = false
  }
}

/* ---------------- 预测结果的百分位换算 ---------------- */

const predictedPercentile = computed(() => {
  const score = result.value?.predicted_score
  const pop = population.value
  if (score === null || score === undefined || !pop.length) return null
  const below = pop.filter((s) => s < score).length
  return (below / pop.length) * 100
})

const predictedComment = computed(() => {
  const p = predictedPercentile.value
  if (p === null) return ''
  if (p >= 95) return '同位置顶级水准'
  if (p >= 85) return '同位置上游主力'
  if (p >= 70) return '同位置稳定首发'
  if (p >= 50) return '同位置平均水平以上'
  if (p >= 30) return '同位置轮换水准'
  return '同位置竞争力偏弱'
})

/** 群体评分分布直方图 + 预测值标线 */
const distributionOption = computed(() => {
  const pop = population.value
  const score = result.value?.predicted_score
  if (!pop.length || score === null || score === undefined) return {}

  // 手动分箱（bins=12），避免额外引入统计依赖
  const min = Math.min(...pop, score)
  const max = Math.max(...pop, score)
  const binCount = 12
  const width = (max - min) / binCount || 1
  const counts = new Array(binCount).fill(0)

  pop.forEach((s) => {
    let idx = Math.floor((s - min) / width)
    if (idx >= binCount) idx = binCount - 1
    if (idx < 0) idx = 0
    counts[idx] += 1
  })

  const labels = counts.map((_, i) => fmt(min + width * (i + 0.5), 0))

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      valueFormatter: (v) => `${v} 人`,
    },
    grid: { top: 34, left: 8, right: 16, bottom: 26, containLabel: true },
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: { fontSize: 10.5, interval: 1 },
    },
    yAxis: { type: 'value', name: '人数', nameGap: 12 },
    series: [
      {
        type: 'bar',
        barMaxWidth: 22,
        itemStyle: { color: 'rgba(58,160,255,0.55)', borderRadius: [3, 3, 0, 0] },
        data: counts,
        markLine: {
          silent: true,
          symbol: ['none', 'circle'],
          lineStyle: { color: CHART_COLORS.accent, width: 2, type: 'solid' },
          label: {
            formatter: `预测 ${fmt(score, 1)}`,
            color: CHART_COLORS.accent,
            fontWeight: 600,
            position: 'insideEndTop',
          },
          data: [
            {
              // 用 x 轴类目定位：找到最接近预测分的中点
              xAxis: labels.reduce(
                (best, l, i) =>
                  Math.abs(Number(l) - score) < Math.abs(Number(best) - score)
                    ? l
                    : best,
                labels[0]
              ),
            },
          ],
        },
      },
    ],
  }
})

/** 特征重要性（模型可解释性） */
const importanceOption = computed(() => {
  const imp = currentModel.value?.importance
  if (!imp?.length) return {}

  const top = [...imp].slice(0, 10).reverse()

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const p = params?.[0]
        if (!p) return ''
        const row = top[p.dataIndex]
        return `${row?.label || ''}<br/>重要性：<b>${fmt(p.value, 4)}</b>`
      },
    },
    grid: { top: 8, left: 8, right: 48, bottom: 8, containLabel: true },
    xAxis: { type: 'value', show: false },
    yAxis: {
      type: 'category',
      data: top.map((i) => i.label),
      axisLabel: { color: '#5a6a82', fontSize: 11.5 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 13,
        itemStyle: { color: CHART_PALETTE[1], borderRadius: [0, 3, 3, 0] },
        label: {
          show: true,
          position: 'right',
          formatter: (p) => fmt(p.value, 3),
          color: '#5a6a82',
          fontSize: 11,
        },
        data: top.map((i) => i.importance),
      },
    ],
  }
})

/** 测试集 预测值 vs 实际值 */
const testScatterOption = computed(() => {
  const model = currentModel.value
  const actual = model?.test_actual
  const predicted = model?.test_predicted
  if (!actual?.length || !predicted?.length) return {}

  const points = actual.map((a, i) => [a, predicted[i]])
  const all = [...actual, ...predicted]
  const lo = Math.min(...all)
  const hi = Math.max(...all)

  return {
    tooltip: {
      trigger: 'item',
      formatter: (p) =>
        `实际评分：<b>${fmt(p.value?.[0], 2)}</b><br/>预测评分：<b>${fmt(p.value?.[1], 2)}</b>`,
    },
    grid: { top: 16, left: 8, right: 16, bottom: 8, containLabel: true },
    xAxis: { type: 'value', name: '实际', min: lo, max: hi, nameGap: 6 },
    yAxis: { type: 'value', name: '预测', min: lo, max: hi, nameGap: 6 },
    series: [
      {
        type: 'scatter',
        symbolSize: 7,
        itemStyle: { color: 'rgba(0,224,122,0.7)' },
        data: points,
        // y = x 参考线：点越贴近这条线，模型越准
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: '#94a3b8', type: 'dashed' },
          label: { show: false },
          data: [[{ coord: [lo, lo] }, { coord: [hi, hi] }]],
        },
      },
    ],
  }
})

/** 已填写的指标数量 */
const filledCount = computed(
  () =>
    metricFields.value.filter((f) => {
      const v = form.value[f.name]
      return v !== undefined && v !== null && v !== ''
    }).length
)
</script>

<template>
  <div>
    <PageHeader
      title="评分预测"
      desc="输入球员的每 90 分钟比赛指标，由各位置随机森林回归模型预测综合评分"
    >
      <el-tag v-if="currentModel" effect="plain" size="small">
        模型测试集 R² = {{ fmt(currentModel.forest_test?.r2, 4) }}
      </el-tag>
    </PageHeader>

    <ErrorState v-if="loadError" :message="loadError" @retry="loadBase" />

    <template v-else-if="models">
      <!-- ============ 位置切换 ============ -->
      <el-card class="filter-card">
        <div class="filter-bar">
          <el-radio-group v-model="position" @change="onPositionChange">
            <el-radio-button v-for="p in positions" :key="p.value" :value="p.value">
              {{ p.label }}
            </el-radio-button>
          </el-radio-group>

          <span v-if="currentModel" class="model-info">
            训练样本 <b class="num">{{ currentModel.sample_count }}</b> 人 ·
            需要填写 <b class="num">{{ metricFields.length }}</b> 项指标
          </span>
        </div>
      </el-card>

      <el-row :gutter="16" class="block">
        <!-- ============ 左：指标输入 ============ -->
        <el-col :xs="24" :lg="14">
          <el-card class="h-full">
            <template #header>
              <span>输入{{ currentModel?.position_label }}比赛表现指标</span>
              <span class="card-sub">
                已填 <b class="accent">{{ filledCount }}</b> / {{ metricFields.length }}
              </span>
            </template>

            <div class="form-actions-top">
              <el-button size="small" @click="fillSample">
                <AppIcon name="zap" :size="13" style="margin-right: 4px" />填入示例数据
              </el-button>
              <el-button size="small" text @click="reset">清空全部</el-button>
            </div>

            <el-form label-position="top" class="metric-form">
              <div class="field-grid">
                <div
                  v-for="f in metricFields"
                  :key="f.name"
                  class="field-item"
                >
                  <div class="field-label">
                    <span class="fl-name">{{ f.label }}</span>
                    <span v-if="f.isPercent" class="fl-warn" title="该指标为百分比尺度，填 72.5 而不是 0.725">
                      百分比尺度
                    </span>
                    <span v-if="f.weight" class="fl-weight">
                      权重 {{ fmtRatio(f.weight, 0) }}
                    </span>
                  </div>

                  <el-input-number
                    v-model="form[f.name]"
                    :step="f.step || 0.01"
                    :precision="f.step && f.step >= 1 ? 0 : 2"
                    :controls="false"
                    :placeholder="f.sample !== undefined ? `如 ${f.sample}` : '请输入'"
                    class="field-input"
                  />

                  <div class="field-hint">
                    <span v-if="f.unit" class="fh-unit">{{ f.unit }}</span>
                    <span v-if="f.hint" class="fh-text">{{ f.hint }}</span>
                    <span v-else-if="f.min !== undefined" class="fh-text">
                      范围 {{ f.min }} – {{ f.max }}
                    </span>
                  </div>
                </div>
              </div>
            </el-form>

            <div class="submit-bar">
              <el-button
                type="primary"
                size="large"
                :loading="submitting"
                @click="submit"
              >
                <AppIcon name="target" :size="16" style="margin-right: 5px" />
                预测综合评分
              </el-button>
              <span class="submit-tip">所有指标均为必填</span>
            </div>
          </el-card>
        </el-col>

        <!-- ============ 右：结果与模型信息 ============ -->
        <el-col :xs="24" :lg="10">
          <!-- 预测结果 -->
          <el-card v-if="result" class="result-card">
            <template #header>
              <span>预测结果</span>
              <span class="card-sub">{{ currentModel?.position_label }}</span>
            </template>

            <div class="result-main">
              <div class="result-score num" :style="{ color: scoreColor(result.predicted_score) }">
                {{ fmtScore(result.predicted_score) }}
              </div>
              <div class="result-label">预测综合评分（0–100）</div>
            </div>

            <template v-if="predictedPercentile !== null">
              <div class="pct-block">
                <div class="pct-head">
                  <span>同位置百分位</span>
                  <span class="pct-value num">{{ fmt(predictedPercentile, 1) }}%</span>
                </div>
                <el-progress
                  :percentage="Math.round(predictedPercentile)"
                  :stroke-width="10"
                  :show-text="false"
                  :color="scoreColor(result.predicted_score)"
                />
                <div class="pct-comment">{{ predictedComment }}</div>
              </div>

              <el-divider style="margin: 16px 0" />
              <BaseChart :option="distributionOption" height="180px" />
            </template>

            <p v-else class="pct-na">
              群体分布数据不足，无法换算百分位
            </p>

            <div class="result-meta">
              模型 R² = {{ fmt(result.model_r2, 4) }} · 位置：{{ currentModel?.position_label }}
            </div>
          </el-card>

          <!-- 未预测时的引导 -->
          <el-card v-else class="result-card placeholder-card">
            <div class="placeholder">
              <div class="ph-icon"><AppIcon name="target" :size="28" /></div>
              <h4>填写左侧指标后点击预测</h4>
              <p>
                模型基于 <b>{{ currentModel?.sample_count }}</b> 名合格
                {{ currentModel?.position_label }}球员训练，
                可点击「填入示例数据」快速体验。
              </p>
            </div>
          </el-card>

          <!-- 模型评估 -->
          <el-card v-if="currentModel" class="block">
            <template #header>
              <span>模型评估</span>
              <span class="card-sub">随机森林 vs 线性回归基准</span>
            </template>

            <div class="eval-grid">
              <div class="eval-item">
                <span class="ei-label">随机森林 R²</span>
                <span class="ei-value num accent">
                  {{ fmt(currentModel.forest_test?.r2, 4) }}
                </span>
              </div>
              <div class="eval-item">
                <span class="ei-label">线性基准 R²</span>
                <span class="ei-value num dim">{{ fmt(currentModel.linear_test?.r2, 4) }}</span>
              </div>
              <div class="eval-item">
                <span class="ei-label">RMSE</span>
                <span class="ei-value num">{{ fmt(currentModel.forest_test?.rmse, 3) }}</span>
              </div>
              <div class="eval-item">
                <span class="ei-label">MAE</span>
                <span class="ei-value num">{{ fmt(currentModel.forest_test?.mae, 3) }}</span>
              </div>
              <div class="eval-item">
                <span class="ei-label">{{ currentModel.cv?.folds || 5 }} 折交叉验证 R²</span>
                <span class="ei-value num">
                  {{ fmt(currentModel.cv?.r2_mean, 4) }}
                  <em class="dim">± {{ fmt(currentModel.cv?.r2_std, 4) }}</em>
                </span>
              </div>
              <div class="eval-item">
                <span class="ei-label">训练样本</span>
                <span class="ei-value num">{{ currentModel.sample_count }} 人</span>
              </div>
            </div>
          </el-card>

          <!-- 特征重要性 -->
          <el-card v-if="currentModel?.importance?.length" class="block">
            <template #header>
              <span>指标重要性</span>
              <span class="card-sub">随机森林特征重要性（可印证权重设计）</span>
            </template>
            <BaseChart :option="importanceOption" height="280px" />
          </el-card>

          <!-- 预测 vs 实际 -->
          <el-card v-if="currentModel?.test_actual?.length" class="block">
            <template #header>
              <span>测试集拟合效果</span>
              <span class="card-sub">点越贴近虚线，预测越准</span>
            </template>
            <BaseChart :option="testScatterOption" height="260px" />
          </el-card>
        </el-col>
      </el-row>
    </template>

    <div v-else-if="loading" class="loading-block" v-loading="true" />
  </div>
</template>

<style scoped>
.filter-card :deep(.el-card__body) {
  padding: 14px 18px;
}

.model-info {
  font-size: 12.5px;
  color: var(--t-2);
}

.model-info b {
  color: var(--c-accent);
  font-size: 14px;
}

.card-sub {
  font-size: 12px;
  font-weight: 400;
  color: var(--t-3);
}

.accent {
  color: var(--c-accent);
}

.dim {
  color: var(--t-2);
}

/* ============ 表单 ============ */
.form-actions-top {
  display: flex;
  align-items: center;
  gap: 4px;
  padding-bottom: 12px;
  margin-bottom: 14px;
  border-bottom: 1px dashed var(--line);
}

.metric-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--sp-4) var(--sp-4);
}

.field-item {
  min-width: 0;
}

.field-label {
  display: flex;
  align-items: center;
  gap: 7px;
  flex-wrap: wrap;
  margin-bottom: 5px;
}

.fl-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--t-1);
}

.fl-warn {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: var(--r-sm);
  color: var(--c-gold);
  background: var(--c-gold-soft);
  border: 1px solid rgba(242, 183, 61, 0.3);
  cursor: help;
}

.fl-weight {
  font-size: 10.5px;
  color: var(--t-3);
}

.field-input {
  width: 100%;
}

.field-input :deep(.el-input__inner) {
  text-align: left;
  font-family: var(--font-num);
}

.field-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  font-size: 11px;
  min-height: 15px;
}

.fh-unit {
  flex-shrink: 0;
  padding: 0 5px;
  border-radius: 3px;
  color: var(--c-info);
  background: var(--c-info-soft);
}

.fh-text {
  color: var(--t-3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.submit-bar {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  margin-top: var(--sp-5);
  padding-top: var(--sp-4);
  border-top: 1px solid var(--line);
}

.submit-tip {
  font-size: 12px;
  color: var(--t-3);
}

/* ============ 预测结果 ============ */
.result-card {
  border-color: var(--c-accent-line) !important;
}

.result-main {
  text-align: center;
  padding: var(--sp-3) 0 var(--sp-4);
}

.result-score {
  font-size: 62px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.03em;
  text-shadow: 0 0 32px currentColor;
}

.result-label {
  margin-top: 8px;
  font-size: 12.5px;
  color: var(--t-2);
}

.pct-block {
  margin-top: var(--sp-2);
}

.pct-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 7px;
  font-size: 12.5px;
  color: var(--t-2);
}

.pct-value {
  font-size: 17px;
  font-weight: 700;
  color: var(--t-1);
}

.pct-comment {
  margin-top: 7px;
  font-size: 12.5px;
  color: var(--c-accent);
  font-weight: 500;
}

.pct-na {
  font-size: 12.5px;
  color: var(--t-3);
  text-align: center;
  padding: var(--sp-4) 0;
}

.result-meta {
  margin-top: var(--sp-4);
  padding-top: var(--sp-3);
  border-top: 1px solid var(--line);
  font-size: 11.5px;
  color: var(--t-3);
  text-align: center;
}

/* ============ 占位卡 ============ */
.placeholder {
  text-align: center;
  padding: var(--sp-5) var(--sp-3);
}

.ph-icon {
  width: 58px;
  height: 58px;
  margin: 0 auto 14px;
  display: grid;
  place-items: center;
  border-radius: var(--r-full);
  color: var(--c-accent);
  background: var(--c-accent-soft);
  border: 1px solid var(--c-accent-line);
}

.placeholder h4 {
  font-size: 15px;
  margin-bottom: 6px;
}

.placeholder p {
  font-size: 12.5px;
  color: var(--t-3);
  line-height: 1.8;
}

.placeholder b {
  color: var(--c-accent);
}

/* ============ 模型评估 ============ */
.eval-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--sp-3);
}

.eval-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 12px;
  border-radius: var(--r-md);
  background: var(--bg-panel-2);
  border: 1px solid var(--line);
}

.ei-label {
  font-size: 11.5px;
  color: var(--t-3);
}

.ei-value {
  font-size: 15px;
  font-weight: 700;
}

.ei-value em {
  font-size: 11px;
  font-style: normal;
  font-weight: 400;
}

.h-full {
  height: 100%;
}

.loading-block {
  height: 300px;
}

/* ============ 响应式 ============ */
@media (max-width: 900px) {
  .field-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
