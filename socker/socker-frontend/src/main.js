import { createApp, h } from 'vue'

/**
 * Element Plus 按需注册
 * =====================
 * 只注册项目实际用到的组件（见下方清单），而不是 app.use(ElementPlus) 全量注册。
 * 效果：JS 主体体积大幅下降（首屏不再下载整个组件库）。
 *
 * ⚠️ 新增组件时，请同步补充到 components 数组，否则模板中的 <el-xxx>
 * 会静默不渲染（Vue 仅输出一条 warning）。
 */
import {
  ElAlert,
  ElAside,
  ElButton,
  ElCard,
  ElCol,
  ElConfigProvider,
  ElContainer,
  ElDescriptions,
  ElDescriptionsItem,
  ElDivider,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElHeader,
  ElInput,
  ElInputNumber,
  ElLoading,
  ElMain,
  ElOption,
  ElPagination,
  ElProgress,
  ElRadioButton,
  ElRadioGroup,
  ElRow,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTabPane,
  ElTabs,
  ElTag,
} from 'element-plus'

/**
 * Element Plus 样式按需引入
 * ========================
 * 不引入 352 kB 的 theme-chalk/index.css（全组件样式），只引入 base（CSS 变量 +
 * reset）与上方组件清单对应的单组件样式，总体积约 148 kB。
 *
 * ⚠️ 新增组件时，除 components 数组外，还需在此处补充 `el-<name>.css`。
 */
import 'element-plus/theme-chalk/base.css'
import 'element-plus/theme-chalk/el-alert.css'
import 'element-plus/theme-chalk/el-button.css'
import 'element-plus/theme-chalk/el-card.css'
import 'element-plus/theme-chalk/el-col.css'
import 'element-plus/theme-chalk/el-divider.css'
import 'element-plus/theme-chalk/el-empty.css'
import 'element-plus/theme-chalk/el-form.css'
import 'element-plus/theme-chalk/el-input.css'
import 'element-plus/theme-chalk/el-input-number.css'
import 'element-plus/theme-chalk/el-loading.css'
import 'element-plus/theme-chalk/el-option.css'
import 'element-plus/theme-chalk/el-pagination.css'
import 'element-plus/theme-chalk/el-progress.css'
import 'element-plus/theme-chalk/el-radio-button.css'
import 'element-plus/theme-chalk/el-radio-group.css'
import 'element-plus/theme-chalk/el-row.css'
import 'element-plus/theme-chalk/el-select.css'
import 'element-plus/theme-chalk/el-table.css'
import 'element-plus/theme-chalk/el-tabs.css'
import 'element-plus/theme-chalk/el-tag.css'
// Element Plus 官方深色主题变量（必须在 base.css 之后引入）
import 'element-plus/theme-chalk/dark/css-vars.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

// 设计令牌 + 全局样式 + Element Plus 深色变量覆盖（引入顺序不可调整）
import './styles/theme.css'

import App from './App.vue'
import router from './router'

// 启用 Element Plus 深色模式（css-vars.css 依赖 html.dark 选择器）
document.documentElement.classList.add('dark')

const components = [
  ElAlert,
  ElAside,
  ElButton,
  ElCard,
  ElCol,
  ElConfigProvider,
  ElContainer,
  ElDescriptions,
  ElDescriptionsItem,
  ElDivider,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElHeader,
  ElInput,
  ElInputNumber,
  ElMain,
  ElOption,
  ElPagination,
  ElProgress,
  ElRadioButton,
  ElRadioGroup,
  ElRow,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTabPane,
  ElTabs,
  ElTag,
]

const app = createApp({
  // 用 ElConfigProvider 注入中文语言包（当前 EP 版本通过 provide(localeContextKey)
  // 实现国际化，直接 provide('locale', ...) 不会生效）
  render: () => h(ElConfigProvider, { locale: zhCn }, { default: () => h(App) }),
})

components.forEach((component) => app.component(component.name, component))

// v-loading 指令：用 install 注册，保证 ElLoading 拿到 app context
app.use(ElLoading)

app.use(router)
app.mount('#app')
