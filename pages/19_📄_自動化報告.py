import os
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.data_loader import load_meta_ads_data
from utils.rag_service import RAGService
from utils.agents import ReportGenerationAgent, ReportGenerationResult
from utils.ui_feedback import queue_completion_message, render_completion_message

st.set_page_config(page_title="📄 自動化報告", page_icon="📄", layout="wide")


@st.cache_resource
def get_report_agent() -> ReportGenerationAgent | None:
    try:
        return ReportGenerationAgent()
    except Exception as exc:
        st.error(f"❌ 無法初始化 ReportGenerationAgent：{exc}")
        return None


def ensure_datetime(df: pd.DataFrame) -> pd.DataFrame:
    if '開始' in df:
        df = df.copy()
        df['開始'] = pd.to_datetime(df['開始'], errors='coerce')
    return df


def compute_metrics(df: pd.DataFrame) -> dict[str, float | None]:
    if df.empty:
        return {}
    spend = df['花費金額 (TWD)'].sum() if '花費金額 (TWD)' in df else 0
    roas = df['購買 ROAS（廣告投資報酬率）'].mean() if '購買 ROAS（廣告投資報酬率）' in df else None
    purchases = df['購買次數'].sum() if '購買次數' in df else None
    ctr = df['CTR（全部）'].mean() * 100 if 'CTR（全部）' in df else None
    return {
        '花費': spend,
        '平均 ROAS': roas,
        '總購買數': purchases,
        '平均 CTR (%)': ctr,
    }


def render_metric_cards(metrics: dict[str, float | None]) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("花費", f"{metrics.get('花費', 0):,.0f} TWD")
    col2.metric("平均 ROAS", f"{metrics.get('平均 ROAS', 0):.2f}" if metrics.get('平均 ROAS') is not None else "-")
    col3.metric("總購買數", f"{metrics.get('總購買數', 0):,.0f}" if metrics.get('總購買數') is not None else "-")
    col4.metric("平均 CTR", f"{metrics.get('平均 CTR (%)', 0):.2f}%" if metrics.get('平均 CTR (%)') is not None else "-")


def render_campaign_table(df: pd.DataFrame, title: str, ascending: bool = False) -> None:
    if df.empty:
        st.info(f"目前沒有{title}資料。")
        return
    order = '購買 ROAS（廣告投資報酬率）'
    table = df.sort_values(order, ascending=ascending).head(10)
    st.dataframe(
        table,
        use_container_width=True,
        column_config={
            '花費金額 (TWD)': st.column_config.NumberColumn(format="%0.0f"),
            '購買 ROAS（廣告投資報酬率）': st.column_config.NumberColumn(format="%0.2f"),
            '購買次數': st.column_config.NumberColumn(format="%0.0f"),
            'CTR（全部）': st.column_config.NumberColumn(format="%0.2f"),
        }
    )


def render_spend_trend(df: pd.DataFrame, start: datetime, end: datetime) -> None:
    period = df[(df['開始'] >= start) & (df['開始'] <= end)]
    if period.empty:
        return
    grouped = period.groupby('開始', as_index=False)['花費金額 (TWD)'].sum()
    fig = px.line(grouped, x='開始', y='花費金額 (TWD)', title='期間內每日花費')
    fig.update_layout(height=380, xaxis_title='日期', yaxis_title='花費 (TWD)')
    st.plotly_chart(fig, use_container_width=True)


