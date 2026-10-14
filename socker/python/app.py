# -*- coding: utf-8 -*-
"""
Flask API 服务入口
==================
为 Java 后端提供数据分析 REST 接口（前后端分离架构中的算法服务层）。

启动方式：
    python app.py
服务地址：
    http://127.0.0.1:5000

接口一览：
    GET  /api/health            健康检查（服务状态 + 数据规模）
    GET  /api/players           球员列表（分页 + 筛选 + 排序）
    GET  /api/players/<name>    球员详情（指标 + 评分 + 聚类 + 相似推荐）
    GET  /api/rankings          位置评分排行榜
    GET  /api/clusters          聚类分型结果（PCA 散点 + 簇画像）
    GET  /api/similar           相似球员推荐
    GET  /api/compare           球员雷达图对比
    GET  /api/models            评分预测模型评估结果
    POST /api/predict           评分预测（输入指标）
    GET  /api/dashboard         看板汇总数据
    GET  /api/meta              位置模型元数据（指标 + 权重 + 中文标签）

统一响应格式：
    {"code": 200, "message": "success", "data": ...}
"""

import math

import numpy as np
import pandas as pd
from flask import Flask, jsonify, request

from football_analysis import config
from football_analysis.pipeline import get_pipeline

app = Flask(__name__)

# 服务启动时构建分析管线（进程内缓存，查询零开销）
pipeline = get_pipeline()


# ============================================================
# 工具函数
# ============================================================

def json_safe(value):
    """递归转换为 JSON 可序列化值（NaN / NA / Inf -> None）。"""
    if value is None or value is pd.NA:
        return None
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else value
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
        return None if math.isnan(value) or math.isinf(value) else value
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def ok(data):
    """成功响应。"""
    return jsonify({"code": 200, "message": "success", "data": json_safe(data)})


def fail(message, code=400):
    """失败响应。"""
    return jsonify({"code": code, "message": str(message), "data": None}), code


def frame_records(frame):
    """DataFrame -> JSON 安全的记录列表。"""
    return json_safe(frame.to_dict(orient="records"))


