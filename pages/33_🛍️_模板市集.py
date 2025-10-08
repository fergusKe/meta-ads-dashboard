import json
from pathlib import Path

import pandas as pd
import streamlit as st

from utils import template_metrics_store, template_store


st.set_page_config(page_title="模板市集", page_icon="🛍️", layout="wide")
st.title("🛍️ 模板市集")
st.caption("探索並下載高效模板，快速打造符合品牌調性的素材。")


@st.cache_data(ttl=1)
def load_metadata() -> pd.DataFrame:
    df = template_store.load_metadata()
    if df.empty:
        return df
    df = df.copy()
    df["tags"] = df["tags"].fillna("").astype(str)
    df["tag_list"] = df["tags"].apply(lambda x: [tag.strip() for tag in x.split(",") if tag.strip()])
    df["price"] = df["price"].fillna(0.0).astype(float)
    return df


def sidebar_filters(df: pd.DataFrame) -> pd.Series:
    st.sidebar.header("篩選條件")
    keyword = st.sidebar.text_input("關鍵字搜尋")
    categories = sorted(df["category"].fillna("").unique()) if not df.empty else []
    selected_categories = st.sidebar.multiselect("分類", [c for c in categories if c])
    formats = sorted(df["format"].fillna("").unique()) if not df.empty else []
    selected_formats = st.sidebar.multiselect("格式", [f for f in formats if f])
    price_type = st.sidebar.selectbox("收費模式", ["全部", "免費", "付費"])
    selected_tags = st.sidebar.text_input("標籤（用逗號分隔）", placeholder="促銷, 節慶")

    if df.empty:
        return pd.Series(dtype=bool)

    mask = pd.Series(True, index=df.index)
    if keyword:
        keyword_lower = keyword.lower()
        mask &= df["name"].str.lower().str.contains(keyword_lower) | df["description"].str.lower().str.contains(keyword_lower)
    if selected_categories:
        mask &= df["category"].isin(selected_categories)
    if selected_formats:
        mask &= df["format"].isin(selected_formats)
    if price_type == "免費":
        mask &= df["price_type"] == "free"
    elif price_type == "付費":
        mask &= df["price_type"] == "paid"
    if selected_tags:
        tags = [tag.strip().lower() for tag in selected_tags.split(",") if tag.strip()]
        if tags:
            mask &= df["tag_list"].apply(lambda tpl: all(tag in [t.lower() for t in tpl] for tag in tags))
    return mask


def render_cards(df: pd.DataFrame, metrics: pd.DataFrame) -> None:
    if df.empty:
        st.info("目前尚無符合條件的模板，請調整篩選條件或稍後再試。")
        return

    metrics = metrics.set_index("template_id") if not metrics.empty else pd.DataFrame()
    cols = st.columns(3)
    for idx, (_, row) in enumerate(df.iterrows()):
        col = cols[idx % 3]
        with col:
            st.container(border=True)
            st.markdown(f"### {row['name']}")
            st.markdown(f"**分類**：{row.get('category', '未指定')}　**格式**：{row.get('format', 'mixed')}")
            st.markdown(f"{row.get('description', '')[:120]}{'...' if len(row.get('description', '')) > 120 else ''}")
            if row["tag_list"]:
                st.markdown("標籤：" + "、".join(row["tag_list"]))
            if not metrics.empty and row["template_id"] in metrics.index:
                stats = metrics.loc[row["template_id"]]
                downloads = int(stats.get("download", 0))
                views = int(stats.get("view", 0))
                st.caption(f"🔁 瀏覽 {views} 次　⬇️ 下載 {downloads} 次")
            price_label = "免費" if row["price_type"] == "free" else f"NT$ {row['price']:,.0f}"
            st.metric("價格", price_label)
            detail_key = f"detail_{row['template_id']}"
            if st.button("查看詳情", key=detail_key):
                st.session_state["selected_template_id"] = row["template_id"]
                st.experimental_rerun()


