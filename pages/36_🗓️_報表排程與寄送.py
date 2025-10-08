from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from utils import report_service
from utils.data_loader import load_meta_ads_data


st.set_page_config(page_title="報表排程與寄送", page_icon="🗓️", layout="wide")
st.title("🗓️ 報表排程與寄送")
st.caption("設定週報 / 月報輸出，預覽報表並建立排程。")


SCHEDULE_PATH = Path("data/reports/schedules.json")


@st.cache_data(ttl=60)
def load_data():
    return load_meta_ads_data(show_sidebar_info=False)


def load_schedule() -> list[dict]:
    if not SCHEDULE_PATH.exists():
        return []
    try:
        return json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_schedule(entries: list[dict]) -> None:
    SCHEDULE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def add_schedule(entry: dict) -> None:
    entries = load_schedule()
    entries.append(entry)
    save_schedule(entries)


def _format_delta_pct(value: float | None) -> str | None:
    if value is None:
        return None
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}% vs 前期"


def _format_delta_abs(value: float | None, suffix: str = "") -> str | None:
    if value is None:
        return None
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}{suffix} vs 前期"


def render_monthly_preview(summary: dict) -> None:
    metrics = summary.get("summary_metrics", {}) or {}
    delta = (summary.get("trend", {}) or {}).get("delta", {}) or {}
    highlights = summary.get("highlights", []) or []
    warnings = summary.get("warnings", []) or []

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("總花費 (NT$)", f"{metrics.get('total_spend', 0):,.0f}", delta=_format_delta_pct(delta.get("spend_pct")))
    with col2:
        st.metric("轉換次數", f"{metrics.get('total_conversions', 0):,.0f}", delta=_format_delta_pct(delta.get("conversions_pct")))
    with col3:
        st.metric("平均 ROAS", f"{metrics.get('weighted_roas', 0):.2f}", delta=_format_delta_abs(delta.get("roas")))
    with col4:
        st.metric("平均 CTR (%)", f"{metrics.get('ctr', 0):.2f}", delta=_format_delta_abs(delta.get("ctr"), suffix=" ppts"))

    if highlights:
        st.markdown("#### 🎯 亮點")
        for item in highlights:
            st.markdown(f"- {item}")

    if warnings:
        st.markdown("#### ⚠️ 待優化")
        for item in warnings:
            st.markdown(f"- {item}")

    custom_suggestions = summary.get("custom_suggestions", []) or []
    if custom_suggestions:
        st.markdown("#### 📬 客製寄送備註")
        for item in custom_suggestions:
            st.markdown(f"- {item}")

    channel_records = summary.get("channel_breakdown", []) or []
    if channel_records:
        channel_df = pd.DataFrame(channel_records).rename(
            columns={"行銷活動名稱": "活動", "花費金額 (TWD)": "花費 (NT$)", "購買次數": "轉換"}
        )
        st.markdown("#### 通路 / 活動花費分布")
        st.dataframe(channel_df, use_container_width=True)

    top_campaigns = summary.get("top_campaigns", []) or []
    if top_campaigns:
        top_df = pd.DataFrame(top_campaigns).rename(
            columns={
                "行銷活動名稱": "活動",
                "花費金額 (TWD)": "花費 (NT$)",
                "購買次數": "轉換",
                "購買 ROAS（廣告投資報酬率）": "平均 ROAS",
            }
        )
        st.markdown("#### 表現最佳活動")
        st.dataframe(top_df, use_container_width=True)

    lagging_campaigns = summary.get("lagging_campaigns", []) or []
    if lagging_campaigns:
        lagging_df = pd.DataFrame(lagging_campaigns).rename(
            columns={
                "行銷活動名稱": "活動",
                "花費金額 (TWD)": "花費 (NT$)",
                "購買次數": "轉換",
                "購買 ROAS（廣告投資報酬率）": "平均 ROAS",
            }
        )
        st.markdown("#### 待優化活動")
        st.dataframe(lagging_df, use_container_width=True)


