# 🌟 Multilayer Weighted Polar Chart (多层带权极坐标下沉图)

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

---

## 📸 效果展示 (Preview)

![Demo Chart](multilayer_polar_demo.png)

---

## 🚀 快速上手 (Quick Start)

### 1. 安装依赖

```bash
pip install matplotlib numpy pandas