import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.data_loader import load_meta_ads_data
from utils.rag_service import RAGService
from utils.agents import BudgetOptimizationAgent, BudgetOptimizationResult
from utils.ui_feedback import queue_completion_message, render_completion_message

st.set_page_config(page_title="💰 預算優化建議", page_icon="💰", layout="wide")


@st.cache_resource
def get_budget_agent() -> BudgetOptimizationAgent | None:
    try:
        return BudgetOptimizationAgent()
    except Exception as exc:
        st.error(f"❌ 無法初始化 BudgetOptimizationAgent：{exc}")
        return None


def compute_budget_metrics(df: pd.DataFrame) -> dict[str, float | None]:
    spend = df['花費金額 (TWD)'].sum() if '花費金額 (TWD)' in df else 0.0
    roas_col = '購買 ROAS（廣告投資報酬率）'
    revenue = (df['花費金額 (TWD)'] * df[roas_col]).sum() if roas_col in df and '花費金額 (TWD)' in df else 0.0
    profit = revenue - spend
    avg_roas = df[roas_col].mean() if roas_col in df else None
    avg_cpa = df['每次購買的成本'].mean() if '每次購買的成本' in df else None
    return {
        'total_spend': spend,
        'total_revenue': revenue,
        'avg_roas': avg_roas,
        'avg_cpa': avg_cpa,
        'total_profit': profit,
    }


def render_summary_cards(metrics: dict[str, float | None]) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("總花費", f"{metrics['total_spend']:,.0f} TWD")
    col2.metric("估算營收", f"{metrics['total_revenue']:,.0f} TWD")
    col3.metric("平均 ROAS", f"{metrics['avg_roas']:.2f}" if metrics['avg_roas'] is not None else "-")
    col4.metric("預估利潤", f"{metrics['total_profit']:,.0f} TWD")


def render_spend_chart(df: pd.DataFrame) -> None:
    if '行銷活動名稱' not in df or '花費金額 (TWD)' not in df or '購買 ROAS（廣告投資報酬率）' not in df:
        return
    grouped = (
        df.groupby('行銷活動名稱', as_index=False)
        .agg({'花費金額 (TWD)': 'sum', '購買 ROAS（廣告投資報酬率）': 'mean'})
        .sort_values('花費金額 (TWD)', ascending=False)
        .head(15)
    )
    fig = px.bar(
        grouped,
        x='行銷活動名稱',
        y='花費金額 (TWD)',
        color='購買 ROAS（廣告投資報酬率）',
        color_continuous_scale='Blues',
        title='花費最高的活動與 ROAS',
    )
    fig.update_layout(xaxis_title="活動", yaxis_title="花費 (TWD)", height=420)
    st.plotly_chart(fig, use_container_width=True)


def render_adjustments(title: str, adjustments: list) -> None:
    st.subheader(title)
    if not adjustments:
        st.info("目前沒有此類建議。")
        return
    for idx, adj in enumerate(adjustments, start=1):
        delta = adj.delta
        delta_str = f"{delta:,.0f} TWD"
        header = f"{adj.priority} {adj.campaign}"
        with st.expander(header, expanded=(idx == 1)):
            st.metric("建議花費", f"{adj.recommended_spend:,.0f} TWD", delta=delta_str)
            st.markdown(f"**理由**：{adj.rationale}")
            st.markdown(f"**預期影響**：{adj.expected_impact}")


def render_opportunities(opportunities: list) -> None:
    st.subheader("📈 成長機會")
    if not opportunities:
        st.info("暫無可再投資的活動。")
        return
    for opp in opportunities:
        with st.expander(f"🚀 {opp.name}", expanded=False):
            st.markdown(f"**目前花費**：{opp.current_spend:,.0f} TWD")
            st.markdown(f"**目前 ROAS**：{opp.current_roas:.2f}")
            st.markdown(f"**建議**：{opp.recommendation}")
            if opp.supporting_metrics:
                st.markdown("**佐證指標：**")
                for metric in opp.supporting_metrics:
                    st.markdown(f"- {metric}")


def render_experiments(experiments: list) -> None:
    st.subheader("🧪 實驗方案")
    if not experiments:
        st.info("暫無建議的預算實驗方案。")
        return
    for exp in experiments:
        with st.expander(f"🧪 {exp.name}", expanded=False):
            st.markdown(f"**假設**：{exp.hypothesis}")
            st.markdown(f"**主要指標**：{exp.metric}")
            st.markdown(f"**預算配置**：{exp.budget_split}")
            if exp.duration_days:
                st.markdown(f"**建議時長**：{exp.duration_days} 天")
            if exp.expected_result:
                st.markdown(f"**預期結果**：{exp.expected_result}")


