from __future__ import annotations

import json
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from utils import (
    creative_store,
    fatigue_analyzer,
    fatigue_pilot_manager,
    fatigue_reporter,
    push_history,
    push_scheduler,
    report_service,
)


st.set_page_config(page_title="素材疲勞預測", page_icon="🛏️", layout="wide")
st.title("🛏️ 素材疲勞預測 PoC")
st.caption("根據素材歷史表現，評估疲勞風險並提供優先處理建議。")


@st.cache_data(ttl=60)
def _load_scores(config: dict | None = None) -> pd.DataFrame:
    df = creative_store.load_performance_data()
    return fatigue_analyzer.calculate_fatigue_scores(df, config=config)


def _render_summary(scores: pd.DataFrame) -> None:
    if scores.empty:
        st.info("資料集中沒有素材紀錄，請先同步素材成效資料。")
        return

    totals = {
        "總素材": len(scores),
        "高風險": int((scores["risk_tier"] == "高風險").sum()),
        "中風險": int((scores["risk_tier"] == "中風險").sum()),
        "低風險": int((scores["risk_tier"] == "低風險").sum()),
    }
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("總素材", totals["總素材"])
    col_b.metric("高風險", totals["高風險"])
    col_c.metric("中風險", totals["中風險"])
    col_d.metric("低風險", totals["低風險"])

    summary = fatigue_analyzer.summarize_by_campaign(scores)
    st.markdown("### 行銷活動風險概況")
    st.dataframe(summary, use_container_width=True)


def _filter_scores(scores: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("篩選條件")
    campaigns = sorted(scores["campaign_id"].dropna().unique())
    selected_campaigns = st.sidebar.multiselect("行銷活動", campaigns)
    risk_levels = ["高風險", "中風險", "低風險"]
    selected_risks = st.sidebar.multiselect("風險等級", risk_levels, default=risk_levels[:2])
    min_score, max_score = st.sidebar.slider("疲勞分數範圍", 0.0, 1.0, (0.4, 1.0), 0.05)

    filtered = scores.copy()
    if selected_campaigns:
        filtered = filtered[filtered["campaign_id"].isin(selected_campaigns)]
    if selected_risks:
        filtered = filtered[filtered["risk_tier"].isin(selected_risks)]
    filtered = filtered[(filtered["fatigue_score"] >= min_score) & (filtered["fatigue_score"] <= max_score)]
    return filtered


def _render_detail(filtered: pd.DataFrame) -> None:
    if filtered.empty:
        st.warning("目前沒有符合條件的素材。")
        return

    st.markdown("### 素材清單")
    display = filtered.copy()
    display["reasons"] = display["reasons"].apply(lambda items: "\n- " + "\n- ".join(items))
    st.dataframe(
        display[[
            "creative_id",
            "campaign_id",
            "risk_tier",
            "fatigue_score",
            "age_days",
            "roas",
            "ctr",
            "spend",
            "conversions",
            "reasons",
        ]],
        use_container_width=True,
    )

    csv_bytes = filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "下載疲勞評估結果 (CSV)",
        data=csv_bytes,
        file_name=f"creative_fatigue_{datetime.utcnow().date()}.csv",
        mime="text/csv",
    )

    report_data = fatigue_reporter.generate_report(filtered)
    report_bytes = json.dumps(report_data, ensure_ascii=False, indent=2).encode("utf-8")
    st.download_button(
        "下載疲勞風險摘要 (JSON)",
        data=report_bytes,
        file_name=f"fatigue_report_{datetime.utcnow().date()}.json",
        mime="application/json",
    )

    push_plan = push_scheduler.generate_push_plan(filtered)
    st.markdown("### 推播建議")
    if push_plan.empty:
        st.info("目前沒有需要推播提醒的素材。")
    else:
        st.dataframe(push_plan, use_container_width=True)
        digest = push_scheduler.compile_digest(push_plan)
        if digest:
            st.markdown("**推播摘要**")
            for item in digest:
                st.markdown(f"- {item}")

        if st.button("記錄推播已送出", use_container_width=True):
            for _, row in push_plan.iterrows():
                push_history.record(
                    campaign_id=row["campaign_id"],
                    creative_id=row["creative_id"],
                    action="fatigue_push",
                    channel=row["channel"],
                    status="sent",
                    notes=row["cta"],
                )
            st.success("已紀錄推播送出時間與內容。")

        ics_events = []
        for _, row in push_plan.iterrows():
            start_time = pd.to_datetime(row["send_at"]).to_pydatetime()
            ics_events.append(
                report_service.create_calendar_event(
                    subject=f"疲勞預警｜{row['campaign_id']}｜{row['creative_id']}",
                    start=start_time,
                    end=start_time + timedelta(minutes=30),
                    description=row["message"],
                )
            )
        if ics_events:
            ics_data = "\n".join(ics_events).encode("utf-8")
            st.download_button(
                "下載推播行事曆 (ICS)",
                data=ics_data,
                file_name="fatigue_push_plan.ics",
                mime="text/calendar",
            )

    st.markdown("### 推播歷史")
    history = push_history.load_history(limit=20)
    if history.empty:
        st.info("尚無推播歷史紀錄。")
    else:
        st.dataframe(history, use_container_width=True)
        summary = push_history.summarize_by_campaign()
        if not summary.empty:
            st.markdown("**活動推播統計**")
            st.dataframe(summary, use_container_width=True)

    st.markdown("### 疲勞試點紀錄")
    with st.expander("新增試點紀錄"):
        with st.form("fatigue_pilot_form"):
            creative_id = st.text_input("素材 ID")
            campaign_id = st.text_input("活動 ID")
            action_taken = st.selectbox("採取行動", ["refresh_creative", "pause", "adjust_budget", "monitor"])
            outcome = st.selectbox("試點結果", ["success", "monitor", "fail"])
            lift = st.number_input("成效提升 (%)", min_value=-100.0, max_value=100.0, value=0.0, step=0.5)
            notes = st.text_area("備註", height=80)
            recorded_by = st.text_input("記錄者", value=st.session_state.get("current_user", ""))
            submit = st.form_submit_button("儲存試點紀錄")
            if submit:
                if not creative_id or not campaign_id:
                    st.error("請填寫素材與活動 ID。")
                else:
                    fatigue_pilot_manager.log_pilot_result(
                        creative_id=creative_id,
                        campaign_id=campaign_id,
                        action_taken=action_taken,
                        outcome=outcome,
                        metrics={"lift": lift},
                        notes=notes,
                        recorded_by=recorded_by,
                    )
                    st.success("已紀錄試點成果。")
                    st.rerun()

    pilot_summary = fatigue_pilot_manager.summarize_results()
    if pilot_summary.empty:
        st.info("尚未建立疲勞試點紀錄。")
    else:
        st.dataframe(pilot_summary, use_container_width=True)


def main() -> None:
    config = {
        "age_threshold_days": st.sidebar.number_input("疲勞門檻 (天)", min_value=7, max_value=60, value=14, step=1),
        "roas_target": st.sidebar.number_input("ROAS 目標", min_value=0.5, max_value=10.0, value=2.5, step=0.1),
        "ctr_target": st.sidebar.number_input("CTR 目標 (%)", min_value=0.1, max_value=20.0, value=1.5, step=0.1),
        "spend_threshold": st.sidebar.number_input("累積花費門檻 (NT$)", min_value=1000.0, max_value=100000.0, value=5000.0, step=500.0),
    }

    scores = _load_scores(config)
    _render_summary(scores)
    filtered = _filter_scores(scores)
    _render_detail(filtered)


if __name__ == "__main__":
    main()
