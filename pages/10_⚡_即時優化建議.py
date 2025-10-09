import os
import hashlib
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from utils.data_loader import load_meta_ads_data
from utils.rag_service import RAGService
from utils.agents import OptimizationAgent, OptimizationResult
from utils.ui_feedback import queue_completion_message, render_completion_message

RUN_BUTTON_KEY = "optimization_run_btn_" + hashlib.md5(__file__.encode("utf-8")).hexdigest()


st.set_page_config(page_title="⚡ 即時優化建議", page_icon="⚡", layout="wide")


@st.cache_resource
def get_optimization_agent() -> OptimizationAgent | None:
    """建立並快取 OptimizationAgent 實例。"""

    try:
        return OptimizationAgent()
    except Exception as exc:  # pragma: no cover - 初始化錯誤給 UI 顯示
        st.error(f"❌ 無法初始化 OptimizationAgent：{exc}")
        return None


def ensure_datetime(df: pd.DataFrame) -> tuple[pd.DataFrame, str | None]:
    """確保存在可用的日期欄位並轉換為 datetime。"""

    candidate_cols = [
        '開始',
        '日期',
        '開跑日期',
        '分析報告開始',
    ]

    date_col = next((col for col in candidate_cols if col in df.columns), None)
    if not date_col:
        return df, None

    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    return df, date_col


def filter_by_date(df: pd.DataFrame, date_col: str | None) -> pd.DataFrame:
    """根據使用者選擇的日期範圍篩選資料。"""

    if not date_col:
        return df

    valid_dates = df[date_col].dropna()
    if valid_dates.empty:
        return df

    min_date = valid_dates.min().date()
    max_date = valid_dates.max().date()
    default_start = max_date - timedelta(days=30)
    if default_start < min_date:
        default_start = min_date

    start_date, end_date = st.date_input(
        "選擇分析日期範圍",
        value=(default_start, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if isinstance(start_date, tuple):  # Streamlit 可能回傳 tuple
        start_date, end_date = start_date

    mask = (df[date_col] >= pd.to_datetime(start_date)) & (df[date_col] <= pd.to_datetime(end_date) + timedelta(days=1))
    filtered = df.loc[mask].copy()

    if filtered.empty:
        st.warning("所選日期範圍內沒有數據，已顯示完整資料供參考。")
        return df

    return filtered


def compute_summary_metrics(df: pd.DataFrame) -> dict[str, float | None]:
    """計算頁面上方的快速指標。"""

    metrics = {}
    metrics['avg_roas'] = float(df['購買 ROAS（廣告投資報酬率）'].mean()) if '購買 ROAS（廣告投資報酬率）' in df else None
    metrics['avg_cpa'] = float(df['每次購買的成本'].mean()) if '每次購買的成本' in df else None
    metrics['total_spend'] = float(df['花費金額 (TWD)'].sum()) if '花費金額 (TWD)' in df else None
    metrics['total_purchases'] = float(df['購買次數'].sum()) if '購買次數' in df else None
    metrics['avg_ctr'] = float(df['CTR（全部）'].mean() * 100) if 'CTR（全部）' in df else None
    return metrics


def build_campaign_table(df: pd.DataFrame) -> pd.DataFrame:
    """整理活動層級表格。"""

    required_cols = ['行銷活動名稱', '花費金額 (TWD)', '購買 ROAS（廣告投資報酬率）', '每次購買的成本']
    if not all(col in df.columns for col in required_cols):
        return pd.DataFrame()

    table = (
        df.groupby('行銷活動名稱', as_index=False)
        .agg({
            '花費金額 (TWD)': 'sum',
            '購買 ROAS（廣告投資報酬率）': 'mean',
            '每次購買的成本': 'mean',
            '觸及人數': 'sum'
        })
        .rename(columns={
            '花費金額 (TWD)': '花費 (TWD)',
            '購買 ROAS（廣告投資報酬率）': 'ROAS',
            '每次購買的成本': 'CPA',
            '觸及人數': '觸及人次'
        })
        .sort_values('花費 (TWD)', ascending=False)
        .head(15)
    )
    return table


def render_summary_cards(metrics: dict[str, float | None]) -> None:
    """顯示概要指標卡片。"""

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("平均 ROAS", f"{metrics['avg_roas']:.2f}" if metrics['avg_roas'] is not None else "-" )
    col2.metric("平均 CPA", f"{metrics['avg_cpa']:.0f} TWD" if metrics['avg_cpa'] is not None else "-")
    col3.metric("總花費", f"{metrics['total_spend']:.0f} TWD" if metrics['total_spend'] is not None else "-")
    col4.metric("總轉換", f"{metrics['total_purchases']:.0f}" if metrics['total_purchases'] is not None else "-")


def render_budget_table(recs: list) -> None:
    if not recs:
        st.info("暫無預算調整建議。")
        return

    df = pd.DataFrame([
        {
            '活動': rec.campaign,
            '目前花費': rec.current_spend,
            '建議花費': rec.recommended_spend,
            '差異': rec.delta,
            '動作': rec.action,
            '優先級': rec.priority,
            '理由': rec.rationale,
        }
        for rec in recs
    ])

    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            '目前花費': st.column_config.NumberColumn(format="%0.0f"),
            '建議花費': st.column_config.NumberColumn(format="%0.0f"),
            '差異': st.column_config.NumberColumn(format="%0.0f"),
        }
    )


