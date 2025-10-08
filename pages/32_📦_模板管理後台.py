import io
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from utils import template_metrics_store, template_store


st.set_page_config(page_title="模板管理後台", page_icon="📦", layout="wide")
st.title("📦 模板管理後台")
st.caption("維護模板市集的上架資料、授權資訊與版本。")


@st.cache_data(ttl=1)
def _load_templates() -> pd.DataFrame:
    df = template_store.load_metadata()
    if df.empty:
        return df
    # 解析 tags 與 extra 欄位，方便閱讀
    df = df.copy()
    df["tags"] = df["tags"].fillna("")
    df["extra"] = df["extra"].fillna("").apply(lambda x: x if isinstance(x, str) else "")
    df["extra"] = df["extra"].apply(_shorten_json)
    return df


def _shorten_json(value: str) -> str:
    if not value:
        return ""
    try:
        if len(value) > 120:
            return value[:117] + "..."
        return value
    except Exception:
        return value


def section_overview(df: pd.DataFrame) -> None:
    st.subheader("概況")
    metrics_df = template_metrics_store.summarize_events()
    merged = df.merge(metrics_df, how="left", on="template_id").fillna(0) if not df.empty else df

    col1, col2, col3, col4 = st.columns(4)
    total = len(df)
    with col1:
        st.metric("模板總數", total)
    with col2:
        approved = len(df[df["status"] == "approved"]) if not df.empty else 0
        st.metric("已上線", approved)
    with col3:
        downloads = int(merged["download"].sum()) if not merged.empty and "download" in merged.columns else 0
        st.metric("累計下載", downloads)
    with col4:
        views = int(merged["view"].sum()) if not merged.empty and "view" in merged.columns else 0
        st.metric("詳情瀏覽", views)

    if not merged.empty:
        display_cols = [
            "template_id",
            "name",
            "status",
            "version",
            "price_type",
            "price",
            "author",
            "reviewer",
            "download",
            "view",
            "updated_at",
        ]
        for col in display_cols:
            if col not in merged.columns:
                merged[col] = 0 if col in {"download", "view"} else ""
        table_df = merged.sort_values("updated_at", ascending=False)[display_cols]
    else:
        table_df = df

    st.dataframe(
        table_df,
        use_container_width=True,
        height=380,
    )


def section_create_template() -> None:
    st.subheader("新增模板")
    with st.form("create_template_form", clear_on_submit=True):
        name = st.text_input("模板名稱", max_chars=60)
        category = st.text_input("分類", placeholder="例如：茶飲、節慶、促銷")
        format_ = st.selectbox("格式", ["mixed", "image", "video", "script", "copy"])
        description = st.text_area("模板說明", height=120)
        tags_text = st.text_input("標籤（以逗號分隔）", placeholder="促銷, 茶飲, 節慶")
        license_type = st.selectbox("授權類型", ["standard", "commercial"])
        price_type = st.selectbox("收費模式", ["free", "paid"])
        price = st.number_input("價格 (TWD)", min_value=0.0, value=0.0, step=10.0, disabled=price_type == "free")
        author = st.text_input("作者/提交人", value=st.session_state.get("current_user", ""))
        uploaded_file = st.file_uploader("模板檔案（zip/pptx/pdf 等）", type=["zip", "pptx", "pdf", "json", "txt"])
        thumbnail_file = st.file_uploader("縮圖（選填）", type=["png", "jpg", "jpeg"])
        extra = st.text_area("額外資訊（JSON）", placeholder='{"cta":"立即購買","適用受眾":"25-45歲"}')

        submitted = st.form_submit_button("建立模板")
        if submitted:
            if not name.strip():
                st.error("請輸入模板名稱")
                return

            template_id = template_store.generate_template_id()
            storage_path = ""
            thumbnail_path = ""

            if uploaded_file is not None:
                dest = template_store.save_uploaded_file(template_id, uploaded_file.name, uploaded_file.getvalue())
                storage_path = dest.as_posix()

            if thumbnail_file is not None:
                thumb_dest = template_store.save_uploaded_file(template_id, f"thumb_{thumbnail_file.name}", thumbnail_file.getvalue())
                thumbnail_path = thumb_dest.as_posix()

            tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
            extra_payload = {}
            if extra.strip():
                try:
                    extra_payload = json.loads(extra)
                except Exception as exc:
                    st.warning(f"額外資訊非有效 JSON：{exc}")

            template_store.upsert_template(
                {
                    "template_id": template_id,
                    "name": name,
                    "category": category,
                    "format": format_,
                    "description": description,
                    "tags": tags,
                    "license_type": license_type,
                    "price_type": price_type,
                    "price": price,
                    "author": author,
                    "storage_path": storage_path,
                    "thumbnail_path": thumbnail_path,
                    "extra": extra_payload,
                    "created_at": datetime.utcnow().isoformat(),
                }
            )
            st.success(f"模板 {name} 已建立（ID: {template_id}）。")
            st.experimental_rerun()