def main() -> None:
    st.title("💰 預算優化建議")
    st.markdown("使用 Pydantic AI Agent 快速評估預算效益，提供具體調整策略。")

    df = load_meta_ads_data()
    if df is None or df.empty:
        st.error("❌ 無法載入數據，請確認資料檔案。")
        return

    metrics = compute_budget_metrics(df)
    render_summary_cards(metrics)
    render_spend_chart(df)

    st.markdown("### ⚙️ 預算設定")
    col1, col2, col3 = st.columns(3)
    with col1:
        target_roas = st.number_input("目標 ROAS", min_value=0.5, max_value=10.0, value=3.0, step=0.1)
    with col2:
        increase_threshold = st.number_input("預算不足門檻 (TWD)", min_value=50.0, max_value=5000.0, value=500.0, step=50.0)
    with col3:
        decrease_threshold = st.number_input("預算過高門檻 (TWD)", min_value=500.0, max_value=20000.0, value=3000.0, step=100.0)

    use_rag = st.checkbox(
        "🧠 啟用歷史案例增強 (RAG)",
        value=True,
        help="若啟用，Agent 會引用知識庫中的預算優化案例作為參考"
    )

    if st.button("🚀 啟動 BudgetOptimizationAgent", type="primary", use_container_width=True):
        agent = get_budget_agent()
        if agent is None:
            st.stop()

        rag_service = None
        rag_status_message = "📚 Step 2: 未啟用 RAG"

        with st.status("📋 Step 1: 初始化 Agent", expanded=True) as status:
            model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
            st.write("✓ Agent：**BudgetOptimizationAgent**")
            st.write(f"✓ 模型：**{model_name}**")
            st.write("✓ 輸出類型：**BudgetOptimizationResult**")
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
                        rag_status_message = "📚 Step 2: RAG 載入失敗"
                except Exception as exc:
                    st.write(f"⚠️ 載入失敗：{exc}")
                    rag_service = None
                    status.update(label="⚠️ Step 2: RAG 未啟用", state="error")
                    rag_status_message = "📚 Step 2: RAG 載入失敗"

        with st.status("🧠 Step 3: 生成預算優化建議", expanded=True) as status:
            st.write("📊 彙整帳戶預算指標…")
            st.write("🤖 正在產出調整策略…")
            try:
                result = agent.optimize_sync(
                    df=df,
                    target_roas=target_roas,
                    increase_threshold=increase_threshold,
                    decrease_threshold=decrease_threshold,
                    rag_service=rag_service,
                )
                status.update(label="✅ Step 3: 生成完成", state="complete")
                st.session_state['budget_result'] = result
                st.session_state['budget_generated_at'] = datetime.now()
                st.session_state['budget_rag_status'] = rag_status_message
                queue_completion_message("budget_optimization_agent", "✅ 預算優化建議已生成")
            except Exception as exc:
                status.update(label="❌ Step 3: 生成失敗", state="error")
                st.error(f"❌ 生成預算優化建議時發生錯誤：{exc}")
                import traceback
                with st.expander("🔍 錯誤詳情"):
                    st.code(traceback.format_exc())

    result: BudgetOptimizationResult | None = st.session_state.get('budget_result')
    if result:
        st.markdown("---")
        st.subheader("🤖 AI 預算優化總結")
        render_completion_message("budget_optimization_agent")

        generated_at = st.session_state.get('budget_generated_at')
        rag_status_message = st.session_state.get('budget_rag_status')
        if rag_status_message:
            st.caption(rag_status_message)
        if generated_at:
            st.caption(f"最後更新時間：{generated_at.strftime('%Y-%m-%d %H:%M:%S')}")

        summary = result.summary
        col1, col2, col3 = st.columns([1, 1, 2])
        col1.metric("整體 ROAS", f"{summary.overall_roas:.2f}")
        col2.metric("預算健康度", f"{summary.health_score}/100")
        with col3:
            st.markdown("**重點洞察**")
            for finding in summary.key_findings:
                st.markdown(f"- {finding}")

        if summary.watch_metrics:
            st.markdown("**建議追蹤指標：**")
            for metric in summary.watch_metrics:
                st.markdown(f"- {metric}")

        st.markdown("### 🚀 建議增加預算")
        render_adjustments("🚀 建議增加預算", result.increase_recommendations)

        st.markdown("### ⚠️ 建議減少/重新分配預算")
        render_adjustments("⚠️ 建議減少/重新分配預算", result.decrease_recommendations)

        st.subheader("🔄 預算重分配重點")
        plan = result.reallocation_plan
        st.metric("建議增加總額", f"{plan.increase_amount:,.0f} TWD")
        st.metric("建議減少總額", f"{plan.decrease_amount:,.0f} TWD")
        st.metric("重新分配總額", f"{plan.reinvest_amount:,.0f} TWD")
        if plan.notes:
            for note in plan.notes:
                st.markdown(f"- {note}")

        render_opportunities(result.growth_opportunities)
        render_experiments(result.experiments)
    else:
        st.info("點擊上方按鈕即可生成 AI 預算優化建議。")


if __name__ == "__main__":
    main()
