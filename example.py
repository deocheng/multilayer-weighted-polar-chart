import pandas as pd
from multilayer_polar import plot_multilayer_polar_map

# 准备你的 DataFrame
# 需包含：主分类列、下沉维度列、总量数值列、0~1 的权重列
df = pd.read_csv("your_data.csv")

# 一行代码生成极坐标下沉图
plot_multilayer_polar_map(
    df=df,
    group_col='Player',        # 外圈主体
    layer_col='Zone',          # 内部圈层
    value_col='TotalShots',    # 主体占比数值
    weight_col='Weight',       # 颜色/弧长权重 (0.0~1.0)
    title="Team Performance Drill-down Map",
    save_path="output.png"
)