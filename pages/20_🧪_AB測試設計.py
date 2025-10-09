import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.data_loader import load_meta_ads_data
from utils.rag_service import RAGService
from utils.agents import ABTestDesignAgent, ABTestDesignResult
from utils.ui_feedback import queue_completion_message, render_completion_message

st.set_page_config(page_title="🧪 A/B 測試設計", page_icon="🧪", layout="wide")


@st.cache_resource
def get_ab_agent() -> ABTestDesignAgent | None:
    try:
        return ABTestDesignAgent()
    except Exception as exc:
        st.error(f"❌ 無法初始化 ABTestDesignAgent：{exc}")
        return None


def ensure_numeric(value: float | None) -> float:
    return float(value) if value is not None else 0.0


def render_baseline_chart(df: pd.DataFrame) -> None:
    if '連結點擊次數' not in df or '購買次數' not in df:
        return
    pivot = df.groupby(pd.to_datetime(df['開始']).dt.date).agg({
        '連結點擊次數': 'sum',
        '購買次數': 'sum'
    }).reset_index()
    if pivot.empty:
        return
    pivot['轉換率 (%)'] = pivot['購買次數'] / pivot['連結點擊次數'] * 100
    fig = px.line(pivot, x='開始', y='轉換率 (%)', title='每日轉換率趨勢')
    fig.update_layout(height=380, xaxis_title='日期', yaxis_title='轉換率 (%)')
    st.plotly_chart(fig, use_container_width=True)


def compute_baseline_metrics(df: pd.DataFrame) -> dict[str, float | None]:
    metrics = {}
    if '購買 ROAS（廣告投資報酬率）' in df:
        metrics['平均 ROAS'] = df['購買 ROAS（廣告投資報酬率）'].mean()
    if 'CTR（全部）' in df:
        metrics['平均 CTR (%)'] = df['CTR（全部）'].mean() * 100
    if '連結點擊次數' in df:
        metrics['每日平均連結點擊'] = df['連結點擊次數'].sum() / max(len(df), 1)
    if '購買次數' in df and '連結點擊次數' in df:
        total_clicks = df['連結點擊次數'].sum()
        metrics['轉換率 (%)'] = (df['購買次數'].sum() / total_clicks * 100) if total_clicks else 0
    return metrics


def render_metrics_card(metrics: dict[str, float | None]) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("平均 ROAS", f"{metrics.get('平均 ROAS', 0):.2f}")
    col2.metric("平均 CTR", f"{metrics.get('平均 CTR (%)', 0):.2f}%")
    col3.metric("每日平均連結點擊", f"{metrics.get('每日平均連結點擊', 0):,.0f}")
    col4.metric("轉換率", f"{metrics.get('轉換率 (%)', 0):.2f}%")


