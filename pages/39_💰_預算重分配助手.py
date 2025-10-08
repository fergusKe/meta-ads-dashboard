from __future__ import annotations

import json
from datetime import date

import pandas as pd
import streamlit as st

from utils import budget_optimizer, usage_store
from utils.data_loader import load_meta_ads_data


st.set_page_config(page_title="預算重分配助手", page_icon="💰", layout="wide")
st.title("💰 預算重分配助手")
st.caption("依據行銷活動 ROAS 與花費，建議資源挪移方向。")


@st.cache_data(ttl=60)
def _load_data():
    df = load_meta_ads_data(show_sidebar_info=False)
    if df is None:
        return pd.DataFrame()
    return df


def main() -> None:
    df = _load_data()
    if df.empty:
        st.error("無法載入投放資料，請稍後再試。")
        return

    st.sidebar.header("參數設定")
    target_roas = st.sidebar.number_input("ROAS 目標", min_value=0.5, max_value=10.0, value=2.0, step=0.1)
    min_spend = st.sidebar.number_input("捐出門檻 (NT$)", min_value=1000.0, max_value=20000.0, value=5000.0, step=500.0)
    shift_ratio = st.sidebar.slider("釋出比例", min_value=0.05, max_value=0.5, value=0.2, step=0.05)
    max_recipient = st.sidebar.slider("接收活動上限", min_value=1, max_value=10, value=5)

    config = budget_optimizer.BudgetConfig(
        target_roas=float(target_roas),
        min_donor_spend=float(min_spend),
        shift_ratio=float(shift_ratio),
        max_recipients=int(max_recipient),
    )

    plan = budget_optimizer.generate_reallocation_plan(df, config=config)

    usage_store.record_event(
        "budget_optimizer",
        "generate",
        {
            "target_roas": config.target_roas,
            "min_spend": config.min_donor_spend,
            "shift_ratio": config.shift_ratio,
            "max_recipients": config.max_recipients,
            "plan_rows": len(plan),
        },
    )

    if plan.empty:
        st.info("目前沒有符合條件的重分配建議。請調整參數或檢視資料品質。")
        return

    summary = budget_optimizer.summarize_shift(plan)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("建議釋出預算", f"NT$ {summary['freed']:,.0f}")
    with col2:
        st.metric("建議追加預算", f"NT$ {summary['reallocated']:,.0f}")
    with col3:
        st.metric("建議活動數", len(plan[plan["role"] == "recipient"]))

    st.markdown("### 詳細建議")
    display = plan.copy()
    display["delta"] = display["delta"].apply(lambda x: f"NT$ {x:,.0f}")
    display["current_spend"] = display["current_spend"].apply(lambda x: f"NT$ {x:,.0f}")
    display["suggested_spend"] = display["suggested_spend"].apply(lambda x: f"NT$ {x:,.0f}")
    st.dataframe(display, use_container_width=True)

    csv_bytes = plan.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "下載建議 (CSV)",
        data=csv_bytes,
        file_name=f"budget_plan_{date.today()}.csv",
        mime="text/csv",
    )

    st.markdown("### 實施紀錄")
    if st.button("標記建議已採納", use_container_width=True):
        usage_store.record_event(
            "budget_optimizer",
            "adopted",
            {
                "target_roas": config.target_roas,
                "freed": summary["freed"],
                "reallocated": summary["reallocated"],
            },
        )
        st.success("已紀錄採納資訊，可在事件追蹤中檢視。")


if __name__ == "__main__":
    main()
