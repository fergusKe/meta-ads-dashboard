import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.data_loader import load_meta_ads_data
from utils.rag_service import RAGService
from utils.agents import AudienceExpansionAgent, AudienceExpansionResult
from utils.ui_feedback import queue_completion_message, render_completion_message

st.set_page_config(page_title="👥 受眾擴展建議", page_icon="👥", layout="wide")


@st.cache_resource
def get_audience_agent() -> AudienceExpansionAgent | None:
    try:
        return AudienceExpansionAgent()
    except Exception as exc:
        st.error(f"❌ 無法初始化 AudienceExpansionAgent：{exc}")
        return None


def compute_audience_overview(df: pd.DataFrame) -> dict:
    overview = {}
    if '年齡' in df:
        overview['age'] = df.groupby('年齡')['花費金額 (TWD)'].sum().to_dict()
    if '性別' in df:
        overview['gender'] = df.groupby('性別')['花費金額 (TWD)'].sum().to_dict()
    if '目標' in df:
        overview['goal'] = df.groupby('目標')['花費金額 (TWD)'].sum().to_dict()
    return overview


def render_performance_heatmap(df: pd.DataFrame) -> None:
    if '年齡' not in df or '性別' not in df or '購買 ROAS（廣告投資報酬率）' not in df:
        st.info("資料不足以繪製受眾表現熱圖。")
        return
    pivot = df.pivot_table(
        values='購買 ROAS（廣告投資報酬率）',
        index='年齡',
        columns='性別',
        aggfunc='mean'
    )
    fig = px.imshow(
        pivot,
        color_continuous_scale='RdYlGn',
        title='受眾 ROAS 熱圖 (年齡 x 性別)',
        aspect='auto'
    )
    fig.update_layout(height=420)
    st.plotly_chart(fig, use_container_width=True)


def render_top_segments(df: pd.DataFrame) -> None:
    if '目標' not in df or '購買 ROAS（廣告投資報酬率）' not in df:
        return
    top = (
        df.groupby('目標', as_index=False)
        .agg({'購買 ROAS（廣告投資報酬率）': 'mean', '花費金額 (TWD)': 'sum', '購買次數': 'sum'})
        .sort_values('購買 ROAS（廣告投資報酬率）', ascending=False)
        .head(10)
    )
    fig = px.bar(
        top,
        x='購買 ROAS（廣告投資報酬率）',
        y='目標',
        orientation='h',
        title='Top 受眾目標 ROAS',
        hover_data=['花費金額 (TWD)', '購買次數']
    )
    fig.update_layout(height=420, xaxis_title="ROAS", yaxis_title="受眾")
    st.plotly_chart(fig, use_container_width=True)


def render_core_audiences(core_audiences: list) -> None:
    st.subheader("🏆 現有高效受眾摘要")
    if not core_audiences:
        st.info("目前沒有辨識出高效受眾。")
        return
    df = pd.DataFrame([
        {
            '年齡': audience.age,
            '性別': audience.gender,
            '目標': audience.interest,
            'ROAS': audience.roas,
            'CTR (%)': audience.ctr,
            '花費 (TWD)': audience.spend,
            '轉換數': audience.conversions,
        }
        for audience in core_audiences
    ])
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            'ROAS': st.column_config.NumberColumn(format="%0.2f"),
            'CTR (%)': st.column_config.NumberColumn(format="%0.2f"),
            '花費 (TWD)': st.column_config.NumberColumn(format="%0.0f"),
            '轉換數': st.column_config.NumberColumn(format="%0.0f"),
        }
    )


def render_expansion_audiences(expansion_audiences: list) -> None:
    st.subheader("🚀 受眾擴展提案")
    if not expansion_audiences:
        st.info("暫無受眾擴展建議。")
        return
    for audience in expansion_audiences:
        with st.expander(f"{audience.priority} {audience.title}", expanded=False):
            st.markdown(f"**受眾輪廓**：{audience.demo_profile}")
            st.markdown(f"**相似度**：{audience.similarity}")
            st.markdown(f"**預期 ROAS**：{audience.expected_roas}")
            st.markdown(f"**建議測試預算**：{audience.test_budget}")
            st.markdown(f"**建議測試期**：{audience.test_duration}")
            if audience.success_metrics:
                st.markdown("**成功指標：**")
                for metric in audience.success_metrics:
                    st.markdown(f"- {metric}")


