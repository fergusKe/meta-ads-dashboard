import pandas as pd
import streamlit as st
from pathlib import Path

from utils.cache_manager import get_agent_cache
from utils.cost_analyzer import CostAnalyzer
from utils.logging_manager import log_event

st.set_page_config(page_title="效能與成本儀表板", page_icon="📊", layout="wide")

st.title("📊 效能與成本儀表板")
st.caption("追蹤 LLM 成本、快取效益與主要指標")

cache = get_agent_cache()
cache_stats = cache.get_stats()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("快取啟用", "是" if cache_stats['enabled'] else "否")
with col2:
    st.metric("有效快取", cache_stats['active_entries'])
with col3:
    st.metric("快取 TTL (秒)", cache_stats['ttl_seconds'])

def _resolve_usage_path() -> Path:
    default_path = Path("data/history/llm_usage.csv")
    try:
        secrets_obj = st.secrets  # may raise if secrets.toml 不存在
        candidate = secrets_obj.get("LLM_USAGE_FILE", None)
        if candidate:
            return Path(candidate)
    except Exception:
        pass
    return default_path


usage_path = _resolve_usage_path()
if not usage_path.exists():
    usage_path = Path("data/history/llm_usage.csv")

if usage_path.exists():
    logs = pd.read_csv(usage_path)
    st.subheader("📈 成本趨勢")
    logs['timestamp'] = pd.to_datetime(logs['timestamp'])
    st.line_chart(logs.set_index('timestamp')['cost'])

    analyzer = CostAnalyzer()
    summary = analyzer.generate_report(logs)

    st.subheader("💰 成本摘要")
    st.metric("本月成本", f"${summary.current_monthly_cost:.2f}")
    st.metric("潛在節省", f"${summary.total_potential_savings:.2f}", delta=f"{summary.savings_percentage:.1f}%")

    st.subheader("📌 優化建議")
    if summary.optimization_opportunities:
        for opp in summary.optimization_opportunities:
            st.info(f"{opp['type']} → 潛在節省 ${opp['potential_savings']:.2f}")
    else:
        st.success("目前沒有顯著的節省機會，保持現狀即可！")

    st.subheader("📦 原始記錄")
    st.dataframe(logs.tail(200), use_container_width=True)
else:
    st.info("尚無 LLM 成本紀錄。")

log_event("dashboard_view", {"page": "效能與成本儀表板"})