def section_manage_templates(df: pd.DataFrame) -> None:
    st.subheader("模板管理")
    if df.empty:
        st.info("尚無模板可以管理。")
        return

    template_options = df["template_id"] + " | " + df["name"]
    selection = st.selectbox("選擇模板", options=template_options)
    template_id = selection.split(" | ")[0]
    record = df[df["template_id"] == template_id].iloc[0]

    st.markdown(f"**目前狀態**：{record['status']}　**版本**：{record['version']}")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("版本 +1", key=f"version_{template_id}"):
            template_store.increment_version(template_id)
            st.success("版本已提升。")
            st.experimental_rerun()
    with col2:
        new_status = st.selectbox(
            "更新狀態",
            options=["draft", "approved", "retired"],
            index=["draft", "approved", "retired"].index(record["status"]) if record["status"] in ["draft", "approved", "retired"] else 0,
            key=f"status_{template_id}",
        )
        reviewer = st.text_input("審核人員", value=record.get("reviewer", ""), key=f"reviewer_{template_id}")
        notes = st.text_area("審核備註", key=f"notes_{template_id}", height=80)
        if st.button("儲存狀態", key=f"save_status_{template_id}"):
            checks = template_store.validate_template(template_id)
            template_store.mark_status(template_id, new_status, reviewer=reviewer, notes=notes, checks=checks)
            st.success("狀態與審核紀錄已更新。")
            st.experimental_rerun()
    with col3:
        if st.button("刪除模板", key=f"delete_{template_id}"):
            template_store.remove_template(template_id)
            st.success("模板已刪除。")
            st.experimental_rerun()

    st.markdown("#### ✔️ 樣板檢查")
    if st.button("執行檢查", key=f"validate_{template_id}"):
        result = template_store.validate_template(template_id)
        if result["ok"]:
            st.success("檢查通過：檔案與欄位皆完整。")
        else:
            st.warning("檢查發現以下問題：\n- " + "\n- ".join(result["issues"]))

    st.markdown("#### 🗒️ 審核紀錄")
    audits = template_store.load_audit_logs(template_id=template_id, limit=10)
    if audits.empty:
        st.write("尚無審核紀錄。")
    else:
        audits = audits.copy()
        audits["checks"] = audits["checks"].apply(lambda x: json.loads(x) if x else {})
        st.table(audits[["timestamp", "status", "reviewer", "notes"]])

    st.markdown("#### 📈 活動事件")
    events = template_metrics_store.load_events(template_id=template_id, limit=20)
    if events.empty:
        st.write("尚無活動事件資料。")
    else:
        st.table(events)


def section_export() -> None:
    st.subheader("匯出資料")
    if st.button("匯出 metadata.csv"):
        export_path = Path("data/templates/metadata_export.csv")
        template_store.export_metadata(export_path)
        with export_path.open("rb") as f:
            st.download_button(
                label="下載 metadata.csv",
                data=io.BytesIO(f.read()),
                file_name="template_metadata.csv",
                mime="text/csv",
                use_container_width=True,
            )


def main() -> None:
    df = _load_templates()
    section_overview(df)
    st.divider()
    section_create_template()
    st.divider()
    section_manage_templates(df)
    st.divider()
    section_export()


if __name__ == "__main__":
    main()
