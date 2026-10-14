# -*- coding: utf-8 -*-
"""
评分模型模块
============
基于"百分位标准化 + 加权综合评分"构建各位置球员评分模型。

评分流程：
1. 删除评分指标缺失的球员
2. 各指标在位置内转换为 0-100 百分位分数
3. 按预设权重加权求和，得到综合评分（0-100）

优势：百分位标准化消除量纲差异，评分结果对异常值稳健。
"""

import numpy as np
import pandas as pd

from football_analysis import config


def percentile_score(series):
    """百分位标准化：转换为 0-100 的百分位分数。"""
    return series.rank(pct=True, method="average") * 100


def check_weights(weights, model_name):
    """校验权重总和是否为 1。"""
    total = sum(weights.values())

    if not np.isclose(total, 1.0):
        raise ValueError(f"{model_name} 权重总和不是 1，当前为：{total}")


def calculate_weighted_score(data, weights):
    """按指标原始列名加权计算综合评分。

    weights 的 key 为指标名（如 "Gls_90"），
    对应的百分位列（"Gls_90_Pct"）参与加权。
    """
    score = pd.Series(0.0, index=data.index)

    for metric, weight in weights.items():
        score += data[metric + "_Pct"] * weight

    return score


def build_score_model(data, model_config):
    """构建单个位置的评分模型。

    Parameters
    ----------
    data : pd.DataFrame
        该位置的合格球员数据。
    model_config : dict
        config.POSITION_MODELS 中该位置的配置
        （包含 metrics、weights、score_name）。

    Returns
    -------
    pd.DataFrame
        增加了各指标百分位列（指标名_Pct）与综合评分列的数据。
    """
    metrics = model_config["metrics"]
    weights = model_config["weights"]
    score_name = model_config["score_name"]

    # 删除评分指标缺失的球员，保证评分可比
    data = data.dropna(subset=metrics).copy()

    # 百分位标准化
    for col in metrics:
        data[col + "_Pct"] = percentile_score(data[col])

    # 权重校验与加权评分
    check_weights(weights, score_name)
    data[score_name] = calculate_weighted_score(data, weights).round(2)

    return data


def build_all_scores(position_frames):
    """对全部位置构建评分模型。

    Parameters
    ----------
    position_frames : dict[str, pd.DataFrame]
        位置 -> 合格球员数据（来自 features.split_by_position）。

    Returns
    -------
    dict[str, pd.DataFrame]
        位置 -> 带评分的数据。
    """
    scored = {}

    for position, data in position_frames.items():
        model_config = config.POSITION_MODELS[position]
        scored[position] = build_score_model(data, model_config)

    return scored
