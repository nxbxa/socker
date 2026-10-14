# -*- coding: utf-8 -*-
"""
可视化模块
==========
生成论文与答辩用分析图表（中文支持，300 DPI PNG）。

图表清单：
1. 各位置评分分布箱线图
2. 各位置评分 TOP10 横向条形图
3. 出场时间与评分关系散点图
4. 敏感性分析分组条形图
5. 聚类结果 PCA 散点图（按位置）
6. 预测模型特征重要性条形图（按位置）
7. 预测值 vs 实际值散点图
8. 球员对比雷达图示例
"""

import os

import matplotlib

# 无界面绘图模式，只生成并保存图片
matplotlib.use("Agg")

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from football_analysis import config

# ------------------------------------------------------------
# 中文字体配置
# ------------------------------------------------------------

_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\NotoSansSC-VF.ttf",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
]

_font_configured = False


def setup_font():
    """配置中文字体（多次调用安全）。"""
    global _font_configured

    if _font_configured:
        return

    for font_path in _FONT_CANDIDATES:
        if os.path.exists(font_path):
            fm.fontManager.addfont(font_path)
            plt.rcParams["font.family"] = (
                fm.FontProperties(fname=font_path).get_name()
            )
            break
    else:
        print("警告：未找到中文字体，图表中文可能显示为方块")

    plt.rcParams["axes.unicode_minus"] = False
    _font_configured = True


def save_figure(filename):
    """保存当前图表到图片目录。"""
    os.makedirs(config.FIGURE_DIR, exist_ok=True)
    plt.tight_layout()
    plt.savefig(
        os.path.join(config.FIGURE_DIR, filename), dpi=300
    )
    plt.close()


# ------------------------------------------------------------
# 1. 各位置评分分布（箱线图）
# ------------------------------------------------------------

def plot_score_distribution(scored_frames):
    setup_font()

    plt.figure(figsize=(10, 6))

    labels, values = [], []
    for position in config.POSITION_MODELS:
        score_name = config.POSITION_MODELS[position]["score_name"]
        labels.append(position)
        values.append(scored_frames[position][score_name].dropna())

    plt.boxplot(values)
    plt.xticks(
        range(1, len(labels) + 1),
        [config.POSITION_MODELS[p]["chinese_name"] for p in labels],
    )
    plt.title("不同位置球员综合评分分布")
    plt.xlabel("球员位置")
    plt.ylabel("综合评分")

    save_figure("position_score_distribution.png")


# ------------------------------------------------------------
# 2. 各位置评分 TOP10（横向条形图）
# ------------------------------------------------------------

def plot_position_top10(scored_frames):
    setup_font()

    for position in config.POSITION_MODELS:
        model_config = config.POSITION_MODELS[position]
        score_name = model_config["score_name"]

        data = scored_frames[position]
        top10 = (
            data.sort_values(score_name, ascending=False)
            .head(10)
            .sort_values(score_name, ascending=True)
        )

        plt.figure(figsize=(10, 6))
        plt.barh(top10["Player"], top10[score_name])
        plt.title(f"{model_config['chinese_name']}球员综合评分 TOP10")
        plt.xlabel("综合评分")
        plt.ylabel("球员")

        save_figure(f"{position}_TOP10.png")


# ------------------------------------------------------------
# 3. 出场时间与评分关系（散点图）
# ------------------------------------------------------------

def plot_minutes_score_relationship(scored_frames):
    setup_font()

    plt.figure(figsize=(10, 6))

    for position in config.POSITION_MODELS:
        model_config = config.POSITION_MODELS[position]
        score_name = model_config["score_name"]
        data = scored_frames[position]

        plt.scatter(
            data["Min"], data[score_name],
            alpha=0.5, label=model_config["chinese_name"],
        )

    plt.title("球员出场时间与综合评分关系")
    plt.xlabel("出场时间（分钟）")
    plt.ylabel("综合评分")
    plt.legend()

    save_figure("minutes_score_relationship.png")


# ------------------------------------------------------------
# 4. 敏感性分析（分组条形图）
# ------------------------------------------------------------

def plot_sensitivity(sensitivity_df):
    """敏感性分析分组条形图。

    X 轴按"方案编号"分组（每位置 3 套备选权重），
    位置以图例区分，避免 12 个长标签互相重叠。
    """
    setup_font()

    plt.figure(figsize=(10, 6))

    positions = sensitivity_df["Position"].unique()

    # 提取方案编号："FW_Scheme1" -> 1
    scheme_no = sensitivity_df["Scheme"].str.extract(r"Scheme(\d+)")[0]
    scheme_no = pd.to_numeric(scheme_no, errors="coerce")

    sensitivity_df = sensitivity_df.assign(Scheme_No=scheme_no)
    schemes = sorted(sensitivity_df["Scheme_No"].dropna().unique())

    x = np.arange(len(schemes))
    width = 0.25

    for i, position in enumerate(positions):
        data = sensitivity_df[sensitivity_df["Position"] == position]

        values = [
            data[data["Scheme_No"] == scheme]["Top20_Overlap"].sum()
            for scheme in schemes
        ]

        plt.bar(
            x + i * width, values, width=width,
            label=config.POSITION_MODELS.get(
                position, {"chinese_name": position}
            )["chinese_name"],
        )

    plt.xticks(
        x + width, [f"方案{int(s)}" for s in schemes]
    )
    plt.ylabel("TOP20 重合率（%）")
    plt.xlabel("权重方案")
    plt.title("不同权重方案下 TOP20 重合率")
    plt.legend()
    plt.ylim(0, 105)

    save_figure("model_sensitivity.png")


