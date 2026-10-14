# -*- coding: utf-8 -*-
"""
球员聚类分型模块
================
基于 K-Means 聚类对同位置球员进行风格分型。

流程：
1. 提取该位置评分指标，Z-Score 标准化（消除量纲差异）
2. 遍历候选簇数 K，以轮廓系数（Silhouette）择优
3. PCA 降到二维，生成可视化坐标
4. 依据簇内指标均值与全体均值的标准差差异，自动为簇命名

用途：识别"高产终结型前锋""组织型中场""拦截型后卫"等风格类型。
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from football_analysis import config


def _select_best_k(X, k_range, random_state):
    """遍历候选簇数，返回轮廓系数最优的 KMeans 模型与评估记录。"""
    records = []
    best_model = None
    best_score = -1.0

    for k in k_range:
        model = KMeans(
            n_clusters=k,
            n_init=10,
            random_state=random_state,
        )
        labels = model.fit_predict(X)

        score = silhouette_score(X, labels)
        records.append({"k": int(k), "silhouette": round(float(score), 4)})

        if score > best_score:
            best_score = score
            best_model = model

    return best_model, records


def _describe_cluster(z_means, metric_labels):
    """依据簇内标准化均值差异为簇自动命名。

    取相对全体均值高出最多的两个维度拼接为类型名；
    若所有维度均低于平均，则命名为"均衡角色型"。
    """
    ranked = sorted(z_means.items(), key=lambda item: item[1], reverse=True)

    top_positive = [(m, v) for m, v in ranked if v > 0]

    if not top_positive:
        return "均衡角色型", []

    top_metrics = top_positive[:2]
    name = "·".join(
        metric_labels.get(m, m) for m, _ in top_metrics
    ) + "型"

    return name, top_metrics


def cluster_position(data, metrics, score_name, k_range=None, random_state=None):
    """对单个位置的球员执行聚类分型。

    Parameters
    ----------
    data : pd.DataFrame
        该位置的合格球员数据（须包含 metrics 全部指标）。
    metrics : list[str]
        参与聚类的指标列名。
    score_name : str
        该位置的综合评分列名（用于簇画像中的平均评分）。

    Returns
    -------
    dict
        包含聚类结果数据（含 Cluster / PC1 / PC2 列）、
        最优 K、轮廓系数、各簇画像与选 K 记录。
    """
    k_range = k_range or config.CLUSTER_K_RANGE
    random_state = (
        config.CLUSTER_RANDOM_STATE if random_state is None else random_state
    )

    # 指标完整的球员才参与聚类
    cluster_data = data.dropna(subset=metrics).copy()
    cluster_data["Score"] = cluster_data[score_name]

    X = cluster_data[metrics].astype(float).values

    # Z-Score 标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 选 K 并聚类
    best_model, k_records = _select_best_k(X_scaled, k_range, random_state)
    labels = best_model.labels_
    k = int(best_model.n_clusters)
    silhouette = silhouette_score(X_scaled, labels)

    # PCA 降至二维（聚类可视化坐标）
    pca = PCA(n_components=2, random_state=random_state)
    coords = pca.fit_transform(X_scaled)

    cluster_data["Cluster"] = labels
    cluster_data["PC1"] = np.round(coords[:, 0], 4)
    cluster_data["PC2"] = np.round(coords[:, 1], 4)

    # 簇画像：各指标均值（原始值）与相对全体的标准化差异
    overall_std = cluster_data[metrics].std()
    overall_mean = cluster_data[metrics].mean()

    profiles = []
    for cluster_id in range(k):
        members = cluster_data[cluster_data["Cluster"] == cluster_id]

        # 簇内均值相对全体均值的标准差差异（>0 表示高于平均水平）
        z_means = {
            metric: float(
                (members[metric].mean() - overall_mean[metric])
                / overall_std[metric]
            )
            for metric in metrics
        }

        name, top_metrics = _describe_cluster(
            z_means, config.METRIC_LABELS
        )

        profile = {
            "cluster": cluster_id,
            "name": name,
            "size": int(len(members)),
            "avg_score": round(float(members["Score"].mean()), 2),
            "top_metrics": [
                {
                    "metric": metric,
                    "label": config.METRIC_LABELS.get(metric, metric),
                    "z_diff": round(value, 3),
                }
                for metric, value in top_metrics
            ],
            "metric_means": {
                metric: round(float(members[metric].mean()), 3)
                for metric in metrics
            },
        }
        profiles.append(profile)

    # 簇按规模降序重编号（簇 0 = 最大簇），便于前端展示稳定
    profiles_sorted = sorted(profiles, key=lambda p: p["size"], reverse=True)
    remap = {p["cluster"]: new_id for new_id, p in enumerate(profiles_sorted)}

    cluster_data["Cluster"] = cluster_data["Cluster"].map(remap)
    for new_id, p in enumerate(profiles_sorted):
        p["cluster"] = new_id

    return {
        "data": cluster_data,
        "k": k,
        "silhouette": round(float(silhouette), 4),
        "k_records": k_records,
        "profiles": profiles_sorted,
        "scaler": scaler,
        "pca": pca,
        "explained_variance": [
            round(float(v), 4) for v in pca.explained_variance_ratio_
        ],
    }


def build_all_clusters(scored_frames):
    """对全部位置执行聚类分型。

    Parameters
    ----------
    scored_frames : dict[str, pd.DataFrame]
        位置 -> 已评分数据（来自 scoring.build_all_scores）。

    Returns
    -------
    dict[str, dict]
        位置 -> 聚类结果（结构见 cluster_position）。
    """
    results = {}

    for position, data in scored_frames.items():
        model_config = config.POSITION_MODELS[position]
        results[position] = cluster_position(
            data, model_config["metrics"], model_config["score_name"]
        )

    return results
