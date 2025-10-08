from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from utils import template_metrics_store, template_review_scheduler, template_store


st.set_page_config(page_title="模板成效儀表", page_icon="📊", layout="wide")
st.title("📊 模板成效儀表")
st.caption("整合模板市集的下載、使用與審核節奏，協助掌握優先優化項目。")


@st.cache_data(ttl=60)
def _load_metadata() -> pd.DataFrame:
    return template_store.load_metadata()


@st.cache_data(ttl=60)
def _load_metrics() -> pd.DataFrame:
    return template_metrics_store.summarize_events()


def _render_overview(meta: pd.DataFrame, metrics: pd.DataFrame) -> None:
    st.subheader("概況指標")
    merged = meta.merge(metrics, how="left", on="template_id").fillna(0) if not meta.empty else meta

    total = len(meta)
    approved = int((meta["status"] == "approved").sum()) if not meta.empty else 0
    downloads = int(merged.get("download", pd.Series(dtype=int)).sum()) if not merged.empty else 0
    views = int(merged.get("view", pd.Series(dtype=int)).sum()) if not merged.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("模板總數", total)
    col2.metric("已上線", approved)
    col3.metric("累計下載", downloads)
    col4.metric("詳情瀏覽", views)

    if merged.empty:
        st.info("尚無模板資料，請先透過管理後台建立模板。")
        return

    display_cols = [
        "template_id",
        "name",
        "status",
        "version",
        "download",
        "view",
        "updated_at",
    ]
    for col in display_cols:
        if col not in merged.columns:
            merged[col] = 0 if col in {"download", "view"} else ""
    st.dataframe(
        merged.sort_values("updated_at", ascending=False)[display_cols],
        use_container_width=True,
        height=380,
    )


def _render_performance(meta: pd.DataFrame, metrics: pd.DataFrame) -> None:
    st.subheader("熱門模板排行")
    if meta.empty or metrics.empty:
        st.info("尚無使用統計，待模板上線後再回來查看。")
        return
    merged = meta.merge(metrics, how="left", on="template_id").fillna(0)
    merged["download"] = merged.get("download", 0).astype(int)
    merged["view"] = merged.get("view", 0).astype(int)
    ranking = merged.sort_values("download", ascending=False).head(10)
    st.bar_chart(
        ranking.set_index("name")[["download", "view"]],
        height=320,
    )


def _render_review_schedule(meta: pd.DataFrame) -> None:
    st.subheader("審核排程")
    schedule = template_review_scheduler.generate_schedule(
        cycle_days=st.sidebar.number_input("審核週期 (天)", min_value=7, max_value=60, value=14, step=1),
        reference_date=datetime.utcnow(),
        template_df=meta,
    )
    if schedule.empty:
        st.info("目前沒有需要安排審核的模板。")
        return
    st.dataframe(schedule, use_container_width=True)

    selected = st.selectbox("選擇模板以記錄審核結果", [""] + schedule["template_id"].tolist())
    if selected:
        reviewer = st.text_input("審核人員")
        outcome = st.selectbox("審核結果", ["pass", "needs_revision", "reject"])
        status = st.selectbox("調整狀態", ["approved", "draft", "retired"], index=0)
        notes = st.text_area("備註", height=100)
        if st.button("記錄審核"):
            if not reviewer:
                st.error("請填寫審核人員")
            else:
                template_review_scheduler.record_review(
                    template_id=selected,
                    reviewer=reviewer,
                    outcome=outcome,
                    status=status,
                    notes=notes,
                    metadata={"schedule": "template_dashboard"},
                )
                st.success("審核紀錄已更新。")
                st.experimental_rerun()


def main() -> None:
    meta = _load_metadata()
    metrics = _load_metrics()
    _render_overview(meta, metrics)
    _render_performance(meta, metrics)
    _render_review_schedule(meta)


if __name__ == "__main__":
    main()
