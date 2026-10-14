# -*- coding: utf-8 -*-
"""
全局配置模块
============
集中管理：
1. 数据与输出文件路径
2. 数据筛选阈值
3. 各位置评分模型的指标与权重
4. 聚类、预测模型超参数
5. 指标中文名称映射（用于 API 输出与图表展示）
"""

from pathlib import Path

# ============================================================
# 1. 路径配置（基于本文件位置定位，与运行时工作目录无关）
# ============================================================

PACKAGE_DIR = Path(__file__).resolve().parent          # football_analysis/
PYTHON_DIR = PACKAGE_DIR.parent                        # python/
PROJECT_ROOT = PYTHON_DIR.parent                       # 项目根目录
DATA_DIR = PROJECT_ROOT / "data"
FIGURE_DIR = DATA_DIR / "figures"

INPUT_FILE = DATA_DIR / "players_data_light-2024_2025.csv"

PLAYER_CLUB_FILE = DATA_DIR / "player_club.csv"
PLAYER_SUMMARY_FILE = DATA_DIR / "player_summary.csv"
VALIDATION_FILE = DATA_DIR / "model_validation.csv"
SENSITIVITY_FILE = DATA_DIR / "model_sensitivity.csv"
CLUSTER_FILE = DATA_DIR / "player_clusters.csv"
PREDICTION_FILE = DATA_DIR / "model_prediction.csv"

POSITION_SCORE_FILES = {
    "FW": DATA_DIR / "fw_player_score.csv",
    "MF": DATA_DIR / "mf_player_score.csv",
    "DF": DATA_DIR / "df_player_score.csv",
    "GK": DATA_DIR / "gk_player_score.csv",
}

# ============================================================
# 2. 数据筛选与出场时间分组
# ============================================================

# 最低出场时间（分钟）：过滤出场过少导致指标不稳定的球员
MIN_MINUTES = 450

MIN_GROUP_BINS = [449, 900, 1500, 2250, float("inf")]
MIN_GROUP_LABELS = ["450-900", "900-1500", "1500-2250", "2250+"]

# ============================================================
# 3. 原始字段重命名（FBref 导出的特殊字段名 -> 友好名）
# ============================================================

RENAME_COLUMNS = {
    # 控球 / 防守对抗
    "Att_stats_possession": "DribAtt",       # 尝试过人次数
    "Att_stats_defense": "DefAtt",           # 防守对抗次数
    "Lost_stats_misc": "DuelLost",           # 对抗失败次数
    # 门将（原始百分比字段不参与汇总，汇总后依据计数字段重算）
    "PSxG+/-": "PSxGD",                      # 赛季累计 PSxG - GA
    "Save%": "SavePctRaw",
    "CS%": "CSPctRaw",
    "Stp%": "StpPctRaw",
    "Cmp_stats_keeper_adv": "GKCmp",         # 门将成功传球数
    "Att_stats_keeper_adv": "GKAtt",         # 门将传球尝试数
    "Cmp%_stats_keeper_adv": "GKCmpPctRaw",
}

# ============================================================
# 4. 数值字段定义
# ============================================================

# 计数类字段：参与按球员汇总（转会球员多条记录求和）
NUMERIC_COLUMNS = [
    # 出场
    "MP", "Starts", "Min", "90s",
    # 进攻
    "Gls", "Ast", "G-PK", "PK", "PKatt", "xG", "npxG", "xAG",
    # 射门
    "Sh", "SoT",
    # 传球
    "Cmp", "Att", "PrgP", "KP",
    # 防守
    "Tkl", "TklW", "Lost", "Int", "Tkl+Int", "Clr",
    # 控球
    "Touches", "Carries", "PrgC", "Succ", "Tkld",
    # 对抗与过人
    "Won", "Recov", "DribAtt", "DefAtt", "DuelLost",
    # 门将
    "GA", "SoTA", "Saves", "CS", "PSxG", "PSxGD",
    "Stp", "Opp", "GKCmp", "GKAtt",
]

