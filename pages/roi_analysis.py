import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.data_loader import load_meta_ads_data, filter_data_by_date_range
import numpy as np

def show_roi_analysis():
    """顯示 ROI 分析頁面"""
    st.markdown("# 💰 ROI 投資報酬率分析")
    st.markdown("深入分析廣告投資報酬率，識別高價值活動與優化機會")

    # 載入數據
    df = load_meta_ads_data()
    if df is None:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    # 時間範圍選擇器
    st.markdown("## 📅 時間範圍設定")

    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        # 優先使用分析報告日期範圍
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

    # ROI 概覽儀表板
    st.markdown("## 📊 ROI 概覽儀表板")

    if not filtered_df.empty:
        # 計算 ROI 指標
        total_spend = filtered_df['花費金額 (TWD)'].sum()
        # 計算總收益：ROAS × 花費金額
        filtered_df_with_revenue = filtered_df[
            (filtered_df['花費金額 (TWD)'] > 0) &
            (~filtered_df['購買 ROAS（廣告投資報酬率）'].isna())
        ].copy()
        filtered_df_with_revenue['計算收益'] = (
            filtered_df_with_revenue['購買 ROAS（廣告投資報酬率）'] *
            filtered_df_with_revenue['花費金額 (TWD)']
        )
        total_revenue = filtered_df_with_revenue['計算收益'].sum()
        total_purchases = filtered_df['購買次數'].sum()
        avg_roas = filtered_df['購買 ROAS（廣告投資報酬率）'].mean()

        # ROI 計算 (ROAS - 1) * 100
        total_roi = ((total_revenue / total_spend) - 1) * 100 if total_spend > 0 else 0
        avg_roi = (avg_roas - 1) * 100 if not np.isnan(avg_roas) else 0

        # 盈虧平衡點
        breakeven_campaigns = len(filtered_df[filtered_df['購買 ROAS（廣告投資報酬率）'] >= 1.0])
        profitable_campaigns = len(filtered_df[filtered_df['購買 ROAS（廣告投資報酬率）'] >= 3.0])
        total_campaigns = len(filtered_df)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "💰 總投資報酬率",
                f"{total_roi:.1f}%",
                delta=f"{'盈利' if total_roi > 0 else '虧損'}"
            )

        with col2:
            st.metric(
                "📈 平均 ROI",
                f"{avg_roi:.1f}%",
                delta=f"ROAS {avg_roas:.2f}" if not np.isnan(avg_roas) else "N/A"
            )

        with col3:
            profitability_rate = (profitable_campaigns / total_campaigns * 100) if total_campaigns > 0 else 0
            st.metric(
                "🎯 獲利活動比例",
                f"{profitability_rate:.1f}%",
                delta=f"{profitable_campaigns}/{total_campaigns}"
            )

        with col4:
            breakeven_rate = (breakeven_campaigns / total_campaigns * 100) if total_campaigns > 0 else 0
            st.metric(
                "⚖️ 盈虧平衡比例",
                f"{breakeven_rate:.1f}%",
                delta=f"{breakeven_campaigns}/{total_campaigns}"
            )

        st.markdown("---")

        # ROI 分析圖表
        tab1, tab2, tab3, tab4 = st.tabs(["📊 ROI 分佈", "💎 價值分析", "📈 趨勢分析", "🔍 深度洞察"])

        with tab1:
            st.markdown("### ROI 分佈分析")

            col_dist1, col_dist2 = st.columns(2)

            with col_dist1:
                # ROI 分佈直方圖
                roi_data = (filtered_df['購買 ROAS（廣告投資報酬率）'] - 1) * 100
                roi_data = roi_data.dropna()

                if not roi_data.empty:
                    fig_hist = px.histogram(
                        x=roi_data,
                        nbins=20,
                        title="ROI 分佈直方圖",
                        labels={'x': 'ROI (%)', 'y': '活動數量'}
                    )

                    # 添加盈虧平衡線
                    fig_hist.add_vline(
                        x=0,
                        line_dash="dash",
                        line_color="red",
                        annotation_text="盈虧平衡點"
                    )

                    # 添加目標線 (200% ROI)
                    fig_hist.add_vline(
                        x=200,
                        line_dash="dash",
                        line_color="green",
                        annotation_text="目標 ROI: 200%"
                    )

                    st.plotly_chart(fig_hist, width='stretch')
                else:
                    st.info("暫無 ROI 數據可供分析")

            with col_dist2:
                # ROI 象限分析
                roi_segments = {
                    "🔴 虧損": len(filtered_df[filtered_df['購買 ROAS（廣告投資報酬率）'] < 1.0]),
                    "🟡 微利": len(filtered_df[(filtered_df['購買 ROAS（廣告投資報酬率）'] >= 1.0) &
                                           (filtered_df['購買 ROAS（廣告投資報酬率）'] < 2.0)]),
                    "🟢 獲利": len(filtered_df[(filtered_df['購買 ROAS（廣告投資報酬率）'] >= 2.0) &
                                           (filtered_df['購買 ROAS（廣告投資報酬率）'] < 3.0)]),
                    "💎 高獲利": len(filtered_df[filtered_df['購買 ROAS（廣告投資報酬率）'] >= 3.0])
                }

                if sum(roi_segments.values()) > 0:
                    fig_pie = px.pie(
                        values=list(roi_segments.values()),
                        names=list(roi_segments.keys()),
                        title="ROI 象限分佈",
                        color_discrete_sequence=['#ff4444', '#ffaa00', '#44ff44', '#00aa44']
                    )
                    st.plotly_chart(fig_pie, width='stretch')
                else:
                    st.info("暫無數據可供象限分析")

        with tab2:
            st.markdown("### 投資價值分析")

            # 花費 vs ROI 散點圖
            scatter_data = filtered_df[
                (filtered_df['花費金額 (TWD)'] > 0) &
                (~filtered_df['購買 ROAS（廣告投資報酬率）'].isna())
            ].copy()

            if not scatter_data.empty:
                scatter_data['ROI (%)'] = (scatter_data['購買 ROAS（廣告投資報酬率）'] - 1) * 100

                fig_scatter = px.scatter(
                    scatter_data,
                    x='花費金額 (TWD)',
                    y='ROI (%)',
                    size='購買次數',
                    color='購買 ROAS（廣告投資報酬率）',
                    hover_data=['行銷活動名稱'],
                    title="花費 vs ROI 關係分析",
                    labels={'花費金額 (TWD)': '花費金額 (TWD)', 'ROI (%)': 'ROI (%)'},
                    color_continuous_scale='RdYlGn'
                )

                # 添加盈虧平衡線
                fig_scatter.add_hline(
                    y=0,
                    line_dash="dash",
                    line_color="red",
                    annotation_text="盈虧平衡線"
                )

                st.plotly_chart(fig_scatter, width='stretch')

                with st.expander("💡 價值分析解讀"):
                    st.markdown("""
                    **如何解讀這個圖表：**
                    - **Y軸 (ROI)**：投資報酬率，0%以上為盈利
                    - **X軸 (花費)**：投資金額
                    - **氣泡大小**：購買次數
                    - **顏色**：ROAS 值，綠色表現好

                    **策略建議：**
                    - **右上角**：高花費+高ROI，值得擴大投資
                    - **左上角**：低花費+高ROI，可考慮增加預算
                    - **右下角**：高花費+低ROI，需要優化或暫停
                    """)
            else:
                st.info("暫無價值分析數據")

        with tab3:
            st.markdown("### ROI 時間趨勢分析")

            trend_col1, trend_col2 = st.columns(2)

            with trend_col1:
                # ROI 趨勢圖
                if '開始' in filtered_df.columns:
                    trend_data = filtered_df.dropna(subset=['開始', '購買 ROAS（廣告投資報酬率）'])

                    if not trend_data.empty:
                        # 按日期計算 ROI
                        daily_roi = trend_data.groupby(trend_data['開始'].dt.date).agg({
                            '購買 ROAS（廣告投資報酬率）': 'mean',
                            '花費金額 (TWD)': 'sum'
                        }).reset_index()

                        daily_roi['ROI (%)'] = (daily_roi['購買 ROAS（廣告投資報酬率）'] - 1) * 100

                        # 過濾有效數據
                        daily_roi = daily_roi[daily_roi['ROI (%)'].notna()]

                        if not daily_roi.empty and len(daily_roi) > 1:
                            fig_trend = px.line(
                                daily_roi,
                                x='開始',
                                y='ROI (%)',
                                title="ROI 時間趨勢",
                                markers=True
                            )

                            # 添加盈虧平衡線
                            fig_trend.add_hline(
                                y=0,
                                line_dash="dash",
                                line_color="red",
                                annotation_text="盈虧平衡"
                            )

                            # 設定 X 軸範圍
                            fig_trend.update_layout(
                                height=400,
                                xaxis=dict(
                                    range=[daily_roi['開始'].min(), daily_roi['開始'].max()]
                                )
                            )

                            st.plotly_chart(fig_trend, width='stretch')
                        else:
                            st.info("暫無足夠的 ROI 趨勢數據")
                    else:
                        st.info("暫無有效的 ROI 趨勢數據")
                else:
                    st.info("缺少日期欄位，無法顯示趨勢")

            with trend_col2:
                # 累積 ROI 趨勢
                if '開始' in filtered_df.columns:
                    trend_data = filtered_df.dropna(subset=['開始', '花費金額 (TWD)', '購買 ROAS（廣告投資報酬率）'])

                    if not trend_data.empty:
                        # 計算每日收益
                        trend_data_with_revenue = trend_data.copy()
                        trend_data_with_revenue['計算收益'] = (
                            trend_data_with_revenue['購買 ROAS（廣告投資報酬率）'] *
                            trend_data_with_revenue['花費金額 (TWD)']
                        )

                        # 按日期排序並計算累積值
                        daily_cumulative = trend_data_with_revenue.groupby(trend_data_with_revenue['開始'].dt.date).agg({
                            '花費金額 (TWD)': 'sum',
                            '計算收益': 'sum'
                        }).reset_index().sort_values('開始')

                        daily_cumulative['累積花費'] = daily_cumulative['花費金額 (TWD)'].cumsum()
                        daily_cumulative['累積收益'] = daily_cumulative['計算收益'].cumsum()
                        daily_cumulative['累積 ROI (%)'] = (
                            (daily_cumulative['累積收益'] / daily_cumulative['累積花費'] - 1) * 100
                        ).fillna(0)

                        if not daily_cumulative.empty and len(daily_cumulative) > 1:
                            fig_cumulative = px.line(
                                daily_cumulative,
                                x='開始',
                                y='累積 ROI (%)',
                                title="累積 ROI 趨勢",
                                markers=True
                            )

                            # 添加盈虧平衡線
                            fig_cumulative.add_hline(
                                y=0,
                                line_dash="dash",
                                line_color="red",
                                annotation_text="盈虧平衡"
                            )

                            # 設定 X 軸範圍
                            fig_cumulative.update_layout(
                                height=400,
                                xaxis=dict(
                                    range=[daily_cumulative['開始'].min(), daily_cumulative['開始'].max()]
                                )
                            )

                            st.plotly_chart(fig_cumulative, width='stretch')
                        else:
                            st.info("暫無累積 ROI 數據")
                    else:
                        st.info("暫無有效的累積數據")
                else:
                    st.info("缺少日期欄位，無法顯示累積趨勢")

        with tab4:
            st.markdown("### 深度 ROI 洞察")

            insight_col1, insight_col2 = st.columns(2)

            with insight_col1:
                st.markdown("#### 🏆 Top 10 最佳 ROI 活動")

                # 計算活動 ROI
                campaign_roi = filtered_df.groupby('行銷活動名稱').agg({
                    '購買 ROAS（廣告投資報酬率）': 'mean',
                    '花費金額 (TWD)': 'sum',
                    '購買次數': 'sum'
                }).reset_index()

                campaign_roi['ROI (%)'] = (campaign_roi['購買 ROAS（廣告投資報酬率）'] - 1) * 100

                # 排序並取前 10 名
                top_campaigns = campaign_roi.nlargest(10, 'ROI (%)')

                if not top_campaigns.empty:
                    fig_top = px.bar(
                        top_campaigns,
                        x='ROI (%)',
                        y='行銷活動名稱',
                        orientation='h',
                        title="Top 10 最佳 ROI 活動",
                        color='ROI (%)',
                        color_continuous_scale='RdYlGn'
                    )

                    fig_top.update_layout(
                        height=500,
                        yaxis={'categoryorder': 'total ascending'}
                    )

                    st.plotly_chart(fig_top, width='stretch')
                else:
                    st.info("暫無活動 ROI 數據")

            with insight_col2:
                st.markdown("#### 📊 ROI 效能矩陣")

                # 創建效能矩陣數據
                if not filtered_df.empty:
                    matrix_data = filtered_df.groupby('行銷活動名稱').agg({
                        '花費金額 (TWD)': 'sum',
                        '購買 ROAS（廣告投資報酬率）': 'mean',
                        '購買次數': 'sum'
                    }).reset_index()

                    matrix_data['ROI (%)'] = (matrix_data['購買 ROAS（廣告投資報酬率）'] - 1) * 100

                    # 計算中位數作為分割點
                    median_spend = matrix_data['花費金額 (TWD)'].median()
                    median_roi = matrix_data['ROI (%)'].median()

                    if not matrix_data.empty:
                        fig_matrix = px.scatter(
                            matrix_data,
                            x='花費金額 (TWD)',
                            y='ROI (%)',
                            size='購買次數',
                            hover_data=['行銷活動名稱'],
                            title="ROI 效能矩陣",
                            labels={'花費金額 (TWD)': '花費金額 (TWD)', 'ROI (%)': 'ROI (%)'}
                        )

                        # 添加象限分割線
                        fig_matrix.add_vline(x=median_spend, line_dash="dash", line_color="gray")
                        fig_matrix.add_hline(y=median_roi, line_dash="dash", line_color="gray")
                        fig_matrix.add_hline(y=0, line_dash="solid", line_color="red")

                        # 添加象限標籤
                        fig_matrix.add_annotation(
                            x=matrix_data['花費金額 (TWD)'].max() * 0.8,
                            y=matrix_data['ROI (%)'].max() * 0.8,
                            text="高花費高ROI<br>🌟明星活動",
                            showarrow=False,
                            bgcolor="lightgreen",
                            bordercolor="green"
                        )

                        fig_matrix.add_annotation(
                            x=matrix_data['花費金額 (TWD)'].max() * 0.2,
                            y=matrix_data['ROI (%)'].max() * 0.8,
                            text="低花費高ROI<br>💎潛力活動",
                            showarrow=False,
                            bgcolor="lightblue",
                            bordercolor="blue"
                        )

                        st.plotly_chart(fig_matrix, width='stretch')
                    else:
                        st.info("暫無效能矩陣數據")

        # ROI 優化建議
        st.markdown("---")
        st.markdown("## 🎯 ROI 優化建議")

        col_rec1, col_rec2, col_rec3 = st.columns(3)

        with col_rec1:
            # 高 ROI 活動
            high_roi_campaigns = filtered_df[filtered_df['購買 ROAS（廣告投資報酬率）'] >= 3.0]
            if not high_roi_campaigns.empty:
                top_performer = high_roi_campaigns.loc[
                    high_roi_campaigns['購買 ROAS（廣告投資報酬率）'].idxmax()
                ]

                st.success(f"""
                **🚀 擴大投資建議**

                最佳表現活動：**{top_performer['行銷活動名稱']}**
                - ROAS: {top_performer['購買 ROAS（廣告投資報酬率）']:.2f}
                - ROI: {((top_performer['購買 ROAS（廣告投資報酬率）'] - 1) * 100):.1f}%
                - 花費: ${top_performer['花費金額 (TWD)']:,.0f}

                **建議動作：**
                - 增加預算 20-50%
                - 複製成功元素到其他活動
                - 擴展相似受眾
                """)
            else:
                st.info("暫無高 ROI 活動可供擴大投資")

        with col_rec2:
            # 需要優化的活動
            poor_roi_campaigns = filtered_df[filtered_df['購買 ROAS（廣告投資報酬率）'] < 1.0]
            if not poor_roi_campaigns.empty:
                worst_performer = poor_roi_campaigns.loc[
                    poor_roi_campaigns['購買 ROAS（廣告投資報酬率）'].idxmin()
                ]

                st.warning(f"""
                **⚠️ 急需優化活動**

                最需優化：**{worst_performer['行銷活動名稱']}**
                - ROAS: {worst_performer['購買 ROAS（廣告投資報酬率）']:.2f}
                - ROI: {((worst_performer['購買 ROAS（廣告投資報酬率）'] - 1) * 100):.1f}%
                - 花費: ${worst_performer['花費金額 (TWD)']:,.0f}

                **建議動作：**
                - 暫停或大幅調整
                - 重新設定目標受眾
                - 更換創意素材
                """)
            else:
                st.success("所有活動都達到盈虧平衡！")

        with col_rec3:
            # 整體策略建議
            overall_roi = (avg_roas - 1) * 100 if not np.isnan(avg_roas) else 0

            if overall_roi >= 200:
                recommendation = "🎉 表現優異，考慮擴大整體預算"
                color = "success"
            elif overall_roi >= 100:
                recommendation = "📈 表現良好，可優化低效活動"
                color = "info"
            elif overall_roi >= 0:
                recommendation = "⚠️ 需要整體優化策略"
                color = "warning"
            else:
                recommendation = "🚨 需要立即調整策略"
                color = "error"

            if color == "success":
                st.success(f"""
                **📊 整體 ROI 評估**

                平均 ROI: **{overall_roi:.1f}%**

                {recommendation}

                **策略重點：**
                - 識別成功模式
                - 規模化優質活動
                - 持續監控表現
                """)
            elif color == "info":
                st.info(f"""
                **📊 整體 ROI 評估**

                平均 ROI: **{overall_roi:.1f}%**

                {recommendation}

                **策略重點：**
                - 優化低效活動
                - 重新分配預算
                - A/B 測試新策略
                """)
            elif color == "warning":
                st.warning(f"""
                **📊 整體 ROI 評估**

                平均 ROI: **{overall_roi:.1f}%**

                {recommendation}

                **策略重點：**
                - 檢視目標設定
                - 優化受眾精準度
                - 改善轉換流程
                """)
            else:
                st.error(f"""
                **📊 整體 ROI 評估**

                平均 ROI: **{overall_roi:.1f}%**

                {recommendation}

                **緊急行動：**
                - 暫停虧損活動
                - 重新評估策略
                - 尋求專業建議
                """)

    else:
        st.info("所選時間範圍內暫無數據")

if __name__ == "__main__":
    show_roi_analysis()