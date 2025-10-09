import json
from pathlib import Path

import pandas as pd
import streamlit as st

from utils import brand_license_store, license_notification_service, license_pilot_tracker
from utils.rag_service import RAGService


st.set_page_config(page_title="品牌知識庫授權", page_icon="🔐", layout="wide")
st.title("🔐 品牌知識庫授權管理")
st.caption("建立授權方案、維護授權檔案並一鍵套用至品牌知識庫。")


@st.cache_data(ttl=1)
def load_metadata() -> pd.DataFrame:
    df = brand_license_store.load_metadata()
    if df.empty:
        return df
    df = df.copy()
    df["tags"] = df["tags"].fillna("").astype(str)
    df["applied_brands"] = df["applied_brands"].fillna("[]").astype(str)
    return df


def section_overview(df: pd.DataFrame) -> None:
    st.subheader("授權方案列表")
    if df.empty:
        st.info("尚未建立任何授權方案。")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("授權方案總數", len(df))
    with col2:
        available = len(df[df["status"] == "available"])
        st.metric("可販售", available)
    with col3:
        applied_total = df["applied_brands"].apply(lambda x: len(json.loads(x) if x else [])).sum()
        st.metric("累計授權次數", applied_total)

    display_cols = ["license_id", "name", "brand", "status", "price_type", "price", "knowledge_path", "updated_at"]
    st.dataframe(df[display_cols], use_container_width=True, height=360)


def section_create_license() -> None:
    st.subheader("新增授權方案")
    with st.form("create_license_form", clear_on_submit=True):
        name = st.text_input("方案名稱")
        brand = st.text_input("適用品牌識別（brand_code）")
        description = st.text_area("授權說明", height=120)
        tags_text = st.text_input("標籤（以逗號分隔）", placeholder="品牌語氣, 禁詞庫")
        status = st.selectbox("狀態", ["draft", "available", "retired"])
        price_type = st.selectbox("收費模式", ["one_time", "subscription", "free"])
        price = st.number_input("價格 (TWD)", min_value=0.0, value=0.0, step=100.0, disabled=price_type == "free")
        terms = st.text_area("授權條款", placeholder="使用者需遵守的條款…", height=100)
        knowledge_file = st.file_uploader("知識庫檔案（txt/md/json）", type=["txt", "md", "json"])
        extra = st.text_area("額外資訊（JSON 選填）")

        submitted = st.form_submit_button("建立授權方案")
        if submitted:
            if not name.strip():
                st.error("請輸入方案名稱")
                return
            if not knowledge_file:
                st.error("請上傳知識庫檔案")
                return

            license_id = f"lic_{name.strip().replace(' ', '_')}_{brand.strip() or 'default'}"
            saved = brand_license_store.save_knowledge_file(license_id, knowledge_file.name, knowledge_file.getvalue())
            knowledge_path = saved.parent.as_posix()

            tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
            extra_payload = {}
            if extra.strip():
                try:
                    extra_payload = json.loads(extra)
                except Exception as exc:
                    st.warning(f"額外資訊非有效 JSON：{exc}")

            brand_license_store.upsert_license(
                {
                    "license_id": license_id,
                    "name": name,
                    "brand": brand,
                    "description": description,
                    "tags": tags,
                    "status": status,
                    "price_type": price_type,
                    "price": price,
                    "knowledge_path": knowledge_path,
                    "terms": terms,
                    "extra": extra_payload,
                }
            )
            st.success(f"授權方案 {license_id} 已建立。")
            st.rerun()


