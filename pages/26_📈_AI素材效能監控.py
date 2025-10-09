import asyncio
from datetime import datetime

import pandas as pd
import streamlit as st

from utils import creative_store
from utils.agents.creative_performance_agent import CreativePerformanceAgent
from utils.ui_feedback import queue_completion_message, render_completion_message


st.set_page_config(page_title="AI 素材效能監控", page_icon="📈", layout="wide")
st.title("📈 AI 素材效能監控")
st.caption("整合素材生成紀錄、投放成效與優化建議，支援後續商業決策。")


@st.cache_resource
def get_agent() -> CreativePerformanceAgent:
    return CreativePerformanceAgent()


def show_dataset(df: pd.DataFrame) -> None:
    st.subheader("資料總覽")
    if df.empty:
        st.info("目前尚未有素材成效資料，請透過下方表單或自動化流程建立。")
        return

    summary_cols = ["creative_id", "asset_type", "status", "primary_kpi", "roas", "ctr", "spend", "conversions"]
    missing_cols = [col for col in summary_cols if col not in df.columns]
    if missing_cols:
        st.warning(f"資料缺少欄位：{', '.join(missing_cols)}，請確認匯入流程。")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("紀錄數", len(df))
    with col2:
        deployed = df[df["status"] == "deployed"] if "status" in df.columns else pd.DataFrame()
        st.metric("上線素材數", len(deployed))
    with col3:
        roas = df["roas"].dropna().mean() if "roas" in df.columns else 0
        st.metric("平均 ROAS", f"{roas:.2f}")
    with col4:
        spend = df["spend"].dropna().sum() if "spend" in df.columns else 0
        st.metric("總花費 (TWD)", f"{spend:,.0f}")

    st.dataframe(
        df.sort_values("last_updated_at", ascending=False) if "last_updated_at" in df.columns else df,
        use_container_width=True,
        height=420,
    )


def manual_entry() -> None:
    st.subheader("手動新增 / 更新素材紀錄")
    with st.expander("新增素材資料", expanded=False):
        with st.form("create_creative_form"):
            creative_id = st.text_input("素材 ID", placeholder="campaign-adset-creative")
            campaign_id = st.text_input("行銷活動 ID", value="")
            asset_type = st.selectbox("素材類型", ["headline", "image", "video", "script", "other"])
            status = st.selectbox("狀態", ["generated", "approved", "deployed", "retired"])
            primary_kpi = st.selectbox("主要 KPI", ["ROAS", "CTR", "CPA", "Conversion"])
            roas = st.number_input("ROAS", min_value=0.0, value=0.0, step=0.1)
            ctr = st.number_input("CTR (%)", min_value=0.0, value=0.0, step=0.1)
            spend = st.number_input("花費 (TWD)", min_value=0.0, value=0.0, step=10.0)
            conversions = st.number_input("轉換數", min_value=0.0, value=0.0, step=1.0)
            submit = st.form_submit_button("儲存紀錄")

        if submit:
            if not creative_id:
                st.error("請輸入素材 ID。")
            else:
                record = {
                    "creative_id": creative_id,
                    "campaign_id": campaign_id,
                    "asset_type": asset_type,
                    "status": status,
                    "primary_kpi": primary_kpi,
                    "roas": roas,
                    "ctr": ctr,
                    "spend": spend,
                    "conversions": conversions,
                    "generated_at": datetime.utcnow(),
                    "last_updated_at": datetime.utcnow(),
                }
                creative_store.upsert_record(record)
                st.success(f"素材 {creative_id} 已更新。")
                st.rerun()


def run_analysis(df: pd.DataFrame) -> None:
    st.subheader("AI 素材洞察（測試版）")
    if df.empty:
        st.info("請先建立素材資料，再執行分析。")
        return

    if st.button("生成最新洞察", use_container_width=True):
        with st.spinner("AI 分析中，請稍候…"):
            agent = get_agent()
            sample_cols = [col for col in df.columns if col in ["creative_id", "asset_type", "roas", "ctr", "spend", "conversions"]]
            sample_df = df[sample_cols].rename(
                columns={
                    "roas": "購買 ROAS（廣告投資報酬率）",
                    "ctr": "CTR（全部）",
                    "spend": "花費金額 (TWD)",
                    "conversions": "購買次數",
                }
            )
            if "CTR（全部）" in sample_df.columns:
                sample_df["CTR（全部）"] = sample_df["CTR（全部）"] / 100  # Agent 使用小數
            else:
                sample_df["CTR（全部）"] = 0.0
            try:
                result = asyncio.run(agent.analyze(df=sample_df))
                st.write("### 🔍 重要洞察")
                for insight in result.insights:
                    st.markdown(f"- **{insight.title}**：{insight.description}")
                st.write("### ⚙️ 優化建議")
                for idea in result.optimizations:
                    st.markdown(f"- {idea.priority} {idea.focus_area}：{'; '.join(idea.action_steps)} → {idea.expected_impact}")
                queue_completion_message("creative_monitor_agent", "✅ 最新素材洞察已生成")
                render_completion_message("creative_monitor_agent")
            except Exception as exc:
                st.error(f"AI 分析失敗：{exc}")


def main() -> None:
    df = creative_store.load_performance_data()
    show_dataset(df)
    manual_entry()
    run_analysis(df)


if __name__ == "__main__":
    main()
