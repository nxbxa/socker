# 足球球员表现可视化预测系统

基于 FBref 2024–2025 赛季比赛数据的三层架构球员分析平台：**综合评分 → 聚类分型 → 相似球员推荐 → 评分预测**。

---

## 目录

- [系统架构](#系统架构)
- [快速启动](#快速启动)
- [功能模块](#功能模块)
- [接口文档](#接口文档)
- [算法说明](#算法说明)
- [项目结构](#项目结构)
- [常见问题](#常见问题)

---

## 系统架构

```
┌─────────────────────┐      ┌──────────────────────┐      ┌────────────────────────┐
│  Vue 3 前端          │      │  Spring Boot 网关     │      │  Flask 分析服务         │
│  127.0.0.1:5173     │ ───► │  127.0.0.1:8080      │ ───► │  127.0.0.1:5000        │
│                     │ /api │                      │ /api │                        │
│  · ECharts 6 图表    │      │  · 统一转发层          │      │  · 评分模型             │
│  · Element Plus     │      │  · 全局异常处理        │      │  · K-Means 聚类 + PCA   │
│  · vue-router       │      │  · 超时与错误映射      │      │  · 余弦相似度检索        │
│                     │      │  · CORS              │      │  · 随机森林回归          │
└─────────────────────┘      └──────────────────────┘      └────────────────────────┘
   Vite 开发代理转发           纯转发，不做业务处理            启动时训练模型并缓存到内存
```

**为什么用三层而不是两层？**

前端不直接访问 Python，而是统一走 Java 网关。好处是：

- 前端只需知道一个地址，Python 服务的迁移/扩容对前端透明
- 跨域、鉴权、限流、日志等横切关注点集中在网关层处理
- Python 侧专注于算法，不必关心 HTTP 语义细节

**统一响应格式**（三层一致，前端拦截器按此解包）：

```json
{ "code": 200, "message": "success", "data": { } }
```

错误时 `code` 为 HTTP 状态码，`message` 为人类可读的中文原因，`data` 为 `null`。

---

## 快速启动

### 前置要求

| 组件 | 版本要求 | 本项目验证版本 |
|---|---|---|
| JDK | 21+ | 21.0.8 |
| Maven | 3.9+ | 3.9.11 |
| Node.js | 20+ | 24.17.0 |
| Python | 3.11+ | 3.13.0（项目 venv） |

### 1. 启动 Python 分析服务（必须先启动）

分析服务在启动时会读取 CSV 并**同步训练 4 个位置的随机森林模型**，首次启动约需数秒。

```powershell
cd D:\PythonProject\socker\python
& ..\.venv\Scripts\python.exe app.py
```

看到 `Running on http://127.0.0.1:5000` 即成功。验证：

```powershell
curl http://127.0.0.1:5000/api/health
```

### 2. 启动 Spring Boot 网关

```powershell
cd D:\xiangmu\socker\socker
mvn spring-boot:run
```

> **若提示无法解析 `spring-boot-starter-parent:4.1.1`**：本机 Maven 全局配置把仓库镜像到了
> alimaven，而本地缓存的构件来源标记为 `central`，导致离线模式（`-o`）不认。
> 使用项目自带的 `settings-local.xml` 绕过（该文件不含 mirror）：
> ```powershell
> mvn -s settings-local.xml spring-boot:run
> ```
> 联网状态下直接 `mvn spring-boot:run` 也可正常工作。

### 3. 启动前端

```powershell
cd D:\xiangmu\socker\socker\socker-frontend
npm install     # 首次
npm run dev
```

浏览器自动打开 <http://127.0.0.1:5173>。

### 启动顺序的重要性

**Python 必须先启动。** 如果先启动前端，页面顶栏会显示「分析服务离线」，各页面显示
明确的错误提示而不是空白页 —— 这是本期健壮性改造的结果（改造前会返回 Spring 的
HTML 错误页，前端只能提示"网络错误"）。

### 端口占用排查

```powershell
Get-NetTCPConnection -LocalPort 5000,8080,5173 -State Listen |
  Select-Object LocalPort, OwningProcess
```

---

## 功能模块

| 页面 | 路由 | 数据来源 | 说明 |
|---|---|---|---|
| 数据仪表盘 | `/dashboard` | `/api/dashboard` | KPI 总览、各位置 TOP5、位置分布、评分分布、模型性能、聚类概览 |
| 球员列表 | `/players` | `/api/players` | 全量 2702 名球员，支持位置/俱乐部/姓名筛选与全库排序分页 |
| 球员详情 | `/players/:name` | `/api/players/<name>` + `/api/compare` | 六维雷达、各位置评分与排名、相似球员、六维明细、分组指标明细 |
| 球员对比 | `/compare` | `/api/compare` | 任选两名球员逐维度对比，支持 URL 分享与一键交换 |
| 评分排行榜 | `/rankings` | `/api/rankings` | TOP3 领奖台、TOP10 条形图、完整榜单（评分色阶） |
| 聚类分型 | `/clusters` | `/api/clusters` | PCA 散点分布、K 值选择曲线、簇画像、成员明细 |
| 相似球员探索 | `/similar` | `/api/similar` | 相似度—实力二维分布，跨位置检索同风格球员 |
| 评分预测 | `/predict` | `/api/models` + `/api/meta` + `/api/predict` | 指标输入（带单位/范围/权重提示）、预测结果百分位、模型评估全貌 |

---

## 接口文档

所有接口经 Java 网关（`8080`）暴露，Python 侧的路径与之完全一致。

### 1. `GET /api/health`

健康检查。返回服务状态、数据规模、各位置合格球员数、所用算法。

### 2. `GET /api/players`

球员列表（分页 + 筛选 + 排序）。

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页条数（1–100） |
| `position` | string | — | 位置模糊匹配，如 `FW` / `MF` / `DF` / `GK` |
| `club` | string | — | 俱乐部名模糊匹配（不区分大小写） |
| `search` | string | — | 球员姓名模糊匹配（不区分大小写） |
| `order` | string | `Best_Score` | 排序字段，白名单：`Best_Score` `Min` `Gls` `Ast` `G+A` `Age` `MP` `FW_Score` `MF_Score` `DF_Score` `GK_Score` |
| `direction` | string | `desc` | `asc` / `desc` |

响应 `data`：`{ total, page, page_size, items[] }`

### 3. `GET /api/players/<name>`

球员详情。

| 参数 | 默认 | 说明 |
|---|---|---|
| `similar_n` | 5 | 相似球员数量（1–20） |

响应 `data`：`{ basic, metric_groups[], metrics[], scores[], best_position, cluster, similar_players[] }`

### 4. `GET /api/rankings`

位置排行榜。

| 参数 | 默认 | 说明 |
|---|---|---|
| `position` | `FW` | 位置代码 |
| `limit` | 20 | 返回条数（1–100） |

响应 `data`：`{ position, position_label, total_players, items[] }`

### 5. `GET /api/clusters`

聚类分型结果。参数 `position`（默认 `FW`）。

响应 `data`：`{ position, position_label, k, silhouette, k_selection[], explained_variance[], profiles[], points[] }`

- `k_selection`：`[{ k, silhouette }]`，用于绘制 K 值选择曲线
- `points`：每名球员的 `pc1` / `pc2` / `cluster` / `cluster_name` / `score`
- `profiles`：每簇的 `name` / `size` / `avg_score` / `top_metrics[]`（含 `z_diff` 标准差偏移）

### 6. `GET /api/similar`

相似球员推荐。

| 参数 | 默认 | 说明 |
|---|---|---|
| `player` | **必填** | 球员姓名 |
| `n` | 10 | 返回条数（1–50） |
| `position` | — | 限定位置（不传则跨位置检索） |

响应 `data`：`{ player, position, position_label, target, similar_players[] }`

### 7. `GET /api/compare`

双人雷达对比。参数 `player1`、`player2`（均必填）。

> 传相同的两个名字，即得到单人六维数据（球员详情页的雷达图用此方式获取）。

响应 `data`：`{ player1, player2, is_goalkeeper_comparison, dimensions[], summary }`

- 门将对门将时自动切换为门将专用维度模型（扑救/稳定/零封/制空/出球/活跃）
- 非门将维度：进攻 / 创造 / 组织 / 盘带 / 防守 / 对抗

### 8. `GET /api/models`

各位置预测模型评估结果：`sample_count`、`metrics[]`、`forest_test`、`linear_test`、`cv`、`importance[]`。

### 9. `POST /api/predict`

评分预测。

请求体：

```json
{
  "position": "FW",
  "metrics": {
    "Gls_90": 0.65, "xG_90": 0.58, "SoT_90": 1.45, "Ast_90": 0.28,
    "xAG_90": 0.25, "G/Sh": 0.15, "Succ_90": 1.6
  }
}
```

响应 `data`：`{ position, predicted_score, model_r2, input_metrics }`

**各位置所需指标**（缺任意一项返回 400）：

| 位置 | 指标 |
|---|---|
| FW | `Gls_90` `xG_90` `SoT_90` `Ast_90` `xAG_90` `G/Sh` `Succ_90` |
| MF | `Gls_90` `Ast_90` `xAG_90` `Cmp_90` `PrgP_90` `KP_90` `Tkl_90` `Int_90` `Succ_90` |
| DF | `Tkl_90` `TklW_90` `Int_90` `Clr_90` `Won_90` `Cmp_90` `Carries_90` `PrgC_90` `Succ_90` |
| GK | `SavePct` `PSxGD_90` `CSPct` `StpPct` `GKCmpPct` |

> ⚠️ **门将指标的尺度与场上球员不同**：`SavePct` / `CSPct` / `StpPct` / `GKCmpPct`
> 是 0–100 的百分数（填 `72.5`，不是 `0.725`）；`PSxGD_90` 是可为负的每 90 分钟值。

### 10. `GET /api/dashboard`

看板汇总：`players_total`、`qualified_total`、`transfer_players`、`position_distribution[]`、`top5_by_position[]`、`score_distribution[]`、`cluster_overview[]`、`model_metrics[]`。

### 11. `GET /api/meta`

元信息：`positions`（每位置的评分列名、中文名、指标及**权重**）、`radar_dimensions_field`、`radar_dimensions_gk`、`metric_labels`（字段→中文名映射）、`min_minutes`。

---

## 算法说明

### 数据来源

FBref 2024–2025 赛季球员比赛数据（`players_data_light-2024_2025.csv`），
经特征工程汇总为 2702 名球员的赛季数据。

**合格球员门槛**：出场时间 ≥ **450 分钟**（`config.MIN_MINUTES`）。

- 按球员去重：**1958 人**合格（占全量 2702 人的 72.5%）
- 按位置统计（一人可满足多个位置，故合计大于去重人数）：
  前锋 653 / 中场 910 / 后卫 817 / 门将 154

### 综合评分：百分位标准化 + 加权求和

```
1. 各指标在位置内计算百分位（0–100），消除量纲差异
2. 按人工设定的权重加权求和 -> 综合评分（0–100）
3. 权重总和校验必须为 1，否则启动报错
```

各位置权重示例（前锋）：进球 25% / xG 15% / 射正 15% / 助攻 15% / xAG 10% / 转化率 10% / 过人 10%。

**优点**：对异常值稳健，且评分天然可解释（"你的进球数超过了 92% 的同位置球员"）。

### 聚类分型：K-Means + PCA

- 候选 K 为 3 / 4 / 5，用**轮廓系数**自动选择最优 K
- 每人取簇内指标 Z-Score 均值最高的 2 项作为该簇的标签依据
- PCA 降到 2 维用于可视化，同时输出前两个主成分的解释方差比

### 相似球员：Z-Score + 余弦相似度

在位置内对指标做 Z-Score 标准化后计算余弦相似度，避免量纲与绝对水平干扰"风格"的判断。

### 评分预测：随机森林回归

- 特征为该位置的评分指标（Per90 原始值），目标为综合评分
- 80/20 划分测试集 + 5 折交叉验证
- 与线性回归基准对比，并通过**特征重要性**印证人工权重设计的合理性
- 门将单独调参（`min_samples_leaf=1`）：样本量少且评分非线性强，树需要更细的叶子

**各位置测试集 R²**（实测）：

| 位置 | 随机森林 R² | 训练样本 |
|---|---|---|
| 前锋 FW | 0.9721 | 653 |

> R² 接近 1 是符合预期的：目标变量由指标加权求和构造而来，模型是在"反向还原"
> 一个确定性的评分函数。其价值在于**验证指标体系的自洽性**，并给出特征重要性排序。

---

## 项目结构

```
socker/                                   # 本仓库（Java + 前端）
├── pom.xml
├── settings-local.xml                    # 离线构建用 Maven 配置（见「快速启动」）
├── docs/
│   └── 项目体检报告.md                     # 全量代码审查与优化清单
├── src/main/java/com/example/socker/
│   ├── SockerApplication.java
│   ├── client/PythonApiClient.java       # Python 服务客户端（RestClient + 超时）
│   ├── config/
│   │   ├── CorsConfig.java               # 跨域配置
│   │   ├── HttpClientConfig.java         # RestClient 与超时策略
│   │   └── PythonApiProperties.java      # Python 服务地址（可外部配置）
│   ├── controller/ApiController.java     # 11 个接口的统一转发层
│   └── exception/
│       ├── GlobalExceptionHandler.java   # 全局异常 -> 统一 JSON
│       ├── PythonServiceException.java   # 上游 4xx/5xx
│       └── PythonServiceUnavailableException.java  # 上游不可达
├── src/main/resources/application.properties
└── socker-frontend/                      # Vue 3 前端
    ├── vite.config.js                    # 代理、别名、手动分包
    └── src/
        ├── main.js                       # Element Plus 按需注册
        ├── App.vue                       # 应用壳（侧边导航 + 顶栏）
        ├── api/request.js                # axios 封装与错误映射
        ├── router/index.js               # 路由表 + 标题守卫 + 404 兜底
        ├── styles/theme.css              # 设计令牌 + 全局样式 + EP 深色覆盖
        ├── theme/echarts.js              # ECharts 统一深色主题
        ├── utils/format.js               # 数值格式化（含空值保护）
        ├── icons/index.js                # 内联 SVG 图标库
        ├── components/                   # BaseChart / StatCard / PageHeader / ErrorState / AppIcon
        └── views/                        # 8 个页面

D:\PythonProject\socker\                  # Python 分析服务（独立目录）
├── data/                                 # CSV 数据与图表输出
│   ├── players_data_light-2024_2025.csv
│   ├── player_summary.csv
│   ├── player_clusters.csv
│   └── figures/
└── python/
    ├── app.py                            # Flask 入口（11 个接口）
    ├── run_analysis.py                   # 离线批量分析
    ├── requirements.txt
    └── football_analysis/
        ├── config.py                     # 位置模型、权重、雷达维度、指标中文名
        ├── data_loader.py                # 数据加载
        ├── features.py                   # 特征工程、Per90 派生
        ├── scoring.py                    # 百分位加权评分
        ├── clustering.py                 # K-Means + PCA
        ├── similarity.py                 # 余弦相似度检索
        ├── prediction.py                 # 随机森林回归
        ├── comparison.py                 # 六维雷达对比
        ├── visualization.py              # 静态图表导出
        └── pipeline.py                   # 管线编排（进程内单例）
```

---

## 常见问题

### 页面显示「分析服务离线」/ 提示"分析服务暂时不可用"

Python 服务没启动或已崩溃。检查：

```powershell
curl http://127.0.0.1:5000/api/health
```

### 接口返回 503 并提示确认 Python 服务

这是**预期行为**（本期改造结果）。之前这种情况下前端只能看到"网络错误"，
现在会明确告知是哪一层出了问题。若 Python 确实在运行，检查 `application.properties`
里的 `python.api.base-url` 是否与实际地址一致。

### `http://127.0.0.1:5173` 打不开，但 `localhost:5173` 可以

Node 17+ 下 `localhost` 可能只解析到 IPv6 的 `::1`。本项目已在 `vite.config.js`
中显式设置 `host: '127.0.0.1'` 修复此问题。

### Maven 报无法解析 `spring-boot-starter-parent:4.1.1`

见「快速启动」第 2 步，使用 `mvn -s settings-local.xml ...`。

### 修改了后端接口但前端拿不到新字段

Java 层是**纯字符串透传**，不需要改 Java 代码；但前端需要同步调整字段引用。
若新增的是 `el-` 组件，记得在 `src/main.js` 的 `components` 数组和样式引入列表中
补充，否则模板中的 `<el-xxx>` 会静默不渲染。

### 前端构建产物怎么部署

当前 `dist/` 未被 Spring Boot 托管（默认静态目录是 `src/main/resources/static`）。
三种方案：

1. 改 `vite.config.js` 的 `build.outDir` 指向 `../src/main/resources/static`（最简单）
2. 用 `frontend-maven-plugin` 在 Maven 构建时自动构建并拷贝
3. 生产用 Nginx 托管静态文件并反向代理 `/api`

注意 SPA 使用 history 路由，生产环境需配置 fallback 到 `index.html`。

---

## 技术栈版本

**后端**：Spring Boot 4.1.1 / Java 21 / Tomcat 11 / Maven 3.9.11

**前端**：Vue 3.5.41 / vue-router 5.2.0 / Element Plus 2.14.5 / ECharts 6.1.0 / Vite 8.2.2 / axios 1.19

**分析服务**：Python 3.13 / Flask 3.1.3 / scikit-learn 1.9.0 / pandas 3.0.5 / NumPy 2.5.2