def section_apply_license(df: pd.DataFrame) -> None:
    st.subheader("套用授權至品牌知識庫")
    if df.empty:
        st.info("尚無授權方案可套用。")
        return

    options = df["license_id"] + " | " + df["name"]
    selection = st.selectbox("選擇授權方案", options)
    license_id = selection.split(" | ")[0]
    record = brand_license_store.get_license(license_id)

    st.markdown(f"**描述**：{record.get('description', '')}")
    st.markdown(f"**知識庫路徑**：{record.get('knowledge_path', '')}")
    try:
        history = record.get("applied_brands", [])
        if history:
            st.write("歷史套用：")
            st.table(pd.DataFrame(history))
    except Exception:
        pass

    brand_code = st.text_input("目標品牌代碼", value=record.get("brand", ""))
    collection_name = st.text_input("RAG Collection 名稱", value="brand_knowledge")
    apply_btn = st.button("套用授權", use_container_width=True)
    if apply_btn:
        if not brand_code.strip():
            st.error("請輸入品牌代碼")
            return
        try:
            rag = RAGService()
            rag_available = rag.load_knowledge_base(collection_name=collection_name)
            if not rag_available:
                st.warning("RAG 未載入，將僅紀錄授權，不進行向量更新。")
                rag = None
        except Exception as exc:
            st.warning(f"RAG 初始化失敗：{exc}\n將僅紀錄授權。")
            rag = None
        try:
            count = brand_license_store.apply_license_to_brand(
                license_id=license_id,
                brand_code=brand_code.strip(),
                rag_service=rag,
                collection_name=collection_name,
            )
            msg = "已記錄授權"
            if rag is not None:
                msg = f"已將 {count} 筆文件套入 RAG 並記錄授權。"
            st.success(msg)
        except Exception as exc:
            st.error(f"套用失敗：{exc}")


def section_delete_license(df: pd.DataFrame) -> None:
    st.subheader("刪除授權方案")
    if df.empty:
        return
    options = df["license_id"] + " | " + df["name"]
    selection = st.selectbox("選擇要刪除的方案", options, key="delete_license_select")
    license_id = selection.split(" | ")[0]
    if st.button("刪除選定方案", key="delete_license_btn"):
        brand_license_store.delete_license(license_id)
        st.success("授權方案已刪除。")
        st.rerun()


def section_notifications() -> None:
    st.subheader("授權到期提醒")
    within_days = st.slider("提醒區間 (天)", min_value=3, max_value=60, value=14, step=1)
    plan = license_notification_service.build_notification_plan(within_days=within_days)
    if plan.empty:
        st.info("目前沒有即將到期的授權。")
    else:
        st.dataframe(plan, use_container_width=True)
        if st.button("同步至通知排程", key="schedule_notifications"):
            license_notification_service.record_notifications(plan, status="scheduled")
            st.success("已記錄提醒排程。")

    history = license_notification_service.load_notification_log()
    if not history.empty:
        st.markdown("**通知紀錄**")
        st.dataframe(history.tail(20), use_container_width=True)


def section_pilot_tracker() -> None:
    st.subheader("授權試點追蹤")
    with st.form("license_pilot_form"):
        license_id = st.text_input("授權 ID")
        brand_code = st.text_input("客戶品牌代碼")
        status = st.selectbox("試點狀態", ["success", "in_progress", "fail"])
        lift = st.number_input("成效提升 (%)", min_value=-100.0, max_value=200.0, value=0.0, step=0.5)
        notes = st.text_area("備註", height=80)
        recorded_by = st.text_input("記錄者", value=st.session_state.get("current_user", ""))
        submitted = st.form_submit_button("儲存試點紀錄")
        if submitted:
            if not license_id or not brand_code:
                st.error("請填寫授權 ID 與品牌代碼。")
            else:
                license_pilot_tracker.log_pilot_event(
                    license_id=license_id,
                    brand_code=brand_code,
                    status=status,
                    metrics={"lift": lift},
                    notes=notes,
                    recorded_by=recorded_by,
                )
                st.success("試點紀錄已儲存。")
                st.rerun()

    summary = license_pilot_tracker.summarize_pilots()
    if summary.empty:
        st.info("尚未建立授權試點紀錄。")
    else:
        st.dataframe(summary, use_container_width=True)


def main() -> None:
    df = load_metadata()
    section_overview(df)
    st.divider()
    section_create_license()
    st.divider()
    section_apply_license(df)
    st.divider()
    section_notifications()
    st.divider()
    section_pilot_tracker()
    st.divider()
    section_delete_license(df)


if __name__ == "__main__":
    main()