def render_actions_section(actions: list) -> None:
    if not actions:
        st.success("目前沒有需要處理的項目 🎉")
        return

    for idx, action in enumerate(actions, start=1):
        header = f"{action.priority} {action.title}"
        with st.expander(header, expanded=(idx == 1)):
            st.write(action.description)
            st.markdown(f"**核心指標**：{action.metric}")
            st.markdown(f"**預期影響**：{action.impact}")
            if action.campaigns:
                st.markdown("**涉及活動**：" + ", ".join(action.campaigns))
            if action.recommended_steps:
                st.markdown("**建議步驟：**")
                for step in action.recommended_steps:
                    st.markdown(f"- {step}")


def render_experiments(experiments: list) -> None:
    if not experiments:
        st.info("暫無建議的實驗方案。")
        return

    for idx, exp in enumerate(experiments, start=1):
        with st.expander(f"🧪 實驗 {idx}：{exp.name}", expanded=(idx == 1)):
            st.markdown(f"**假設**：{exp.hypothesis}")
            st.markdown(f"**主要指標**：{exp.metric}")
            if exp.variations:
                st.markdown("**變體設計：**")
                for variation in exp.variations:
                    st.markdown(f"- {variation}")
            st.markdown(f"**預期結果**：{exp.expected_outcome}")


