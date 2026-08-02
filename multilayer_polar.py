"""
Multilayer Weighted Polar Chart (多层带权极坐标下沉图)
--------------------------------------------------
A visualization tool designed to render high-density multidimensional data,
highlighting entity relationships and hierarchical drill-down weights.

Author: Your Name / GitHub Username
License: MIT
"""

import matplotlib.pyplot as plt
import numpy as np
import matplotlib.colors as mcolors
import pandas as pd


def plot_multilayer_polar_map(
    df: pd.DataFrame,
    group_col: str,
    layer_col: str,
    value_col: str,
    weight_col: str,
    title: str = "Multilayer Weighted Polar Map",
    center_legend: str = "DATA DRILL-DOWN MAP\n───────\n■ High Weight (Dark)\n■ Low Weight (Light)",
    cmap_base_colors: list = ["#dbeafe", "#60a5fa", "#1d4ed8"],
    cmap_sub_colors: list = ["#3b82f6", "#1e3a8a", "#0f172a"],
    gap_ratio: float = 0.05,
    figsize: tuple = (10, 10),
    save_path: str = None
):
    """
    绘制多层带权极坐标下沉图
    
    Parameters:
    -----------
    df : pd.DataFrame
        包含数据的 Pandas DataFrame
    group_col : str
        外圈主分类/实体列名 (如: Player / Department / Traffic Source)
    layer_col : str
        内部圈层下沉维度列名 (如: Zone / Quarter / Product Category)
    value_col : str
        决定外圈扇形角度占比例的数值列名 (如: Total Shots / Total Budget)
    weight_col : str
        决定圈层颜色深浅和完成度/弧长比例的权重列名 (取值范围 0.0 - 1.0)
    title : str
        图表标题
    center_legend : str
        圆心展示的图例/说明文本
    cmap_base_colors : list
        主区域颜色的渐变色板 (低权重 -> 高权重)
    cmap_sub_colors : list
        子/关键区域颜色的渐变色板 (低权重 -> 高权重)
    gap_ratio : float
        11点钟留白缺口占全圆的比例
    figsize : tuple
        画布尺寸
    save_path : str, optional
        高清图片保存路径 (如: 'output.png')
    """
    # 1. 画布与基础设置
    fig, ax = plt.subplots(figsize=figsize, subplot_kw={'projection': 'polar'})
    fig.patch.set_facecolor('#080e1a')
    ax.set_facecolor('#080e1a')

    # 正上方 12 点钟为起点 (0°)，顺时针方向展开
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)

    # 2. 数据预处理
    # 按照外圈实体汇总总数值并排序
    group_totals = df.groupby(group_col)[value_col].sum()
    groups = group_totals.index.tolist()
    group_values = group_totals.values
    grand_total = group_values.sum()

    # 获取圈层列表
    layers = df[layer_col].unique().tolist()
    num_layers = len(layers)

    # 计算各圈层的半径高度 (按总值比例或等分)
    layer_totals = df.groupby(layer_col)[value_col].sum().reindex(layers).fillna(1)
    r_min = 2.0
    total_r_span = 5.0
    layer_r_heights = (layer_totals.values / layer_totals.sum()) * total_r_span

    # 色彩渐变映射器
    cmap_base = mcolors.LinearSegmentedColormap.from_list("custom_base", cmap_base_colors)
    cmap_sub = mcolors.LinearSegmentedColormap.from_list("custom_sub", cmap_sub_colors)

    # 3. 角度计算（从 12 点钟起点顺时针排列，留出缺口）
    total_gap_angle = 2 * np.pi * gap_ratio
    remaining_span = 2 * np.pi - total_gap_angle
    inter_group_gap = 0.02  # 每个组之间的微小缝隙

    cur_angle = 0.0
    sector_angles = []

    for val in group_values:
        p_span = (val / grand_total) * remaining_span - inter_group_gap
        sector_angles.append((cur_angle, cur_angle + p_span))
        cur_angle += p_span + inter_group_gap

    # 4. 绘制主体扇形
    for i, g_name in enumerate(groups):
        theta_start, theta_end = sector_angles[i]
        theta_mid = (theta_start + theta_end) / 2
        
        # 外圈主实体标签
        total_val_str = f"{group_values[i]:,.0f}" if isinstance(group_values[i], (int, np.integer)) else f"{group_values[i]:.1f}"
        ax.text(
            theta_mid, r_min + total_r_span + 0.75, 
            f"{g_name}\n({total_val_str})", 
            ha='center', va='center', color='white', fontweight='bold', fontsize=9,
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#1e293b', edgecolor='#334155', alpha=0.9)
        )

        r_current = r_min
        for z, l_name in enumerate(layers):
            r_inner = r_current
            r_outer = r_current + layer_r_heights[z]
            layer_h = layer_r_heights[z]
            r_current = r_outer

            # 提取该组在当前圈层的权重数据
            sub_df = df[(df[group_col] == g_name) & (df[layer_col] == l_name)]
            weight = sub_df[weight_col].values[0] if not sub_df.empty else 0.0
            
            # 计算弧长覆盖
            group_theta_span = theta_end - theta_start
            theta_draw_end = theta_start + group_theta_span * weight

            # 绘制底层网格阴影 (未覆盖部分)
            if weight < 1.0:
                theta_gap_grid = np.linspace(theta_draw_end, theta_end, 30)
                ax.fill_between(theta_gap_grid, r_inner, r_outer, color='#ffffff', alpha=0.03, edgecolor='none')

            # 绘制真实数据区域
            theta_active_grid = np.linspace(theta_start, theta_draw_end, 50)
            base_color = cmap_base(weight)
            ax.fill_between(theta_active_grid, r_inner, r_outer, color=base_color, alpha=0.9, edgecolor='#ffffff', lw=0.3)

            # 可选：绘制内部关键子维度层 (如 Clutch 区域)
            if 'sub_weight' in df.columns:
                sub_w = sub_df['sub_weight'].values[0] if not sub_df.empty else 0.0
                if sub_w > 0:
                    r_sub_outer = r_inner + layer_h * sub_w
                    sub_color = cmap_sub(weight)
                    ax.fill_between(theta_active_grid, r_inner, r_sub_outer, color=sub_color, alpha=0.95, edgecolor='#ffffff', lw=0.3)

    # 5. 图示文字严格沿 12 点钟垂直线左侧对齐（无框纯净版）
    r_pos = r_min
    for z, l_name in enumerate(layers):
        r_mid = r_pos + layer_r_heights[z] / 2
        # theta = 0 指向正上方 12 点钟方向，ha='right' 使其垂直贴在分割线左侧
        ax.text(0, r_mid, f"{l_name} ", ha='right', va='center', color='#ffffff', fontsize=9, fontweight='bold')
        r_pos += layer_r_heights[z]

    # 6. 美化轴线与圆心
    ax.grid(False)
    ax.set_yticklabels([])
    ax.set_xticklabels([])

    if center_legend:
        ax.text(0, 0, center_legend, ha='center', va='center', color='#f1f5f9', fontsize=9.5, fontweight='bold')

    plt.title(title, color='white', fontsize=12, fontweight='bold', pad=30)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
        print(f"Chart saved to {save_path}")

    return fig, ax


