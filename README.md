# Personal Growth OS

> 让循环跑起来，系统会越来越强。

认知驱动型个人成长操作系统 —— 由 AI 驱动，帮你每天小步前进，长期复利积累。

## 国内适配版

| 组件 | 方案 | 说明 |
|------|------|------|
| 数据库 | **SQLite** | 零依赖，本地运行，单用户够用 |
| AI | **小米 MiMo** | OpenAI兼容API，国内低延迟 |
| 消息推送 | **飞书 Webhook** | 国内无障碍，富文本卡片 |
| 定时任务 | **APScheduler** | Python原生，无需额外服务 |
| 看板 | **Streamlit** | Python生态，一键启动 |
| 后端 | **FastAPI** | 自动API文档，异步支持 |

## 核心功能

- **7 个 AI Agent**：决策、闭环、模式识别、资产分类、洞察提取、苏格拉底提问、方向校准
- **4 大循环**：日循环（晨间决策+晚间闭环）、周复盘、月报告、季度校准
- **飞书推送**：晨间决策卡片、晚间分析卡片、周复盘报告
- **Streamlit 看板**：行动/资产/认知/主线 四大看板
- **全自动化**：APScheduler 定时调度，无需手动触发

## 快速开始

### 1. 安装

```bash
cd growth-os
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. 配置 .env

```bash
# 必填：小米 MiMo API Key
MIMO_API_KEY=your-key-here

# 可选：飞书 Webhook（消息推送）
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
```

### 3. 启动

```bash
# API 服务（含定时任务）
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# 看板（另一个终端）
streamlit run dashboard/app.py
```

### 4. 使用

```bash
# 健康检查
curl http://localhost:8000/health

# 创建目标
curl -X POST http://localhost:8000/api/goals \
  -H "Content-Type: application/json" \
  -d '{"title":"学习数据分析","level":"month","priority":4}'

# 晨间决策（AI生成今日任务）
curl http://localhost:8000/api/loop/daily/morning

# 晚间闭环（提交流水账）
curl -X POST http://localhost:8000/api/loop/daily/evening \
  -H "Content-Type: application/json" \
  -d '{"raw_notes":"今天学习了SQL...","mood":4,"energy":3}'

# 查看状态
curl http://localhost:8000/api/dashboard/stats
```

### 5. Swagger 文档

启动后访问 http://localhost:8000/docs 查看完整 API 文档。

## 项目结构

```
growth-os/
├── backend/
│   ├── app/
│   │   ├── api/            # 24 个 REST 端点
│   │   ├── agents/         # 7 个 AI Agent
│   │   ├── models/         # Pydantic 数据模型
│   │   └── services/       # DB、LLM、飞书、调度器、规则引擎
│   └── prompts/            # 7 个 Agent Prompt 模板
├── dashboard/              # Streamlit 看板
├── sql/                    # SQLite 建表脚本
├── obsidian/               # Obsidian 模板
├── n8n/                    # n8n 工作流（备用）
├── powerbi/                # Power BI 配置（备用）
├── docker-compose.yml
├── Makefile
└── .env.example
```

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/loop/daily/morning` | GET | 晨间决策 |
| `/api/loop/daily/evening` | POST | 晚间闭环 |
| `/api/loop/weekly/run` | POST | 周复盘 |
| `/api/loop/monthly/run` | POST | 月报告 |
| `/api/loop/quarterly/run` | POST | 季度校准 |
| `/api/goals` | GET/POST | 目标管理 |
| `/api/assets` | GET/POST | 资产管理 |
| `/api/insights` | GET/POST | 洞察管理 |
| `/api/reviews` | GET | 复盘查询 |
| `/api/dashboard/stats` | GET | 仪表盘数据 |
| `/api/agents/{name}` | POST | 直接调用 Agent |

## 成本

| 项目 | 月成本 |
|------|--------|
| MiMo API | ~¥5-15 |
| 其他 | ¥0 |
| **总计** | **~¥5-15** |

## 成功标准

- ✅ 稳定运行 ≥ 60 天，日循环达成率 ≥ 80%
- ✅ 数据库已有 ≥ 60 条日志、≥ 4 份周复盘、≥ 20 个资产
- ✅ 主观感受：「成长是可见的、可控的、有方向的」

---

> 系统永远是手段，不是目的。
