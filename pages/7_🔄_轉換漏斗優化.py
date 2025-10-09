import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.data_loader import load_meta_ads_data
from utils.rag_service import RAGService
from utils.agents import FunnelAnalysisAgent, FunnelAnalysisResult
from utils.ui_feedback import queue_completion_message, render_completion_message

st.set_page_config(page_title="🔄 轉換漏斗優化", page_icon="🔄", layout="wide")


@st.cache_resource
def get_funnel_agent() -> FunnelAnalysisAgent | None:
    try:
        return FunnelAnalysisAgent()
    except Exception as exc:
        st.error(f"❌ 無法初始化 FunnelAnalysisAgent：{exc}")
        return None


def ensure_stage_mapping(df: pd.DataFrame) -> dict[str, str]:
    candidates = {
        '觸及': '觸及人數',
        '曝光': '曝光次數',
        '點擊': '連結點擊次數',
        '頁面瀏覽': '連結頁面瀏覽次數',
        '內容瀏覽': '內容瀏覽次數',
        '加入購物車': '加到購物車次數',
        '開始結帳': '開始結帳次數',
        '完成購買': '購買次數',
    }
    mapping = {}
    for stage, column in candidates.items():
        if column in df.columns and df[column].sum() > 0:
            mapping[stage] = column
    return mapping


