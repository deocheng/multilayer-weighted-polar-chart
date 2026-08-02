# 计算该层数据占用的角度弧长
draw_span = group_theta_span * weight

# 🌟 关键：以 theta_mid（中心线）做对称镜像对齐
theta_draw_start = theta_mid - (draw_span / 2)
theta_draw_end = theta_mid + (draw_span / 2)

# 1. 绘制左侧对称缺口
theta_gap_left = np.linspace(theta_start, theta_draw_start, 15)
ax.fill_between(theta_gap_left, r_inner, r_outer, color='#ffffff', alpha=0.03, edgecolor='none')

# 2. 绘制右侧对称缺口
theta_gap_right = np.linspace(theta_draw_end, theta_end, 15)
ax.fill_between(theta_gap_right, r_inner, r_outer, color='#ffffff', alpha=0.03, edgecolor='none')

# 3. 绘制居中对称的数据填充区域
theta_active_grid = np.linspace(theta_draw_start, theta_draw_end, 50)
ax.fill_between(theta_active_grid, r_inner, r_outer, color=base_color, alpha=0.9, edgecolor='#ffffff', lw=0.3)