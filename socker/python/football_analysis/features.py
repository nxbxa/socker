# -*- coding: utf-8 -*-
"""
特征工程模块
============
职责：
1. 按球员汇总赛季数据（转会球员多条记录合并）
2. 计算比例类派生指标（传球成功率、射正率、门将扑救率等）
3. 计算 Per90 标准化指标（消除出场时间差异）
4. 最低出场时间筛选与按位置拆分（FW / MF / DF / GK）
"""

import numpy as np
import pandas as pd

from football_analysis import config


# ------------------------------------------------------------
# 1. 球员-俱乐部明细
# ------------------------------------------------------------

def build_player_club(df):
    """输出球员-俱乐部明细（保留原始字段，每行 = 一条俱乐部记录）。"""
    return df.copy()


# ------------------------------------------------------------
# 2. 按球员汇总赛季数据
# ------------------------------------------------------------

def _merge_positions(series):
    """合并球员的多条位置记录，去重后按字母排序。"""
    positions = set()

    for value in series.dropna():
        for pos in str(value).split(","):
            pos = pos.strip()
            if pos:
                positions.add(pos)

    return ",".join(sorted(positions))


def _merge_squads(series):
    """合并球员效力过的俱乐部，去重后排序。"""
    squads = sorted(set(series.dropna().astype(str)))
    return ",".join(squads)


def _parse_nation(value):
    """解析 FBref 国籍字段。

    原始格式为 "fr FRA"（国旗代码 + 空格 + 三字母国家代码），
    解析为 (国旗代码, 国家代码) 元组；异常格式原样返回。

    Examples
    --------
    "fr FRA" -> ("fr", "FRA")
    "FRA"    -> (None, "FRA")
    """
    if value is None or pd.isna(value):
        return (None, None)

    parts = str(value).strip().split()

    if len(parts) >= 2:
        return (parts[0], parts[1])
    if len(parts) == 1:
        return (None, parts[0])
    return (None, None)


def summarize_players(df):
    """将明细数据汇总为"每球员一行"的赛季数据。

    汇总规则：
    - 数值字段求和（min_count=1：全缺失保持 NaN 而不是 0）
    - 国籍、出生年份取首条；年龄取最大（赛季中长一岁）
    - 位置、俱乐部合并去重
    - 国籍解析为 Nation（三字母代码）+ Nation_Flag（国旗代码）
    """
    # 数值字段汇总
    summary = (
        df.groupby("Player", as_index=False)[config.NUMERIC_COLUMNS]
        .sum(min_count=1)
    )

    # 基础信息
    basic_info = (
        df.groupby("Player")
        .agg({"Nation": "first", "Born": "first", "Age": "max"})
        .reset_index()
    )

    # 国籍解析："fr FRA" -> Nation="FRA", Nation_Flag="fr"
    nation_parsed = basic_info["Nation"].apply(_parse_nation)
    basic_info["Nation_Flag"] = nation_parsed.str[0]
    basic_info["Nation"] = nation_parsed.str[1]

    position_info = (
        df.groupby("Player")["Pos"].apply(_merge_positions).reset_index()
    )
    squad_info = (
        df.groupby("Player")["Squad"].apply(_merge_squads).reset_index()
    )
    squad_info = squad_info.rename(columns={"Squad": "Squads"})

    summary = summary.merge(basic_info, on="Player", how="left")
    summary = summary.merge(position_info, on="Player", how="left")
    summary = summary.merge(squad_info, on="Player", how="left")

    return summary


# ------------------------------------------------------------
# 3. 比例类派生指标
# ------------------------------------------------------------

