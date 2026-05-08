import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os

DB_PATH = os.getenv('SQLITE_DB_PATH', os.path.join(os.path.dirname(__file__), '..', 'data', 'growth.db'))

@st.cache_resource
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def query(sql, params=None):
    conn = get_conn()
    return pd.read_sql_query(sql, conn, params=params or [])

st.set_page_config(page_title='Personal Growth OS', page_icon='🌱', layout='wide')
st.title('🌱 Personal Growth OS')

tab1, tab2, tab3, tab4 = st.tabs(['📊 行动看板', '📦 资产看板', '🧠 认知看板', '🎯 主线看板'])

with tab1:
    st.header('行动看板')
    col1, col2, col3, col4 = st.columns(4)

    # 30-day completion rate
    df_30d = query('SELECT completed FROM daily_logs WHERE log_date >= date("now", "-30 days")')
    rate = (df_30d['completed'].sum() / len(df_30d) * 100) if len(df_30d) > 0 else 0
    col1.metric('30天完成率', f'{rate:.0f}%')

    # Streak
    df_all = query('SELECT log_date, completed FROM daily_logs ORDER BY log_date DESC')
    streak = 0
    for _, row in df_all.iterrows():
        if row['completed']:
            streak += 1
        else:
            break
    col2.metric('连续天数', f'{streak}天')

    # Average mood this week
    df_week = query('SELECT mood, energy FROM daily_logs WHERE log_date >= date("now", "-7 days")')
    avg_mood = df_week['mood'].mean() if len(df_week) > 0 else 0
    avg_energy = df_week['energy'].mean() if len(df_week) > 0 else 0
    col3.metric('本周平均情绪', f'{avg_mood:.1f}/5')
    col4.metric('本周平均精力', f'{avg_energy:.1f}/5')

    # Mood + Energy trend
    st.subheader('情绪 & 精力趋势（近30天）')
    df_trend = query('SELECT log_date, mood, energy FROM daily_logs WHERE log_date >= date("now", "-30 days") ORDER BY log_date')
    if len(df_trend) > 0:
        df_trend['log_date'] = pd.to_datetime(df_trend['log_date'])
        st.line_chart(df_trend.set_index('log_date')[['mood', 'energy']])

    # Completion by day of week
    st.subheader('按星期统计完成率')
    df_dow = query('''
        SELECT
            CASE CAST(strftime('%w', log_date) AS INTEGER)
                WHEN 0 THEN '日' WHEN 1 THEN '一' WHEN 2 THEN '二'
                WHEN 3 THEN '三' WHEN 4 THEN '四' WHEN 5 THEN '五'
                WHEN 6 THEN '六'
            END as weekday,
            COUNT(*) as total,
            SUM(completed) as done
        FROM daily_logs
        GROUP BY strftime('%w', log_date)
        ORDER BY strftime('%w', log_date)
    ''')
    if len(df_dow) > 0:
        df_dow['rate'] = (df_dow['done'] / df_dow['total'] * 100).round(0)
        st.bar_chart(df_dow.set_index('weekday')['rate'])

    # Recent logs
    st.subheader('最近7天记录')
    df_recent = query('''
        SELECT log_date as 日期, core_task as 核心任务,
               CASE completed WHEN 1 THEN '✅' ELSE '❌' END as 完成,
               mood as 情绪, energy as 精力, ai_summary as AI总结
        FROM daily_logs ORDER BY log_date DESC LIMIT 7
    ''')
    if len(df_recent) > 0:
        st.dataframe(df_recent, use_container_width=True)

with tab2:
    st.header('资产看板')
    col1, col2 = st.columns(2)

    total = query('SELECT COUNT(*) as cnt FROM assets')
    col1.metric('资产总数', int(total['cnt'].iloc[0]))

    df_types = query('SELECT type, COUNT(*) as count FROM assets GROUP BY type')
    if len(df_types) > 0:
        col2.bar_chart(df_types.set_index('type'))

    st.subheader('资产质量分布')
    df_quality = query('SELECT quality, COUNT(*) as count FROM assets GROUP BY quality ORDER BY quality')
    if len(df_quality) > 0:
        st.bar_chart(df_quality.set_index('quality'))

    st.subheader('最近资产')
    df_assets = query('SELECT title as 标题, type as 类型, quality as 质量, created_at as 创建时间 FROM assets ORDER BY created_at DESC LIMIT 10')
    if len(df_assets) > 0:
        st.dataframe(df_assets, use_container_width=True)

with tab3:
    st.header('认知看板')
    col1, col2, col3 = st.columns(3)

    total_insights = query('SELECT COUNT(*) as cnt FROM insights')
    col1.metric('洞察总数', int(total_insights['cnt'].iloc[0]))

    df_types = query('SELECT type, COUNT(*) as count FROM insights GROUP BY type')
    if len(df_types) > 0:
        col2.bar_chart(df_types.set_index('type'))

    avg_conf = query('SELECT AVG(confidence) as avg FROM insights')
    col3.metric('平均置信度', f'{avg_conf["avg"].iloc[0]:.1f}/5' if avg_conf['avg'].iloc[0] else 'N/A')

    st.subheader('最近洞察')
    df_ins = query('SELECT content as 内容, type as 类型, confidence as 置信度, created_at as 时间 FROM insights ORDER BY created_at DESC LIMIT 10')
    if len(df_ins) > 0:
        st.dataframe(df_ins, use_container_width=True)

with tab4:
    st.header('主线看板')

    df_goals = query('SELECT title as 目标, level as 层级, status as 状态, progress as 进度 FROM goals WHERE deleted_at IS NULL ORDER BY level')
    if len(df_goals) > 0:
        for _, g in df_goals.iterrows():
            st.write(f'**[{g["层级"]}] {g["目标"]}** — {g["状态"]}')
            st.progress(g['进度'] / 100 if g['进度'] else 0)

    st.subheader('复盘记录')
    df_reviews = query('SELECT period as 周期, start_date as 开始, end_date as 结束, completion_rate as 完成率 FROM reviews ORDER BY start_date DESC LIMIT 10')
    if len(df_reviews) > 0:
        st.dataframe(df_reviews, use_container_width=True)

    st.subheader('AI 成本统计')
    df_cost = query('''
        SELECT agent_name as Agent, COUNT(*) as 调用次数,
               ROUND(SUM(cost_usd), 4) as 总成本,
               ROUND(AVG(latency_ms), 0) as 平均延迟ms
        FROM ai_interactions WHERE status='success'
        GROUP BY agent_name ORDER BY 总成本 DESC
    ''')
    if len(df_cost) > 0:
        st.dataframe(df_cost, use_container_width=True)
