from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import roi_simulator, usage_store
from utils.data_loader import load_meta_ads_data


st.set_page_config(page_title="ROI 模擬器", page_icon="📊", layout="wide")
st.title("📊 ROI 模擬器")
st.caption("根據歷史投放表現，模擬不同預算與成效假設下的營收與 ROI。")


@st.cache_data(ttl=60)
def _load_data() -> pd.DataFrame | None:
    return load_meta_ads_data(show_sidebar_info=False)


def _date_inputs() -> tuple[datetime, datetime]:
    today = date.today()
    default_end = today
    default_start = today - timedelta(days=28)
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("分析起始日", value=default_start)
    with col2:
        end_date = st.date_input("分析結束日", value=default_end)
    if start_date > end_date:
        st.error("起始日不可晚於結束日")
    return datetime.combine(start_date, datetime.min.time()), datetime.combine(end_date, datetime.max.time())


def plot_projection(result: dict) -> None:
    baseline = result["baseline"]
    projected = result["projected"]
    fig = go.Figure(
        data=[
            go.Bar(name="Baseline", x=["花費", "營收", "淨利"], y=[baseline["spend"], baseline["revenue"], baseline["profit"]]),
            go.Bar(name="Projected", x=["花費", "營收", "淨利"], y=[projected["spend"], projected["revenue"], projected["net_profit"]]),
        ]
    )
    fig.update_layout(barmode="group", title="Baseline vs Projected 指標比較", yaxis_title="金額 (TWD)")
    st.plotly_chart(fig, use_container_width=True)


