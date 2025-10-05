import os
from dataclasses import dataclass
from typing import Callable, Optional

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from importlib import import_module

from utils.data_loader import load_meta_ads_data

# 載入環境變數
load_dotenv()

# 設定頁面配置
st.set_page_config(
    page_title="耘初茶食 Meta 廣告分析儀表板",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定義 CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }

    .metric-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
        color: #333333;
    }

    .metric-container h2 {
        color: #1f77b4;
        font-size: 2rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }

    .metric-container p {
        color: #666666;
        margin: 0;
        font-size: 0.9rem;
    }

    .status-good {
        color: #28a745;
        font-weight: bold;
    }

    .status-warning {
        color: #ffc107;
        font-weight: bold;
    }

    .status-danger {
        color: #dc3545;
        font-weight: bold;
    }

    .sidebar-header {
        color: #1f77b4;
        font-weight: bold;
        font-size: 1.2rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


@dataclass(frozen=True)
class PageConfig:
    label: str
    module: Optional[str]
    callable: str
    flag: Optional[str] = None


PAGE_DEFINITIONS: list[PageConfig] = [
    PageConfig("🏠 首頁概覽", None, "show_homepage"),
    PageConfig("📊 整體效能儀表板", "pages.1_📊_整體效能儀表板", "show_performance_dashboard"),
    PageConfig("🎯 活動分析", "pages.2_🎯_活動分析", "show_campaign_analysis"),
    PageConfig("👥 受眾洞察", "pages.3_👥_受眾洞察", "show_audience_insights"),
    PageConfig("💰 ROI 分析", "pages.4_💰_ROI分析", "show_roi_analysis"),
    PageConfig("🎨 素材成效分析", "pages.5_🎨_素材成效分析", "show_creative_analysis"),
    PageConfig("📈 廣告品質評分", "pages.6_📈_廣告品質評分", "show_quality_score_analysis"),
    PageConfig("🔄 轉換漏斗優化", "pages.7_🔄_轉換漏斗優化", "show_funnel_optimization"),
    PageConfig("📋 詳細數據表格", "pages.8_📋_詳細數據表格", "show_detailed_data_table"),
    PageConfig("📈 趨勢分析", "pages.09_📈_趨勢分析", "show_trend_analysis"),
    PageConfig("⚡ 即時優化建議", "pages.10_⚡_即時優化建議", "show_optimization_recommendations", "ENABLE_PERFORMANCE_PREDICTION"),
    PageConfig("🤖 AI 素材製作首頁", "pages.11_🤖_AI素材製作首頁", "show_ai_creative_hub", "ENABLE_AI_IMAGE_GENERATION"),
    PageConfig("✍️ AI 文案生成", "pages.12_✍️_AI文案生成", "main", "ENABLE_AI_COPYWRITING"),
    PageConfig("🎨 AI 圖片生成", "pages.13_🎨_AI圖片生成", "main", "ENABLE_AI_IMAGE_GENERATION"),
    PageConfig("🧠 智能素材優化", "pages.14_🧠_智能素材優化", "main", "ENABLE_AI_IMAGE_GENERATION"),
    PageConfig("🎯 智能投放策略", "pages.15_🎯_智能投放策略", "main", "ENABLE_PERFORMANCE_PREDICTION"),
]


def _env_flag(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_page_enabled(config: PageConfig) -> bool:
    return config.flag is None or _env_flag(config.flag)


def _get_page_config(label: str) -> Optional[PageConfig]:
    for config in PAGE_DEFINITIONS:
        if config.label == label and _is_page_enabled(config):
            return config
    return None


def _load_page_view(config: PageConfig) -> Callable[[], None]:
    module_path = config.module
    callable_name = config.callable

    if callable_name is None:
        raise RuntimeError("頁面缺少可呼叫的處理函式設定")

    if module_path:
        try:
            module = import_module(module_path)
        except ImportError as exc:
            raise RuntimeError(f"無法載入模組：{module_path} ({exc})") from exc

        try:
            view = getattr(module, callable_name)
        except AttributeError as exc:
            raise RuntimeError(f"模組缺少處理函式：{callable_name}") from exc
    else:
        view = globals().get(callable_name)
        if view is None:
            raise RuntimeError(f"找不到函式：{callable_name}")

    if not callable(view):
        raise RuntimeError("頁面處理函式不可呼叫")

    return view

def main():
    # 側邊欄導航
    with st.sidebar:
        st.markdown('<p class="sidebar-header">📊 導航選單</p>', unsafe_allow_html=True)

        # 檢查是否有導航指令
        if 'navigate_to' in st.session_state:
            target_page = st.session_state.navigate_to
            del st.session_state.navigate_to
        else:
            target_page = None

        # 統一的頁面選擇（依據環境旗標篩選）
        available_configs = [config for config in PAGE_DEFINITIONS if _is_page_enabled(config)]
        page_options = [config.label for config in available_configs]

        if not page_options:
            st.error("❌ 所有功能頁面皆被停用，請檢查環境旗標設定。")
            st.stop()

        # 如果有導航指令，設定對應的索引
        default_index = 0
        if target_page and target_page in page_options:
            default_index = page_options.index(target_page)

        page = st.selectbox(
            "選擇功能頁面",
            page_options,
            index=default_index
        )

        # 設定區
        st.markdown("---")
        st.markdown("### ⚙️ 設定")
        if st.button("🔄 重新載入數據"):
            st.cache_data.clear()
            st.rerun()

        st.info("💡 數據更新時間：每小時")

    page_config = _get_page_config(page)
    if not page_config:
        st.error(f"❌ 找不到頁面設定：{page}")
        st.stop()

    try:
        page_view = _load_page_view(page_config)
    except RuntimeError as exc:
        st.error(f"❌ 無法載入「{page}」頁面：{exc}")
        st.stop()

    try:
        page_view()
    except Exception as exc:  # pragma: no cover - streamlit runtime handling
        st.error(f"❌ 顯示「{page}」時發生未預期錯誤。")
        st.exception(exc)

def show_homepage():
    """顯示首頁概覽"""
    st.markdown('<h1 class="main-header">🏠 耘初茶食 Meta 廣告效能概覽</h1>', unsafe_allow_html=True)

    # 載入數據
    df = load_meta_ads_data()
    if df is None:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    # 使用分析報告期間篩選數據（與其他頁面保持一致）
    if '分析報告開始' in df.columns and '分析報告結束' in df.columns:
        report_start_dates = df['分析報告開始'].dropna()
        report_end_dates = df['分析報告結束'].dropna()

        if not report_start_dates.empty and not report_end_dates.empty:
            # 正確的篩選邏輯：廣告投放日期在分析報告期間內
            report_start = report_start_dates.min()
            report_end = report_end_dates.max()

            filtered_df = df[
                (df['開始'] >= report_start) &
                (df['開始'] <= report_end)
            ].copy()
        else:
            filtered_df = df
    else:
        filtered_df = df

    # 計算關鍵指標（使用篩選後的數據）
    total_spend = filtered_df['花費金額 (TWD)'].sum()
    total_purchases = filtered_df['購買次數'].sum()
    total_reach = filtered_df['觸及人數'].sum()
    total_impressions = filtered_df['曝光次數'].sum()
    avg_roas = filtered_df['購買 ROAS（廣告投資報酬率）'].mean()
    avg_cpa = filtered_df['每次購買的成本'].mean()
    avg_ctr = filtered_df['CTR（全部）'].mean()
    conversion_rate = (total_purchases / total_reach * 100) if total_reach > 0 else 0

    # 關鍵指標卡片區 (4x2 佈局)
    st.markdown("## 📊 關鍵效能指標")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="💰 總花費",
            value=f"${total_spend:,.0f} TWD",
            delta=None
        )

    with col2:
        st.metric(
            label="🛒 總購買次數",
            value=f"{total_purchases:.0f}",
            delta=None
        )

    with col3:
        st.metric(
            label="📈 平均 ROAS",
            value=f"{avg_roas:.2f}",
            delta=None,
            delta_color="normal" if avg_roas >= 3.0 else "inverse"
        )

    with col4:
        st.metric(
            label="👥 總觸及人數",
            value=f"{total_reach:,.0f}",
            delta=None
        )

    # 第二行指標
    col5, col6, col7, col8 = st.columns(4)

    with col5:
        st.metric(
            label="🎯 整體轉換率",
            value=f"{conversion_rate:.3f}%",
            delta=None
        )

    with col6:
        st.metric(
            label="💵 平均 CPA",
            value=f"${avg_cpa:.0f} TWD",
            delta=None
        )

    with col7:
        st.metric(
            label="👁️ 總曝光次數",
            value=f"{total_impressions:,.0f}",
            delta=None
        )

    with col8:
        st.metric(
            label="🖱️ 平均 CTR",
            value=f"{avg_ctr:.2f}%",
            delta=None
        )

    st.markdown("---")

    # 快速趨勢圖表
    st.markdown("## 📈 快速趨勢分析")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("### 📊 ROAS 趨勢")
        # 使用篩選後的數據進行趨勢分析
        if '開始' in filtered_df.columns:
            # 只使用有效的日期和數據
            df_with_dates = filtered_df.dropna(subset=['開始', '購買 ROAS（廣告投資報酬率）'])
            if not df_with_dates.empty:
                # 按日期分組計算 ROAS，只保留有數據的日期
                daily_roas = df_with_dates.groupby(df_with_dates['開始'].dt.date)['購買 ROAS（廣告投資報酬率）'].mean()

                # 進一步過濾掉 ROAS 為 0 或異常值的數據
                daily_roas = daily_roas[daily_roas > 0]

                if not daily_roas.empty and len(daily_roas) > 1:
                    st.line_chart(daily_roas)
                else:
                    st.info("暫無足夠的 ROAS 趨勢數據")
            else:
                st.info("暫無有效的 ROAS 數據")
        else:
            st.info("缺少日期欄位，無法顯示趨勢")

    with col_chart2:
        st.markdown("### 💰 花費 vs 購買次數")
        if '開始' in filtered_df.columns:
            # 只使用篩選後的有效日期和數據
            df_with_dates = filtered_df.dropna(subset=['開始'])
            df_with_data = df_with_dates[(df_with_dates['花費金額 (TWD)'] > 0) | (df_with_dates['購買次數'] > 0)]

            if not df_with_data.empty:
                daily_metrics = df_with_data.groupby(df_with_data['開始'].dt.date).agg({
                    '花費金額 (TWD)': 'sum',
                    '購買次數': 'sum'
                })

                # 只保留有實際數據的日期
                daily_metrics = daily_metrics[(daily_metrics['花費金額 (TWD)'] > 0) | (daily_metrics['購買次數'] > 0)]

                if not daily_metrics.empty and len(daily_metrics) > 1:
                    st.bar_chart(daily_metrics)
                else:
                    st.info("暫無足夠的花費趨勢數據")
            else:
                st.info("暫無有效的花費數據")
        else:
            st.info("缺少日期欄位，無法顯示趨勢")

    # 警報與狀態指示器
    st.markdown("---")
    st.markdown("## 🚨 廣告狀態監控")

    # 計算各狀態活動數量（使用篩選後的數據）
    good_campaigns = len(filtered_df[filtered_df['購買 ROAS（廣告投資報酬率）'] >= 3.0])
    warning_campaigns = len(filtered_df[(filtered_df['購買 ROAS（廣告投資報酬率）'] >= 1.0) &
                                (filtered_df['購買 ROAS（廣告投資報酬率）'] < 3.0)])
    poor_campaigns = len(filtered_df[filtered_df['購買 ROAS（廣告投資報酬率）'] < 1.0])

    col_status1, col_status2, col_status3 = st.columns(3)

    with col_status1:
        st.markdown(f"""
        <div class="metric-container">
            <div class="status-good">🟢 表現良好</div>
            <h2>{good_campaigns}</h2>
            <p>ROAS ≥ 3.0 的活動</p>
        </div>
        """, unsafe_allow_html=True)

    with col_status2:
        st.markdown(f"""
        <div class="metric-container">
            <div class="status-warning">🟡 需要關注</div>
            <h2>{warning_campaigns}</h2>
            <p>1.0 ≤ ROAS < 3.0 的活動</p>
        </div>
        """, unsafe_allow_html=True)

    with col_status3:
        st.markdown(f"""
        <div class="metric-container">
            <div class="status-danger">🔴 表現不佳</div>
            <h2>{poor_campaigns}</h2>
            <p>ROAS < 1.0 的活動</p>
        </div>
        """, unsafe_allow_html=True)

    # 快速動作按鈕
    st.markdown("---")
    st.markdown("## ⚡ 快速動作")

    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        if st.button("📊 查看詳細分析", use_container_width=True):
            st.info("請使用左側導航選單進入詳細分析頁面")

    with col_btn2:
        if st.button("📋 下載分析期間報告", use_container_width=True):
            # 生成分析期間報告
            csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="💾 下載 CSV",
                data=csv,
                file_name=f"耘初茶食_廣告報告_{pd.Timestamp.today().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

    with col_btn3:
        if st.button("⚙️ 設定警報閾值", use_container_width=True):
            st.info("警報設定功能開發中...")

    # 數據摘要
    st.markdown("---")
    st.markdown("## 📋 數據摘要")

    col_summary1, col_summary2 = st.columns(2)

    with col_summary1:
        # 計算實際數據範圍，優先使用分析報告日期
        if '分析報告開始' in filtered_df.columns and '分析報告結束' in filtered_df.columns:
            report_start_dates = filtered_df['分析報告開始'].dropna()
            report_end_dates = filtered_df['分析報告結束'].dropna()

            if not report_start_dates.empty and not report_end_dates.empty:
                actual_start = report_start_dates.min().strftime('%Y-%m-%d')
                actual_end = report_end_dates.max().strftime('%Y-%m-%d')
                date_range_text = f"{actual_start} 至 {actual_end} (分析期間)"
                valid_count = len(filtered_df.dropna(subset=['分析報告開始']))
            else:
                date_range_text = "無分析期間"
                valid_count = len(filtered_df)
        elif '開始' in filtered_df.columns and not filtered_df['開始'].isna().all():
            valid_dates = filtered_df['開始'].dropna()
            if not valid_dates.empty:
                actual_start = valid_dates.min().strftime('%Y-%m-%d')
                actual_end = valid_dates.max().strftime('%Y-%m-%d')
                date_range_text = f"{actual_start} 至 {actual_end} (廣告期間)"
                valid_count = len(valid_dates)
            else:
                date_range_text = "無有效日期"
                valid_count = 0
        else:
            date_range_text = "無日期資訊"
            valid_count = len(filtered_df)

        st.info(f"""
        **📊 數據概況**
        - 分析期間記錄：{len(filtered_df):,} 筆
        - 數據範圍：{date_range_text}
        - 有效記錄：{valid_count:,} 筆
        - 最後更新：{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
        """)

    with col_summary2:
        st.success(f"""
        **🎯 重點洞察**
        - 平均 ROAS：{avg_roas:.2f} {'✅ 良好' if avg_roas >= 3.0 else '⚠️ 需改善' if avg_roas >= 1.0 else '❌ 虧損'}
        - 轉換率：{conversion_rate:.3f}%
        - 總投資報酬：{((avg_roas - 1) * 100):.1f}% {'盈利' if avg_roas > 1 else '虧損'}
        """)

if __name__ == "__main__":
    main()