# ==========================================
# 演示运行示例 (Demo Usage)
# ==========================================
if __name__ == "__main__":
    # 模拟生成一份“多维数据下沉”数据集 (例如：球员投篮分布与权重)
    demo_data = []
    players = ['Player 1', 'Player 2', 'Player 3', 'Player 4', 'Player 5']
    player_shots = [1500, 1200, 900, 700, 500]
    zones = ['0-8 ft (Rim-Paint)', '8-16ft (Mid)', '16-24ft (Long Mid)', '24+ft (3PT)']
    
    # 权重矩阵 (例如: 命中率 / 擅长权重 0.0~1.0)
    weights = [
        [1.0, 0.8, 0.5, 0.9],
        [0.9, 1.0, 0.7, 0.6],
        [1.0, 0.4, 0.2, 0.1],
        [0.6, 0.6, 0.8, 1.0],
        [0.8, 0.5, 0.4, 0.7],
    ]
    
    # 关键时刻占比 (Optional)
    sub_weights = [
        [0.35, 0.25, 0.40, 0.30],
        [0.30, 0.45, 0.20, 0.25],
        [0.50, 0.30, 0.10, 0.00],
        [0.20, 0.30, 0.35, 0.45],
        [0.25, 0.20, 0.15, 0.35],
    ]

    for p_idx, p in enumerate(players):
        for z_idx, z in enumerate(zones):
            demo_data.append({
                'Player': p,
                'TotalShots': player_shots[p_idx],
                'Zone': z,
                'Weight': weights[p_idx][z_idx],
                'sub_weight': sub_weights[p_idx][z_idx]
            })

    df = pd.DataFrame(demo_data)

    # 调用绘图工具
    plot_multilayer_polar_map(
        df=df,
        group_col='Player',
        layer_col='Zone',
        value_col='TotalShots',
        weight_col='Weight',
        title="Multilayer Weighted Polar Chart Demo",
        save_path='multilayer_polar_demo.png'
    )
    plt.show()