# 基础信息字段（非数值，汇总时取首条/合并）
REQUIRED_COLUMNS = [
    "Player", "Nation", "Pos", "Age", "Born", "Squad",
] + NUMERIC_COLUMNS

# 参与 Per90 标准化的字段（总量 / 出场分钟 × 90）
PER90_COLUMNS = [
    # 进攻
    "Gls", "Ast", "xG", "xAG",
    # 射门
    "Sh", "SoT",
    # 传球
    "Cmp", "PrgP", "KP",
    # 防守
    "Tkl", "TklW", "Int", "Clr",
    # 控球
    "Touches", "Carries", "PrgC", "Succ",
    # 杂项
    "Recov", "Won",
    # 门将
    "Saves", "SoTA",
]

# ============================================================
# 5. 位置评分模型：指标与权重（权重总和为 1）
# ============================================================

POSITION_MODELS = {
    "FW": {
        "score_name": "FW_Score",
        "chinese_name": "前锋",
        "metrics": [
            "Gls_90", "xG_90", "SoT_90", "Ast_90",
            "xAG_90", "G/Sh", "Succ_90",
        ],
        "weights": {
            "Gls_90": 0.25,
            "xG_90": 0.15,
            "SoT_90": 0.15,
            "Ast_90": 0.15,
            "xAG_90": 0.10,
            "G/Sh": 0.10,
            "Succ_90": 0.10,
        },
    },
    "MF": {
        "score_name": "MF_Score",
        "chinese_name": "中场",
        "metrics": [
            "Gls_90", "Ast_90", "xAG_90", "Cmp_90", "PrgP_90",
            "KP_90", "Tkl_90", "Int_90", "Succ_90",
        ],
        "weights": {
            "Gls_90": 0.10,
            "Ast_90": 0.15,
            "xAG_90": 0.15,
            "Cmp_90": 0.10,
            "PrgP_90": 0.15,
            "KP_90": 0.10,
            "Tkl_90": 0.10,
            "Int_90": 0.05,
            "Succ_90": 0.10,
        },
    },
    "DF": {
        "score_name": "DF_Score",
        "chinese_name": "后卫",
        "metrics": [
            "Tkl_90", "TklW_90", "Int_90", "Clr_90", "Won_90",
            "Cmp_90", "Carries_90", "PrgC_90", "Succ_90",
        ],
        "weights": {
            "Tkl_90": 0.15,
            "TklW_90": 0.10,
            "Int_90": 0.15,
            "Clr_90": 0.15,
            "Won_90": 0.15,
            "Cmp_90": 0.10,
            "Carries_90": 0.05,
            "PrgC_90": 0.10,
            "Succ_90": 0.05,
        },
    },
    "GK": {
        "score_name": "GK_Score",
        "chinese_name": "门将",
        "metrics": [
            "SavePct", "PSxGD_90", "CSPct", "StpPct", "GKCmpPct",
        ],
        "weights": {
            "SavePct": 0.25,
            "PSxGD_90": 0.25,
            "CSPct": 0.20,
            "StpPct": 0.15,
            "GKCmpPct": 0.15,
        },
    },
}

