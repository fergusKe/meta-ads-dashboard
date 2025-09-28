import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from utils.data_loader import load_meta_ads_data, filter_data_by_date_range
from utils.visualizations import (
    create_roas_distribution_chart,
    create_cpa_vs_purchases_scatter,
    create_ctr_vs_cpm_chart,
    create_spend_vs_efficiency_bubble,
    create_funnel_chart,
    create_performance_comparison_table,
    create_time_series_chart,
    create_campaign_performance_chart
)

def show_performance_dashboard():
    """顯示整體效能儀表板"""
    st.markdown("# 📊 整體效能儀表板")
    st.markdown("深入分析廣告投放效能，提供多維度的效能檢視")

    # 載入數據
    df = load_meta_ads_data()
    if df is None:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    # 時間範圍選擇器
    st.markdown("## 📅 時間範圍設定")

    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        # 優先使用分析報告日期範圍，這是實際的數據範圍
        if '分析報告開始' in df.columns and '分析報告結束' in df.columns:
            report_start_dates = df['分析報告開始'].dropna()
            report_end_dates = df['分析報告結束'].dropna()

            if not report_start_dates.empty and not report_end_dates.empty:
                data_min_date = report_start_dates.min().date()
                data_max_date = report_end_dates.max().date()
                default_start = data_min_date
                default_end = data_max_date
                date_source = "分析報告"
            else:
                # 備用：使用開始日期
                if '開始' in df.columns and not df['開始'].isna().all():
                    valid_dates = df['開始'].dropna()
                    if not valid_dates.empty:
                        data_min_date = valid_dates.min().date()
                        data_max_date = valid_dates.max().date()
                        default_start = data_min_date
                        default_end = data_max_date
                        date_source = "廣告開始"
                    else:
                        data_min_date = datetime.now().date() - timedelta(days=30)
                        data_max_date = datetime.now().date()
                        default_start = data_min_date
                        default_end = data_max_date
                        date_source = "預設"
                else:
                    data_min_date = datetime.now().date() - timedelta(days=30)
                    data_max_date = datetime.now().date()
                    default_start = data_min_date
                    default_end = data_max_date
                    date_source = "預設"
        else:
            # 備用：使用開始日期
            if '開始' in df.columns and not df['開始'].isna().all():
                valid_dates = df['開始'].dropna()
                if not valid_dates.empty:
                    data_min_date = valid_dates.min().date()
                    data_max_date = valid_dates.max().date()
                    default_start = data_min_date
                    default_end = data_max_date
                    date_source = "廣告開始"
                else:
                    data_min_date = datetime.now().date() - timedelta(days=30)
                    data_max_date = datetime.now().date()
                    default_start = data_min_date
                    default_end = data_max_date
                    date_source = "預設"
            else:
                data_min_date = datetime.now().date() - timedelta(days=30)
                data_max_date = datetime.now().date()
                default_start = data_min_date
                default_end = data_max_date
                date_source = "預設"

        start_date = st.date_input(
            "開始日期",
            value=default_start,
            min_value=data_min_date,
            max_value=data_max_date,
            help=f"實際數據範圍：{data_min_date} 至 {data_max_date} (來源：{date_source})"
        )

    with col2:
        end_date = st.date_input(
            "結束日期",
            value=default_end,
            min_value=data_min_date,
            max_value=data_max_date,
            help=f"實際數據範圍：{data_min_date} 至 {data_max_date} (來源：{date_source})"
        )

    with col3:
        # 快速選項
        quick_options = st.selectbox(
            "快速選擇",
            ["自訂範圍", "最近 7 天", "最近 30 天", "最近 90 天", "全部時間"]
        )

        if quick_options != "自訂範圍":
            if quick_options == "最近 7 天":
                start_date = max(data_max_date - timedelta(days=7), data_min_date)
                end_date = data_max_date
            elif quick_options == "最近 30 天":
                start_date = max(data_max_date - timedelta(days=30), data_min_date)
                end_date = data_max_date
            elif quick_options == "最近 90 天":
                start_date = max(data_max_date - timedelta(days=90), data_min_date)
                end_date = data_max_date
            elif quick_options == "全部時間":
                start_date = data_min_date
                end_date = data_max_date

    # 篩選數據
    if start_date <= end_date:
        filtered_df = filter_data_by_date_range(df, start_date, end_date)
    else:
        st.error("開始日期不能晚於結束日期！")
        filtered_df = df

    st.markdown("---")

    # 效能指標矩陣
    st.markdown("## 📈 效能指標分析")

    tab1, tab2, tab3, tab4 = st.tabs(["📊 分佈分析", "🎯 關係分析", "⚡ 效率分析", "📋 指標對比"])

    with tab1:
        st.markdown("### ROAS 分佈分析")
        roas_chart = create_roas_distribution_chart(filtered_df)
        if roas_chart:
            st.plotly_chart(roas_chart, use_container_width=True)
        else:
            st.info("暫無 ROAS 數據可供分析")

        # 活動效能排行
        st.markdown("### 🏆 活動效能排行")
        campaign_chart = create_campaign_performance_chart(filtered_df)
        if campaign_chart:
            st.plotly_chart(campaign_chart, use_container_width=True)
        else:
            st.info("暫無活動數據可供分析")

    with tab2:
        st.markdown("### CPA vs 購買次數關係")
        cpa_chart = create_cpa_vs_purchases_scatter(filtered_df)
        if cpa_chart:
            st.plotly_chart(cpa_chart, use_container_width=True)

            with st.expander("💡 圖表解讀"):
                st.markdown("""
                **如何解讀這個圖表：**
                - **X軸 (CPA)**：每次購買成本，越低越好
                - **Y軸 (購買次數)**：轉換次數，越高越好
                - **氣泡大小**：花費金額
                - **顏色**：ROAS 值，綠色表示表現好，紅色表示需改善

                **理想區域**：右下角（低CPA + 高購買次數）
                """)
        else:
            st.info("暫無 CPA 數據可供分析")

        st.markdown("### CTR vs CPM 效率分析")
        ctr_chart = create_ctr_vs_cpm_chart(filtered_df)
        if ctr_chart:
            st.plotly_chart(ctr_chart, use_container_width=True)
        else:
            st.info("暫無 CTR/CPM 數據可供分析")

    with tab3:
        st.markdown("### 花費 vs 轉換效率分析")
        efficiency_chart = create_spend_vs_efficiency_bubble(filtered_df)
        if efficiency_chart:
            st.plotly_chart(efficiency_chart, use_container_width=True)

            with st.expander("💡 轉換效率說明"):
                st.markdown("""
                **轉換效率** = 購買次數 / 花費金額 × 1000

                表示每花費 1000 元能獲得多少次轉換

                - **高效率**：每千元獲得較多轉換
                - **低效率**：需要優化預算分配或廣告策略
                """)
        else:
            st.info("暫無效率數據可供分析")

    with tab4:
        st.markdown("### 📊 效能指標對比表")
        comparison_table = create_performance_comparison_table(filtered_df)
        if comparison_table is not None:
            st.dataframe(
                comparison_table,
                use_container_width=True,
                column_config={
                    "指標": st.column_config.TextColumn("指標", width="medium"),
                    "實際值": st.column_config.TextColumn("實際值", width="small"),
                    "目標值": st.column_config.TextColumn("目標值", width="small"),
                    "達成率": st.column_config.TextColumn("達成率", width="small"),
                    "狀態": st.column_config.TextColumn("狀態", width="small")
                }
            )

            with st.expander("🎯 目標值設定說明"):
                st.markdown("""
                **目標值設定依據：**
                - **ROAS**: 3.0 (行業標準)
                - **CPA**: 300 TWD (根據產品毛利設定)
                - **CTR**: 2.0% (Facebook 平均值)
                - **CPM**: 100 TWD (市場平均成本)
                - **轉換率**: 1.0% (電商行業平均)
                """)
        else:
            st.info("暫無數據可供對比")

    st.markdown("---")

    # 漏斗轉換分析
    st.markdown("## 🎯 轉換漏斗分析")

    funnel_col1, funnel_col2 = st.columns([2, 1])

    with funnel_col1:
        funnel_chart = create_funnel_chart(filtered_df)
        if funnel_chart:
            st.plotly_chart(funnel_chart, use_container_width=True)
        else:
            st.info("暫無完整的漏斗數據")

    with funnel_col2:
        st.markdown("### 📈 漏斗效率指標")

        if not filtered_df.empty:
            # 計算各階段轉換率
            total_reach = filtered_df['觸及人數'].sum()
            total_clicks = filtered_df['點擊次數（全部）'].sum()
            total_page_views = filtered_df['連結頁面瀏覽次數'].sum()
            total_add_to_cart = filtered_df['加到購物車次數'].sum()
            total_checkout = filtered_df['開始結帳次數'].sum()
            total_purchases = filtered_df['購買次數'].sum()

            if total_reach > 0:
                click_rate = (total_clicks / total_reach * 100) if total_clicks > 0 else 0
                st.metric("觸及→點擊率", f"{click_rate:.2f}%")

            if total_clicks > 0:
                page_view_rate = (total_page_views / total_clicks * 100) if total_page_views > 0 else 0
                st.metric("點擊→頁面瀏覽率", f"{page_view_rate:.2f}%")

            if total_page_views > 0:
                cart_rate = (total_add_to_cart / total_page_views * 100) if total_add_to_cart > 0 else 0
                st.metric("瀏覽→加購率", f"{cart_rate:.2f}%")

            if total_add_to_cart > 0:
                checkout_rate = (total_checkout / total_add_to_cart * 100) if total_checkout > 0 else 0
                st.metric("加購→結帳率", f"{checkout_rate:.2f}%")

            if total_checkout > 0:
                purchase_rate = (total_purchases / total_checkout * 100) if total_purchases > 0 else 0
                st.metric("結帳→購買率", f"{purchase_rate:.2f}%")

            # 整體轉換率
            if total_reach > 0:
                overall_conversion = (total_purchases / total_reach * 100)
                st.metric("整體轉換率", f"{overall_conversion:.3f}%")

    st.markdown("---")

    # 時間趨勢分析
    st.markdown("## 📈 時間趨勢分析")

    trend_col1, trend_col2 = st.columns(2)

    with trend_col1:
        st.markdown("### ROAS 趨勢")
        # 確保只使用篩選後的有效數據
        roas_trend = create_time_series_chart(
            filtered_df,
            '開始',
            '購買 ROAS（廣告投資報酬率）',
            "ROAS 時間趨勢"
        )
        if roas_trend:
            st.plotly_chart(roas_trend, use_container_width=True)
        else:
            st.info("暫無 ROAS 趨勢數據，可能是因為選擇的時間範圍內沒有有效數據")

    with trend_col2:
        st.markdown("### 花費趨勢")
        # 確保只使用篩選後的有效數據
        spend_trend = create_time_series_chart(
            filtered_df,
            '開始',
            '花費金額 (TWD)',
            "花費時間趨勢"
        )
        if spend_trend:
            st.plotly_chart(spend_trend, use_container_width=True)
        else:
            st.info("暫無花費趨勢數據，可能是因為選擇的時間範圍內沒有有效數據")

    # 數據摘要
    st.markdown("---")
    st.markdown("## 📋 期間數據摘要")

    summary_col1, summary_col2, summary_col3 = st.columns(3)

    with summary_col1:
        st.info(f"""
        **📊 基本統計**
        - 分析期間：{start_date} 至 {end_date}
        - 總記錄數：{len(filtered_df):,} 筆
        - 活動數量：{filtered_df['行銷活動名稱'].nunique()} 個
        - 廣告組數：{filtered_df['廣告組合名稱'].nunique()} 個
        """)

    with summary_col2:
        if not filtered_df.empty:
            total_spend = filtered_df['花費金額 (TWD)'].sum()
            total_purchases = filtered_df['購買次數'].sum()
            avg_roas = filtered_df['購買 ROAS（廣告投資報酬率）'].mean()

            st.success(f"""
            **💰 投放成效**
            - 總花費：${total_spend:,.0f} TWD
            - 總購買：{total_purchases:.0f} 次
            - 平均 ROAS：{avg_roas:.2f}
            - 投資效益：{((avg_roas - 1) * 100):.1f}% {'盈利' if avg_roas > 1 else '虧損'}
            """)

    with summary_col3:
        if not filtered_df.empty:
            good_campaigns = len(filtered_df[filtered_df['購買 ROAS（廣告投資報酬率）'] >= 3.0])
            total_campaigns = len(filtered_df)
            good_rate = (good_campaigns / total_campaigns * 100) if total_campaigns > 0 else 0

            st.warning(f"""
            **⚡ 效能評估**
            - 優秀活動：{good_campaigns} 個
            - 優秀率：{good_rate:.1f}%
            - 需優化：{total_campaigns - good_campaigns} 個
            - 建議動作：{'繼續擴展優秀活動' if good_rate > 50 else '重點優化低效活動'}
            """)

if __name__ == "__main__":
    show_performance_dashboard()