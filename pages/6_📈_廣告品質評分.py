import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.data_loader import load_meta_ads_data
from utils.rag_service import RAGService
from utils.agents import QualityScoreAgent, QualityAnalysisResult

st.set_page_config(page_title="📈 廣告品質評分", page_icon="📈", layout="wide")


@st.cache_resource
def get_quality_agent() -> QualityScoreAgent | None:
    try:
        return QualityScoreAgent()
    except Exception as exc:
        st.error(f"❌ 無法初始化 QualityScoreAgent：{exc}")
        return None


def compute_quality_overview(df: pd.DataFrame) -> dict:
    overview = {}
    for col in ['品質排名', '互動率排名', '轉換率排名']:
        if col in df.columns:
            overview[col] = df[col].value_counts().to_dict()
    score_cols = [col for col in df.columns if col.endswith('分數')]
    score_summary = {}
    for col in score_cols:
        score_summary[col] = {
            'mean': float(df[col].mean()),
            'median': float(df[col].median()),
            'max': float(df[col].max()),
        }
    overview['scores'] = score_summary
    return overview


def render_distribution_pies(df: pd.DataFrame) -> None:
    color_map = {
        '平均以上': '#2ecc71',
        '平均': '#f39c12',
        '平均以下': '#e74c3c',
        '未知': '#95a5a6'
    }
    cols = st.columns(3)
    for idx, col in enumerate(['品質排名', '互動率排名', '轉換率排名']):
        if col not in df.columns:
            continue
        distribution = df[col].value_counts()
        fig = px.pie(
            names=distribution.index,
            values=distribution.values,
            title=f"{col} 分布",
            color=distribution.index,
            color_discrete_map=color_map,
            hole=0.4
        )
        fig.update_layout(height=320)
        cols[idx % 3].plotly_chart(fig, use_container_width=True)


def render_score_hist(df: pd.DataFrame) -> None:
    score_cols = [col for col in df.columns if col.endswith('分數')]
    if not score_cols:
        return
    tab = st.tabs(score_cols)
    for idx, col in enumerate(score_cols):
        with tab[idx]:
            fig = px.histogram(df[df[col] > 0], x=col, nbins=25, title=f"{col} 分布")
            fig.update_layout(height=360)
            st.plotly_chart(fig, use_container_width=True)
            col1, col2, col3 = st.columns(3)
            filtered = df[df[col] > 0][col]
            if not filtered.empty:
                col1.metric("平均", f"{filtered.mean():.2f}")
                col2.metric("中位數", f"{filtered.median():.2f}")
                col3.metric("最高分", f"{filtered.max():.2f}")


def render_low_quality_table(df: pd.DataFrame) -> None:
    if '品質排名' not in df:
        return
    low_df = df[df['品質排名'] == '平均以下']
    if low_df.empty:
        st.success("目前沒有品質排名平均以下的廣告。")
        return
    st.markdown("### ⚠️ 品質待優化廣告")
    columns = ['廣告名稱', '行銷活動名稱', '花費金額 (TWD)', '購買 ROAS（廣告投資報酬率）', 'CTR（全部）', '互動率排名', '轉換率排名']
    existing = [col for col in columns if col in low_df.columns]
    st.dataframe(low_df[existing].sort_values('花費金額 (TWD)', ascending=False).head(20), use_container_width=True)


def render_issues(issues: list) -> None:
    st.subheader("🚨 需優先處理的問題")
    if not issues:
        st.info("暫無高優先級問題。")
        return
    for issue in issues:
        with st.expander(f"{issue.priority} {issue.title}", expanded=False):
            st.write(issue.description)
            if issue.impacted_ads:
                st.markdown("**受影響廣告：**")
                for ad in issue.impacted_ads:
                    st.markdown(f"- {ad}")
            if issue.recommended_actions:
                st.markdown("**建議措施：**")
                for action in issue.recommended_actions:
                    st.markdown(f"- {action}")
            if issue.metrics_to_watch:
                st.markdown("**追蹤指標：**")
                for metric in issue.metrics_to_watch:
                    st.markdown(f"- {metric}")