# 敏感性分析备选权重方案（每位置 3 套，权重总和均为 1）
SENSITIVITY_SCHEMES = {
    "FW": [
        # 方案1：降低进球指标影响
        {"Gls_90": 0.20, "xG_90": 0.20, "SoT_90": 0.15, "Ast_90": 0.15,
         "xAG_90": 0.10, "G/Sh": 0.10, "Succ_90": 0.10},
        # 方案2：加强创造能力
        {"Gls_90": 0.20, "xG_90": 0.15, "SoT_90": 0.10, "Ast_90": 0.20,
         "xAG_90": 0.15, "G/Sh": 0.10, "Succ_90": 0.10},
        # 方案3：加强效率与突破
        {"Gls_90": 0.20, "xG_90": 0.15, "SoT_90": 0.10, "Ast_90": 0.15,
         "xAG_90": 0.10, "G/Sh": 0.15, "Succ_90": 0.15},
    ],
    "MF": [
        # 方案1：加强进攻创造
        {"Gls_90": 0.15, "Ast_90": 0.20, "xAG_90": 0.20, "Cmp_90": 0.10,
         "PrgP_90": 0.10, "KP_90": 0.10, "Tkl_90": 0.05, "Int_90": 0.05,
         "Succ_90": 0.05},
        # 方案2：加强组织能力
        {"Gls_90": 0.05, "Ast_90": 0.15, "xAG_90": 0.15, "Cmp_90": 0.15,
         "PrgP_90": 0.20, "KP_90": 0.10, "Tkl_90": 0.10, "Int_90": 0.05,
         "Succ_90": 0.05},
        # 方案3：加强防守
        {"Gls_90": 0.10, "Ast_90": 0.10, "xAG_90": 0.10, "Cmp_90": 0.10,
         "PrgP_90": 0.10, "KP_90": 0.05, "Tkl_90": 0.20, "Int_90": 0.10,
         "Succ_90": 0.15},
    ],
    "DF": [
        # 方案1：加强防守
        {"Tkl_90": 0.20, "TklW_90": 0.15, "Int_90": 0.20, "Clr_90": 0.15,
         "Won_90": 0.10, "Cmp_90": 0.05, "Carries_90": 0.05, "PrgC_90": 0.05,
         "Succ_90": 0.05},
        # 方案2：加强传球和推进
        {"Tkl_90": 0.10, "TklW_90": 0.10, "Int_90": 0.10, "Clr_90": 0.10,
         "Won_90": 0.10, "Cmp_90": 0.15, "Carries_90": 0.10, "PrgC_90": 0.15,
         "Succ_90": 0.10},
        # 方案3：加强身体对抗
        {"Tkl_90": 0.10, "TklW_90": 0.10, "Int_90": 0.10, "Clr_90": 0.10,
         "Won_90": 0.25, "Cmp_90": 0.10, "Carries_90": 0.05, "PrgC_90": 0.05,
         "Succ_90": 0.15},
    ],
    "GK": [
        # 方案1：加强扑救
        {"SavePct": 0.35, "PSxGD_90": 0.25, "CSPct": 0.20, "StpPct": 0.10,
         "GKCmpPct": 0.10},
        # 方案2：加强出球
        {"SavePct": 0.20, "PSxGD_90": 0.20, "CSPct": 0.15, "StpPct": 0.15,
         "GKCmpPct": 0.30},
        # 方案3：加强稳定性
        {"SavePct": 0.20, "PSxGD_90": 0.35, "CSPct": 0.25, "StpPct": 0.10,
         "GKCmpPct": 0.10},
    ],
}

# ============================================================
# 6. 聚类与预测模型超参数
# ============================================================

CLUSTER_K_RANGE = range(3, 6)      # 候选簇数：3 / 4 / 5
CLUSTER_RANDOM_STATE = 42

RF_PARAMS = {
    "n_estimators": 300,
    "max_depth": 8,
    "min_samples_leaf": 3,
    "random_state": 42,
}

# GK 单独调参（经网格搜索确定：max_depth × min_samples_leaf 组合）：
# GK 样本量少（约 150 人）且评分由百分位加权和构成（非线性强），
# 树需要更细的叶子才能拟合；过大的 min_samples_leaf 会导致欠拟合
# （测试集 R² 反而低于线性回归基准）
RF_PARAMS_GK = {
    "n_estimators": 300,
    "max_depth": 8,
    "min_samples_leaf": 1,
    "random_state": 42,
}

CV_FOLDS = 5
TEST_SIZE = 0.2

# ============================================================
# 7. 雷达图维度定义（每维度 = 维度内指标百分位的均值）
# ============================================================