def main() -> None:
    df = _load_data()
    if df is None:
        st.error("無法載入投放資料")
        return

    start_dt, end_dt = _date_inputs()
    baseline = roi_simulator.calculate_baseline(df, start_dt, end_dt)
    st.subheader("Baseline 指標")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("總花費 (TWD)", f"{baseline.spend:,.0f}")
    col2.metric("平均 ROAS", f"{baseline.roas:.2f}")
    col3.metric("轉換數", f"{baseline.conversions:,.0f}")
    col4.metric("CPA (TWD)", f"{baseline.cpa:,.0f}")

    st.session_state.setdefault("roi_simulation", None)

    st.subheader("模擬與報告設定")
    with st.form("roi_simulation_form"):
        col1, col2 = st.columns(2)
        with col1:
            brand_name = st.text_input("品牌名稱", value="耘初茶食")
            scenario_name = st.text_input("情境名稱", value="加碼投放情境")
            new_budget = st.number_input("模擬花費 (TWD)", min_value=0.0, value=float(baseline.spend), step=1000.0)
            expected_roas = st.number_input("預期 ROAS", min_value=0.0, value=float(baseline.roas if baseline.roas > 0 else 1.0), step=0.1)
        with col2:
            analyst = st.text_input("報告撰寫人（選填）", value=st.session_state.get("current_user", ""))
            conversion_uplift = st.slider("預期轉換提升 (%)", min_value=-50, max_value=200, value=20)
            fixed_cost = st.number_input("固定成本 (TWD)", min_value=0.0, value=0.0, step=500.0)
            ai_cost = st.number_input("AI 工具成本 (TWD)", min_value=0.0, value=0.0, step=500.0)
        notes_text = st.text_area("備註（每行一則，可留白）", height=120)
        submitted = st.form_submit_button("執行模擬", type="primary")

    if submitted:
        result = roi_simulator.simulate_roi(
            baseline,
            new_budget=new_budget,
            expected_roas=expected_roas,
            conversion_uplift_pct=conversion_uplift,
            fixed_cost=fixed_cost,
            ai_tool_cost=ai_cost,
        )
        notes = [line.strip() for line in notes_text.splitlines() if line.strip()]
        request = roi_simulator.ROIReportRequest(
            brand_name=brand_name or "未命名品牌",
            start_date=start_dt,
            end_date=end_dt,
            scenario_name=scenario_name or "ROI 模擬情境",
            analyst=analyst or None,
            notes=notes or None,
        )
        st.session_state["roi_simulation"] = {"result": result, "request": request}
        usage_store.record_event(
            "roi_simulator",
            "simulate",
            {
                "brand": request.brand_name,
                "scenario": request.scenario_name,
                "new_budget": new_budget,
                "expected_roas": expected_roas,
                "conversion_uplift_pct": conversion_uplift,
            },
        )
        st.success("模擬完成，結果已更新。")

    simulation_state = st.session_state.get("roi_simulation")
    if simulation_state:
        result = simulation_state["result"]
        request: roi_simulator.ROIReportRequest = simulation_state["request"]
        delta = result["delta"]
        baseline_revenue = result["baseline"]["revenue"]

        st.subheader("模擬結果")
        col1, col2, col3 = st.columns(3)
        col1.metric("淨利 (Projected)", f"{result['projected']['net_profit']:,.0f}")
        incremental_pct = f"{delta['incremental_revenue'] / baseline_revenue * 100:.1f}%" if baseline_revenue else None
        col2.metric("增量營收", f"{delta['incremental_revenue']:,.0f}", incremental_pct)
        col3.metric("ROI", f"{delta['roi'] * 100:.1f}%")

        plot_projection(result)

        df_summary = roi_simulator.simulation_to_dataframe(result)
        st.dataframe(df_summary, use_container_width=True)

        csv_bytes = df_summary.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="下載模擬結果 (CSV)",
            data=csv_bytes,
            file_name=f"roi_simulation_{date.today()}.csv",
            mime="text/csv",
            on_click=lambda: usage_store.record_event(
                "roi_simulator",
                "download_csv",
                {"brand": request.brand_name, "scenario": request.scenario_name},
            ),
        )

        try:
            safe_brand = request.brand_name.replace(" ", "_")
            safe_scenario = request.scenario_name.replace(" ", "_")
            ppt_path = Path("data/reports/roi") / f"roi_{safe_brand}_{safe_scenario}_{date.today()}.pptx"
            ppt_file = roi_simulator.generate_roi_ppt(result, request, ppt_path.as_posix())
            ppt_bytes = ppt_file.read_bytes()
            st.download_button(
                label="下載 ROI 報表 PPT",
                data=ppt_bytes,
                file_name=ppt_file.name,
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                on_click=lambda: usage_store.record_event(
                    "roi_simulator",
                    "download_ppt",
                    {"brand": request.brand_name, "scenario": request.scenario_name},
                ),
            )
        except RuntimeError as exc:
            st.warning(str(exc))

        st.markdown("#### 模型假設說明")
        st.write(
            """
            - Baseline 係以指定期間內的實際花費與 ROAS 計算。
            - 預期 ROAS 與轉換提升為手動輸入假設，系統不會直接預測。
            - 淨利 = 模擬營收 − 模擬花費 − 固定成本 − AI 工具成本。
            - ROI = 淨利 / 模擬花費。
            """
        )

    usage_summary = usage_store.summarize_events(feature="roi_simulator")
    latest_events = usage_store.load_events(feature="roi_simulator", limit=10, parse_metadata=True)
    daily_summary = usage_store.summarize_daily(feature="roi_simulator")
    top_scenarios = usage_store.top_metadata_entries("roi_simulator", "scenario", limit=5)

    with st.expander("📈 模擬使用追蹤", expanded=False):
        if usage_summary.empty and latest_events.empty:
            st.info("目前尚無使用紀錄。")
        else:
            if not usage_summary.empty:
                totals = usage_summary.iloc[0].to_dict()
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("模擬次數", int(totals.get("simulate", 0)))
                col_b.metric("CSV 下載", int(totals.get("download_csv", 0)))
                col_c.metric("PPT 下載", int(totals.get("download_ppt", 0)))
                st.dataframe(usage_summary, use_container_width=True)

            if not daily_summary.empty:
                try:
                    import altair as alt

                    chart_data = (
                        daily_summary.pivot(index="date", columns="event_type", values="count")
                        .fillna(0)
                        .reset_index()
                    )
                    chart = (
                        alt.Chart(chart_data)
                        .transform_fold(
                            [col for col in chart_data.columns if col != "date"],
                            as_=["event_type", "count"],
                        )
                        .mark_line(point=True)
                        .encode(
                            x="date:T",
                            y="count:Q",
                            color="event_type:N",
                            tooltip=["date:T", "event_type:N", "count:Q"],
                        )
                        .properties(height=260)
                    )
                    st.altair_chart(chart, use_container_width=True)
                except Exception:
                    st.write("每日事件統計")
                    st.dataframe(daily_summary, use_container_width=True)

            if not top_scenarios.empty:
                st.write("熱門情境")
                st.dataframe(top_scenarios, use_container_width=True)

            if not latest_events.empty:
                st.write("最新事件")
                st.dataframe(latest_events, use_container_width=True)


if __name__ == "__main__":
    main()