def render_experiments(experiments: list) -> None:
    st.subheader("🧪 品質提升實驗")
    if not experiments:
        st.info("暫無實驗建議。")
        return
    for exp in experiments:
        with st.expander(exp.name, expanded=False):
            st.markdown(f"**假設**：{exp.hypothesis}")
            if exp.steps:
                st.markdown("**執行步驟：**")
                for step in exp.steps:
                    st.markdown(f"- {step}")
            st.markdown(f"**預期結果**：{exp.expected_outcome}")


def main() -> None:
    st.title("📈 廣告品質評分")
    st.markdown("透過 Pydantic AI Agent 分析品質排名，快速掌握帳戶健康狀況。")

    df = load_meta_ads_data()
    if df is None or df.empty:
        st.error("❌ 無法載入數據。")
        return

    render_distribution_pies(df)
    render_score_hist(df)
    render_low_quality_table(df)

    st.markdown("### 🤖 AI 品質診斷")
    use_rag = st.checkbox(
        "🧠 啟用歷史案例增強 (RAG)",
        value=True,
        help="若啟用，Agent 會引用知識庫中的品質提升案例"
    )

    if st.button("🚀 啟動 QualityScoreAgent", type="primary", use_container_width=True):
        agent = get_quality_agent()
        if agent is None:
            st.stop()

        rag_service = None
        rag_status_message = "📚 Step 2: 未啟用 RAG"

        with st.status("📋 Step 1: 初始化 Agent", expanded=True) as status:
            model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
            st.write("✓ Agent：**QualityScoreAgent**")
            st.write(f"✓ 模型：**{model_name}**")
            st.write("✓ 輸出類型：**QualityAnalysisResult**")
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

        with st.status("🧠 Step 3: 生成品質建議", expanded=True) as status:
            st.write("📊 整理品質數據…")
            st.write("🤖 正在產出診斷…")
            try:
                result = agent.analyze_sync(df=df, rag_service=rag_service)
                status.update(label="✅ Step 3: 生成完成", state="complete")
                st.session_state['quality_result'] = result
                st.session_state['quality_generated_at'] = datetime.now()
                st.session_state['quality_rag_status'] = rag_status_message
            except Exception as exc:
                status.update(label="❌ Step 3: 生成失敗", state="error")
                st.error(f"❌ 生成品質分析時發生錯誤：{exc}")
                import traceback
                with st.expander("🔍 錯誤詳情"):
                    st.code(traceback.format_exc())

    result: QualityAnalysisResult | None = st.session_state.get('quality_result')
    if result:
        st.markdown("---")
        st.subheader("🤖 AI 品質總結")

        generated_at = st.session_state.get('quality_generated_at')
        rag_status_message = st.session_state.get('quality_rag_status')
        if rag_status_message:
            st.caption(rag_status_message)
        if generated_at:
            st.caption(f"最後更新時間：{generated_at.strftime('%Y-%m-%d %H:%M:%S')}")

        summary = result.summary
        st.metric("品質健康度", f"{summary.health_score}/100")
        st.markdown(f"**整體狀態**：{summary.overall_status}")
        st.markdown("**亮點：**")
        for s in summary.strengths:
            st.markdown(f"- {s}")
        st.markdown("**弱點：**")
        for w in summary.weaknesses:
            st.markdown(f"- {w}")
        if summary.improvement_focus:
            st.markdown("**優先改善方向：**")
            for focus in summary.improvement_focus:
                st.markdown(f"- {focus}")

        render_issues(result.issues)
        render_experiments(result.experiments)
    else:
        st.info("點擊上方按鈕即可生成 AI 品質分析報告。")


if __name__ == "__main__":
    main()
