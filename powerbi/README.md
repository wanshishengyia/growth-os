# Growth OS — Power BI 集成指南

> 将 Growth OS 数据连接到 Power BI，构建可视化仪表板

---

## 前置条件

- [Power BI Desktop](https://powerbi.microsoft.com/desktop/)（免费下载）
- Supabase 项目（PostgreSQL 数据库）
- 已运行 `data-views.sql` 中的视图创建脚本

---

## 步骤一：在 Supabase 中创建视图

1. 打开 Supabase Dashboard → SQL Editor
2. 复制 `data-views.sql` 中的全部内容
3. 执行脚本，创建 6 个视图：
   - `v_action_dashboard` — 行动数据
   - `v_asset_dashboard` — 资产数据
   - `v_cognition_dashboard` — 认知数据
   - `v_life_dashboard` — 目标数据
   - `v_monthly_trends` — 月度趋势
   - `v_streak_calc` — 连续天数

4. 验证视图创建成功：
   ```sql
   SELECT * FROM v_action_dashboard LIMIT 5;
   SELECT * FROM v_streak_calc;
   ```

---

## 步骤二：获取数据库连接信息

在 Supabase Dashboard 中获取：

1. 进入 **Settings** → **Database**
2. 记录以下信息：

| 参数 | 位置 | 示例值 |
|------|------|--------|
| Host | Connection string 中的主机名 | `db.xxxxx.supabase.co` |
| Port | 默认 PostgreSQL 端口 | `5432` |
| Database | 数据库名 | `postgres` |
| User | 用户名 | `postgres` |
| Password | 你设置的数据库密码 | ****** |

> ⚠️ **安全提示：** 不要将密码提交到 Git 仓库。使用环境变量或 Power BI 参数管理。

---

## 步骤三：在 Power BI Desktop 中连接

### 3.1 新建连接

1. 打开 Power BI Desktop
2. 点击 **Get Data** → **PostgreSQL database**
3. 填写连接信息：
   - **Server:** `db.xxxxx.supabase.co`（替换为你的 Host）
   - **Database:** `postgres`
4. 点击 **OK**

### 3.2 认证

1. 选择 **Database** 认证方式
2. 输入 **User** 和 **Password**
3. 点击 **Connect**

### 3.3 选择视图

在 Navigator 中勾选以下视图：

```
☑ v_action_dashboard
☑ v_asset_dashboard
☑ v_cognition_dashboard
☑ v_life_dashboard
☑ v_monthly_trends
☑ v_streak_calc
```

点击 **Load** 加载数据。

---

## 步骤四：配置数据模型

### 4.1 关系设置

在 Power BI 的 **Model** 视图中，确保以下关系：

```
v_action_dashboard.goal_title  ←→  v_life_dashboard.title
v_asset_dashboard.related_goal ←→  v_life_dashboard.title
v_monthly_trends.month         ←→  v_asset_dashboard.month
v_monthly_trends.month         ←→  v_cognition_dashboard.month
```

> 注意：Power BI 会自动检测关系，但请确认方向和基数正确。

### 4.2 计算列和度量值

在 DAX 中创建以下常用度量值：

```dax
// 30天完成率
Completion Rate 30d = 
DIVIDE(
    CALCULATE(COUNTROWS(v_action_dashboard), v_action_dashboard[completed] = TRUE),
    COUNTROWS(v_action_dashboard),
    0
)

// 当前连续天数
Current Streak = 
MAX(v_streak_calc[streak_days])

// 月度完成率趋势
Monthly Completion Rate = 
DIVIDE(
    [Completed Days],
    [Total Days],
    0
)

// 资产复利指数
Asset Compound Index = 
SUM(v_asset_dashboard[quality]) * SUM(v_asset_dashboard[reuse_count])
```

---

## 步骤五：创建仪表板

参考 `dashboard-specs.md` 中的详细规格创建四个看板：

| 看板 | 频率 | 主要视图 |
|------|------|---------|
| Action Dashboard (行动看板) | 每日 | `v_action_dashboard`, `v_streak_calc` |
| Asset Dashboard (资产看板) | 每周 | `v_asset_dashboard` |
| Cognition Dashboard (认知看板) | 每两周 | `v_cognition_dashboard` |
| Life Dashboard (主线看板) | 每月 | `v_life_dashboard`, `v_monthly_trends` |

---

## 步骤六：发布和刷新

### 发布到 Power BI Service

1. 在 Power BI Desktop 中点击 **Publish**
2. 选择目标 Workspace
3. 在 Power BI Service 中配置数据源凭据

### 配置自动刷新

1. 进入 Power BI Service → **Settings** → **Datasets**
2. 配置 **Gateway connection**（如需要）
3. 设置 **Scheduled refresh**：
   - 频率：每日
   - 时间：06:00 (UTC+8)
4. 添加刷新失败通知邮箱

---

## 故障排查

### 连接超时

- 确认 Supabase 项目的数据库未被暂停
- 检查 IP 白名单：Supabase → Settings → Database → Network Restrictions
- 如果设置了网络限制，添加 Power BI Gateway 的 IP

### 视图不存在

- 确认已在 Supabase SQL Editor 中执行了 `data-views.sql`
- 检查视图所属 schema（默认 `public`）

### 数据为空

- 确认 `daily_logs`、`assets`、`insights`、`goals` 表中有数据
- `v_action_dashboard` 仅显示最近90天的数据

### 性能优化

- 如果数据量大，使用 Power BI 的增量刷新
- 在 Power BI Desktop 中关闭 Auto Date/Time
- 考虑在 Supabase 中为视图涉及的列添加索引

---

## 文件结构

```
growth-os/powerbi/
├── README.md              ← 本文件（连接指南）
├── data-views.sql         ← SQL 视图定义
└── dashboard-specs.md     ← 仪表板设计规格
```
