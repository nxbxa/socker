# -*- coding: utf-8 -*-
"""
数据分析管线模块
================
组装完整分析流程，供 Flask API 与离线批处理复用：

原始数据 -> 特征工程 -> 位置评分 -> 聚类分型 -> 相似索引 -> 评分预测模型

启动时构建一次并缓存（进程内单例），API 查询全部基于内存数据。
"""

import pandas as pd

from football_analysis import config
from football_analysis.clustering import build_all_clusters
from football_analysis.comparison import build_radar_comparison
from football_analysis.data_loader import load_raw_csv, prepare_dataframe
from football_analysis.features import (
    build_features,
    build_player_club,
    split_by_position,
)
from football_analysis.prediction import (
    build_all_prediction_models,
    predict_score,
)
from football_analysis.scoring import build_all_scores
from football_analysis.similarity import SimilarityEngine


class AnalysisPipeline:
    """足球球员数据分析管线。"""

    def __init__(self):
        self.raw = None                    # 分析用明细（重命名后字段名）
        self.player_club = None            # 球员-俱乐部明细（FBref 原始字段名）
        self.summary = None                # 球员赛季汇总
        self.position_frames = None        # {"FW": df, ...} 合格球员分组
        self.scored = None                 # {"FW": df with score, ...}
        self.clusters = None               # {"FW": cluster result, ...}
        self.similarity = None             # SimilarityEngine
        self.prediction_models = None      # {"FW": model bundle, ...}
        self.all_players = None            # 全员大表（多位置评分 + 聚类合并）

    # --------------------------------------------------------
    # 构建管线
    # --------------------------------------------------------

    def build(self, input_file=None):
        """执行完整分析流程。"""
        # 1. 数据加载与特征工程
        # player_club 保留 FBref 原始字段名（明细导出用）；
        # raw 为重命名后的分析用数据
        raw_original = load_raw_csv(input_file)
        self.player_club = build_player_club(raw_original)
        self.raw = prepare_dataframe(raw_original)
        self.summary = build_features(self.raw)

        # 2. 位置拆分与评分
        self.position_frames = split_by_position(self.summary)
        self.scored = build_all_scores(self.position_frames)

        # 3. 聚类分型
        self.clusters = build_all_clusters(self.scored)

        # 4. 相似球员索引
        self.similarity = SimilarityEngine(self.scored)

        # 5. 评分预测模型
        self.prediction_models = build_all_prediction_models(self.scored)

        # 6. 全员大表
        self.all_players = self._build_all_players()

        return self

    # --------------------------------------------------------
    # 全员大表
    # --------------------------------------------------------

    def _build_all_players(self):
        """将各位置评分与聚类结果合并为全员大表（每球员一行）。

        列结构：
        - 基础信息：Player / Nation / Pos / Age / Born / Squads / MP / Min ...
        - 各位置评分：FW_Score / MF_Score / DF_Score / GK_Score
        - 主位置：Best_Position（评分最高的位置）+ Best_Score
        - 聚类类型：主位置对应的聚类类型名（Cluster_Name）
        """
        base_cols = [
            "Player", "Nation", "Nation_Flag", "Pos", "Age", "Born", "Squads",
            "MP", "Min", "Gls", "Ast", "G+A",
        ]
        base_cols = [c for c in base_cols if c in self.summary.columns]

        all_players = self.summary[base_cols].copy()

        score_cols = []

        for position in config.POSITION_MODELS:
            score_name = config.POSITION_MODELS[position]["score_name"]
            score_col = f"{position}_Score"
            score_cols.append(score_col)

            # 评分列
            scores = self.scored[position][["Player", score_name]].copy()
            all_players = all_players.merge(
                scores, on="Player", how="left"
            )

            # 聚类类型列
            cluster_data = self.clusters[position]["data"]
            profile_map = {
                p["cluster"]: p["name"]
                for p in self.clusters[position]["profiles"]
            }
            cluster_col = f"{position}_Cluster"
            clusters = cluster_data[["Player", "Cluster"]].copy()
            clusters[cluster_col] = clusters["Cluster"].map(profile_map)
            all_players = all_players.merge(
                clusters[["Player", cluster_col]], on="Player", how="left"
            )

        # 主位置：评分最高的位置（无任何位置评分的球员为空）
        score_matrix = all_players[score_cols]
        has_score = score_matrix.notna().any(axis=1)

        all_players["Best_Position"] = None
        all_players["Best_Score"] = None

        if has_score.any():
            best_col = score_matrix[has_score].idxmax(axis=1)
            all_players.loc[has_score, "Best_Position"] = (
                best_col.str.split("_").str[0]
            )
            all_players.loc[has_score, "Best_Score"] = (
                score_matrix[has_score].max(axis=1)
            )

        # 主位置聚类类型名
        def _cluster_name(row):
            position = row["Best_Position"]
            if pd.isna(position):
                return None
            return row.get(f"{position}_Cluster")

        all_players["Cluster_Name"] = all_players.apply(
            _cluster_name, axis=1
        )

        return all_players

    # --------------------------------------------------------
    # 查询接口（供 API 调用）
    # --------------------------------------------------------

    def get_position_frame(self, position):
        """获取某位置的已评分数据，无效位置抛出 KeyError。"""
        if position not in self.scored:
            raise KeyError(f"无效位置：{position}（可选：{list(self.scored)}）")
        return self.scored[position]

    def find_player_summary(self, player_name):
        """在汇总数据中查找球员，未找到返回 None。"""
        rows = self.summary[self.summary["Player"] == player_name]
        return rows.iloc[0] if not rows.empty else None

    def get_player_scores(self, player_name):
        """获取球员在各位置的评分与聚类信息。"""
        rows = self.all_players[
            self.all_players["Player"] == player_name
        ]
        return rows.iloc[0] if not rows.empty else None

    def get_player_cluster(self, player_name):
        """获取球员主位置的聚类详情（PCA 坐标、类型名）。"""
        scores = self.get_player_scores(player_name)

        if scores is None or pd.isna(scores["Best_Position"]):
            return None

        position = scores["Best_Position"]
        cluster_data = self.clusters[position]["data"]
        rows = cluster_data[cluster_data["Player"] == player_name]

        if rows.empty:
            return None

        row = rows.iloc[0]
        profiles = self.clusters[position]["profiles"]
        profile = next(
            (p for p in profiles if p["cluster"] == int(row["Cluster"])), None
        )

        return {
            "position": position,
            "position_label": config.POSITION_MODELS[position]["chinese_name"],
            "cluster": int(row["Cluster"]),
            "cluster_name": row["Cluster_Name"]
            if "Cluster_Name" in row and not pd.isna(row["Cluster_Name"])
            else (profile["name"] if profile else None),
            "pc1": float(row["PC1"]),
            "pc2": float(row["PC2"]),
            "k": self.clusters[position]["k"],
            "silhouette": self.clusters[position]["silhouette"],
            "profile": profile,
        }

    def find_similar(self, player_name, n=10, position=None):
        """相似球员推荐（委托 SimilarityEngine）。"""
        return self.similarity.find_similar(player_name, n=n, position=position)

    def compare_players(self, player1, player2):
        """球员雷达图对比（委托 comparison 模块）。"""
        return build_radar_comparison(player1, player2, self.summary)

    def predict(self, position, metrics_values):
        """评分预测（委托 prediction 模块）。"""
        if position not in self.prediction_models:
            raise KeyError(f"无效位置：{position}")
        return predict_score(
            self.prediction_models[position], metrics_values
        )


# ------------------------------------------------------------
# 进程内单例
# ------------------------------------------------------------

_pipeline_instance = None


def get_pipeline():
    """获取管线单例（首次调用时构建）。"""
    global _pipeline_instance

    if _pipeline_instance is None:
        _pipeline_instance = AnalysisPipeline().build()

    return _pipeline_instance