# 非门将球员：六维通用能力模型
RADAR_DIMENSIONS_FIELD = {
    "进攻": ["Gls_90", "xG_90", "Sh_90"],
    "创造": ["Ast_90", "xAG_90", "KP_90"],
    "组织": ["Cmp_90", "PrgP_90"],
    "盘带": ["Succ_90", "PrgC_90"],
    "防守": ["Tkl_90", "Int_90", "Clr_90"],
    "对抗": ["Won_90", "Recov_90"],
}

# 门将：六维门将能力模型
RADAR_DIMENSIONS_GK = {
    "扑救": ["SavePct"],
    "稳定": ["PSxGD_90"],
    "零封": ["CSPct"],
    "制空": ["StpPct"],
    "出球": ["GKCmpPct"],
    "活跃": ["Saves_90", "SoTA_90"],
}

# ============================================================
# 8. 指标中文名称映射（用于 API 输出、聚类命名、图表展示）
# ============================================================

METRIC_LABELS = {
    # 出场
    "MP": "出场场次", "Starts": "首发场次", "Min": "出场时间", "90s": "90分钟场次",
    # 进攻
    "Gls": "进球", "Ast": "助攻", "G+A": "进球+助攻", "G-PK": "非点球进球",
    "PK": "点球进球", "PKatt": "点球尝试", "xG": "预期进球", "npxG": "非点球预期进球",
    "xAG": "预期助攻",
    # 射门
    "Sh": "射门", "SoT": "射正", "SoT%": "射正率", "G/Sh": "每次射门进球率",
    "G/SoT": "每次射正进球率",
    # 传球
    "Cmp": "成功传球", "Att": "传球尝试", "Cmp%": "传球成功率", "PrgP": "推进传球",
    "KP": "关键传球",
    # 防守
    "Tkl": "抢断", "TklW": "抢断成功", "Int": "拦截", "Tkl+Int": "抢断+拦截",
    "Clr": "解围", "Lost": "被过次数", "DefAtt": "防守对抗",
    # 控球
    "Touches": "触球", "Carries": "持球推进", "PrgC": "带球推进", "Succ": "成功过人",
    "Succ%": "过人成功率", "Tkld": "被抢断", "DribAtt": "尝试过人",
    # 对抗与杂项
    "Won": "对抗成功", "DuelLost": "对抗失败", "WonPct": "对抗成功率", "Recov": "球权回收",
    # 门将
    "GA": "失球", "SoTA": "面对射门", "Saves": "扑救", "SavePct": "扑救成功率",
    "CS": "零封场次", "CSPct": "零封率", "PSxG": "扑救预期进球", "PSxGD": "扑救贡献",
    "PSxGD_90": "每90分钟扑救贡献", "Stp": "拦截传中", "Opp": "面对传中",
    "StpPct": "传中拦截率", "GKCmp": "门将成功传球", "GKAtt": "门将传球尝试",
    "GKCmpPct": "门将传球成功率",
    # Per90 指标（聚类 / 相似推荐 / 雷达图使用）
    "Gls_90": "进球", "Ast_90": "助攻", "xG_90": "预期进球", "xAG_90": "预期助攻",
    "Sh_90": "射门", "SoT_90": "射正", "Cmp_90": "传球", "PrgP_90": "推进传球",
    "KP_90": "关键传球", "Tkl_90": "抢断", "TklW_90": "抢断成功", "Int_90": "拦截",
    "Clr_90": "解围", "Won_90": "对抗", "Carries_90": "持球推进",
    "PrgC_90": "带球推进", "Succ_90": "过人", "Recov_90": "球权回收",
    "Touches_90": "触球", "Saves_90": "扑救", "SoTA_90": "面对射门",
}

# 基础信息字段中文名
BASIC_LABELS = {
    "Player": "球员", "Nation": "国籍", "Pos": "位置", "Age": "年龄",
    "Born": "出生年份", "Squads": "效力俱乐部", "Min_Group": "出场时间分组",
}
