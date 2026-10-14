from itertools import groupby

import pandas as pd

# 读取数据
df = pd.read_csv("../data/players_data_light-2024_2025.csv")

# ==========================
# 1. 查看数据规模
# ==========================
print("数据规模：", df.shape)


# ==========================
# 2. 查看所有字段
# ==========================
print("\n========== 所有字段 ==========")

for i, column in enumerate(df.columns, start=1):
    print(i, column)


# ==========================
# 3. 查看每个字段的数据类型
# ==========================
print("\n========== 数据类型 ==========")

print(df.dtypes)


# ==========================
# 4. 查看缺失值
# ==========================
print("\n========== 缺失值统计 ==========")

missing = df.isna().sum()

print(missing[missing > 0].sort_values(ascending=False))

print("\n========== 球员位置 ==========")
print(df["Pos"].value_counts())

print("\n========== 球员数量 ==========")
print("记录数量：", len(df))
print("不同球员数量：", df["Player"].nunique())

print("\n========== 重复球员 ==========")
player_count = df["Player"].value_counts()
print(player_count[player_count > 1].head(20))

print("\n========== Max Aarons ==========")
print(
    df[df["Player"] == "Max Aarons"][[
        "Player",
        "Nation",
        "Pos",
        "Squad",
        "Comp",
        "Age",
        "MP",
        "Starts",
        "Min",
        "Gls",
        "Ast"
    ]]
)

# 找出出现多次的球员
duplicate_players = df[
    df["Player"].duplicated(keep=False)
]

# 查看这些球员分别效力过几个俱乐部
club_count = duplicate_players.groupby("Player")["Squad"].nunique()

print("\n========== 转会球员俱乐部数量 ==========")
print(club_count.value_counts())