def main() -> None:
    st.title("🧪 A/B 測試設計")
    st.markdown("利用 Pydantic AI Agent 協助規劃實驗策略、變體與執行流程。")

    df = load_meta_ads_data()
    if df is None or df.empty:
        st.error("❌ 無法載入數據。")
        return

    df = df.copy()
    if '開始' in df:
        df['開始'] = pd.to_datetime(df['開始'], errors='coerce')

    render_baseline_chart(df)
    metrics = compute_baseline_metrics(df)
    render_metrics_card(metrics)

    st.markdown("### ⚙️ 測試設定")
    objective_options = ['提升 CTR', '提升轉換率', '提升 ROAS', '降低 CPA']
    objective = st.selectbox("測試目標", objective_options)
    use_rag = st.checkbox(
        "🧠 啟用歷史案例增強 (RAG)",
        value=True,
        help="若啟用，Agent 會引用已建立的成功案例提供靈感"
    )

    if st.button("🚀 生成 A/B 測試計畫", type="primary", use_container_width=True):
        agent = get_ab_agent()
        if agent is None:
            st.stop()

        rag_service = None
        rag_status_message = "📚 Step 2: 未啟用 RAG"

        with st.status("📋 Step 1: 初始化 Agent", expanded=True) as status:
            model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
            st.write("✓ Agent：**ABTestDesignAgent**")
            st.write(f"✓ 模型：**{model_name}**")
            st.write("✓ 輸出類型：**ABTestDesignResult**")
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

        with st.status("🧠 Step 3: 生成測試計畫", expanded=True) as status:
            st.write("📊 分析現有素材與受眾數據…")
            st.write("🤖 正在撰寫測試策略…")
            try:
                result = agent.design_sync(df=df, objective=objective, rag_service=rag_service)
                status.update(label="✅ Step 3: 生成完成", state="complete")
                st.session_state['abtest_result'] = result
                st.session_state['abtest_generated_at'] = datetime.now()
                st.session_state['abtest_rag_status'] = rag_status_message
                queue_completion_message("abtest_design_agent", "✅ A/B 測試計畫已生成")
            except Exception as exc:
                status.update(label="❌ Step 3: 生成失敗", state="error")
                st.error(f"❌ 生成測試計畫時發生錯誤：{exc}")
                import traceback
                with st.expander("🔍 錯誤詳情"):
                    st.code(traceback.format_exc())

    result: ABTestDesignResult | None = st.session_state.get('abtest_result')
    if result:
        st.markdown("---")
        st.subheader("🤖 AI A/B 測試計畫")
        render_completion_message("abtest_design_agent")

        generated_at = st.session_state.get('abtest_generated_at')
        rag_status_message = st.session_state.get('abtest_rag_status')
        if rag_status_message:
            st.caption(rag_status_message)
        if generated_at:
            st.caption(f"最後更新時間：{generated_at.strftime('%Y-%m-%d %H:%M:%S')}")

        st.markdown(result.overall_summary)

        if result.baseline_metrics:
            st.markdown("### 📊 基準指標")
            base_df = pd.DataFrame([
                {'指標': m.name, '數值': m.value} for m in result.baseline_metrics
            ])
            st.dataframe(base_df, use_container_width=True)

        if result.test_ideas:
            st.markdown("### 🧠 測試方案")
            for idea in result.test_ideas:
                with st.expander(f"{idea.priority} {idea.variable}", expanded=False):
                    st.markdown(f"**假設**：{idea.hypothesis}")
                    if idea.variations:
                        st.markdown("**變體設計：**")
                        for variation in idea.variations:
                            st.markdown(f"- {variation.name}: {variation.details}")
                    if idea.success_metrics:
                        st.markdown("**成功指標：**")
                        for metric in idea.success_metrics:
                            st.markdown(f"- {metric}")
                    if idea.guardrail_metrics:
                        st.markdown("**護欄指標：**")
                        for metric in idea.guardrail_metrics:
                            st.markdown(f"- {metric}")
                    st.markdown(f"**建議測試期**：{idea.test_duration}")
                    st.markdown(f"**預算配置**：{idea.budget_allocation}")
                    st.markdown(f"**預期影響**：{idea.expected_impact}")

        if result.sample_size_notes:
            st.markdown("### 📐 样本與時程建議")
            for note in result.sample_size_notes:
                st.markdown(f"- {note}")

        if result.risk_management:
            st.markdown("### ⚠️ 風險管理")
            for note in result.risk_management:
                st.markdown(f"- {note}")

        st.markdown("### 📋 執行檢查清單")
        checklist = result.execution_checklist
        st.markdown("**測試前：**")
        for item in checklist.before:
            st.markdown(f"- [ ] {item}")
        st.markdown("**測試中：**")
        for item in checklist.during:
            st.markdown(f"- [ ] {item}")
        st.markdown("**測試後：**")
        for item in checklist.after:
            st.markdown(f"- [ ] {item}")

        if result.advanced_strategies:
            st.markdown("### 💡 進階建議")
            for strategy in result.advanced_strategies:
                with st.expander(strategy.title, expanded=False):
                    st.write(strategy.description)
    else:
        st.info("點擊上方按鈕即可生成 AI 測試設計建議。")


if __name__ == "__main__":
    main()
