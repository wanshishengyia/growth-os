# Feishu (飞书) Integration Setup for Growth OS

## Overview

Growth OS uses Feishu to send formatted notifications (morning decisions, evening reviews, weekly reports, alerts). There are two messaging modes:

1. **Incoming Webhook** (simplest) — sends messages to a Feishu group chat
2. **Bot API** (advanced) — sends direct messages to a specific user

---

## Option 1: Incoming Webhook (Recommended to start)

### Steps

1. **Open Feishu** and go to the group chat where you want to receive messages.

2. **Add a Custom Bot**:
   - Click the group name (top) → **Settings** (设置) → **Bots** (机器人)
   - Click **Add Bot** (添加机器人) → **Custom Bot** (自定义机器人)
   - Give it a name (e.g. "Growth OS") and optionally an avatar
   - Click **Create**

3. **Copy the Webhook URL**:
   - The URL looks like: `https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
   - Copy this entire URL

4. **Configure `.env`**:
   ```bash
   FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your-actual-webhook-id
   ```

5. **Test**:
   ```bash
   curl -X POST "$FEISHU_WEBHOOK_URL" \
     -H "Content-Type: application/json" \
     -d '{"msg_type":"text","content":{"text":"Hello from Growth OS!"}}'
   ```

---

## Option 2: Bot API (Direct Messages)

Use this if you want to receive DMs instead of group messages.

### Steps

1. **Go to [Feishu Open Platform](https://open.feishu.cn/app)**

2. **Create an App** (or use your existing app):
   - App ID: `cli_a945e2c820fb9bd4`
   - Note down the **App ID** and **App Secret**

3. **Enable Permissions**:
   - Go to **Permissions & Scopes** (权限管理)
   - Enable: `im:message:send_as_bot` (send messages as bot)

4. **Get your User Open ID**:
   - Your Feishu user open_id: `ou_0e89ec7ff241057d91d3fd7fac83eb24`
   - (This is auto-detected from your Feishu session)

5. **Configure `.env`**:
   ```bash
   FEISHU_APP_ID=cli_a945e2c820fb9bd4
   FEISHU_APP_SECRET=your-app-secret
   FEISHU_USER_ID=ou_0e89ec7ff241057d91d3fd7fac83eb24
   ```

6. **Publish the App** (if new):
   - Go to **App Versions** → **Create Version** → **Submit for Review**
   - Once approved, the bot can send messages

---

## Configuration Summary

| Variable | Required | Description |
|---|---|---|
| `FEISHU_WEBHOOK_URL` | Webhook mode | Group bot webhook URL |
| `FEISHU_APP_ID` | Bot API mode | Feishu app ID |
| `FEISHU_APP_SECRET` | Bot API mode | Feishu app secret |
| `FEISHU_USER_ID` | Bot API mode | Recipient's open_id |

**You only need one mode**: either the webhook URL or the app credentials. If both are configured, DM-capable methods (like `send_dm`) use Bot API; others fall back to webhook.

---

## Message Types

The `FeishuMessenger` sends rich **card messages** with color-coded headers:

| Method | Header | Color | Use Case |
|---|---|---|---|
| `send_morning()` | ☀️ 早安 · 今日决策 | Blue | Daily morning task decision |
| `send_evening()` | 🌙 晚安 · 今日分析 | Green | Evening reflection |
| `send_review()` | 📋 周复盘 | Purple | Weekly review report |
| `send_status()` | 📊 系统状态 | Indigo | System dashboard |
| `send_assets()` | 🗂 最近资产 | Orange | Recent assets list |
| `send_insights()` | 💡 最近洞察 | Yellow | Recent insights |
| `send_alert()` | ⚠️ ... | Red | Alerts & errors |

---

## Architecture Note

The old Telegram Bot used polling (`run_polling()`) with command handlers. The new Feishu integration is **push-only** (send messages, no receive). Command input is handled via the FastAPI REST API endpoints instead:

- `POST /api/loops/morning` → triggers morning decision → sends card via Feishu
- `POST /api/loops/night` → triggers evening loop → sends card via Feishu
- `POST /api/reviews/weekly` → triggers weekly review → sends card via Feishu
- `GET /api/dashboard/stats` → system stats (use Feishu to notify)