def get_previous_period(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    delta = end - start
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - delta
    return prev_start, prev_end


def main() -> None:
    st.title("📄 自動化報告")
    st.markdown("以 Pydantic AI Agent 快速生成週報/月報，掌握投放重點與行動計畫。")

    df = load_meta_ads_data()
    if df is None or df.empty:
        st.error("❌ 無法載入數據。")
        return

    df = ensure_datetime(df)
    if '開始' not in df or df['開始'].isna().all():
        st.error("❌ 無法取得日期欄位，請確認資料是否包含 '開始' 欄位。")
        return

    max_date = df['開始'].max().date()

    report_type = st.selectbox(
        "選擇報告類型",
        options=["週報（最近 7 天）", "月報（最近 30 天）", "自訂期間"],
    )

    if report_type == "自訂期間":
        start_date, end_date = st.date_input(
            "選擇報告期間",
            value=(max_date - timedelta(days=6), max_date),
            max_value=max_date,
        )
    elif report_type == "週報（最近 7 天）":
        start_date = max_date - timedelta(days=6)
        end_date = max_date
    else:
        start_date = max_date - timedelta(days=29)
        end_date = max_date

    if start_date > end_date:
        st.error("❌ 開始日期必須早於結束日期")
        return

    current_start = pd.to_datetime(start_date)
    current_end = pd.to_datetime(end_date) + timedelta(days=1) - timedelta(seconds=1)
    prev_start, prev_end = get_previous_period(current_start, current_end)

    period_df = df[(df['開始'] >= current_start) & (df['開始'] <= current_end)]
    if period_df.empty:
        st.warning("所選期間沒有數據。")
    else:
        st.markdown("### 📊 期間概況")
        render_metric_cards(compute_metrics(period_df))
        render_spend_trend(df, current_start, current_end)

        st.markdown("### 🏷️ 活動表現概覽")
        grouped = period_df.groupby('行銷活動名稱', as_index=False).agg({
            '花費金額 (TWD)': 'sum',
            '購買 ROAS（廣告投資報酬率）': 'mean',
            '購買次數': 'sum',
            'CTR（全部）': 'mean'
        })
        if not grouped.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### 🏆 高效活動")
                render_campaign_table(grouped.copy(), "高效活動", ascending=False)
            with col2:
                st.markdown("#### ⚠️ 需改善活動")
                render_campaign_table(grouped.copy(), "待改善活動", ascending=True)

    st.markdown("### 🤖 AI 自動化報告")
    use_rag = st.checkbox(
        "🧠 啟用歷史案例增強 (RAG)",
        value=True,
        help="若啟用，Agent 會引用知識庫中的成功案例"
    )

    if st.button("🚀 生成報告", type="primary", use_container_width=True):
        agent = get_report_agent()
        if agent is None:
            st.stop()

        rag_service = None
        rag_status_message = "📚 Step 2: 未啟用 RAG"

        with st.status("📋 Step 1: 初始化 Agent", expanded=True) as status:
            model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
            st.write("✓ Agent：**ReportGenerationAgent**")
            st.write(f"✓ 模型：**{model_name}**")
            st.write("✓ 輸出類型：**ReportGenerationResult**")
            status.update(label="✅ Step 1: 初始化完成", state="complete")

        if use_rag:
            with st.status("📚 Step 2: 載入 RAG 知識庫", expanded=True) as status:
                try:
                    rag_service = RAGService()
                    if rag_service.load_knowledge_base("ad_creatives"):
                        st.write("✓ 知識庫：**ad_creatives**")
                        st.write("✓ 檢索模式：語義搜尋 (Top 3)")
                        status.update(label="✅ Step 2: RAG 載入完成", state="complete")
                        rag_status_message = "📚 Step 2: 已載入 RAG 知識庫"
                    else:
                        st.write("⚠️ 知識庫載入失敗，將改用一般模式")
                        rag_service = None
                        status.update(label="⚠️ Step 2: RAG 未啟用", state="error")
                        rag_status_message = "📚 Step 2: RAG 失敗"
                except Exception as exc:
                    st.write(f"⚠️ 載入失敗：{exc}")
                    rag_service = None
                    status.update(label="⚠️ Step 2: RAG 未啟用", state="error")
                    rag_status_message = "📚 Step 2: RAG 失敗"

        with st.status("🧠 Step 3: 生成報告", expanded=True) as status:
            st.write("📊 整理指標與活動資料…")
            st.write("🤖 正在撰寫報告內容…")
            try:
                result = agent.generate_sync(
                    df=df,
                    current_start=current_start,
                    current_end=current_end,
                    previous_start=prev_start,
                    previous_end=prev_end,
                    rag_service=rag_service,
                )
                status.update(label="✅ Step 3: 生成完成", state="complete")
                st.session_state['report_result'] = result
                st.session_state['report_generated_at'] = datetime.now()
                st.session_state['report_rag_status'] = rag_status_message
                queue_completion_message("report_generation_agent", "✅ 自動化報告已生成")
            except Exception as exc:
                status.update(label="❌ Step 3: 生成失敗", state="error")
                st.error(f"❌ 生成報告時發生錯誤：{exc}")
                import traceback
                with st.expander("🔍 錯誤詳情"):
                    st.code(traceback.format_exc())

    result: ReportGenerationResult | None = st.session_state.get('report_result')
    if result:
        st.markdown("---")
        st.subheader("🤖 AI 自動化報告")
        render_completion_message("report_generation_agent")

        timestamp = st.session_state.get('report_generated_at')
        rag_status_message = st.session_state.get('report_rag_status')
        if rag_status_message:
            st.caption(rag_status_message)
        if timestamp:
            st.caption(f"最後更新時間：{timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

        summary = result.summary
        st.markdown(f"**報告類型**：{summary.report_type}")
        st.markdown(f"**期間**：{summary.period}")
        st.markdown(f"**整體狀態**：{summary.overall_status}")

        if summary.key_insights:
            st.markdown("### 📌 關鍵洞察")
            for insight in summary.key_insights:
                st.markdown(f"- {insight}")

        if summary.metrics:
            st.markdown("### 📊 指標比較")
            metric_df = pd.DataFrame([
                {
                    '指標': m.name,
                    '本期': m.current_value,
                    '前期': m.previous_value,
                    '變化 (%)': m.change_percent,
                }
                for m in summary.metrics
            ])
            st.dataframe(
                metric_df,
                use_container_width=True,
                column_config={
                    '本期': st.column_config.NumberColumn(format="%0.2f"),
                    '前期': st.column_config.NumberColumn(format="%0.2f"),
                    '變化 (%)': st.column_config.NumberColumn(format="%0.2f"),
                }
            )

        if result.successes:
            st.markdown("### 🏆 成功案例")
            for item in result.successes:
                with st.expander(item.name, expanded=False):
                    st.markdown(f"**花費**：{item.spend:,.0f} TWD")
                    st.markdown(f"**ROAS**：{item.roas:.2f}")
                    if item.ctr is not None:
                        st.markdown(f"**CTR**：{item.ctr:.2f}%")
                    if item.conversions is not None:
                        st.markdown(f"**轉換數**：{item.conversions:,.0f}")
                    if item.notes:
                        st.markdown(f"**成功因素**：{item.notes}")

        if result.issues:
            st.markdown("### ⚠️ 需改善項目")
            for item in result.issues:
                with st.expander(item.name, expanded=False):
                    st.markdown(f"**花費**：{item.spend:,.0f} TWD")
                    st.markdown(f"**ROAS**：{item.roas:.2f}")
                    if item.ctr is not None:
                        st.markdown(f"**CTR**：{item.ctr:.2f}%")
                    if item.conversions is not None:
                        st.markdown(f"**轉換數**：{item.conversions:,.0f}")
                    if item.notes:
                        st.markdown(f"**分析**：{item.notes}")

        if result.action_plan:
            st.markdown("### ✅ 行動計畫")
            for item in result.action_plan:
                st.markdown(f"**{item.priority} {item.action}** — {item.expected_impact} ({item.timeline})")

        if result.strategies:
            st.markdown("### 💡 策略建議")
            for strategy in result.strategies:
                with st.expander(strategy.title, expanded=False):
                    st.write(strategy.description)
    else:
        st.info("點擊上方按鈕即可生成 AI 自動化報告。")


if __name__ == "__main__":
    main()
