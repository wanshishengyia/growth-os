# Personal Growth OS - Complete Implementation Plan

> **Goal:** Build a complete AI-driven personal growth operating system with 7 agents, 4 time-scale loops, Telegram bot, and data visualization.

**Architecture:** FastAPI backend + Supabase (PostgreSQL) + 7 AI Agents + Telegram Bot + n8n automation + Power BI dashboards

**Tech Stack:** Python 3.11+, FastAPI, Supabase, Claude/OpenAI API, python-telegram-bot, n8n, Power BI

---

## Phase 1: Foundation (Database + Backend + Agents)

### Task 1.1: Project Scaffolding
- [ ] Create monorepo structure
- [ ] requirements.txt with all dependencies
- [ ] .env.example
- [ ] Makefile
- [ ] Dockerfile
- [ ] docker-compose.yml

### Task 1.2: Database Schema
- [ ] SQL init script (7 tables + indexes + triggers + views)
- [ ] Supabase client wrapper
- [ ] Seed data script for testing

### Task 1.3: Pydantic Models
- [ ] All 7 table models (Goal, DailyLog, Insight, Asset, Review, EnvironmentRule, AIInteraction)
- [ ] Agent I/O schemas (7 agents × input + output)
- [ ] API request/response models

### Task 1.4: Prompt Library
- [ ] 7 Agent prompt files (v1.0)
- [ ] Prompt loader with versioning support

### Task 1.5: AI Client
- [ ] Unified LLM client (Claude + OpenAI)
- [ ] Token counting + cost tracking
- [ ] Retry + timeout + fallback logic

### Task 1.6: Agent Implementations
- [ ] Base Agent class
- [ ] A1 Action Decider
- [ ] A2 Loop Closer
- [ ] A3 Pattern Finder
- [ ] A4 Asset Classifier
- [ ] A5 Insight Miner
- [ ] A6 Socratic Questioner
- [ ] A7 Direction Calibrator
- [ ] Agent Router

### Task 1.7: API Endpoints
- [ ] Loop endpoints (morning/evening/weekly/monthly/quarterly)
- [ ] CRUD endpoints (goals/assets/insights/reviews)
- [ ] Agent direct-call endpoints
- [ ] Dashboard stats endpoint
- [ ] Health check

### Task 1.8: Business Rules Engine
- [ ] 6 core rules implementation
- [ ] Rule executor service

## Phase 2: Interaction Layer (Telegram Bot + Obsidian)

### Task 2.1: Telegram Bot
- [ ] Bot setup + command handlers
- [ ] /morning, /night, /review commands
- [ ] InlineKeyboard for mood/energy
- [ ] Message formatting

### Task 2.2: Obsidian Integration
- [ ] Daily Note template
- [ ] Weekly/Monthly templates
- [ ] File writer service

## Phase 3: Automation (n8n Workflows)

### Task 3.1: n8n Setup
- [ ] Docker deployment
- [ ] 7 workflow definitions

## Phase 4: Visualization (Power BI)

### Task 4.1: Database Views
- [ ] Aggregation views for dashboards

### Task 4.2: Dashboard Specs
- [ ] 4 dashboard definitions

---

## Execution Order
1. Tasks 1.1-1.4 in parallel (foundation)
2. Task 1.5 (AI client)
3. Task 1.6 (agents)
4. Task 1.7-1.8 (API + rules)
5. Phase 2
6. Phase 3
7. Phase 4
