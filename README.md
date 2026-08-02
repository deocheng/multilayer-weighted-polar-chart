# 🌟 多层带权极坐标下沉图 (Multilayer Weighted Polar Chart)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个用于展示**高维数据关联性与粒度下沉（Association & Progressive Drill-down）**的极客风 Python 可视化工具组件。

传统柱状图或折线图在表达“宏观主体占比”、“中观维度下沉”和“微观质量/权重”时往往需要拆分多图。本项目通过极坐标下沉结构，在一张圆图内完美融合了**横向关联**与**纵向深度**。

---

## ✨ 核心特性 (Key Features)

- **横向关联性（Horizontal Association）**：最外圈基于总量自动计算弧长，首尾相连，直观展示各主体（如球员、部门、渠道）的全局份额。
- **纵向多层下沉（Multilayer Drill-down）**：由外向内逐层下沉至具体细分维度（如投篮距离、业务线、功能模块）。
- **动态权重色彩映射（Weight-based Color Mapping）**：
  - 扇形填充弧长代表完成度/覆盖率；
  - 色彩深度（深蓝 $\rightarrow$ 淡冰蓝）直接映射权重大小（如命中率、ROI、健康度），擅长/高权重项一眼可知。
- **无框垂直对齐图例（Clean Vertical Axis Legend）**：图示文字优雅对齐于 12 点钟垂直分割线左侧，告别笨重的图例方框，极具科技感。
- **可切换对齐方式（Left / Center）**：支持从扇区左侧填充（`"left"`），或沿扇区中心线对称展开为「翅膀」布局（`"center"`）。

---

## 📸 效果展示 (Preview)

![Demo Chart](multilayer_polar_demo.png)

---

## 🎯 参考布局 (Annotated Layout Reference)

以下为「Team Shot Map」主题的对齐示意图,可作为自定义样式与排版的参考:

![Exact User Layout](exact_user_layout.png)

---

## 🚀 快速上手 (Quick Start)

### 1. 安装依赖

```bash
pip install matplotlib numpy pandas
```

> 💡 绘图时传入 `align_mode='center'` 即可启用「对称翅膀」居中对齐；不传时默认 `"left"`。

---

## 🏀 真实应用实例：Team Shot Radial (`team_shot_radial.py`)

`team_shot_radial.py` 是本图表主题的一个**端到端真实应用**：直连 NBA 出手数据库，生成可交互的纯 SVG/HTML 投篮分布图（无需 matplotlib）。它与通用库 `multilayer_polar.py` 是同一「多层带权极坐标下沉图」主题的两条实现路线：

| 维度 | `multilayer_polar.py`（通用库） | `team_shot_radial.py`（真实应用） |
| --- | --- | --- |
| 数据来源 | 传入 pandas `DataFrame` | 直连 PostgreSQL（`fct_pbp_shots`） |
| 渲染方式 | matplotlib → PNG | 纯 SVG → HTML（自带交互控件） |
| 对齐方式 | `left` / `center` 可选 | 固定扇形、左侧线对齐（left-edge） |
| 维度表达 | 权重着色 + 弧长 | 权重着色 + 弧长 + **clutch 关键时刻黄色叠加** + **环上命中/出手数据标签** |

该脚本已完整落地「下沉图」特性：

- **固定角度扇形**：每名球员占固定 45° 扇区，扇区间留 5° 间隙，剩余角度在左上形成大留白标签区；
- **左侧线对齐填充**：每环弧长从扇区左边缘起，按「该球员此距离带出手 ÷ 全队该距离最高者」（真实倍数、不压缩）展开；
- **bi-proportional 环厚**：径向厚度按全队该距离带真实出手占比分配（篮下最厚、长中距最薄）；
- **clutch 叠加**：黄色环叠加在楔形左缘，表示关键时刻（`is_clutch`，最后 5 秒）出手；
- **数据标签**：环上白字 = 命中数/出手数（整体命中率），正下方黄字 = 关键时刻 命中/出手；
- **中心球员数据块**：排名 + 各距离带出手明细；图例为沉入背景的无框文字条。

### 依赖与配置

```bash
pip install psycopg2-binary python-dotenv
```

在同目录创建 `.env`（**切勿提交**，已在 `.gitignore` 忽略）：

```dotenv
DB_HOST=localhost
DB_PORT=5433
DB_NAME=nba
DB_USER=postgres
DB_PASSWORD=your_password
```

数据表需含 `fct_pbp_shots(season, team, player_slug, shot_distance, is_make, is_clutch)`。

### 用法

```bash
python team_shot_radial.py 2025 BOS 5
# 参数: <赛季> <球队三字码> <Top N 球员>
# 输出: team_shot_radial.html (本地浏览器打开, 可切换赛季 / 球队 / 人数)
```

---

## 📂 文件结构

```
multilayer-weighted-polar-chart/
├── multilayer_polar.py        # 通用库: plot_multilayer_polar_map (支持 align_mode='left'|'center')
├── example.py                 # 通用库使用示例
├── team_shot_radial.py        # 真实应用: NBA 出手分布 (DB 驱动, SVG/HTML 输出)
├── README.md
├── LICENSE                    # MIT (Deo Cheng, 2026)
├── .gitignore
├── multilayer_polar_demo.png  # 通用库预览图
└── exact_user_layout.png      # 「Team Shot Map」参考布局图
```