def section_preview(df: pd.DataFrame) -> None:
    st.subheader("即時預覽報表")
    report_type = st.selectbox("報表類型", ["週報", "月報"])
    today = date.today()
    if report_type == "週報":
        start = today - timedelta(days=7)
    else:
        start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    end = today

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("起始日期", value=start)
    with col2:
        end_date = st.date_input("結束日期", value=end)

    brand_name = st.text_input("品牌名稱", value="耘初茶食")
    analyst = st.text_input("報告撰寫人（選填）", value=st.session_state.get("current_user", ""))
    suggestions_text = st.text_area("建議行動（每行一則，可留白）", height=120)
    suggestions = [s.strip() for s in suggestions_text.split("\n") if s.strip()]
    generate_btn = st.button("預覽報表", type="primary")

    if generate_btn:
        try:
            req = report_service.WeeklyReportRequest(
                brand_name=brand_name or "未命名品牌",
                start_date=datetime.combine(start_date, datetime.min.time()),
                end_date=datetime.combine(end_date, datetime.max.time()),
                analyst=analyst or None,
            )
            if report_type == "週報":
                output_dir = Path("data/reports/preview")
                output_dir.mkdir(parents=True, exist_ok=True)
                generated = report_service.generate_weekly_report(
                    df,
                    req,
                    output_path=(output_dir / f"preview_weekly_{start_date}_{end_date}.pptx").as_posix(),
                    suggestions=suggestions or None,
                )
                with generated.open("rb") as f:
                    st.download_button(
                        label="下載週報 PPT 預覽",
                        data=f.read(),
                        file_name=generated.name,
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        use_container_width=True,
                    )
                st.success("週報預覽已生成。")
            else:
                summary = report_service.generate_monthly_summary(df, req)
                if suggestions:
                    summary["custom_suggestions"] = suggestions
                st.success("月報摘要已生成，以下為 AI 洞察與建議。")
                render_monthly_preview(summary)

                html_content = report_service.build_monthly_email_html(summary)
                json_payload = json.dumps(summary, default=str, ensure_ascii=False, indent=2)
                col_a, col_b = st.columns(2)
                with col_a:
                    st.download_button(
                        label="下載月報摘要 JSON",
                        data=json_payload.encode("utf-8"),
                        file_name=f"monthly_{start_date}_{end_date}.json",
                        mime="application/json",
                        use_container_width=True,
                    )
                with col_b:
                    st.download_button(
                        label="下載 HTML 郵件模板",
                        data=html_content.encode("utf-8"),
                        file_name=f"monthly_{start_date}_{end_date}.html",
                        mime="text/html",
                        use_container_width=True,
                    )
                with st.expander("HTML 郵件預覽", expanded=False):
                    st.markdown(html_content, unsafe_allow_html=True)
        except RuntimeError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"生成報表失敗：{exc}")


def section_schedule(df: pd.DataFrame) -> None:
    st.subheader("建立排程")
    schedule_type = st.selectbox("排程報表類型", ["週報", "月報"], key="schedule_type")
    day_of_week = st.selectbox("發送星期（週報）", ["星期一", "星期二", "星期三", "星期四", "星期五"], key="dow", disabled=schedule_type != "週報")
    day_of_month = st.number_input("發送日期（1-28）", min_value=1, max_value=28, value=5, key="dom", disabled=schedule_type == "週報")
    send_time = st.time_input("發送時間", value=datetime.strptime("09:00", "%H:%M").time())
    recipients = st.text_area("收件人 Email（以逗號分隔）", placeholder="marketing@brand.com, agency@partner.com")
    subject = st.text_input("郵件主旨", value="[AI 投放報表] {{brand}} {{period}} 週報")
    body = st.text_area(
        "郵件內容",
        value="團隊好，\n\n請查閱本期 AI 投放報表，附件為 PPT。\n如有任何問題歡迎回覆此郵件。\n\n敬祝 商祺\nAI 投放助手\n",
        height=160,
    )

    expiry_date = st.date_input("排程有效期限", value=date.today() + timedelta(days=90))
    create_btn = st.button("建立排程", type="primary")

    if create_btn:
        if not recipients.strip():
            st.error("請輸入至少一位收件人")
            return
        schedule_entry = {
            "type": schedule_type,
            "day_of_week": day_of_week if schedule_type == "週報" else None,
            "day_of_month": day_of_month if schedule_type == "月報" else None,
            "send_time": send_time.strftime("%H:%M"),
            "recipients": [mail.strip() for mail in recipients.split(",") if mail.strip()],
            "subject": subject,
            "body": body,
            "expiry_date": expiry_date.isoformat(),
            "created_at": datetime.utcnow().isoformat(),
        }
        add_schedule(schedule_entry)
        st.success("排程已建立。暫以 JSON 儲存，後續可串接寄信服務。")
        st.experimental_rerun()

    st.markdown("#### 已建立排程")
    entries = load_schedule()
    if not entries:
        st.info("目前尚未建立排程。")
    else:
        st.table(entries)
        if st.button("匯出排程檔 (ics)"):
            today = datetime.utcnow()
            cals = []
            for entry in entries:
                subject_fmt = entry["subject"].replace("{{brand}}", "耘初茶食").replace("{{period}}", "本週")
                start_dt = today + timedelta(days=1)
                cal_str = report_service.create_calendar_event(
                    subject_fmt,
                    start=start_dt,
                    end=start_dt + timedelta(hours=1),
                    description=entry["body"],
                )
                cals.append(cal_str)
            export_path = Path("data/reports/schedules.ics")
            export_path.write_text("\n".join(cals), encoding="utf-8")
            with export_path.open("rb") as f:
                st.download_button(
                    label="下載排程 (.ics)",
                    data=f.read(),
                    file_name="report_schedules.ics",
                    mime="text/calendar",
                    use_container_width=True,
                )


def main() -> None:
    df = load_data()
    if df is None or df.empty:
        st.error("無法載入投放資料")
        return

    section_preview(df)
    st.divider()
    section_schedule(df)


if __name__ == "__main__":
    main()
