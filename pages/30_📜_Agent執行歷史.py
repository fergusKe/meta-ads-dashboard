import streamlit as st

from utils.history_manager import load_history
from utils.exporter import export_json

st.set_page_config(page_title="Agent 執行歷史", page_icon="📜", layout="wide")

st.title("📜 Agent 執行歷史")
records = load_history()

if not records:
    st.info("尚無執行紀錄")
else:
    st.caption(f"共 {len(records)} 筆最近紀錄")
    for record in records:
        with st.expander(f"{record['timestamp']} - {record['agent']}", expanded=False):
            st.markdown("**輸入**")
            st.json(record.get('inputs', {}))
            st.markdown("**輸出摘要**")
            st.code(record.get('output_summary', ''), language="json")
            st.markdown("**其他資訊**")
            st.json(record.get('metadata', {}))

    if st.button("匯出最近紀錄為 JSON"):
        path = export_json({"records": records}, prefix="agent_history")
        st.success(f"已匯出至 {path.as_posix()}")
