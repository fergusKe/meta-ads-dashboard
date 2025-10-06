import streamlit as st

from utils.preferences import get_user_preference, set_user_preference

st.set_page_config(page_title="個人化偏好", page_icon="⚙️", layout="centered")

st.title("⚙️ 個人化偏好設定")

complexity = st.selectbox(
    "文案生成複雜度",
    options=["fast", "balanced", "quality"],
    index=["fast", "balanced", "quality"].index(get_user_preference("copywriting_complexity", "balanced"))
)
set_user_preference("copywriting_complexity", complexity)

image_complexity = st.selectbox(
    "圖片提示複雜度",
    options=["fast", "balanced", "quality"],
    index=["fast", "balanced", "quality"].index(get_user_preference("image_prompt_complexity", "balanced"))
)
set_user_preference("image_prompt_complexity", image_complexity)

st.success("偏好設定已更新，將於下一次執行時套用。")
