import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import os

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

        # 統一的頁面選擇
        page_options = [
            "🏠 首頁概覽",
            "📊 整體效能儀表板",
            "🎯 活動分析",
            "👥 受眾洞察",
            "💰 ROI 分析",
            "📈 趨勢分析",
            "⚡ 即時優化建議",
            "🤖 AI 素材製作首頁",
            "✍️ AI 文案生成",
            "🎨 AI 圖片生成",
            "🧠 智能素材優化",
            "📋 詳細數據表格"
        ]

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

    # 根據選擇顯示對應頁面
    if page == "🏠 首頁概覽":
        show_homepage()
    elif page == "📊 整體效能儀表板":
        from pages.performance_dashboard import show_performance_dashboard
        show_performance_dashboard()
    elif page == "🎯 活動分析":
        from pages.campaign_analysis import show_campaign_analysis
        show_campaign_analysis()
    elif page == "👥 受眾洞察":
        from pages.audience_insights import show_audience_insights
        show_audience_insights()
    elif page == "💰 ROI 分析":
        from pages.roi_analysis import show_roi_analysis
        show_roi_analysis()
    elif page == "📈 趨勢分析":
        from pages.trend_analysis import show_trend_analysis
        show_trend_analysis()
    elif page == "⚡ 即時優化建議":
        from pages.optimization_recommendations import show_optimization_recommendations
        show_optimization_recommendations()
    elif page == "🤖 AI 素材製作首頁":
        from pages.ai_creative_hub import show_ai_creative_hub
        show_ai_creative_hub()
    elif page == "✍️ AI 文案生成":
        from pages.ai_copywriting import main as show_ai_copywriting
        show_ai_copywriting()
    elif page == "🎨 AI 圖片生成":
        from pages.ai_image_generation import main as show_ai_image_generation
        show_ai_image_generation()
    elif page == "🧠 智能素材優化":
        from pages.smart_creative_optimization import main as show_smart_creative_optimization
        show_smart_creative_optimization()
    elif page == "📋 詳細數據表格":
        from pages.detailed_data_table import main as show_detailed_data_table
        show_detailed_data_table()

@st.cache_data
def load_data():
    """載入並快取 Meta 廣告數據"""
    try:
        data_file = os.getenv('DATA_FILE_PATH', '耘初茶食.xlsx')
        df = pd.read_excel(data_file)

        # 基本數據清理
        date_columns = ['開始', '結束時間', '分析報告開始', '分析報告結束']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # 填充數值型欄位的缺失值
        numeric_columns = df.select_dtypes(include=['number']).columns
        df[numeric_columns] = df[numeric_columns].fillna(0)

        return df
    except Exception as e:
        st.error(f"❌ 數據載入失敗：{e}")
        return None

def show_homepage():
    """顯示首頁概覽"""
    st.markdown('<h1 class="main-header">🏠 耘初茶食 Meta 廣告效能概覽</h1>', unsafe_allow_html=True)

    # 載入數據
    df = load_data()
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