def render_detail(template_id: str, df: pd.DataFrame) -> None:
    row = df[df["template_id"] == template_id]
    if row.empty:
        st.warning("找不到指定模板。")
        return
    record = row.iloc[0]
    st.header(record["name"])
    st.markdown(f"**分類**：{record.get('category', '未指定')}　**格式**：{record.get('format', 'mixed')}")
    st.markdown(f"**狀態**：{record.get('status', 'draft')}　**版本**：{record.get('version', 1)}")
    st.markdown(record.get("description", ""))
    if record["tag_list"]:
        st.markdown("**標籤**：" + "、".join(record["tag_list"]))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**授權類型**：{record.get('license_type', 'standard')}")
        st.markdown(f"**作者**：{record.get('author', '')}")
        st.markdown(f"**審核人**：{record.get('reviewer', '')}")
    with col2:
        st.markdown(f"**建立時間**：{record.get('created_at', '')}")
        st.markdown(f"**更新時間**：{record.get('updated_at', '')}")
        price_label = "免費" if record["price_type"] == "free" else f"NT$ {record['price']:,.0f}"
        st.markdown(f"**價格**：{price_label}")

    if record.get("extra"):
        try:
            extra = json.loads(record["extra"])
            st.write("**額外資訊**")
            st.json(extra, expanded=False)
        except Exception:
            st.write("**額外資訊**")
            st.markdown(record["extra"])

    feedback_summary = template_metrics_store.summarize_feedback(template_id)
    if not feedback_summary.empty:
        summary_row = feedback_summary.iloc[0]
        st.metric("平均評分", f"{summary_row['avg_rating']}/5", help="依據最新使用者回饋計算")
        st.caption(f"共 {int(summary_row['feedback_count'])} 筆回饋")

    consent = st.checkbox("我已閱讀並同意授權條款", key=f"consent_{template_id}")
    storage_path = Path(record["storage_path"]) if record.get("storage_path") else None
    if not consent:
        st.info("請勾選授權條款後即可下載。")
    elif storage_path and storage_path.exists():
        data = storage_path.read_bytes()
        download_clicked = st.download_button(
            label="下載模板",
            data=data,
            file_name=storage_path.name,
            mime="application/octet-stream",
            use_container_width=True,
        )
        if download_clicked:
            template_metrics_store.record_event(
                template_id=template_id,
                event_type="download",
                metadata={"filename": storage_path.name},
            )
    elif storage_path:
        st.error("找不到模板檔案，請聯繫管理員。")
    else:
        st.warning("此模板尚未上傳檔案。")

    st.divider()
    st.markdown("### 使用回饋")
    with st.form(f"feedback_form_{template_id}", clear_on_submit=True):
        rating = st.slider("整體滿意度 (1-5)", min_value=1, max_value=5, value=5)
        comment = st.text_area("想分享的建議或使用情境", placeholder="這個模板幫我節省了準備週報的時間...", height=120)
        contact = st.text_input("聯絡方式（選填）", placeholder="email 或 LINE ID")
        submitted = st.form_submit_button("送出回饋")
        if submitted:
            template_metrics_store.record_event(
                template_id=template_id,
                event_type="feedback",
                metadata={
                    "rating": rating,
                    "comment": comment.strip(),
                    "contact": contact.strip(),
                },
            )
            st.success("感謝回饋，我們會持續優化模板品質。")
            st.experimental_rerun()

    feedback_df = template_metrics_store.load_feedback(template_id, limit=10)
    if feedback_df.empty:
        st.info("目前尚無回饋，歡迎成為第一位分享者！")
    else:
        display_cols = feedback_df[["rating", "comment", "contact", "timestamp"]].rename(
            columns={
                "rating": "評分",
                "comment": "回饋內容",
                "contact": "聯絡資訊",
                "timestamp": "時間",
            }
        )
        st.table(display_cols)

    st.divider()
    if st.button("返回市集列表"):
        st.session_state.pop("selected_template_id", None)
        st.experimental_rerun()


def main() -> None:
    df = load_metadata()
    mask = sidebar_filters(df)
    metrics_summary = template_metrics_store.summarize_events()

    selected_template_id = st.session_state.get("selected_template_id")
    if selected_template_id:
        view_key = f"view_logged_{selected_template_id}"
        if not st.session_state.get(view_key):
            template_metrics_store.record_event(selected_template_id, "view")
            st.session_state[view_key] = True
        render_detail(selected_template_id, df)
        return

    filtered = df[mask] if not df.empty else df
    st.write(f"共 {len(filtered)} 個模板")
    render_cards(filtered, metrics_summary)


if __name__ == "__main__":
    main()
