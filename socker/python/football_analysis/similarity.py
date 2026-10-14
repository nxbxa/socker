# -*- coding: utf-8 -*-
"""
相似球员推荐模块
================
基于多维表现指标的余弦相似度，为任意球员推荐最相似的球员。

流程：
1. 在球员主要位置（评分最高的位置）内提取指标矩阵
2. Z-Score 标准化指标（各指标等权参与距离计算）
3. 计算目标球员与全体球员的余弦相似度
4. 返回相似度最高的 N 名球员（球探筛选 / 替补引援场景）
"""

import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from football_analysis import config


class SimilarityEngine:
    """相似球员推荐引擎（启动时构建索引，查询零开销）。"""

    def __init__(self, scored_frames):
        """
        Parameters
        ----------
        scored_frames : dict[str, pd.DataFrame]
            位置 -> 已评分数据（来自 scoring.build_all_scores）。
        """
        self._index = {}

        for position, data in scored_frames.items():
            metrics = config.POSITION_MODELS[position]["metrics"]

            valid = data.dropna(subset=metrics).copy()

            # Z-Score 标准化（均值方差存入索引，保证查询向量同尺度）
            means = valid[metrics].mean()
            stds = valid[metrics].std().replace(0, 1)

            matrix = (valid[metrics] - means) / stds
            similarity = cosine_similarity(matrix.values)

            self._index[position] = {
                "players": valid["Player"].tolist(),
                "metrics": metrics,
                "matrix": matrix.values,
                "similarity": similarity,
                "frame": valid.reset_index(drop=True),
                "means": means,
                "stds": stds,
            }

    def get_primary_position(self, player_name):
        """返回球员的主要位置（评分最高的位置）。

        多位置球员（如 "FW,MF"）会在多个位置有评分，
        取评分最高的位置作为主要位置进行相似度计算。
        """
        best_position = None
        best_score = -1.0

        for position, index in self._index.items():
            frame = index["frame"]
            rows = frame[frame["Player"] == player_name]

            if rows.empty:
                continue

            score = rows[
                config.POSITION_MODELS[position]["score_name"]
            ].max()

            if score > best_score:
                best_score = score
                best_position = position

        if best_position is None:
            raise LookupError(f"未找到球员：{player_name}")

        return best_position

    def find_similar(self, player_name, n=10, position=None):
        """查找与指定球员最相似的 N 名球员。

        Parameters
        ----------
        player_name : str
            目标球员姓名。
        n : int
            返回相似球员数量。
        position : str, optional
            指定在某个位置内查找；缺省时自动使用球员主要位置。

        Returns
        -------
        dict
            目标球员信息、主要位置、相似球员列表（含相似度与关键指标）。
        """
        if position is None:
            position = self.get_primary_position(player_name)

        index = self._index.get(position)
        if index is None:
            raise LookupError(f"无效位置：{position}")

        players = index["players"]
        if player_name not in players:
            raise LookupError(
                f"球员 {player_name} 在位置 {position} 无完整指标数据"
            )

        target_idx = players.index(player_name)
        score_name = config.POSITION_MODELS[position]["score_name"]

        # 相似度排序（排除自身）
        similarities = index["similarity"][target_idx]
        ranked = sorted(
            enumerate(similarities), key=lambda item: item[1], reverse=True
        )
        ranked = [(i, s) for i, s in ranked if players[i] != player_name]

        target_row = index["frame"].iloc[target_idx]
        metrics = index["metrics"]

        similar_players = []
        for idx, sim in ranked[:n]:
            row = index["frame"].iloc[idx]

            similar_players.append({
                "player": row["Player"],
                "position": row["Pos"],
                "nation": row.get("Nation"),
                "nation_flag": row.get("Nation_Flag"),
                "squads": row.get("Squads", ""),
                "age": None if pd.isna(row["Age"]) else int(row["Age"]),
                "minutes": float(row["Min"]),
                "score": float(row[score_name]),
                "similarity": round(float(sim), 4),
                "metrics": {
                    metric: None
                    if pd.isna(row[metric]) else float(row[metric])
                    for metric in metrics
                },
            })

        return {
            "player": player_name,
            "position": position,
            "position_label": config.POSITION_MODELS[position]["chinese_name"],
            "target": {
                "position": target_row["Pos"],
                "nation": target_row.get("Nation"),
                "nation_flag": target_row.get("Nation_Flag"),
                "squads": target_row.get("Squads", ""),
                "age": None
                if pd.isna(target_row["Age"]) else int(target_row["Age"]),
                "minutes": float(target_row["Min"]),
                "score": float(target_row[score_name]),
                "metrics": {
                    metric: None
                    if pd.isna(target_row[metric]) else float(target_row[metric])
                    for metric in metrics
                },
            },
            "similar_players": similar_players,
        }
