# -*- coding: utf-8 -*-
"""
足球球员数据分析核心包
======================

模块结构：
- config            全局配置（路径、阈值、评分权重、模型超参数）
- data_loader       数据加载与字段校验
- features          特征工程（汇总、派生指标、Per90、位置拆分）
- scoring           位置评分模型（百分位标准化 + 加权综合评分）
- clustering        球员聚类分型（K-Means + PCA + 轮廓系数选 K）
- similarity        相似球员推荐（Z-Score 标准化 + 余弦相似度）
- comparison        球员对比雷达图数据
- prediction        评分预测模型（随机森林回归 + 交叉验证）
- visualization     分析结果可视化（论文图表）
- pipeline          数据分析管线组装（供 API 与批处理复用）
"""

from football_analysis.pipeline import AnalysisPipeline, get_pipeline

__all__ = ["AnalysisPipeline", "get_pipeline"]
