# -*- coding: utf-8 -*-
"""
球员对比模块
============
为任意两名球员生成多维能力雷达图对比数据。

维度模型（六维）：
- 场上球员：进攻 / 创造 / 组织 / 盘带 / 防守 / 对抗
- 门将：    扑救 / 稳定 / 零封 / 制空 / 出球 / 活跃

计算方式：
1. 每个维度由若干底层指标构成
2. 各指标在基准群体（合格非门将球员或合格门将）中计算百分位
3. 维度得分 = 维度内各指标百分位的均值（0-100）
4. 百分位基准基于群体而非仅同位置球员，保证跨位置对比语义一致
"""

import numpy as np
import pandas as pd

from football_analysis import config


def _is_goalkeeper(pos_value):
    return "GK" in str(pos_value)


def _player_percentile(base_frame, player_row, metric):
    """计算球员某指标在基准群体中的百分位（0-100）。"""
    series = base_frame[metric].dropna()

    if series.empty or pd.isna(player_row[metric]):
        return None

    return float(
        (series < player_row[metric]).sum() / len(series) * 100
    )


def _dimension_score(base_frame, player_row, dimension_metrics):
    """维度得分 = 维度内各可用指标百分位的均值。"""
    values = []
    details = {}

    for metric in dimension_metrics:
        percentile = _player_percentile(base_frame, player_row, metric)

        if percentile is not None:
            values.append(percentile)

        metric_value = player_row[metric]
        details[metric] = {
            "label": config.METRIC_LABELS.get(metric, metric),
            "value": None if pd.isna(metric_value) else float(metric_value),
            "percentile": percentile,
        }

    score = round(float(np.mean(values)), 2) if values else None

    return score, details


def build_radar_comparison(player1, player2, summary, min_minutes=None):
    """构建两名球员的雷达图对比数据。

    Parameters
    ----------
    player1, player2 : str
        球员姓名。
    summary : pd.DataFrame
        球员赛季汇总数据（来自 features.build_features）。
    min_minutes : int, optional
        合格球员的最低出场时间（百分位基准群体过滤）。

    Returns
    -------
    dict
        两名球员基础信息、六维得分、每维度明细指标、综合优势统计。
    """
    threshold = config.MIN_MINUTES if min_minutes is None else min_minutes

    rows = {}
    for name in [player1, player2]:
        row = summary[summary["Player"] == name]

        if row.empty:
            raise LookupError(f"未找到球员：{name}")

        rows[name] = row.iloc[0]

    # 门将对门将（双方均为门将才用门将维度）
    both_gk = all(
        _is_goalkeeper(rows[name]["Pos"]) for name in [player1, player2]
    )

    dimensions = (
        config.RADAR_DIMENSIONS_GK if both_gk
        else config.RADAR_DIMENSIONS_FIELD
    )

    # 百分位基准群体：合格门将 or 合格非门将
    qualified = summary[summary["Min"] >= threshold]
    base_gk = qualified[qualified["Pos"].str.contains("GK", na=False)]
    base_field = qualified[~qualified["Pos"].str.contains("GK", na=False)]

    base_frame = base_gk if both_gk else base_field

    def player_info(name):
        row = rows[name]
        return {
            "player": name,
            "nation": row["Nation"],
            "position": row["Pos"],
            "squads": row["Squads"],
            "age": None if pd.isna(row["Age"]) else int(row["Age"]),
            "minutes": float(row["Min"]),
            "goals": None if pd.isna(row["Gls"]) else float(row["Gls"]),
            "assists": None if pd.isna(row["Ast"]) else float(row["Ast"]),
        }

    dimension_results = []
    win_counts = {player1: 0, player2: 0}

    for dimension_name, dimension_metrics in dimensions.items():
        score1, details1 = _dimension_score(
            base_frame, rows[player1], dimension_metrics
        )
        score2, details2 = _dimension_score(
            base_frame, rows[player2], dimension_metrics
        )

        diff = None
        if score1 is not None and score2 is not None:
            diff = round(score1 - score2, 2)
            if diff > 0:
                win_counts[player1] += 1
            elif diff < 0:
                win_counts[player2] += 1

        dimension_results.append({
            "name": dimension_name,
            "player1_score": score1,
            "player2_score": score2,
            "diff": diff,
            "player1_metrics": details1,
            "player2_metrics": details2,
        })

    return {
        "player1": player_info(player1),
        "player2": player_info(player2),
        "is_goalkeeper_comparison": both_gk,
        "dimensions": dimension_results,
        "summary": {
            "player1_wins": win_counts[player1],
            "player2_wins": win_counts[player2],
            "total_dimensions": len(dimension_results),
        },
    }
