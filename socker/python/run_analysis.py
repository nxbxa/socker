# -*- coding: utf-8 -*-
"""
离线批处理入口
==============
执行完整分析管线并输出：

数据文件（CSV）：
    1. player_club.csv            球员-俱乐部明细（原始字段）
    2. player_summary.csv         球员赛季汇总（含全部派生指标）
    3. fw/mf/df/gk_player_score.csv  各位置评分结果（含聚类标签）
    4. player_clusters.csv        聚类分型结果（PCA 坐标 + 簇画像）
    5. model_validation.csv       模型验证（相关性 + 聚类 + 预测指标）
    6. model_prediction.csv       预测模型评估详情
    7. model_sensitivity.csv      敏感性分析（TOP20 重合率）

论文图表（PNG，data/figures/）：
    评分分布 / TOP10 / 出场时间关系 / 敏感性 /
    聚类散点 / 特征重要性 / 预测对比 / 雷达图示例

用法：
    python run_analysis.py
"""

import pandas as pd

from football_analysis import config
from football_analysis.pipeline import AnalysisPipeline
from football_analysis.scoring import calculate_weighted_score
from football_analysis.visualization import plot_all


def print_section(title):
    """打印章节分隔标题。"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


# ============================================================
# 敏感性分析
# ============================================================

def top20_players(data, score):
    """获取评分前 20 的球员集合。"""
    return set(data.assign(_score=score).nlargest(20, "_score")["Player"])


def run_sensitivity_analysis(scored_frames):
    """不同权重方案下的 TOP20 重合率分析。

    判断标准：
    - TOP20 重合率 >= 80%   模型具有较高稳定性
    - TOP20 重合率 60%~80%  模型具有一定稳定性
    - TOP20 重合率 < 60%    模型对权重变化比较敏感，需要进一步研究
    """
    results = []

    for position, data in scored_frames.items():
        base_weights = config.POSITION_MODELS[position]["weights"]
        schemes = config.SENSITIVITY_SCHEMES[position]

        base_top20 = top20_players(
            data, calculate_weighted_score(data, base_weights)
        )

        for i, scheme in enumerate(schemes, 1):
            scheme_top20 = top20_players(
                data, calculate_weighted_score(data, scheme)
            )

            overlap = len(base_top20 & scheme_top20) / 20 * 100

            results.append({
                "Position": position,
                "Scheme": f"{position}_Scheme{i}",
                "Top20_Overlap": round(overlap, 2),
            })

    return pd.DataFrame(results)


# ============================================================
# 输出数据文件
# ============================================================

def save_data_files(pipeline, sensitivity_df):
    """输出全部 CSV 数据文件。"""
    print_section("输出数据文件")

    # 1. 球员-俱乐部明细（原始字段）
    pipeline.player_club.to_csv(
        config.PLAYER_CLUB_FILE, index=False, encoding="utf-8-sig"
    )
    print(f"保存成功：{config.PLAYER_CLUB_FILE}（{len(pipeline.player_club)} 行）")

    # 2. 球员赛季汇总
    pipeline.summary.to_csv(
        config.PLAYER_SUMMARY_FILE, index=False, encoding="utf-8-sig"
    )
    print(f"保存成功：{config.PLAYER_SUMMARY_FILE}（{len(pipeline.summary)} 行）")

    # 3. 各位置评分结果（含聚类标签）
    result_columns = ["Player", "Nation", "Born", "Age", "Pos", "Squads", "Min"]

    cluster_frames = []

    for position, data in pipeline.scored.items():
        model_config = config.POSITION_MODELS[position]
        score_name = model_config["score_name"]
        metrics = model_config["metrics"]

        cluster_result = pipeline.clusters[position]
        cluster_data = cluster_result["data"]
        profile_map = {
            p["cluster"]: p["name"] for p in cluster_result["profiles"]
        }

        columns = (
            result_columns
            + metrics
            + [col + "_Pct" for col in metrics]
            + [score_name]
        )

        result = data[columns].sort_values(score_name, ascending=False)

        # 附加聚类信息（按球员合并）
        cluster_info = cluster_data[["Player", "Cluster"]].copy()
        cluster_info["Cluster_Name"] = cluster_info["Cluster"].map(profile_map)
        result = result.merge(
            cluster_info, on="Player", how="left"
        )

        file_path = config.POSITION_SCORE_FILES[position]
        result.to_csv(file_path, index=False, encoding="utf-8-sig")
        print(f"保存成功：{file_path}（{len(result)} 行）")

        # 聚类明细（供合并）
        cluster_frames.append(
            cluster_data.assign(
                Position=position,
                Cluster_Name=cluster_data["Cluster"].map(profile_map),
                Score=cluster_data["Score"],
            )[
                [
                    "Player", "Position", "Cluster", "Cluster_Name",
                    "Score", "PC1", "PC2", "Min", "Pos",
                ]
            ].rename(columns={"Pos": "Raw_Position"})
        )

    # 4. 聚类分型结果
    all_clusters = pd.concat(cluster_frames, ignore_index=True)
    all_clusters.to_csv(
        config.CLUSTER_FILE, index=False, encoding="utf-8-sig"
    )
    print(f"保存成功：{config.CLUSTER_FILE}（{len(all_clusters)} 行）")

    # 5. 模型验证（评分与出场时间相关性 + 聚类 + 预测指标）
    validation_rows = []

    for position, data in pipeline.scored.items():
        score_name = config.POSITION_MODELS[position]["score_name"]
        cluster_result = pipeline.clusters[position]
        prediction = pipeline.prediction_models[position]

        correlation = data[[score_name, "Min"]].corr().iloc[0, 1]

        validation_rows.append({
            "Position": position,
            "Player_Count": len(data),
            "Mean_Score": round(data[score_name].mean(), 2),
            "Median_Score": round(data[score_name].median(), 2),
            "Min_Score": round(data[score_name].min(), 2),
            "Max_Score": round(data[score_name].max(), 2),
            "Min_Correlation": round(correlation, 4),
            "Cluster_K": cluster_result["k"],
            "Cluster_Silhouette": cluster_result["silhouette"],
            "RF_Test_R2": prediction["forest_test"]["r2"],
            "RF_CV_R2": prediction["cv"]["r2_mean"],
            "Linear_Test_R2": prediction["linear_test"]["r2"],
        })

    validation_df = pd.DataFrame(validation_rows)
    validation_df.to_csv(
        config.VALIDATION_FILE, index=False, encoding="utf-8-sig"
    )
    print(f"保存成功：{config.VALIDATION_FILE}")
    print("\n模型验证结果：")
    print(validation_df.to_string(index=False))

    # 6. 预测模型评估详情
    prediction_rows = []

    for position, bundle in pipeline.prediction_models.items():
        top_features = "; ".join(
            f"{item['label']}({item['importance']})"
            for item in bundle["importance"][:3]
        )

        prediction_rows.append({
            "Position": position,
            "Sample_Count": bundle["sample_count"],
            "RF_Test_R2": bundle["forest_test"]["r2"],
            "RF_Test_RMSE": bundle["forest_test"]["rmse"],
            "RF_Test_MAE": bundle["forest_test"]["mae"],
            "Linear_Test_R2": bundle["linear_test"]["r2"],
            "Linear_Test_RMSE": bundle["linear_test"]["rmse"],
            "Linear_Test_MAE": bundle["linear_test"]["mae"],
            "CV_R2_Mean": bundle["cv"]["r2_mean"],
            "CV_R2_Std": bundle["cv"]["r2_std"],
            "Top_Features": top_features,
        })

    prediction_df = pd.DataFrame(prediction_rows)
    prediction_df.to_csv(
        config.PREDICTION_FILE, index=False, encoding="utf-8-sig"
    )
    print(f"\n保存成功：{config.PREDICTION_FILE}")
    print("\n评分预测模型评估：")
    print(prediction_df.to_string(index=False))

    # 7. 敏感性分析
    sensitivity_df.to_csv(
        config.SENSITIVITY_FILE, index=False, encoding="utf-8-sig"
    )
    print(f"\n保存成功：{config.SENSITIVITY_FILE}")
    print("\nTOP20 重合率：")
    print(sensitivity_df.to_string(index=False))


# ============================================================
# 主流程
# ============================================================

def main():
    print_section("足球球员数据分析：离线批处理")

    # 1. 构建分析管线
    pipeline = AnalysisPipeline().build()

    print("数据规模：", pipeline.raw.shape)
    print("汇总球员数量：", len(pipeline.summary))

    for position, frame in pipeline.scored.items():
        label = config.POSITION_MODELS[position]["chinese_name"]
        score_name = config.POSITION_MODELS[position]["score_name"]

        cluster_result = pipeline.clusters[position]
        prediction = pipeline.prediction_models[position]

        print(
            f"\n{label}（{position}）：{len(frame)} 名合格球员，"
            f"平均评分 {frame[score_name].mean():.2f}"
        )
        print(
            f"  聚类：K={cluster_result['k']}，"
            f"轮廓系数={cluster_result['silhouette']}"
        )
        for profile in cluster_result["profiles"]:
            print(
                f"    簇{profile['cluster']}：{profile['name']}"
                f"（{profile['size']}人，平均评分 {profile['avg_score']}）"
            )
        print(
            f"  预测模型：测试集 R2={prediction['forest_test']['r2']}，"
            f"交叉验证 R2={prediction['cv']['r2_mean']}，"
            f"线性基准 R2={prediction['linear_test']['r2']}"
        )

    # 2. 敏感性分析
    print_section("敏感性分析")
    sensitivity_df = run_sensitivity_analysis(pipeline.scored)
    print("""
