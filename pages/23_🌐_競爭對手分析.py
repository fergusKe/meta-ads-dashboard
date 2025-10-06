import os
from datetime import datetime
from typing import List, Dict

import pandas as pd
import requests
import streamlit as st

from utils.data_loader import load_meta_ads_data
from utils.rag_service import RAGService
from utils.agents import CompetitorAnalysisAgent, CompetitorAnalysisResult

st.set_page_config(page_title="🌐 競爭對手分析", page_icon="🌐", layout="wide")


@st.cache_resource
def get_competitor_agent() -> CompetitorAnalysisAgent | None:
    try:
        return CompetitorAnalysisAgent()
    except Exception as exc:
        st.error(f"❌ 無法初始化 CompetitorAnalysisAgent：{exc}")
        return None


def search_ad_library(search_terms: str, access_token: str, limit: int = 10) -> List[Dict]:
    """呼叫 Meta Ad Library API 取得競品廣告資料。"""

    base_url = "https://graph.facebook.com/v18.0/ads_archive"
    params = {
        'access_token': access_token,
        'search_terms': search_terms,
        'ad_reached_countries': 'TW',
        'ad_active_status': 'ALL',
        'limit': limit,
        'fields': 'id,ad_creative_body,ad_creative_link_caption,ad_creative_link_title,'
                  'page_name,ad_delivery_start_time,impressions,spend'
    }

    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        return payload.get('data', [])
    except requests.exceptions.RequestException as exc:  # pragma: no cover - API 例外
        st.error(f"API 請求失敗：{exc}")
    except Exception as exc:  # pragma: no cover
        st.error(f"發生錯誤：{exc}")
    return []


def render_competitor_cards(competitor_ads: List[Dict]) -> None:
    if not competitor_ads:
        st.info("尚未取得競品廣告資料。")
        return

    st.markdown("### 📚 競品廣告樣本")
    for ad in competitor_ads[:6]:
        with st.expander(ad.get('page_name', '未知品牌'), expanded=False):
            st.markdown(f"**標題**：{ad.get('ad_creative_link_title', '無')}")
            st.markdown(f"**文案**：{(ad.get('ad_creative_body') or '')[:400]}")
            st.caption(
                " | ".join(
                    filter(
                        None,
                        [
                            f"開始投放：{ad.get('ad_delivery_start_time', '未知')}",
                            f"曝光：{_format_range(ad.get('impressions'))}",
                            f"花費：{_format_range(ad.get('spend'))}"
                        ],
                    )
                )
            )


def render_analysis(result: CompetitorAnalysisResult) -> None:
    st.subheader("🤖 AI 競品分析總結")
    st.markdown(result.overview)

    if result.competitor_strengths:
        st.markdown("### 🏆 競品強項分析")
        for item in result.competitor_strengths:
            st.markdown(f"- {item}")

    if result.our_differentiators:
        st.markdown("### 🎯 我們的差異化亮點")
        for item in result.our_differentiators:
            st.markdown(f"- {item}")

    if result.differentiation_ideas:
        st.markdown("### 💡 差異化文案構想")
        for idea in result.differentiation_ideas:
            with st.expander(idea.title, expanded=False):
                st.markdown(idea.description)
                st.markdown(f"**為何有效**：{idea.reason}")

    if result.avoid_strategies:
        st.markdown("### 🚫 避免同質化策略")
        for item in result.avoid_strategies:
            st.markdown(f"- {item}")

    if result.market_insights:
        st.markdown("### 📊 市場洞察")
        for item in result.market_insights:
            st.markdown(f"- {item}")

    if result.action_plan:
        st.markdown("### ✅ 行動計畫")
        for action in result.action_plan:
            st.markdown(f"**{action.priority} {action.action}** — {action.expected_impact}")

    if result.competitor_samples:
        st.markdown("### 📌 競品素材摘要")
        for sample in result.competitor_samples:
            with st.expander(sample.brand, expanded=False):
                st.markdown(f"**標題**：{sample.headline}")
                st.markdown(f"**文案**：{sample.body}")
                meta = []
                if sample.start_time:
                    meta.append(f"開始：{sample.start_time}")
                if sample.impressions:
                    meta.append(f"曝光：{sample.impressions}")
                if sample.spend:
                    meta.append(f"花費：{sample.spend}")
                if meta:
                    st.caption(" | ".join(meta))