def calculate_ratio_metrics(summary):
    """在汇总数据上计算比例指标（分母为 0 时置 NaN）。

    包含：
    - 场上球员：传球成功率、射正率、射门/射正转化率、过人/对抗成功率、G+A
    - 门将：扑救成功率、零封率、传中拦截率、门将传球成功率、
            每 90 分钟扑救贡献（PSxGD_90）
    """
    def safe_ratio(numerator, denominator, scale=100.0):
        return numerator / denominator.replace(0, np.nan) * scale

    # ---- 场上球员 ----
    summary["Cmp%"] = safe_ratio(summary["Cmp"], summary["Att"])
    summary["SoT%"] = safe_ratio(summary["SoT"], summary["Sh"])
    summary["G/Sh"] = safe_ratio(summary["Gls"], summary["Sh"], scale=1.0)
    summary["G/SoT"] = safe_ratio(summary["Gls"], summary["SoT"], scale=1.0)
    summary["Succ%"] = safe_ratio(summary["Succ"], summary["DribAtt"])
    summary["WonPct"] = safe_ratio(
        summary["Won"], summary["Won"] + summary["DuelLost"]
    )
    summary["G+A"] = summary["Gls"] + summary["Ast"]

    # ---- 门将 ----
    summary["SavePct"] = safe_ratio(summary["Saves"], summary["SoTA"])
    summary["CSPct"] = safe_ratio(summary["CS"], summary["MP"])
    summary["StpPct"] = safe_ratio(summary["Stp"], summary["Opp"])
    summary["GKCmpPct"] = safe_ratio(summary["GKCmp"], summary["GKAtt"])
    # 每 90 分钟扑救贡献 = (PSxG - GA) / 出场时间 × 90
    summary["PSxGD_90"] = safe_ratio(
        summary["PSxGD"], summary["Min"], scale=90.0
    )

    return summary


# ------------------------------------------------------------
# 4. Per90 标准化指标
# ------------------------------------------------------------

def calculate_per90_metrics(summary):
    """计算 Per90 指标：总量 / 出场分钟 × 90。

    不直接使用原始 90s 字段，避免原始数据四舍五入造成误差。
    """
    minutes = summary["Min"].replace(0, np.nan)

    for col in config.PER90_COLUMNS:
        summary[col + "_90"] = summary[col] * 90 / minutes

    return summary


def finalize_summary(summary):
    """汇总数据收尾：类型转换、无穷值处理、浮点保留两位。"""
    # 年龄、出生年份转可空整数
    for col in ["Age", "Born"]:
        summary[col] = pd.to_numeric(summary[col], errors="coerce").astype("Int64")

    # 无穷值统一处理为 NaN
    summary = summary.replace([np.inf, -np.inf], np.nan)

    # 浮点数保留两位小数
    float_columns = summary.select_dtypes(
        include=["float64", "float32"]
    ).columns
    summary[float_columns] = summary[float_columns].round(2)

    return summary


# ------------------------------------------------------------
# 5. 最低出场时间筛选与按位置拆分
# ------------------------------------------------------------

def split_by_position(summary, min_minutes=None):
    """筛选合格球员并按位置拆分。

    规则：
    - 出场时间 >= MIN_MINUTES 的球员进入分析
    - 多位置球员（如 "FW,MF"）按 contains 规则同时进入对应位置组，
      与原始版本行为一致

    Returns
    -------
    dict[str, pd.DataFrame]
        {"FW": df, "MF": df, "DF": df, "GK": df}，均带 Min_Group 分组列。
    """
    threshold = config.MIN_MINUTES if min_minutes is None else min_minutes

    qualified = summary[summary["Min"] >= threshold].copy()

    def add_min_group(data):
        data = data.copy()
        data["Min_Group"] = pd.cut(
            data["Min"],
            bins=config.MIN_GROUP_BINS,
            labels=config.MIN_GROUP_LABELS,
        )
        return data

    result = {}
    for position in config.POSITION_MODELS:
        subset = qualified[
            qualified["Pos"].str.contains(position, na=False)
        ]
        result[position] = add_min_group(subset)

    return result


def build_features(raw_df):
    """特征工程主入口：明细数据 -> 球员赛季汇总（含全部派生指标）。

    输入为 data_loader.load_raw_data 的返回值
    （已完成字段重命名与数值转换）。

    Returns
    -------
    pd.DataFrame
        每球员一行的赛季汇总数据。
    """
    data = raw_df.copy()

    summary = summarize_players(data)
    summary = calculate_ratio_metrics(summary)
    summary = calculate_per90_metrics(summary)
    summary = finalize_summary(summary)

    return summary
