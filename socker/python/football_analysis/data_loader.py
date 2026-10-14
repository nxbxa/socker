# -*- coding: utf-8 -*-
"""
数据加载模块
============
职责：
1. 读取原始球员比赛数据 CSV（保留原始字段名）
2. 重命名 FBref 特殊字段名为友好名（对照表见 config.RENAME_COLUMNS）
3. 校验必需字段是否齐全
4. 数值字段类型转换（无法解析的值统一置为 NaN）
"""

import pandas as pd

from football_analysis import config


def load_raw_csv(input_file=None):
    """读取原始 CSV（保留 FBref 原始字段名，不做任何转换）。

    用途：导出球员-俱乐部明细等需要原始字段名的场景。
    """
    path = input_file or config.INPUT_FILE
    return pd.read_csv(path)


def prepare_dataframe(df):
    """重命名字段并转换数值类型。

    步骤：FBref 特殊字段名 -> 友好名 -> 必需字段校验 -> 数值转换。
    """
    data = df.rename(columns=config.RENAME_COLUMNS).copy()

    # 必需字段校验（基于重命名后的字段名）
    missing = [
        col for col in config.REQUIRED_COLUMNS if col not in data.columns
    ]
    if missing:
        raise ValueError(f"原始 CSV 缺少以下字段：{missing}")

    # 数值字段类型转换
    for col in config.NUMERIC_COLUMNS:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    return data


def load_raw_data(input_file=None):
    """读取原始 CSV 并完成字段重命名、校验与数值转换。

    Returns
    -------
    pd.DataFrame
        分析用明细数据（每行 = 球员在某俱乐部的一个赛季记录）。
    """
    return prepare_dataframe(load_raw_csv(input_file))