def get_int_arg(name, default, minimum=1, maximum=100):
    """解析整型查询参数（带范围限制）。"""
    try:
        value = int(request.args.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


# ============================================================
# CORS（前后端分离跨域支持）
# ============================================================

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


# ============================================================
# 1. 健康检查
# ============================================================

@app.route("/api/health")
def health():
    data = {
        "status": "running",
        "players_total": int(len(pipeline.summary)),
        "qualified_by_position": {
            position: int(len(frame))
            for position, frame in pipeline.scored.items()
        },
        "positions": list(config.POSITION_MODELS.keys()),
        "algorithms": {
            "scoring": "百分位标准化 + 加权综合评分",
            "clustering": "K-Means + PCA",
            "similarity": "Z-Score + 余弦相似度",
            "prediction": "随机森林回归",
        },
    }
    return ok(data)


# ============================================================
# 2. 球员列表（分页 + 筛选 + 排序）
# ============================================================

SORTABLE_COLUMNS = {
    "Best_Score", "Min", "Gls", "Ast", "G+A", "Age", "MP",
    "FW_Score", "MF_Score", "DF_Score", "GK_Score",
}


@app.route("/api/players")
def players():
    frame = pipeline.all_players

    # 位置筛选（按球员原始位置模糊匹配，如 FW 匹配 "FW,MF"）
    position = request.args.get("position")
    if position:
        frame = frame[frame["Pos"].str.contains(position, na=False)]

    # 俱乐部筛选
    club = request.args.get("club")
    if club:
        frame = frame[
            frame["Squads"].str.contains(club, case=False, na=False)
        ]

    # 姓名搜索
    search = request.args.get("search")
    if search:
        frame = frame[
            frame["Player"].str.contains(search, case=False, na=False)
        ]

    # 排序
    order_by = request.args.get("order", "Best_Score")
    if order_by not in SORTABLE_COLUMNS:
        return fail(f"非法排序字段：{order_by}，可选：{sorted(SORTABLE_COLUMNS)}")
    direction = request.args.get("direction", "desc")
    frame = frame.sort_values(
        order_by,
        ascending=(direction == "asc"),
        na_position="last",
    )

    # 分页
    total = int(len(frame))
    page = get_int_arg("page", 1)
    page_size = get_int_arg("page_size", 20, minimum=1, maximum=100)

    start = (page - 1) * page_size
    items = frame.iloc[start:start + page_size]

    return ok({
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": frame_records(items),
    })


# ============================================================
# 3. 球员详情
# ============================================================

# 指标分组（球员详情页按分组渲染，避免 60+ 项平铺）
METRIC_GROUPS = {
    "出场": ["MP", "Starts", "Min"],
    "进攻": ["Gls", "Ast", "G+A", "xG", "xAG"],
    "射门": ["Sh", "SoT", "SoT%", "G/Sh", "G/SoT"],
    "传球": ["Cmp", "Att", "Cmp%", "PrgP", "KP"],
    "防守": ["Tkl", "TklW", "Int", "Clr"],
    "控球与对抗": [
        "Touches", "Carries", "PrgC", "Succ", "DribAtt", "Succ%",
        "Won", "DuelLost", "WonPct", "Recov",
    ],
    "门将": [
        "GA", "SoTA", "Saves", "SavePct", "CS", "CSPct",
        "PSxGD", "PSxGD_90", "Stp", "Opp", "StpPct", "GKCmpPct",
    ],
    "场均效率(Per90)": [
        "Gls_90", "Ast_90", "xG_90", "xAG_90", "Sh_90", "SoT_90",
        "KP_90", "PrgP_90", "Tkl_90", "Int_90", "Succ_90",
    ],
}

# 平铺指标清单（兼容旧版前端 / 简单渲染场景）
DETAIL_METRICS = [
    metric for metrics in METRIC_GROUPS.values() for metric in metrics
]


@app.route("/api/players/<player_name>")
def player_detail(player_name):
    row = pipeline.find_player_summary(player_name)

    if row is None:
        return fail(f"未找到球员：{player_name}", 404)

    # 基础信息（Nation 已解析为三字母代码，Nation_Flag 为国旗代码）
    basic = {
        "player": row["Player"],
        "nation": row.get("Nation"),
        "nation_flag": row.get("Nation_Flag"),
        "position": row["Pos"],
        "age": row["Age"],
        "born": row["Born"],
        "squads": row["Squads"],
    }

    # 指标分组（每组含中文名与指标明细）
    metric_groups = []
    for group_name, group_metrics in METRIC_GROUPS.items():
        items = [
            {
                "name": metric,
                "label": config.METRIC_LABELS.get(metric, metric),
                "value": row.get(metric),
            }
            for metric in group_metrics
            if metric in row.index
        ]
        if items:
            metric_groups.append({"group": group_name, "metrics": items})

    # 各位置评分与排名
    scores = []
    scores_row = pipeline.get_player_scores(player_name)

    for position in config.POSITION_MODELS:
        score_col = f"{position}_Score"

        if scores_row is None or pd.isna(scores_row.get(score_col)):
            continue

        position_frame = pipeline.scored[position]
        score_name = config.POSITION_MODELS[position]["score_name"]
        # 竞赛排名法：并列同分同名次，下一名跳号
        # （与体育榜单惯例一致；scored 数据无 NaN 评分）
        rank = int(
            (position_frame[score_name] > scores_row[score_col]).sum() + 1
        )

        scores.append({
            "position": position,
            "position_label": config.POSITION_MODELS[position]["chinese_name"],
            "score": scores_row[score_col],
            "rank": rank,
            "total": int(len(position_frame)),
        })

    # 聚类信息
    cluster = pipeline.get_player_cluster(player_name)

    # 相似球员推荐（数量可通过 similar_n 参数调整，默认 5）
    similar_n = get_int_arg("similar_n", 5, minimum=1, maximum=20)
    try:
        similar = pipeline.find_similar(player_name, n=similar_n)
        similar_brief = [
            {
                "player": item["player"],
                "position": item["position"],
                "nation": item.get("nation"),
                "similarity": item["similarity"],
                "score": item["score"],
                "squads": item["squads"],
            }
            for item in similar["similar_players"]
        ]
    except (LookupError, KeyError):
        similar_brief = []

    return ok({
        "basic": basic,
        "metric_groups": metric_groups,
        "metrics": [
            {
                "name": metric,
                "label": config.METRIC_LABELS.get(metric, metric),
                "value": row.get(metric),
            }
            for metric in DETAIL_METRICS
            if metric in row.index
        ],
        "scores": scores,
        "best_position": None if scores_row is None
        else scores_row["Best_Position"],
        "cluster": cluster,
        "similar_players": similar_brief,
    })


# ============================================================
# 4. 位置评分排行榜
# ============================================================

@app.route("/api/rankings")
def rankings():
    position = request.args.get("position", "FW")

    try:
        frame = pipeline.get_position_frame(position)
    except KeyError as exc:
        return fail(exc, 404)

    limit = get_int_arg("limit", 20, minimum=1, maximum=100)
    score_name = config.POSITION_MODELS[position]["score_name"]
    metrics = config.POSITION_MODELS[position]["metrics"]

    ranked = frame.sort_values(score_name, ascending=False).head(limit)

    items = []
    for rank, (_, row) in enumerate(ranked.iterrows(), start=1):
        items.append({
            "rank": rank,
            "player": row["Player"],
            "nation": row.get("Nation"),
            "nation_flag": row.get("Nation_Flag"),
            "position": row["Pos"],
            "squads": row.get("Squads", ""),
            "age": row["Age"],
            "minutes": row["Min"],
            "score": row[score_name],
            "metrics": {metric: row[metric] for metric in metrics},
        })

    return ok({
        "position": position,
        "position_label": config.POSITION_MODELS[position]["chinese_name"],
        "total_players": int(len(frame)),
        "items": items,
    })


# ============================================================
# 5. 聚类分型结果
# ============================================================

@app.route("/api/clusters")
def clusters():
    position = request.args.get("position", "FW")

    try:
        result = pipeline.clusters[position]
    except KeyError:
        return fail(
            f"无效位置：{position}（可选：{list(pipeline.clusters)}）", 404
        )

    data = result["data"]
    score_name = config.POSITION_MODELS[position]["score_name"]
    profile_map = {p["cluster"]: p["name"] for p in result["profiles"]}

    points = [
        {
            "player": row["Player"],
            "position": row["Pos"],
            "squads": row.get("Squads", ""),
            "minutes": row["Min"],
            "score": row[score_name],
            "cluster": int(row["Cluster"]),
            "cluster_name": profile_map[int(row["Cluster"])],
            "pc1": row["PC1"],
            "pc2": row["PC2"],
        }
        for _, row in data.iterrows()
    ]

    return ok({
        "position": position,
        "position_label": config.POSITION_MODELS[position]["chinese_name"],
        "k": result["k"],
        "silhouette": result["silhouette"],
        "k_selection": result["k_records"],
        "explained_variance": result["explained_variance"],
        "profiles": result["profiles"],
        "points": points,
    })


# ============================================================
# 6. 相似球员推荐
# ============================================================

@app.route("/api/similar")
def similar():
    player_name = request.args.get("player")

    if not player_name:
        return fail("缺少参数：player")

    n = get_int_arg("n", 10, minimum=1, maximum=50)
    position = request.args.get("position")

    try:
        result = pipeline.find_similar(player_name, n=n, position=position)
    except LookupError as exc:
        return fail(exc, 404)
    except KeyError as exc:
        return fail(exc, 404)

    return ok(result)


# ============================================================
# 7. 球员雷达图对比
# ============================================================

@app.route("/api/compare")
def compare():
    player1 = request.args.get("player1")
    player2 = request.args.get("player2")

    if not player1 or not player2:
        return fail("缺少参数：player1 / player2")

    try:
        result = pipeline.compare_players(player1, player2)
    except LookupError as exc:
        return fail(exc, 404)

    return ok(result)


# ============================================================
# 8. 评分预测模型评估
# ============================================================

@app.route("/api/models")
def models():
    result = {}

    for position, bundle in pipeline.prediction_models.items():
        result[position] = {
            "position": position,
            "position_label": config.POSITION_MODELS[position]["chinese_name"],
            "sample_count": bundle["sample_count"],
            "metrics": bundle["metrics"],
            "forest_test": bundle["forest_test"],
            "linear_test": bundle["linear_test"],
            "cv": bundle["cv"],
            "importance": bundle["importance"],
        }

    return ok(result)


# ============================================================
# 9. 评分预测（POST）
# ============================================================

@app.route("/api/predict", methods=["POST", "OPTIONS"])
def predict():
    if request.method == "OPTIONS":
        return jsonify({"code": 200, "message": "success", "data": None})

    body = request.get_json(silent=True)

    if not body:
        return fail("请求体必须为 JSON 格式")

    position = body.get("position")
    metrics_values = body.get("metrics")

    if not position or position not in pipeline.prediction_models:
        return fail(
            f"无效位置：{position}（可选：{list(pipeline.prediction_models)}）"
        )

    if not isinstance(metrics_values, dict) or not metrics_values:
        return fail("metrics 必须为非空对象（指标名 -> 指标值）")

    try:
        result = pipeline.predict(position, metrics_values)
    except (ValueError, TypeError) as exc:
        return fail(exc)

    return ok(result)


# ============================================================
# 10. 看板汇总数据
# ============================================================

@app.route("/api/dashboard")
def dashboard():
    summary = pipeline.summary
    all_players = pipeline.all_players

    # 位置分布（合格球员按位置统计）
    position_distribution = [
        {
            "position": position,
            "position_label": config.POSITION_MODELS[position]["chinese_name"],
            "count": int(len(pipeline.scored[position])),
        }
        for position in config.POSITION_MODELS
    ]

    # 各位置 TOP5
    top5_by_position = []
    for position in config.POSITION_MODELS:
        score_name = config.POSITION_MODELS[position]["score_name"]
        top5 = pipeline.scored[position].sort_values(
            score_name, ascending=False
        ).head(5)

        top5_by_position.append({
            "position": position,
            "position_label": config.POSITION_MODELS[position]["chinese_name"],
            "players": [
                {
                    "player": row["Player"],
                    "nation": row.get("Nation"),
                    "nation_flag": row.get("Nation_Flag"),
                    "age": row.get("Age"),
                    "score": row[score_name],
                    "squads": row.get("Squads", ""),
                }
                for _, row in top5.iterrows()
            ],
        })

    # 评分分布（每位置 10 个分箱）
    score_distribution = []
    for position in config.POSITION_MODELS:
        score_name = config.POSITION_MODELS[position]["score_name"]
        scores = pipeline.scored[position][score_name].dropna()

        counts, bin_edges = np.histogram(scores, bins=10)

        score_distribution.append({
            "position": position,
            "position_label": config.POSITION_MODELS[position]["chinese_name"],
            "bins": [round(float(v), 1) for v in bin_edges],
            "counts": [int(v) for v in counts],
        })

    # 聚类概览
    cluster_overview = [
        {
            "position": position,
            "position_label": config.POSITION_MODELS[position]["chinese_name"],
            "k": result["k"],
            "silhouette": result["silhouette"],
            "clusters": [
                {"name": profile["name"], "size": profile["size"]}
                for profile in result["profiles"]
            ],
        }
        for position, result in pipeline.clusters.items()
    ]

    # 预测模型指标概览
    model_metrics = [
        {
            "position": position,
            "forest_r2": bundle["forest_test"]["r2"],
            "linear_r2": bundle["linear_test"]["r2"],
            "cv_r2": bundle["cv"]["r2_mean"],
        }
        for position, bundle in pipeline.prediction_models.items()
    ]

    # 转会球员（赛季中效力多支俱乐部）
    transfer_players = int(
        all_players["Squads"].str.contains(",", na=False).sum()
    )

    return ok({
        "players_total": int(len(summary)),
        # 合格球员：出场时间 >= 最低出场时间阈值（与分位置统计同口径）
        "qualified_total": int(
            (summary["Min"] >= config.MIN_MINUTES).sum()
        ),
        "transfer_players": transfer_players,
        "position_distribution": position_distribution,
        "top5_by_position": top5_by_position,
        "score_distribution": score_distribution,
        "cluster_overview": cluster_overview,
        "model_metrics": model_metrics,
    })


# ============================================================
# 11. 位置模型元数据（指标 + 权重 + 中文标签）
# ============================================================

@app.route("/api/meta")
def meta():
    positions = {}

    for position, model_config in config.POSITION_MODELS.items():
        positions[position] = {
            "score_name": model_config["score_name"],
            "position_label": model_config["chinese_name"],
            "metrics": [
                {
                    "name": metric,
                    "label": config.METRIC_LABELS.get(metric, metric),
                    "weight": model_config["weights"][metric],
                }
                for metric in model_config["metrics"]
            ],
        }

    return ok({
        "positions": positions,
        "radar_dimensions_field": config.RADAR_DIMENSIONS_FIELD,
        "radar_dimensions_gk": config.RADAR_DIMENSIONS_GK,
        "metric_labels": config.METRIC_LABELS,
        "min_minutes": config.MIN_MINUTES,
    })


# ============================================================
# 全局错误处理
# ============================================================

@app.errorhandler(404)
def not_found(_):
    return fail("接口不存在", 404)


@app.errorhandler(500)
def internal_error(exc):
    return fail(f"服务器内部错误：{exc}", 500)


if __name__ == "__main__":
    print("=" * 60)
    print("足球球员数据分析服务")
    print("=" * 60)
    print("接口文档地址：http://127.0.0.1:5000/api/health")
    print("服务启动中...")
    app.run(host="127.0.0.1", port=5000, debug=False)
