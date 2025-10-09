import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.data_loader import load_meta_ads_data
from utils.rag_service import RAGService
from utils.agents import CreativePerformanceAgent, CreativeAnalysisResult
from utils.ui_feedback import queue_completion_message, render_completion_message

st.set_page_config(page_title="🎨 素材成效分析", page_icon="🎨", layout="wide")


@st.cache_resource
def get_creative_agent() -> CreativePerformanceAgent | None:
    try:
        return CreativePerformanceAgent()
    except Exception as exc:
        st.error(f"❌ 無法初始化 CreativePerformanceAgent：{exc}")
        return None


def compute_creative_metrics(df: pd.DataFrame) -> dict[str, float | None]:
    metrics = {
        'total_creatives': len(df),
        'avg_roas': float(df['購買 ROAS（廣告投資報酬率）'].mean()) if '購買 ROAS（廣告投資報酬率）' in df else None,
        'avg_ctr': float(df['CTR（全部）'].mean() * 100) if 'CTR（全部）' in df else None,
        'avg_cpa': float(df['每次購買的成本'].mean()) if '每次購買的成本' in df else None,
    }
    return metrics


def render_summary_cards(metrics: dict[str, float | None]) -> None:
    col1, col2, col3 = st.columns(3)
    col1.metric("素材數量", f"{metrics['total_creatives']:,}")
    col2.metric("平均 ROAS", f"{metrics['avg_roas']:.2f}" if metrics['avg_roas'] else "-")
    col3.metric("平均 CTR", f"{metrics['avg_ctr']:.2f}%" if metrics['avg_ctr'] else "-")


def render_top_creatives(df: pd.DataFrame) -> None:
    if 'headline' not in df or '內文' not in df:
        st.info("目前資料缺少 Headline 或內文欄位，無法顯示素材明細。")
        return

    grouped = (
        df.groupby('headline', as_index=False)
        .agg({
            '購買 ROAS（廣告投資報酬率）': 'mean',
            'CTR（全部）': 'mean',
            '花費金額 (TWD)': 'sum',
            '購買次數': 'sum'
        })
        .sort_values('購買 ROAS（廣告投資報酬率）', ascending=False)
        .head(10)
    )

    fig = px.bar(
        grouped,
        x='購買 ROAS（廣告投資報酬率）',
        y='headline',
        orientation='h',
        color='CTR（全部）',
        title='Top 10 高 ROAS Headline',
        color_continuous_scale='Blues'
    )
    fig.update_layout(height=480, xaxis_title="ROAS", yaxis_title="Headline")
    st.plotly_chart(fig, use_container_width=True)


def render_segment_performance(df: pd.DataFrame) -> None:
    if '行銷活動名稱' not in df or '購買 ROAS（廣告投資報酬率）' not in df:
        return
    top_campaigns = (
        df.groupby('行銷活動名稱', as_index=False)
        .agg({'花費金額 (TWD)': 'sum', '購買 ROAS（廣告投資報酬率）': 'mean', 'CTR（全部）': 'mean'})
        .sort_values('花費金額 (TWD)', ascending=False)
        .head(10)
    )
    fig = px.scatter(
        top_campaigns,
        x='花費金額 (TWD)',
        y='購買 ROAS（廣告投資報酬率）',
        size='CTR（全部）',
        size_max=30,
        hover_name='行銷活動名稱',
        title='活動層級素材表現'
    )
    fig.update_layout(height=420, xaxis_title="花費 (TWD)", yaxis_title="ROAS")
    st.plotly_chart(fig, use_container_width=True)


def render_summary_table(metrics: list) -> None:
    if not metrics:
        st.info("尚無素材指標資料。")
        return
    df = pd.DataFrame([
        {
            '類型': m.name,
            '內容': m.value,
            'ROAS': m.roas,
            'CTR (%)': m.ctr,
            'CPA': m.cpa,
            '轉換數': m.conversions,
            '曝光數': m.impressions,
            '花費 (TWD)': m.spend,
        }
        for m in metrics
    ])
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            'ROAS': st.column_config.NumberColumn(format="%0.2f"),
            'CTR (%)': st.column_config.NumberColumn(format="%0.2f"),
            'CPA': st.column_config.NumberColumn(format="%0.0f"),
            '轉換數': st.column_config.NumberColumn(format="%0.0f"),
            '曝光數': st.column_config.NumberColumn(format="%0.0f"),
            '花費 (TWD)': st.column_config.NumberColumn(format="%0.0f"),
        }
    )


def render_insights(insights: list) -> None:
    st.subheader("🔍 主要洞察")
    if not insights:
        st.info("暫無洞察。")
        return
    for insight in insights:
        with st.expander(insight.title, expanded=False):
            st.write(insight.description)
            if insight.supporting_examples:
                st.markdown("**範例：**")
                for example in insight.supporting_examples:
                    st.markdown(f"- {example}")