def main() -> None:
    st.title("⚡ 即時優化建議")
    st.markdown("利用 Pydantic AI Agent 快速盤點帳戶健康、鎖定緊急問題並規劃下一步行動。")

    df = load_meta_ads_data()
    if df is None or df.empty:
        st.error("❌ 無法載入廣告數據，請確認資料檔案是否存在。")
        return

    df, date_col = ensure_datetime(df)
    filtered_df = filter_by_date(df, date_col)

    st.markdown("### 📊 帳戶概況")
    metrics = compute_summary_metrics(filtered_df)
    render_summary_cards(metrics)

    campaign_table = build_campaign_table(filtered_df)
    if not campaign_table.empty:
        st.markdown("#### 🔝 花費最高的活動（前 15）")
        st.dataframe(
            campaign_table,
            use_container_width=True,
            column_config={
                '花費 (TWD)': st.column_config.NumberColumn(format="%0.0f"),
                'ROAS': st.column_config.NumberColumn(format="%.2f"),
                'CPA': st.column_config.NumberColumn(format="%0.0f"),
                '觸及人次': st.column_config.NumberColumn(format="%0.0f"),
            }
        )

    st.markdown("### ⚙️ 優化參數設定")
    col1, col2, col3 = st.columns(3)
    with col1:
        target_roas = st.number_input("目標 ROAS", min_value=0.5, max_value=10.0, value=3.0, step=0.1)
    with col2:
        max_cpa = st.number_input("最大 CPA (TWD)", min_value=50, max_value=2000, value=300, step=10)
    with col3:
        min_daily_budget = st.number_input("最小日預算 (TWD)", min_value=100, max_value=10000, value=500, step=50)

    st.markdown("### 🤖 AI 即時優化建議 (Pydantic Agent)")
    use_rag = st.checkbox(
        "🧠 啟用歷史案例增強 (RAG)",
        value=True,
        help="載入歷史高效案例，協助 Agent 生成更貼近品牌的建議"
    )

    run_agent = st.button(
        "🚀 啟動 OptimizationAgent",
        key=f"{RUN_BUTTON_KEY}_{st.session_state.get('optimization_button_nonce', 0)}",
        type="primary",
        use_container_width=True,
    )
    st.session_state['optimization_button_nonce'] = st.session_state.get('optimization_button_nonce', 0) + 1

    if run_agent:
        optimization_agent = get_optimization_agent()
        if optimization_agent is None:
            st.stop()

        rag_service = None
        rag_status_message = "📚 Step 2: 已跳過 RAG 知識庫"

        with st.status("📋 Step 1: 初始化 OptimizationAgent", expanded=True) as status:
            model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
            st.write("✓ Agent 類型：**OptimizationAgent**")
            st.write(f"✓ 模型：**{model_name}**（從 .env 讀取）")
            st.write("✓ 輸出類型：**OptimizationResult**")
            status.update(label="✅ Step 1: Agent 初始化完成", state="complete")

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
        else:
            rag_status_message = "📚 Step 2: 未啟用 RAG"

        with st.status("🧠 Step 3: 生成優化建議", expanded=True) as status:
            st.write("📊 整合最新數據與參數…")
            st.write("🤖 正在呼叫 Pydantic Agent…")

            try:
                result = optimization_agent.optimize_sync(
                    df=filtered_df,
                    target_roas=target_roas,
                    max_cpa=max_cpa,
                    min_daily_budget=min_daily_budget,
                    rag_service=rag_service,
                )
                st.write("✓ 產出優化建議套件")
                st.write("✓ 型別驗證通過（Pydantic）")
                status.update(label="✅ Step 3: 優化建議生成完成", state="complete")

                st.session_state['optimization_result'] = result
                st.session_state['optimization_generated_at'] = datetime.now()
                st.session_state['optimization_rag_status'] = rag_status_message
                queue_completion_message("optimization_agent", "✅ 即時優化建議分析完成")
            except Exception as exc:
                status.update(label="❌ Step 3: 生成失敗", state="error")
                st.error(f"❌ 生成優化建議時發生錯誤：{exc}")
                import traceback
                with st.expander("🔍 錯誤詳情"):
                    st.code(traceback.format_exc())

    optimization_result: OptimizationResult | None = st.session_state.get('optimization_result')

    if optimization_result:
        generated_at = st.session_state.get('optimization_generated_at')
        rag_status_message = st.session_state.get('optimization_rag_status')
        render_completion_message("optimization_agent")

        st.markdown("---")
        st.subheader("🤖 AI 優化總覽")

        if rag_status_message:
            st.caption(rag_status_message)
        if generated_at:
            st.caption(f"最後更新時間：{generated_at.strftime('%Y-%m-%d %H:%M:%S')}")

        summary = optimization_result.summary
        col1, col2, col3 = st.columns([1, 1, 2])
        col1.metric("帳戶健康分數", f"{summary.health_score}/100")
        col2.metric("狀態評估", summary.overall_status)
        with col3:
            st.markdown("**關鍵洞察**")
            for insight in summary.key_insights:
                st.markdown(f"- {insight}")

        focus_col1, focus_col2 = st.columns(2)
        with focus_col1:
            st.markdown("**優先聚焦領域**")
            for area in summary.focus_areas:
                st.markdown(f"- {area}")
        with focus_col2:
            st.markdown("**下一步行動**")
            for step in summary.next_steps:
                st.markdown(f"- {step}")

        st.markdown("---")
        st.subheader("🚨 高優先級行動")
        render_actions_section(optimization_result.urgent_actions)

        st.subheader("📈 成長機會與優化建議")
        render_actions_section(optimization_result.opportunities)

        st.subheader("💰 預算重新分配建議")
        render_budget_table(optimization_result.budget_recommendations)

        st.subheader("🧪 實驗計畫")
        render_experiments(optimization_result.experiment_plan)

        if optimization_result.watchlist:
            st.subheader("👀 監控清單")
            for item in optimization_result.watchlist:
                st.markdown(f"- {item}")
    else:
        st.info("點擊上方按鈕即可生成最新的 AI 優化建議。")


if __name__ == "__main__":
    main()