def main() -> None:
    st.title("🌐 競爭對手分析")
    st.markdown("結合 Meta Ad Library 與 Pydantic AI Agent，快速產出競品差異化策略。")

    our_ads = load_meta_ads_data()
    if our_ads is None or our_ads.empty:
        st.error("❌ 無法載入我們的廣告數據。")
        return

    our_ads = our_ads.copy()

    st.markdown("### 🔍 搜尋競品廣告")
    col1, col2 = st.columns([3, 2])
    with col1:
        search_terms = st.text_input("輸入競品品牌或關鍵字", value="台灣茶飲")
    with col2:
        access_token = st.text_input("Meta Access Token", value=os.getenv('META_ACCESS_TOKEN', ''), type="password")

    limit = st.slider("下載廣告數量", min_value=5, max_value=25, value=10)

    competitor_ads: List[Dict] = st.session_state.get('competitor_ads', [])

    if st.button("🔎 搜尋競品廣告", type="primary"):
        if not access_token:
            st.error("請提供 Meta API Access Token。")
        else:
            competitor_ads = search_ad_library(search_terms, access_token, limit)
            st.session_state['competitor_ads'] = competitor_ads
            if not competitor_ads:
                st.warning("未找到相關競品廣告，請嘗試不同關鍵字。")

    if competitor_ads:
        render_competitor_cards(competitor_ads)

    st.markdown("### 🤖 AI 競品分析")
    use_rag = st.checkbox(
        "🧠 啟用歷史案例增強 (RAG)",
        value=True,
        help="若啟用，Agent 會引用知識庫中的成功案例"
    )

    if st.button("🚀 生成競品分析", type="primary", use_container_width=True):
        if not competitor_ads:
            st.warning("請先搜尋並載入競品廣告。")
        else:
            agent = get_competitor_agent()
            if agent is None:
                st.stop()

            rag_service = None
            rag_status_message = "📚 Step 2: 未啟用 RAG"

            with st.status("📋 Step 1: 初始化 Agent", expanded=True) as status:
                model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
                st.write("✓ Agent：**CompetitorAnalysisAgent**")
                st.write(f"✓ 模型：**{model_name}**")
                st.write("✓ 輸出類型：**CompetitorAnalysisResult**")
                status.update(label="✅ Step 1: 初始化完成", state="complete")

            if use_rag:
                with st.status("📚 Step 2: 載入 RAG 知識庫", expanded=True) as status:
                    try:
                        rag_service = RAGService()
                        if rag_service.load_knowledge_base("ad_creatives"):
                            st.write("✓ 知識庫：**ad_creatives**")
                            st.write("✓ 檢索模式：語義搜尋 (Top 3)")
                            status.update(label="✅ Step 2: RAG 載入完成", state="complete")
                            rag_status_message = "📚 Step 2: 已載入 RAG 知識庫"
                        else:
                            st.write("⚠️ 知識庫載入失敗，將改用一般模式")
                            rag_service = None
                            status.update(label="⚠️ Step 2: RAG 未啟用", state="error")
                            rag_status_message = "📚 Step 2: RAG 失敗"
                    except Exception as exc:  # pragma: no cover
                        st.write(f"⚠️ 載入失敗：{exc}")
                        rag_service = None
                        status.update(label="⚠️ Step 2: RAG 未啟用", state="error")
                        rag_status_message = "📚 Step 2: RAG 失敗"

            with st.status("🧠 Step 3: 生成分析", expanded=True) as status:
                st.write("📊 分析我們的廣告與競品素材…")
                st.write("🤖 正在產出差異化策略…")
                try:
                    result = agent.analyze_sync(
                        our_ads=our_ads,
                        competitor_ads=competitor_ads,
                        rag_service=rag_service,
                    )
                    status.update(label="✅ Step 3: 生成完成", state="complete")
                    st.session_state['competitor_result'] = result
                    st.session_state['competitor_generated_at'] = datetime.now()
                    st.session_state['competitor_rag_status'] = rag_status_message
                except Exception as exc:
                    status.update(label="❌ Step 3: 生成失敗", state="error")
                    st.error(f"❌ 生成競品分析時發生錯誤：{exc}")
                    import traceback
                    with st.expander("🔍 錯誤詳情"):
                        st.code(traceback.format_exc())

    result: CompetitorAnalysisResult | None = st.session_state.get('competitor_result')
    if result:
        st.markdown("---")
        generated_at = st.session_state.get('competitor_generated_at')
        rag_status_message = st.session_state.get('competitor_rag_status')
        if rag_status_message:
            st.caption(rag_status_message)
        if generated_at:
            st.caption(f"最後更新時間：{generated_at.strftime('%Y-%m-%d %H:%M:%S')}")

        render_analysis(result)

        if st.session_state.get('competitor_ads'):
            st.markdown("### 💾 下載分析報告")
            report = _build_report_markdown(result, st.session_state['competitor_ads'], generated_at)
            st.download_button(
                label="📥 下載競品分析報告 (Markdown)",
                data=report,
                file_name=f"競品分析報告_{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown"
            )
    else:
        st.info("點擊上方按鈕即可生成 AI 競品分析。")


def _format_range(value) -> Optional[str]:
    if isinstance(value, dict):
        lower = value.get('lower_bound')
        upper = value.get('upper_bound')
        if lower is not None and upper is not None:
            return f"{lower} ~ {upper}"
    return None


def _build_report_markdown(result: CompetitorAnalysisResult, competitor_ads: List[Dict], generated_at: datetime | None) -> str:
    timestamp = generated_at.strftime('%Y-%m-%d %H:%M:%S') if generated_at else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines = [
        "# 競品分析報告",
        f"**生成時間**：{timestamp}",
        "",
        "## 概要",
        result.overview,
        "",
        "## 競品強項",
    ]
    lines.extend([f"- {item}" for item in result.competitor_strengths])
    lines.append("\n## 我們的差異化")
    lines.extend([f"- {item}" for item in result.our_differentiators])
    lines.append("\n## 差異化文案構想")
    for idea in result.differentiation_ideas:
        lines.append(f"### {idea.title}")
        lines.append(idea.description)
        lines.append(f"- 為何有效：{idea.reason}\n")
    lines.append("## 避免策略")
    lines.extend([f"- {item}" for item in result.avoid_strategies])
    lines.append("\n## 市場洞察")
    lines.extend([f"- {item}" for item in result.market_insights])
    lines.append("\n## 行動建議")
    for action in result.action_plan:
        lines.append(f"- {action.priority} {action.action} — {action.expected_impact}")
    lines.append("\n## 競品廣告樣本")
    for ad in competitor_ads[:5]:
        lines.append(f"### {ad.get('page_name', '未知品牌')}")
        lines.append(f"- 標題：{ad.get('ad_creative_link_title', '無')}")
        body = (ad.get('ad_creative_body') or '').replace('\n', ' ')
        lines.append(f"- 內文：{body[:200]}")
        lines.append("")
    lines.append("---\n**本報告由 Meta 廣告智能分析儀表板自動生成**")
    return '\n'.join(lines)


if __name__ == "__main__":
    main()