# ------------------------------------------------------------
# 5. 聚类结果 PCA 散点图
# ------------------------------------------------------------

def plot_cluster_scatter(cluster_results):
    setup_font()

    for position, result in cluster_results.items():
        data = result["data"]
        profiles = {p["cluster"]: p for p in result["profiles"]}

        plt.figure(figsize=(10, 7))

        for cluster_id in sorted(data["Cluster"].unique()):
            members = data[data["Cluster"] == cluster_id]
            profile = profiles[cluster_id]

            plt.scatter(
                members["PC1"], members["PC2"],
                alpha=0.7, s=40,
                label=f"簇{cluster_id}：{profile['name']}（{profile['size']}人）",
            )

        chinese = config.POSITION_MODELS[position]["chinese_name"]
        variance = result["explained_variance"]

        plt.title(
            f"{chinese}球员聚类分型（K={result['k']}，"
            f"轮廓系数={result['silhouette']}）"
        )
        plt.xlabel(f"主成分1（解释方差 {variance[0] * 100:.1f}%）")
        plt.ylabel(f"主成分2（解释方差 {variance[1] * 100:.1f}%）")
        plt.legend(loc="best", fontsize=9)

        save_figure(f"{position}_cluster_scatter.png")


# ------------------------------------------------------------
# 6. 预测模型特征重要性（横向条形图）
# ------------------------------------------------------------

def plot_feature_importance(prediction_models):
    setup_font()

    for position, bundle in prediction_models.items():
        importance = bundle["importance"]

        metrics = [item["label"] for item in importance][::-1]
        values = [item["importance"] for item in importance][::-1]

        plt.figure(figsize=(10, 6))
        plt.barh(metrics, values)
        plt.title(
            f"{config.POSITION_MODELS[position]['chinese_name']}"
            f"评分预测模型特征重要性（随机森林）"
        )
        plt.xlabel("特征重要性")
        plt.ylabel("指标")

        save_figure(f"{position}_feature_importance.png")


# ------------------------------------------------------------
# 7. 预测值 vs 实际值（散点图，四位置子图）
# ------------------------------------------------------------

def plot_prediction_vs_actual(prediction_models):
    setup_font()

    positions = list(prediction_models.keys())

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()

    for ax, position in zip(axes, positions):
        bundle = prediction_models[position]

        actual = bundle["test_actual"]
        predicted = bundle["test_predicted"]

        ax.scatter(actual, predicted, alpha=0.6, s=30)

        # 对角参考线
        bounds = [
            min(min(actual), min(predicted)),
            max(max(actual), max(predicted)),
        ]
        ax.plot(bounds, bounds, "r--", alpha=0.7, linewidth=1)

        chinese = config.POSITION_MODELS[position]["chinese_name"]
        ax.set_title(
            f"{chinese}（测试集 R²={bundle['forest_test']['r2']}）",
            fontsize=11,
        )
        ax.set_xlabel("实际评分")
        ax.set_ylabel("预测评分")

    # 多余子图隐藏
    for ax in axes[len(positions):]:
        ax.set_visible(False)

    fig.suptitle("随机森林评分预测：预测值与实际值对比", fontsize=14)

    save_figure("prediction_vs_actual.png")


# ------------------------------------------------------------
# 8. 球员对比雷达图示例
# ------------------------------------------------------------

def plot_radar_example(comparison_result, filename="radar_example.png"):
    """渲染雷达图对比结果（comparison.build_radar_comparison 的返回值）。"""
    setup_font()

    dimensions = comparison_result["dimensions"]
    names = [d["name"] for d in dimensions]

    values1 = [
        d["player1_score"] if d["player1_score"] is not None else 0
        for d in dimensions
    ]
    values2 = [
        d["player2_score"] if d["player2_score"] is not None else 0
        for d in dimensions
    ]

    # 雷达图角度
    angles = np.linspace(0, 2 * np.pi, len(names), endpoint=False).tolist()

    values1 += values1[:1]
    values2 += values2[:1]
    angles += angles[:1]

    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, polar=True)

    ax.plot(angles, values1, linewidth=2, label=comparison_result["player1"]["player"])
    ax.fill(angles, values1, alpha=0.25)

    ax.plot(angles, values2, linewidth=2, label=comparison_result["player2"]["player"])
    ax.fill(angles, values2, alpha=0.25)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(names)
    ax.set_ylim(0, 100)
    ax.set_title("球员六维能力对比", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.2, 1.1))

    save_figure(filename)


# ------------------------------------------------------------
# 全部图表
# ------------------------------------------------------------

def plot_all(pipeline, sensitivity_df=None):
    """生成全部分析图表。

    Parameters
    ----------
    pipeline : AnalysisPipeline
        已构建的分析管线。
    sensitivity_df : pd.DataFrame, optional
        敏感性分析结果（含 Position / Scheme / Top20_Overlap 列）。
    """
    scored = pipeline.scored

    plot_score_distribution(scored)
    plot_position_top10(scored)
    plot_minutes_score_relationship(scored)

    if sensitivity_df is not None:
        plot_sensitivity(sensitivity_df)

    plot_cluster_scatter(pipeline.clusters)
    plot_feature_importance(pipeline.prediction_models)
    plot_prediction_vs_actual(pipeline.prediction_models)

    # 雷达图示例：FW 评分前二球员对比
    fw_score_name = config.POSITION_MODELS["FW"]["score_name"]
    top2 = pipeline.scored["FW"].sort_values(
        fw_score_name, ascending=False
    ).head(2)

    if len(top2) == 2:
        comparison = pipeline.compare_players(
            top2.iloc[0]["Player"], top2.iloc[1]["Player"]
        )
        plot_radar_example(comparison)
