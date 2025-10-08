from __future__ import annotations

import json
import streamlit as st

from utils import platform_specs, usage_store


st.set_page_config(page_title="多平台轉換中心", page_icon="🔁", layout="wide")
st.title("🔁 多平台轉換中心")
st.caption("查閱各平台素材規格，搭配 AI 模板快速轉換。")


@st.cache_data(ttl=60)
def _load_specs():
    return platform_specs.load_specs()


def main() -> None:
    df = _load_specs()
    platforms = sorted(df["platform"].unique())
    selected_platforms = st.sidebar.multiselect("平台", platforms)
    formats = sorted(df["ad_format"].unique())
    selected_formats = st.sidebar.multiselect("版位格式", formats)

    filtered = platform_specs.filter_specs(selected_platforms, selected_formats)
    st.markdown("### 平台規格表")
    st.dataframe(filtered, use_container_width=True)

    if not filtered.empty and st.button("匯出選取規格", use_container_width=True):
        bundle = platform_specs.export_spec_bundle(filtered)
        st.success("已匯出規格包。")
        with open(bundle, "rb") as f:
            st.download_button(
                "下載規格 ZIP",
                data=f.read(),
                file_name=bundle.name,
                mime="application/zip",
            )
        usage_store.record_event(
            "platform_specs",
            "export",
            {"platforms": list(filtered["platform"].unique())},
        )

    st.markdown("### AI 轉換模板")
    templates = platform_specs.list_conversion_templates()
    for template in templates:
        with st.expander(f"{template.platform}｜{template.format_name}｜{template.objective}"):
            st.code(template.prompt, language="markdown")
            st.markdown("**轉換檢查清單**")
            for item in template.checklist:
                st.markdown(f"- {item}")

    usage_store.record_event("platform_specs", "view", {"records": len(filtered)})


if __name__ == "__main__":
    main()