def render_lookalike_strategies(strategies: list) -> None:
    st.subheader("🎯 Lookalike 策略")
    if not strategies:
        st.info("暫無 Lookalike 建議。")
        return
    for strategy in strategies:
        with st.expander(strategy.source_audience, expanded=False):
            st.markdown(f"**相似度設定**：{strategy.similarity}")
            if strategy.regions:
                st.markdown(f"**建議地區**：{', '.join(strategy.regions)}")
            st.markdown(f"**策略說明**：{strategy.rationale}")
            st.markdown(f"**預期成效**：{strategy.expected_scale}")


def render_watchout_audiences(watchouts: list) -> None:
    st.subheader("⚠️ 需避免的受眾")
    if not watchouts:
        st.info("目前沒有需要特別避免的受眾。")
        return
    for audience in watchouts:
        st.warning(f"**{audience.description}** — {audience.reason}")


def render_execution_plan(plan: list) -> None:
    st.subheader("🗓️ 30 天執行計畫")
    if not plan:
        st.info("尚未提供執行計畫。")
        return
    df = pd.DataFrame([
        {'週別': item.week, '重點': '\n'.join(item.focus)} for item in plan
    ])
    st.dataframe(df, use_container_width=True)


def main() -> None:
    st.title("👥 受眾擴展建議")
    st.markdown("透過 Pydantic AI Agent 分析受眾表現，探索新的成長機會。")

    df = load_meta_ads_data()
    if df is None or df.empty:
        st.error("❌ 無法載入數據。")
        return

    render_performance_heatmap(df)
    render_top_segments(df)

    st.markdown("### ⚙️ AI 受眾擴展設定")
    use_rag = st.checkbox(
        "🧠 啟用歷史案例增強 (RAG)",
        value=True,
        help="若啟用，Agent 會引用知識庫中的受眾擴展案例"
    )

    if st.button("🚀 啟動 AudienceExpansionAgent", type="primary", use_container_width=True):
        agent = get_audience_agent()
        if agent is None:
            st.stop()

        rag_service = None
        rag_status_message = "📚 Step 2: 未啟用 RAG"

        with st.status("📋 Step 1: 初始化 Agent", expanded=True) as status:
            model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
            st.write("✓ Agent：**AudienceExpansionAgent**")
            st.write(f"✓ 模型：**{model_name}**")
            st.write("✓ 輸出類型：**AudienceExpansionResult**")
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

        with st.status("🧠 Step 3: 生成受眾擴展建議", expanded=True) as status:
            st.write("📊 分析現有受眾表現…")
            st.write("🤖 正在產出擴展策略…")
            try:
                result = agent.analyze_sync(df=df, rag_service=rag_service)
                status.update(label="✅ Step 3: 生成完成", state="complete")
                st.session_state['audience_result'] = result
                st.session_state['audience_generated_at'] = datetime.now()
                st.session_state['audience_rag_status'] = rag_status_message
                queue_completion_message("audience_expansion_agent", "✅ 受眾擴展建議已生成")
            except Exception as exc:
                status.update(label="❌ Step 3: 生成失敗", state="error")
                st.error(f"❌ 生成受眾擴展建議時發生錯誤：{exc}")
                import traceback
                with st.expander("🔍 錯誤詳情"):
                    st.code(traceback.format_exc())

    result: AudienceExpansionResult | None = st.session_state.get('audience_result')
    if result:
        st.markdown("---")
        st.subheader("🤖 AI 受眾擴展總結")
        render_completion_message("audience_expansion_agent")

        generated_at = st.session_state.get('audience_generated_at')
        rag_status_message = st.session_state.get('audience_rag_status')
        if rag_status_message:
            st.caption(rag_status_message)
        if generated_at:
            st.caption(f"最後更新時間：{generated_at.strftime('%Y-%m-%d %H:%M:%S')}")

        summary = result.summary
        st.metric("受眾健康度", summary.health_status)
        st.markdown("**關鍵洞察：**")
        for insight in summary.key_insights:
            st.markdown(f"- {insight}")
        if summary.recommended_metrics:
            st.markdown("**建議追蹤指標：**")
            for metric in summary.recommended_metrics:
                st.markdown(f"- {metric}")

        render_core_audiences(result.core_audiences)
        render_expansion_audiences(result.expansion_audiences)
        render_lookalike_strategies(result.lookalike_strategies)
        render_watchout_audiences(result.watchout_audiences)
        render_execution_plan(result.execution_plan)
    else:
        st.info("點擊上方按鈕即可生成 AI 受眾擴展建議。")


if __name__ == "__main__":
    main()
