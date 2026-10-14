import axios from 'axios'
import { ElMessage } from 'element-plus'

/**
 * 统一请求封装
 * ============
 * 链路：Vue (5173) --/api--> Spring Boot (8080) --转发--> Flask (5000)
 *
 * 后端的统一响应格式为 { code, message, data }：
 *   - code === 200 → 直接返回 data，业务代码无需层层解包
 *   - code !== 200 → 抛出带后端原始 message 的错误
 *
 * 错误分三类，必须有区分度，否则排查问题时完全无从下手：
 *   1. 业务错误：后端明确返回了 code/message
 *   2. HTTP 错误：网关或服务返回了非 2xx 状态码
 *   3. 网络错误：服务没启动 / 断网 / 超时
 */
const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

/** 把各种形态的错误统一转成人类可读的中文提示 */
function toFriendlyMessage(error) {
  // 超时
  if (error.code === 'ECONNABORTED' || /timeout/i.test(error.message || '')) {
    return '请求超时，分析服务可能正在处理大量数据，请稍后重试'
  }

  const response = error.response

  // 没有 response：请求根本没发出去（后端没启动 / 断网）
  if (!response) {
    return '无法连接后端服务，请确认 Spring Boot（8080）已启动'
  }

  const { status, data } = response

  // 后端返回了统一格式的错误体，优先使用它的 message
  if (data && typeof data === 'object' && data.message) {
    return data.message
  }
  if (typeof data === 'string' && data.trim() && !data.trim().startsWith('<')) {
    return data
  }

  // Spring Boot 默认错误页是 HTML，不能直接展示给用户
  const statusText = {
    400: '请求参数有误',
    404: '请求的接口或数据不存在',
    405: '请求方法不被允许',
    500: '后端服务内部错误，请查看 Spring Boot 控制台日志',
    502: '网关无法连接分析服务，请确认 Flask（5000）已启动',
    503: '分析服务暂时不可用',
    504: '分析服务响应超时',
  }

  return statusText[status] || `请求失败（HTTP ${status}）`
}

request.interceptors.response.use(
  (response) => {
    const res = response.data

    // 正常路径：后端统一格式 { code, message, data }
    if (res && typeof res === 'object' && 'code' in res) {
      if (res.code === 200) {
        return res.data
      }
      return Promise.reject(new Error(res.message || '请求失败'))
    }

    // 兜底：后端直接返回了裸数据（如 /api/health 的 health 字段）
    if (res !== undefined && res !== null) {
      return res
    }

    return Promise.reject(new Error('后端返回了空响应'))
  },
  (error) => Promise.reject(new Error(toFriendlyMessage(error)))
)

/**
 * 带全局错误提示的请求方法。
 * 各视图自行处理成功逻辑，失败时统一弹一次 message，避免重复写 try/catch 提示。
 *
 * @param {object} config axios 请求配置
 * @param {string} hint 兜底提示前缀
 */
export async function requestWithTip(config, hint = '数据加载失败') {
  try {
    return await request(config)
  } catch (e) {
    ElMessage.error(e.message && e.message !== hint ? e.message : hint)
    throw e
  }
}

export default request
