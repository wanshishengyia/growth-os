# Personal Growth OS

> 让循环跑起来，系统会越来越强。

认知驱动型个人成长操作系统 —— 由 AI 驱动，帮你每天小步前进，长期复利积累。

## 这是什么

一个完整的个人成长系统，不是笔记工具，不是 ToDo App。它有：

- **7 个 AI Agent**：决策、闭环、模式识别、资产分类、洞察提取、苏格拉底提问、方向校准
- **4 大循环**：日循环（晨间决策+晚间闭环）、周复盘、月报告、季度校准
- **Telegram Bot**：移动端交互，随时记录
- **Obsidian 集成**：深度思考和知识整理
- **Power BI 看板**：可视化成长曲线
- **n8n 自动化**：7 个工作流，全自动化运行

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python + FastAPI |
| 数据库 | Supabase (PostgreSQL) |
| AI | Claude / OpenAI API |
| 移动端 | Telegram Bot |
| 笔记 | Obsidian + 本地 REST API |
| 自动化 | n8n |
| 可视化 | Power BI |
| 部署 | Docker + Docker Compose |

## 现在我做的事

1. 早上从 Telegram 收到 AI 给我的「今日核心 + 起步动作」
2. 白天就做这一件事
3. 晚上发一段流水账给 Bot，AI 帮我闭环
4. 周日 AI 帮我看出本周的模式，我自己写复盘结论
5. 月末看一眼 Power BI 看板，确认我真的在变强

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
cd growth-os

# 复制环境变量
cp .env.example .env
# 编辑 .env，填入你的密钥

# 安装依赖
make init
```

### 2. 配置 Supabase

1. 注册 [Supabase](https://supabase.com)，创建项目
2. 在 SQL Editor 中依次执行：
   - `sql/001_init_schema.sql`（建表）
   - `sql/002_views.sql`（视图）
   - `sql/003_seed.sql`（测试数据，可选）
3. 将 URL 和 Key 填入 `.env`

### 3. 配置 AI

```bash
# 在 .env 中设置
ANTHROPIC_API_KEY=sk-ant-xxx    # Claude（推荐）
# 或
OPENAI_API_KEY=sk-xxx           # GPT-4o
AI_PRIMARY_PROVIDER=claude      # 或 openai
```

### 4. 配置 Telegram Bot

1. 在 Telegram 找 @BotFather，创建 Bot，获取 Token
2. 将 Token 和你的 Chat ID 填入 `.env`

### 5. 启动

```bash
# 本地开发
make dev

# Docker 部署
make deploy
```

### 6. 开始使用

```bash
# 通过 API 触发晨间决策
curl http://localhost:8000/api/loop/daily/morning

# 通过 API 提交晚间流水账
curl -X POST http://localhost:8000/api/loop/daily/evening \
  -H "Content-Type: application/json" \
  -d '{"raw_notes": "今天...", "mood": 3, "energy": 4}'

# 或直接用 Telegram
# /morning - 获取今日决策
# /night - 提交晚间流水账
# /review - 周复盘
# /status - 查看系统状态
```

## 项目结构

```
growth-os/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/            # 28 个 API 端点
│   │   ├── agents/         # 7 个 AI Agent
│   │   ├── models/         # Pydantic 数据模型
│   │   └── services/       # 核心服务（DB、LLM、Telegram、规则引擎）
│   └── prompts/            # 7 个 Agent Prompt 模板（v1.0）
├── sql/                    # 数据库脚本
│   ├── 001_init_schema.sql # 建表（7张表+索引+触发器）
│   ├── 002_views.sql       # 视图
│   └── 003_seed.sql        # 测试数据
├── n8n/                    # n8n 自动化工作流
│   └── workflows/          # 7 个工作流 JSON
├── obsidian/               # Obsidian 模板
│   └── templates/          # 日/周/月/洞察/资产模板
├── powerbi/                # Power BI 配置
│   ├── data-views.sql      # 看板专用视图
│   └── dashboard-specs.md  # 4 个看板规格
├── docker-compose.yml
├── Dockerfile
├── Makefile
└── .env.example
```

## API 概览

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/loop/daily/morning` | GET | 晨间决策 |
| `/api/loop/daily/evening` | POST | 晚间闭环 |
| `/api/loop/weekly/run` | POST | 周复盘 |
| `/api/loop/weekly/submit` | POST | 提交周复盘结论 |
| `/api/loop/monthly/run` | POST | 月报告 |
| `/api/loop/quarterly/run` | POST | 季度校准 |
| `/api/goals` | GET/POST | 目标管理 |
| `/api/assets` | GET/POST | 资产管理 |
| `/api/insights` | GET/POST | 洞察管理 |
| `/api/reviews` | GET | 复盘查询 |
| `/api/dashboard/stats` | GET | 仪表盘数据 |
| `/api/agents/{name}` | POST | 直接调用 Agent |

完整文档：启动后访问 `http://localhost:8000/docs`（Swagger UI）

## 成本

| 项目 | 月成本 |
|------|--------|
| AI API（7个Agent） | ~$2-5 |
| Supabase（免费层） | $0 |
| VPS（可选） | ~$5-10 |
| **总计** | **$2-15** |

## 成功标准

系统成功的判定不是「建好了」，而是：

- ✅ 稳定运行 ≥ 60 天，日循环达成率 ≥ 80%
- ✅ 数据库已有 ≥ 60 条日志、≥ 4 份周复盘、≥ 20 个资产
- ✅ 主观感受：「成长是可见的、可控的、有方向的」

## 防沉迷开发纪律

1. Phase 1 完成当天起，每天至少用一次系统
2. 每周日 21:00 做「使用情况自检」
3. Phase 之间设置 7 天「纯使用期」
4. 开发投入与使用产出比例 ≤ 3:1

---

> 系统永远是手段，不是目的。当系统成为目的本身时，该砍掉的不是功能，而是对「完美系统」的执念。