def compute_funnel_dataframe(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    data = []
    previous = None
    for stage, column in mapping.items():
        value = float(df[column].sum())
        if previous is None:
            conv = 100.0
            drop = 0.0
        else:
            conv = (value / previous * 100) if previous else 0.0
            drop = 100 - conv
        data.append({'階段': stage, '數量': value, '轉換率': conv, '流失率': drop})
        previous = value
    return pd.DataFrame(data)


def render_funnel_chart(funnel_df: pd.DataFrame) -> None:
    fig = go.Figure(go.Funnel(
        y=funnel_df['階段'],
        x=funnel_df['數量'],
        textinfo="value+percent previous",  # percent relative to previous stage
        connector=dict(line=dict(color='gray', width=2)),
        marker=dict(color=px.colors.sequential.Aggrnyl[: len(funnel_df)])
    ))
    fig.update_layout(title="整體轉換漏斗", height=500)
    st.plotly_chart(fig, use_container_width=True)


def render_waterfall(funnel_df: pd.DataFrame) -> None:
    values = [funnel_df['數量'].iloc[0]]
    text = [f"{int(values[0]):,}"]
    for _, row in funnel_df.iloc[1:].iterrows():
        delta = row['數量'] - funnel_df['數量'].iloc[0]
        values.append(row['數量'] - values[-1])
        text.append(f"{row['數量']:,.0f}")

    fig = go.Figure(go.Waterfall(
        name="漏斗流失",
        orientation="v",
        measure=['absolute'] + ['relative'] * (len(funnel_df) - 1),
        x=funnel_df['階段'],
        y=[funnel_df['數量'].iloc[0]] + [funnel_df['數量'].iloc[i] - funnel_df['數量'].iloc[i - 1] for i in range(1, len(funnel_df))],
        text=text,
        decreasing={"marker": {"color": "#e74c3c"}},
        increasing={"marker": {"color": "#2ecc71"}},
        connector={"line": {"color": "gray"}}
    ))
    fig.update_layout(title="漏斗瀑布圖", height=450, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


def render_stage_table(funnel_df: pd.DataFrame) -> None:
    st.dataframe(
        funnel_df,
        use_container_width=True,
        column_config={
            '數量': st.column_config.NumberColumn(format="%0.0f"),
            '轉換率': st.column_config.NumberColumn(format="%0.2f"),
            '流失率': st.column_config.NumberColumn(format="%0.2f"),
        },
    )


def render_segment_chart(df: pd.DataFrame, stage_mapping: dict[str, str], column: str) -> None:
    if column not in df.columns:
        st.info("此分群欄位在資料中不存在。")
        return

    top_groups = df[column].value_counts().head(4).index.tolist()
    if not top_groups:
        st.info("沒有足夠的分群資料可供比較。")
        return

    fig = go.Figure()
    for group in top_groups:
        group_df = df[df[column] == group]
        prev = None
        rates = []
        labels = []
        for stage, col in stage_mapping.items():
            if col not in group_df:
                continue
            count = float(group_df[col].sum())
            if prev is None:
                rate = 100.0
            else:
                rate = (count / prev * 100) if prev else 0.0
            rates.append(rate)
            labels.append(stage)
            prev = count

        if rates:
            fig.add_trace(go.Scatter(x=labels, y=rates, mode='lines+markers', name=str(group)))

    fig.update_layout(
        title=f"{column} 分群轉換率對比",
        xaxis_title="階段",
        yaxis_title="相對轉換率 (%)",
        hovermode='x unified',
        height=450,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_actions(actions: list) -> None:
    if not actions:
        st.success("目前沒有高優先級瓶頸，維持現有策略即可。")
        return

    for idx, action in enumerate(actions, start=1):
        with st.expander(f"{action.priority} {action.title}", expanded=(idx == 1)):
            st.write(action.description)
            st.markdown(f"**目標階段**：{action.target_stage}")
            st.markdown(f"**預期影響**：{action.expected_impact}")
            if action.kpis:
                st.markdown("**追蹤指標：**")
                for kpi in action.kpis:
                    st.markdown(f"- {kpi}")
            if action.steps:
                st.markdown("**建議步驟：**")
                for step in action.steps:
                    st.markdown(f"- {step}")


def render_experiments(experiments: list) -> None:
    if not experiments:
        st.info("暫無建議的實驗方案。")
        return

    for idx, exp in enumerate(experiments, start=1):
        with st.expander(f"🧪 實驗 {idx}：{exp.name}", expanded=(idx == 1)):
            st.markdown(f"**假設**：{exp.hypothesis}")
            st.markdown(f"**主要指標**：{exp.metric}")
            if exp.audience:
                st.markdown(f"**適用受眾**：{exp.audience}")
            if exp.duration_days:
                st.markdown(f"**預估時長**：{exp.duration_days} 天")
            if exp.expected_result:
                st.markdown(f"**預期結果**：{exp.expected_result}")


def main() -> None:
    st.title("🔄 轉換漏斗優化")
    st.markdown("以 Pydantic AI Agent 快速掌握漏斗瓶頸，提供具體優化行動。")

    df = load_meta_ads_data()
    if df is None or df.empty:
        st.error("❌ 無法載入廣告數據，請確認資料檔案是否存在。")
        return

    stage_mapping = ensure_stage_mapping(df)
    if len(stage_mapping) < 2:
        st.warning("資料中可用的漏斗階段不足，請確認欄位是否完整。")
        return

    funnel_df = compute_funnel_dataframe(df, stage_mapping)

    st.markdown("### 📊 整體漏斗概況")
    render_funnel_chart(funnel_df)
    render_waterfall(funnel_df)
    render_stage_table(funnel_df)

    st.markdown("### 🔍 分群對比")
    segment_choices = [col for col in ['裝置', '平台', '年齡', '性別'] if col in df.columns]
    selected_segment = st.selectbox(
        "選擇要檢視的分群欄位",
        options=segment_choices,
        index=0 if segment_choices else None,
    )
    if selected_segment:
        render_segment_chart(df, stage_mapping, selected_segment)

    st.markdown("### ⚙️ AI 漏斗分析 (Pydantic Agent)")
    use_rag = st.checkbox(
        "🧠 啟用歷史案例增強 (RAG)",
        value=True,
        help="若 RAG 知識庫已建置，Agent 會引用歷史成功案例洞察"
    )

    run_agent = st.button("🚀 啟動 FunnelAnalysisAgent", type="primary", use_container_width=True)

    if run_agent:
        funnel_agent = get_funnel_agent()
        if funnel_agent is None:
            st.stop()

        rag_service = None
        rag_status_message = "📚 Step 2: 未啟用 RAG"

        with st.status("📋 Step 1: 初始化 FunnelAnalysisAgent", expanded=True) as status:
            model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
            st.write("✓ Agent 類型：**FunnelAnalysisAgent**")
            st.write(f"✓ 模型：**{model_name}**")
            st.write("✓ 輸出類型：**FunnelAnalysisResult**")
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
                        rag_status_message = "📚 Step 2: RAG 載入失敗，使用一般模式"
                except Exception as exc:
                    st.write(f"⚠️ 載入失敗：{exc}")
                    rag_service = None
                    status.update(label="⚠️ Step 2: RAG 未啟用", state="error")
                    rag_status_message = "📚 Step 2: RAG 載入失敗，使用一般模式"

        with st.status("🧠 Step 3: 生成漏斗洞察", expanded=True) as status:
            st.write("📊 彙整漏斗指標…")
            st.write("🤖 正在分析瓶頸與建議…")
            try:
                result = funnel_agent.analyze_sync(
                    df=df,
                    conversion_stage_columns=stage_mapping,
                    segment_columns=['裝置', '平台', '年齡', '性別'],
                    rag_service=rag_service,
                )
                status.update(label="✅ Step 3: 分析完成", state="complete")
                st.session_state['funnel_analysis_result'] = result
                st.session_state['funnel_analysis_generated_at'] = datetime.now()
                st.session_state['funnel_analysis_rag_status'] = rag_status_message
                queue_completion_message("funnel_analysis_agent", "✅ 漏斗分析完成")
            except Exception as exc:
                status.update(label="❌ Step 3: 分析失敗", state="error")
                st.error(f"❌ 產生漏斗分析時發生錯誤：{exc}")
                import traceback
                with st.expander("🔍 錯誤詳情"):
                    st.code(traceback.format_exc())

    analysis_result: FunnelAnalysisResult | None = st.session_state.get('funnel_analysis_result')

    if analysis_result:
        st.markdown("---")
        st.subheader("🤖 AI 漏斗總結")
        render_completion_message("funnel_analysis_agent")

        generated_at = st.session_state.get('funnel_analysis_generated_at')
        rag_status_message = st.session_state.get('funnel_analysis_rag_status')
        if rag_status_message:
            st.caption(rag_status_message)
        if generated_at:
            st.caption(f"最後更新時間：{generated_at.strftime('%Y-%m-%d %H:%M:%S')}")

        summary = analysis_result.summary
        col1, col2, col3 = st.columns([1, 1, 2])
        col1.metric("整體轉換率", f"{summary.overall_conversion_rate:.2f}%")
        col2.metric("健康度", f"{summary.health_score}/100")
        with col3:
            st.markdown("**重點洞察**")
            for insight in summary.key_findings:
                st.markdown(f"- {insight}")

        st.markdown(f"**主要瓶頸階段**：{summary.main_bottleneck}")

        if summary.watch_metrics:
            st.markdown("**建議追蹤指標：**")
            for metric in summary.watch_metrics:
                st.markdown(f"- {metric}")

        st.markdown("### 📈 各階段細節 (AI 摘要)")
        stage_rows = []
        for stage in analysis_result.stages:
            stage_rows.append({
                '階段': stage.name,
                '人數/次數': stage.count,
                '轉換率 (%)': stage.conversion_rate,
                '流失率 (%)': stage.drop_rate,
                '基準值': stage.benchmark,
                '備註': stage.note,
            })
        stage_df = pd.DataFrame(stage_rows)
        st.dataframe(
            stage_df,
            use_container_width=True,
            column_config={
                '人數/次數': st.column_config.NumberColumn(format="%0.0f"),
                '轉換率 (%)': st.column_config.NumberColumn(format="%0.2f"),
                '流失率 (%)': st.column_config.NumberColumn(format="%0.2f"),
                '基準值': st.column_config.NumberColumn(format="%0.2f"),
            },
        )

        st.markdown("### 🎯 分群洞察")
        if analysis_result.segment_insights:
            for insight in analysis_result.segment_insights:
                with st.expander(insight.segment_name, expanded=False):
                    st.markdown(f"**最佳階段**：{insight.best_stage} ({insight.best_stage_metric:.2f}%)")
                    st.markdown(f"**最需優化**：{insight.worst_stage} ({insight.worst_stage_metric:.2f}%)")
                    if insight.opportunities:
                        st.markdown("**建議行動：**")
                        for opp in insight.opportunities:
                            st.markdown(f"- {opp}")
        else:
            st.info("尚無分群洞察資料。")

        st.markdown("### ✅ 優化建議列表")
        render_actions(analysis_result.actions)

        st.markdown("### 🧪 實驗方案建議")
        render_experiments(analysis_result.experiments)
    else:
        st.info("點擊上方按鈕即可生成 AI 漏斗分析報告。")


if __name__ == "__main__":
    main()
