from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import streamlit as st

from utils import report_service
from utils.data_loader import load_meta_ads_data


st.set_page_config(page_title="週報白標輸出", page_icon="📄", layout="wide")
st.title("📄 AI 週報白標輸出")
st.caption("匯總投放數據，生成可直接寄給客戶的 PPT 報告。")


@st.cache_data(ttl=60)
def _load_data():
    df = load_meta_ads_data(show_sidebar_info=False)
    return df


def render_qa_report(report: dict) -> None:
    status = report.get("status", "ok")
    status_map = {
        "ok": "✅ 通過",
        "warning": "⚠️ 有警示",
        "error": "❌ 阻擋",
    }
    st.markdown(f"**檢查狀態**：{status_map.get(status, status)}　（資料筆數：{report.get('record_count', 0)}）")

    coverage = report.get("coverage", {})
    if coverage:
        ratio = coverage.get("coverage_ratio", 0.0)
        ratio_pct = f"{ratio * 100:.0f}%"
        st.caption(
            f"請求期間：{coverage.get('requested_start', '-')}"
            f" ～ {coverage.get('requested_end', '-')}"
            f"｜資料期間：{coverage.get('data_start', '-')}"
            f" ～ {coverage.get('data_end', '-')}"
            f"｜覆蓋天數：{coverage.get('days_with_data', 0)}/{coverage.get('days_expected', 0)}（{ratio_pct}）"
        )

    metrics = report.get("metrics", {})
    if metrics:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("總花費 (NT$)", f"{metrics.get('total_spend', 0):,.0f}")
        with col2:
            st.metric("總轉換", f"{metrics.get('total_conversions', 0):,.0f}")
        with col3:
            st.metric("平均 ROAS", f"{metrics.get('weighted_roas', 0):.2f}")
        with col4:
            st.metric("平均 CTR (%)", f"{metrics.get('ctr', 0):.2f}")

    issues = report.get("issues", [])
    if not issues:
        st.success("所有檢查項目皆通過。")
        return

    for issue in issues:
        level = issue.get("level")
        message = issue.get("message", "")
        if level == "error":
            st.error(message)
        elif level == "warning":
            st.warning(message)
        else:
            st.info(message)


def main() -> None:
    df = _load_data()
    if df is None or df.empty:
        st.error("無法載入投放資料，請確認資料檔案是否存在。")
        return

    today = date.today()
    default_end = today
    default_start = today - timedelta(days=7)

    st.sidebar.header("週報設定")
    brand_name = st.sidebar.text_input("品牌名稱", value="耘初茶食")
    start_date = st.sidebar.date_input("起始日期", value=default_start)
    end_date = st.sidebar.date_input("結束日期", value=default_end)
    analyst = st.sidebar.text_input("報告撰寫人（選填）", value=st.session_state.get("current_user", ""))
    logo_file = st.sidebar.file_uploader("品牌 Logo（選填）", type=["png", "jpg", "jpeg"])

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    st.write("### 下週建議行動")
    suggestions_text = st.text_area(
        "可輸入多條建議，每行一則。若留白將使用預設建議。",
        height=120,
    )
    suggestions = [s.strip() for s in suggestions_text.split("\n") if s.strip()]

    st.write("### QA 檢查")
    qa_placeholder = st.empty()
    qa_triggered = st.button("執行 QA 檢查")
    if qa_triggered:
        qa_report = report_service.run_weekly_qa(
            df,
            start_dt,
            end_dt,
        )
        st.session_state["weekly_qa_report"] = qa_report

    qa_report = st.session_state.get("weekly_qa_report")
    if qa_report:
        with qa_placeholder.container():
            render_qa_report(qa_report)

    report_button = st.button("生成週報 PPT", type="primary")

    if report_button:
        try:
            if start_date > end_date:
                st.error("起始日期不可晚於結束日期。")
                return

            qa_result = report_service.run_weekly_qa(df, start_dt, end_dt)
            st.session_state["weekly_qa_report"] = qa_result
            qa_placeholder.empty()
            with qa_placeholder.container():
                render_qa_report(qa_result)
            if qa_result["status"] == "error":
                st.error("資料檢查未通過，請先依照上述提示調整資料或日期區間。")
                return
            if qa_result["status"] == "warning":
                st.warning("資料檢查存在警示，建議生成後再進行人工覆核。")

            logo_path = None
            if logo_file:
                logo_dir = Path("assets/reports/logo_cache")
                logo_dir.mkdir(parents=True, exist_ok=True)
                logo_path = logo_dir / logo_file.name
                logo_path.write_bytes(logo_file.getvalue())
                logo_path = logo_path.as_posix()

            req = report_service.WeeklyReportRequest(
                brand_name=brand_name or "未命名品牌",
                start_date=start_dt,
                end_date=end_dt,
                logo_path=logo_path,
                analyst=analyst or None,
            )
            output_path = Path("data/reports") / f"weekly_{brand_name}_{start_date}_{end_date}.pptx"
            generated = report_service.generate_weekly_report(
                df,
                req,
                output_path=output_path.as_posix(),
                suggestions=suggestions or None,
            )
            st.success("週報已生成！")
            with generated.open("rb") as f:
                st.download_button(
                    label="下載週報 PPT",
                    data=f.read(),
                    file_name=generated.name,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True,
                )
        except RuntimeError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"生成週報失敗：{exc}")


if __name__ == "__main__":
    main()
