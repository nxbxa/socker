# -*- coding: utf-8 -*-
"""
评分预测模型模块
================
使用随机森林回归拟合各位置综合评分，并与线性回归基准对比。

建模思路：
- 特征：该位置的评分指标（Per90 原始值）
- 目标：百分位加权综合评分
- 评估：80/20 划分 + 5 折交叉验证（R² / RMSE / MAE）
- 对比：随机森林（非线性） vs 线性回归（线性基准）
- 解释：特征重要性排序，验证评分权重设计的合理性

意义：机器学习模型能够高精度复现综合评分，说明指标体系
对球员能力具有较强的解释力；特征重要性可与人工权重互相印证。
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import KFold, cross_val_score, train_test_split

from football_analysis import config


def _rmse(y_true, y_pred):
    return root_mean_squared_error(y_true, y_pred)


def _get_rf_params(position):
    """获取指定位置的随机森林超参数（GK 单独调参防过拟合）。"""
    if position == "GK":
        return config.RF_PARAMS_GK
    return config.RF_PARAMS


def train_position_model(data, metrics, score_name):
    """训练单个位置的评分预测模型。

    Parameters
    ----------
    data : pd.DataFrame
        该位置的已评分数据。
    metrics : list[str]
        特征列（评分指标原始值）。
    score_name : str
        目标列（综合评分）。

    Returns
    -------
    dict
        模型对象、测试集与交叉验证评估结果、特征重要性、
        测试集预测值（可视化用）。
    """
    position = score_name.split("_")[0]
    rf_params = _get_rf_params(position)

    frame = data.dropna(subset=metrics + [score_name])

    X = frame[metrics].astype(float).values
    y = frame[score_name].astype(float).values

    # ---- 1. 训练 / 测试划分 ----
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=config.TEST_SIZE, random_state=42
    )

    # ---- 2. 随机森林（非线性模型） ----
    forest = RandomForestRegressor(**rf_params)
    forest.fit(X_train, y_train)

    y_pred_forest = forest.predict(X_test)

    forest_test = {
        "r2": round(float(r2_score(y_test, y_pred_forest)), 4),
        "rmse": round(float(_rmse(y_test, y_pred_forest)), 4),
        "mae": round(float(mean_absolute_error(y_test, y_pred_forest)), 4),
    }

    # ---- 3. 线性回归（基准模型） ----
    linear = LinearRegression()
    linear.fit(X_train, y_train)

    y_pred_linear = linear.predict(X_test)

    linear_test = {
        "r2": round(float(r2_score(y_test, y_pred_linear)), 4),
        "rmse": round(float(_rmse(y_test, y_pred_linear)), 4),
        "mae": round(float(mean_absolute_error(y_test, y_pred_linear)), 4),
    }

    # ---- 4. 5 折交叉验证 ----
    kfold = KFold(n_splits=config.CV_FOLDS, shuffle=True, random_state=42)

    cv_scores = cross_val_score(
        RandomForestRegressor(**rf_params), X, y,
        cv=kfold, scoring="r2",
    )

    cv_result = {
        "folds": config.CV_FOLDS,
        "r2_mean": round(float(cv_scores.mean()), 4),
        "r2_std": round(float(cv_scores.std()), 4),
        "r2_folds": [round(float(v), 4) for v in cv_scores],
    }

    # ---- 5. 全量数据重训练（用于在线预测） ----
    final_forest = RandomForestRegressor(**rf_params)
    final_forest.fit(X, y)

    # ---- 6. 特征重要性 ----
    importance = sorted(
        (
            {
                "metric": metric,
                "label": config.METRIC_LABELS.get(metric, metric),
                "importance": round(float(value), 4),
            }
            for metric, value in zip(metrics, final_forest.feature_importances_)
        ),
        key=lambda item: item["importance"],
        reverse=True,
    )

    return {
        "position": position,
        "model": final_forest,
        "metrics": metrics,
        "sample_count": int(len(frame)),
        "forest_test": forest_test,
        "linear_test": linear_test,
        "cv": cv_result,
        "importance": importance,
        "test_actual": [round(float(v), 2) for v in y_test],
        "test_predicted": [round(float(v), 2) for v in y_pred_forest],
    }


def predict_score(model_bundle, metrics_values):
    """使用训练好的模型预测评分。

    Parameters
    ----------
    model_bundle : dict
        train_position_model 的返回值。
    metrics_values : dict[str, float]
        指标名 -> 指标值（Per90 原始尺度）。

    Returns
    -------
    dict
        预测评分、模型评估摘要与输入指标回显。
    """
    metrics = model_bundle["metrics"]

    missing = [m for m in metrics if m not in metrics_values]
    if missing:
        raise ValueError(f"缺少预测所需指标：{missing}")

    X = np.array(
        [[float(metrics_values[m]) for m in metrics]], dtype=float
    )

    prediction = float(model_bundle["model"].predict(X)[0])

    return {
        "position": model_bundle["position"],
        "predicted_score": round(prediction, 2),
        "model_r2": model_bundle["forest_test"]["r2"],
        "input_metrics": {
            m: metrics_values[m] for m in metrics
        },
    }


def build_all_prediction_models(scored_frames):
    """训练全部位置的评分预测模型。

    Returns
    -------
    dict[str, dict]
        位置 -> 模型包（结构见 train_position_model）。
    """
    bundles = {}

    for position, data in scored_frames.items():
        model_config = config.POSITION_MODELS[position]
        bundles[position] = train_position_model(
            data, model_config["metrics"], model_config["score_name"]
        )

    return bundles
