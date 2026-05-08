# Power BI Dashboard Specifications

> Growth OS 可视化看板详细设计

---

## Dashboard A: Action Dashboard (行动看板)

**核心问题：** "Am I maintaining my action rhythm?" — 我的行动节奏是否在保持？

**使用频率：** 最高频，每日查看

**数据源：** `v_action_dashboard`, `v_streak_calc`

### 视觉组件

| # | 组件类型 | 标题 | 数据说明 |
|---|---------|------|---------|
| 1 | KPI Card | 30-Day Completion Rate | 近30天完成率（%），`COUNT(completed=true) / COUNT(*)` |
| 2 | KPI Card | Current Streak | 当前连续天数，来自 `v_streak_calc.streak_days` |
| 3 | KPI Card | Avg Mood This Week | 本周平均情绪值，`AVG(mood)` WHERE week = current |
| 4 | Line Chart | Mood & Energy Trend | 双轴折线图，X=log_date, Y1=mood, Y2=energy，近30天 |
| 5 | Bar Chart | Completion by Day of Week | 柱状图，X=day_of_week (Mon-Sun), Y=completion rate |
| 6 | Heatmap | Focus Minutes Calendar | 日历热力图，颜色深浅=focus_minutes，近30天 |
| 7 | Table | Last 7 Days Summary | 表格：date, core_task, completed(✓/✗), mood, energy |

### 交互设计
- 点击日历热力图某天 → 高亮该天详情
- 全局日期筛选器：默认30天，可选7天/90天
- 完成率 KPI 使用颜色编码：≥80% 绿色，60-79% 黄色，<60% 红色

---

## Dashboard B: Asset Dashboard (资产看板)

**核心问题：** "Is my compounding accumulation on track?" — 我的复利积累是否在正轨？

**使用频率：** 每周查看

**数据源：** `v_asset_dashboard`

### 视觉组件

| # | 组件类型 | 标题 | 数据说明 |
|---|---------|------|---------|
| 1 | KPI Card | Total Assets | 资产总数，`COUNT(*)` |
| 2 | Pie Chart | Assets by Type | 饼图，按 type 分组统计 |
| 3 | Bar Chart | Monthly Asset Creation | 柱状图，X=month, Y=COUNT，展示月度新增趋势 |
| 4 | Histogram | Quality Distribution | 直方图，X=quality (1-5), Y=COUNT，展示质量分布 |
| 5 | Table | Top 10 Most Reused | 表格：title, type, quality, reuse_count，按reuse_count降序 |
| 6 | Word Cloud | Tag Frequency | 词频图，从 tags 字段提取关键词频次 |

### 交互设计
- 点击饼图某类型 → 筛选其他组件仅显示该类型
- 质量分布直方图支持点击筛选
- 月度柱状图支持时间范围缩放

---

## Dashboard C: Cognition Dashboard (认知看板)

**核心问题：** "Is my cognition upgrading?" — 我的认知是否在升级？

**使用频率：** 每两周查看

**数据源：** `v_cognition_dashboard`

### 视觉组件

| # | 组件类型 | 标题 | 数据说明 |
|---|---------|------|---------|
| 1 | KPI Card | Total Insights | 洞察总数 |
| 2 | Donut Chart | Insights by Type | 环形图，按 type 分组（question/insight/principle/model） |
| 3 | Line Chart | Monthly Insight Creation | 折线图，X=month, Y=COUNT，展示月度新增 |
| 4 | Line Chart | Confidence Trend | 折线图，X=month, Y=AVG(confidence)，展示信心趋势 |
| 5 | Table | Top 10 Most Validated | 表格：content, type, confidence, validated_count |
| 6 | KPI Card | Question→Insight Ratio | 转化率：insight数量 / question数量 |

### 交互设计
- 环形图点击某类型 → 筛选表格和折线图
- 信心趋势折线图支持与创建量对比
- 表格支持按 validated_count 排序

---

## Dashboard D: Life Dashboard (主线看板)

**核心问题：** "Am I moving in the right direction?" — 我是否在正确的方向上前进？

**使用频率：** 每月查看（配合月度复盘）

**数据源：** `v_life_dashboard`, `v_monthly_trends`

### 视觉组件

| # | 组件类型 | 标题 | 数据说明 |
|---|---------|------|---------|
| 1 | Progress Bars | Active Goals | 进度条，每个活跃目标显示 progress% |
| 2 | Gantt Chart | Goal Timeline | 甘特图，X=时间, Y=goals, 条形=start_date→end_date |
| 3 | Line Chart | Direction Alignment | 折线图，X=month, Y=alignment_score（需计算） |
| 4 | Radar Chart | Self-Assessment | 雷达图，多维度自评分数（life/goal/resource/insight） |
| 5 | KPI Card | Months in Current Stage | 当前阶段已持续月数 |

### 交互设计
- 甘特图点击目标 → 显示关联资产数和完成天数
- 进度条使用颜色区分 goal_level
- 雷达图支持多时间点叠加对比

---

## 全局设计规范

### 颜色方案
| 含义 | 颜色 | Hex |
|------|------|-----|
| 正面/完成 | 绿色 | `#22C55E` |
| 警告/中等 | 黄色 | `#EAB308` |
| 负面/未完成 | 红色 | `#EF4444` |
| 主色调 | 蓝色 | `#3B82F6` |
| 辅助色 | 紫色 | `#8B5CF6` |
| 背景 | 深灰 | `#1E1E2E` |

### 字体
- 标题：Inter Bold, 16px
- 正文：Inter Regular, 12px
- KPI 数字：Inter Bold, 32px

### 刷新策略
- Power BI Gateway 每日自动刷新（06:00 UTC+8）
- 手动刷新：在 Power BI Service 中点击"立即刷新"
- 增量刷新：仅加载最近90天数据以优化性能