判断标准：
TOP20 重合率 >= 80%    模型具有较高稳定性
TOP20 重合率 60%~80%   模型具有一定稳定性
TOP20 重合率 < 60%     模型对权重变化比较敏感，需要进一步研究
""")

    # 3. 输出数据文件
    save_data_files(pipeline, sensitivity_df)

    # 4. 生成全部图表
    print_section("生成分析图表")
    plot_all(pipeline, sensitivity_df)
    print(f"图表输出目录：{config.FIGURE_DIR}")

    # 5. 完成
    print_section("全部完成")
    print("""
生成的数据文件：
  - player_club.csv / player_summary.csv
  - fw_player_score.csv / mf_player_score.csv
    df_player_score.csv / gk_player_score.csv
  - player_clusters.csv
  - model_validation.csv / model_prediction.csv
  - model_sensitivity.csv

生成的图表（data/figures/）：
  - position_score_distribution.png
  - FW_TOP10.png / MF_TOP10.png / DF_TOP10.png / GK_TOP10.png
  - minutes_score_relationship.png
  - model_sensitivity.png
  - FW_cluster_scatter.png / MF_cluster_scatter.png
    DF_cluster_scatter.png / GK_cluster_scatter.png
  - FW_feature_importance.png / MF_feature_importance.png
    DF_feature_importance.png / GK_feature_importance.png
  - prediction_vs_actual.png
  - radar_example.png
""")


if __name__ == "__main__":
    main()