def render_optimizations(optimizations: list) -> None:
    st.subheader("✅ 優化建議")
    if not optimizations:
        st.info("暫無具體優化建議。")
        return
    for opt in optimizations:
        with st.expander(f"{opt.priority} {opt.focus_area}", expanded=False):
            st.markdown("**建議步驟：**")
            for step in opt.action_steps:
                st.markdown(f"- {step}")
            st.markdown(f"**預期影響**：{opt.expected_impact}")
            if opt.metrics_to_watch:
                st.markdown("**追蹤指標：**")
                for metric in opt.metrics_to_watch:
                    st.markdown(f"- {metric}")


def render_experiments(experiments: list) -> None:
    st.subheader("🧪 素材實驗方案")
    if not experiments:
        st.info("暫無建議的素材實驗方案。")
        return
    for exp in experiments:
        with st.expander(exp.name, expanded=False):
            st.markdown(f"**假設**：{exp.hypothesis}")
            if exp.variations:
                st.markdown("**測試變體：**")
                for variation in exp.variations:
                    st.markdown(f"- {variation}")
            st.markdown(f"**主要指標**：{exp.primary_metric}")
            if exp.duration_days:
                st.markdown(f"**建議時長**：{exp.duration_days} 天")


def main() -> None:
    st.title("🎨 素材成效分析")
    st.markdown("透過 Pydantic AI Agent 分析素材表現，快速取得洞察與優化策略。")

    df = load_meta_ads_data()
    if df is None or df.empty:
        st.error("❌ 無法載入素材數據。")
        return

    metrics = compute_creative_metrics(df)
    render_summary_cards(metrics)
    render_top_creatives(df)
    render_segment_performance(df)

    st.markdown("### ⚙️ AI 素材分析設定")
    segment_options = [col for col in ['行銷活動名稱', '廣告組合名稱', '裝置', '年齡'] if col in df.columns]
    group_column = st.selectbox(
        "分群欄位",
        options=segment_options,
        index=0 if segment_options else None,
        help="AI 會針對此欄位做素材成效的差異比較"
    )
    use_rag = st.checkbox(
        "🧠 啟用歷史案例增強 (RAG)",
        value=True,
        help="若啟用，Agent 會引用知識庫中的素材優化案例"
    )

    if st.button("🚀 啟動 CreativePerformanceAgent", type="primary", use_container_width=True):
        agent = get_creative_agent()
        if agent is None:
            st.stop()

        rag_service = None
        rag_status_message = "📚 Step 2: 未啟用 RAG"

        with st.status("📋 Step 1: 初始化 Agent", expanded=True) as status:
            model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
            st.write("✓ Agent：**CreativePerformanceAgent**")
            st.write(f"✓ 模型：**{model_name}**")
            st.write("✓ 輸出類型：**CreativeAnalysisResult**")
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

        with st.status("🧠 Step 3: 生成素材洞察", expanded=True) as status:
            st.write("📊 整理素材指標…")
            st.write("🤖 正在產出分析與建議…")
            try:
                result = agent.analyze_sync(
                    df=df,
                    group_column=group_column or '行銷活動名稱',
                    rag_service=rag_service,
                )
                status.update(label="✅ Step 3: 產出完成", state="complete")
                st.session_state['creative_analysis_result'] = result
                st.session_state['creative_generated_at'] = datetime.now()
                st.session_state['creative_rag_status'] = rag_status_message
                queue_completion_message("creative_performance_agent", "✅ AI 素材洞察已生成")
            except Exception as exc:
                status.update(label="❌ Step 3: 生成失敗", state="error")
                st.error(f"❌ 生成素材分析時發生錯誤：{exc}")
                import traceback
                with st.expander("🔍 錯誤詳情"):
                    st.code(traceback.format_exc())

    result: CreativeAnalysisResult | None = st.session_state.get('creative_analysis_result')
    if result:
        st.markdown("---")
        st.subheader("🤖 AI 素材成效總結")
        render_completion_message("creative_performance_agent")

        generated_at = st.session_state.get('creative_generated_at')
        rag_status_message = st.session_state.get('creative_rag_status')
        if rag_status_message:
            st.caption(rag_status_message)
        if generated_at:
            st.caption(f"最後更新時間：{generated_at.strftime('%Y-%m-%d %H:%M:%S')}")

        summary = result.summary
        st.markdown("### 📌 整體摘要")
        render_summary_table(summary.top_creatives)
        render_summary_table(summary.low_creatives)

        if summary.fatigue_signals:
            st.warning("**素材疲勞警訊**：")
            for signal in summary.fatigue_signals:
                st.markdown(f"- {signal}")

        render_insights(result.insights)
        render_optimizations(result.optimizations)
        render_experiments(result.experiments)
    else:
        st.info("點擊上方按鈕即可生成 AI 素材分析報告。")


if __name__ == "__main__":
    main()
