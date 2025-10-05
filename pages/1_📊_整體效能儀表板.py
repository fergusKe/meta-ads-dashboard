import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys
from pathlib import Path

# 添加父目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_loader import load_meta_ads_data, calculate_summary_metrics
from utils.ad_display import (
    display_top_bottom_ads,
    format_ad_display_name
)

def show_performance_dashboard():
    """顯示整體效能儀表板 - 升級版"""
    st.markdown("# 📊 整體效能儀表板")
    st.markdown("深入分析廣告投放效能，包含完整轉換漏斗與月度趨勢")

    # 載入數據
    df = load_meta_ads_data()
    if df is None or df.empty:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    # ========== 第一部分：核心 KPI 卡片 ==========
    st.markdown("## 📈 核心成效指標")

    metrics = calculate_summary_metrics(df)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="總花費",
            value=f"${metrics['total_spend']:,.0f}",
            help="廣告總投資金額"
        )

    with col2:
        st.metric(
            label="總觸及",
            value=f"{metrics['total_reach']:,.0f}",
            help="不重複觸及人數"
        )

    with col3:
        st.metric(
            label="總購買",
            value=f"{metrics['total_purchases']:,.0f}",
            help="完成購買次數"
        )

    with col4:
        st.metric(
            label="平均 ROAS",
            value=f"{metrics['avg_roas']:.2f}x",
            help="廣告投資報酬率"
        )

    with col5:
        st.metric(
            label="平均 CPA",
            value=f"${metrics['avg_cpa']:,.0f}",
            help="每次購買成本"
        )

    # 第二排 KPI
    col6, col7, col8, col9, col10 = st.columns(5)

    with col6:
        st.metric(
            label="平均頻率",
            value=f"{metrics['avg_frequency']:.2f}",
            help="每人平均看到廣告次數"
        )

    with col7:
        st.metric(
            label="平均 CTR",
            value=f"{metrics['avg_ctr']:.2f}%",
            help="點擊率"
        )

    with col8:
        st.metric(
            label="加購次數",
            value=f"{metrics['total_add_to_cart']:,.0f}",
            help="加入購物車總次數"
        )

    with col9:
        st.metric(
            label="結帳次數",
            value=f"{metrics['total_checkout']:,.0f}",
            help="開始結帳總次數"
        )

    with col10:
        st.metric(
            label="整體轉換率",
            value=f"{metrics['overall_conversion_rate']:.2f}%",
            help="從觸及到購買的轉換率"
        )

    st.markdown("---")

    # ========== 第二部分：完整轉換漏斗 ==========
    st.markdown("## 🎯 完整轉換漏斗分析")

    funnel_col1, funnel_col2 = st.columns([3, 2])

    with funnel_col1:
        # 創建漏斗圖
        funnel_data = {
            '階段': [
                '1. 觸及',
                '2. 曝光',
                '3. 點擊',
                '4. 頁面瀏覽',
                '5. 內容瀏覽',
                '6. 加入購物車',
                '7. 開始結帳',
                '8. 完成購買'
            ],
            '數量': [
                metrics['total_reach'],
                metrics['total_impressions'],
                metrics['total_clicks'],
                metrics['total_page_views'],
                metrics['total_content_views'],
                metrics['total_add_to_cart'],
                metrics['total_checkout'],
                metrics['total_purchases']
            ]
        }

        # 計算轉換率
        funnel_df = pd.DataFrame(funnel_data)
        funnel_df['轉換率'] = funnel_df['數量'].pct_change() * -100
        funnel_df.loc[0, '轉換率'] = 100  # 第一階段為 100%

        # 計算相對於首階段的比例
        first_stage = funnel_df.loc[0, '數量']
        funnel_df['留存率'] = (funnel_df['數量'] / first_stage * 100)

        fig_funnel = go.Figure(go.Funnel(
            y=funnel_df['階段'],
            x=funnel_df['數量'],
            textposition="inside",
            textinfo="value+percent initial",
            marker=dict(
                color=['#1f77b4', '#2ca02c', '#ff7f0e', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f'],
                line=dict(width=2, color='white')
            ),
            connector=dict(line=dict(color='gray', width=1))
        ))

        fig_funnel.update_layout(
            title="完整轉換漏斗（7月-10月）",
            height=500,
            showlegend=False
        )

        st.plotly_chart(fig_funnel, use_container_width=True)

    with funnel_col2:
        st.markdown("### 📊 各階段轉換率")

        # 顯示各階段轉換率
        if metrics['total_impressions'] > 0:
            click_rate = metrics['total_clicks'] / metrics['total_impressions'] * 100
            st.metric("曝光→點擊", f"{click_rate:.2f}%")

        if metrics['total_clicks'] > 0:
            page_view_rate = metrics['total_page_views'] / metrics['total_clicks'] * 100
            st.metric("點擊→頁面瀏覽", f"{page_view_rate:.2f}%")

        if metrics['total_page_views'] > 0:
            content_view_rate = metrics['total_content_views'] / metrics['total_page_views'] * 100
            st.metric("頁面→內容瀏覽", f"{content_view_rate:.2f}%")

        if metrics['total_content_views'] > 0:
            add_to_cart_rate = metrics['total_add_to_cart'] / metrics['total_content_views'] * 100
            st.metric("內容→加購", f"{add_to_cart_rate:.2f}%")

        if metrics['total_add_to_cart'] > 0:
            checkout_rate = metrics['total_checkout'] / metrics['total_add_to_cart'] * 100
            st.metric("加購→結帳", f"{checkout_rate:.2f}%")

        if metrics['total_checkout'] > 0:
            purchase_rate = metrics['total_purchases'] / metrics['total_checkout'] * 100
            st.metric("結帳→購買", f"{purchase_rate:.2f}%")

        st.markdown("---")
        st.markdown("### 🎯 流失分析")

        # 計算最大流失點
        funnel_df['流失數'] = funnel_df['數量'].diff() * -1
        funnel_df.loc[0, '流失數'] = 0

        max_loss_idx = funnel_df['流失數'].idxmax()
        if max_loss_idx > 0:
            max_loss_stage = funnel_df.loc[max_loss_idx, '階段']
            max_loss_value = funnel_df.loc[max_loss_idx, '流失數']

            st.warning(f"""
            **最大流失點：{max_loss_stage}**

            流失人數：{max_loss_value:,.0f}

            建議優化此階段！
            """)

    st.markdown("---")

    # ========== 第三部分：月度趨勢分析 ==========
    st.markdown("## 📅 月度趨勢分析")

    # 按月份聚合數據
    if '年月' in df.columns:
        monthly_df = df.groupby('年月').agg({
            '花費金額 (TWD)': 'sum',
            '觸及人數': 'sum',
            '曝光次數': 'sum',
            '連結點擊次數': 'sum',
            '購買次數': 'sum',
            '加到購物車次數': 'sum',
            '購買 ROAS（廣告投資報酬率）': 'mean',
            '每次購買的成本': 'mean'
        }).reset_index()

        # 計算月度轉換率
        monthly_df['轉換率'] = (monthly_df['購買次數'] / monthly_df['觸及人數'] * 100)

        trend_col1, trend_col2 = st.columns(2)

        with trend_col1:
            # 花費與購買趨勢
            fig_spend = go.Figure()

            fig_spend.add_trace(go.Bar(
                x=monthly_df['年月'],
                y=monthly_df['花費金額 (TWD)'],
                name='花費',
                marker_color='#1f77b4',
                yaxis='y',
                text=monthly_df['花費金額 (TWD)'].apply(lambda x: f'${x:,.0f}'),
                textposition='outside'
            ))

            fig_spend.add_trace(go.Scatter(
                x=monthly_df['年月'],
                y=monthly_df['購買次數'],
                name='購買次數',
                mode='lines+markers',
                marker=dict(size=10, color='#ff7f0e'),
                line=dict(width=3, color='#ff7f0e'),
                yaxis='y2'
            ))

            fig_spend.update_layout(
                title="月度花費 vs 購買次數",
                xaxis_title="月份",
                yaxis=dict(title="花費 (TWD)", side='left'),
                yaxis2=dict(title="購買次數", side='right', overlaying='y'),
                hovermode='x unified',
                height=400
            )

            st.plotly_chart(fig_spend, use_container_width=True)

        with trend_col2:
            # ROAS 與轉換率趨勢
            fig_roas = go.Figure()

            fig_roas.add_trace(go.Scatter(
                x=monthly_df['年月'],
                y=monthly_df['購買 ROAS（廣告投資報酬率）'],
                name='ROAS',
                mode='lines+markers',
                marker=dict(size=10, color='#2ca02c'),
                line=dict(width=3, color='#2ca02c'),
                yaxis='y'
            ))

            fig_roas.add_trace(go.Scatter(
                x=monthly_df['年月'],
                y=monthly_df['轉換率'],
                name='轉換率',
                mode='lines+markers',
                marker=dict(size=10, color='#d62728'),
                line=dict(width=3, color='#d62728'),
                yaxis='y2'
            ))

            fig_roas.update_layout(
                title="月度 ROAS vs 轉換率",
                xaxis_title="月份",
                yaxis=dict(title="ROAS", side='left'),
                yaxis2=dict(title="轉換率 (%)", side='right', overlaying='y'),
                hovermode='x unified',
                height=400
            )

            st.plotly_chart(fig_roas, use_container_width=True)

        # 月度成長率
        st.markdown("### 📈 月度成長率")

        growth_col1, growth_col2, growth_col3, growth_col4 = st.columns(4)

        if len(monthly_df) >= 2:
            # 計算最近一個月 vs 上個月的成長率
            latest_month = monthly_df.iloc[-1]
            prev_month = monthly_df.iloc[-2]

            spend_growth = ((latest_month['花費金額 (TWD)'] - prev_month['花費金額 (TWD)']) / prev_month['花費金額 (TWD)'] * 100) if prev_month['花費金額 (TWD)'] > 0 else 0
            purchase_growth = ((latest_month['購買次數'] - prev_month['購買次數']) / prev_month['購買次數'] * 100) if prev_month['購買次數'] > 0 else 0
            roas_growth = ((latest_month['購買 ROAS（廣告投資報酬率）'] - prev_month['購買 ROAS（廣告投資報酬率）']) / prev_month['購買 ROAS（廣告投資報酬率）'] * 100) if prev_month['購買 ROAS（廣告投資報酬率）'] > 0 else 0
            conversion_growth = ((latest_month['轉換率'] - prev_month['轉換率']) / prev_month['轉換率'] * 100) if prev_month['轉換率'] > 0 else 0

            with growth_col1:
                st.metric(
                    "花費成長",
                    f"{spend_growth:+.1f}%",
                    delta=f"${latest_month['花費金額 (TWD)'] - prev_month['花費金額 (TWD)']:,.0f}"
                )

            with growth_col2:
                st.metric(
                    "購買成長",
                    f"{purchase_growth:+.1f}%",
                    delta=f"{latest_month['購買次數'] - prev_month['購買次數']:+.0f} 次"
                )

            with growth_col3:
                st.metric(
                    "ROAS 變化",
                    f"{roas_growth:+.1f}%",
                    delta=f"{latest_month['購買 ROAS（廣告投資報酬率）'] - prev_month['購買 ROAS（廣告投資報酬率）']:+.2f}"
                )

            with growth_col4:
                st.metric(
                    "轉換率變化",
                    f"{conversion_growth:+.1f}%",
                    delta=f"{latest_month['轉換率'] - prev_month['轉換率']:+.2f}%"
                )

    st.markdown("---")

    # ========== 第四部分：月度 × 指標熱力圖 ==========
    st.markdown("## 🔥 月度成效熱力圖")

    if '年月' in df.columns:
        # 創建熱力圖數據
        heatmap_metrics = ['花費金額 (TWD)', '購買次數', '購買 ROAS（廣告投資報酬率）', '加到購物車次數', '整體轉換率']
        heatmap_df = monthly_df[['年月'] + [m for m in heatmap_metrics if m in monthly_df.columns]].set_index('年月')

        # 標準化數據（0-100）
        heatmap_normalized = (heatmap_df - heatmap_df.min()) / (heatmap_df.max() - heatmap_df.min()) * 100

        fig_heatmap = go.Figure(data=go.Heatmap(
            z=heatmap_normalized.values.T,
            x=heatmap_normalized.index,
            y=heatmap_normalized.columns,
            colorscale='RdYlGn',
            text=heatmap_df.values.T,
            texttemplate='%{text:.0f}',
            textfont={"size": 12},
            colorbar=dict(title="相對表現")
        ))

        fig_heatmap.update_layout(
            title="月度指標表現熱力圖（顏色代表相對表現）",
            xaxis_title="月份",
            yaxis_title="指標",
            height=400
        )

        st.plotly_chart(fig_heatmap, use_container_width=True)

    st.markdown("---")

    # ========== 第五部分：表現最佳與最差廣告 ==========
    st.markdown("## 🎯 表現最佳與最差廣告")

    st.markdown("""
    快速識別表現突出的廣告（值得擴大預算）和表現不佳的廣告（需要優化或暫停）。
    """)

    # 添加廣告階層顯示
    df['廣告階層'] = df.apply(format_ad_display_name, axis=1)

    # 按 ROAS 顯示 Top/Bottom 廣告
    st.markdown("### 📊 ROAS 表現對比")
    display_top_bottom_ads(
        df,
        metric='購買 ROAS（廣告投資報酬率）',
        top_n=10
    )

    # 按花費金額顯示 Top 廣告（花費最多的廣告）
    st.markdown("### 💰 花費最多的廣告")
    st.markdown("這些廣告消耗了最多預算，需要密切監控其 ROAS 是否達標。")

    top_spend_ads = df.nlargest(10, '花費金額 (TWD)')

    st.dataframe(
        top_spend_ads[[
            '廣告階層',
            '花費金額 (TWD)',
            '購買 ROAS（廣告投資報酬率）',
            '購買次數',
            'CTR（全部）',
            '每次購買的成本'
        ]],
        use_container_width=True,
        column_config={
            "廣告階層": "廣告",
            "花費金額 (TWD)": st.column_config.NumberColumn("花費", format="$%d"),
            "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
            "購買次數": st.column_config.NumberColumn("購買次數", format="%d"),
            "CTR（全部）": st.column_config.NumberColumn("CTR (%)", format="%.2f"),
            "每次購買的成本": st.column_config.NumberColumn("CPA", format="$%.0f")
        },
        hide_index=True
    )

    # 關鍵洞察
    high_spend_low_roas = top_spend_ads[top_spend_ads['購買 ROAS（廣告投資報酬率）'] < 2.0]

    if not high_spend_low_roas.empty:
        st.error(f"""
**⚠️ 警告：發現 {len(high_spend_low_roas)} 個高花費但低 ROAS 的廣告**

這些廣告消耗大量預算但回報不佳，建議：
1. 立即降低預算或暫停
2. 分析失敗原因（受眾、素材、Landing Page）
3. 將預算轉移到高 ROAS 廣告

**潛在節省**：若暫停這些廣告，可節省約 ${high_spend_low_roas['花費金額 (TWD)'].sum():,.0f}
        """)
    else:
        st.success("✅ 所有高花費廣告的 ROAS 都在合理範圍內")

    st.markdown("---")

    # ========== 第六部分：數據摘要 ==========
    st.markdown("## 📋 數據摘要")

    summary_col1, summary_col2, summary_col3 = st.columns(3)

    with summary_col1:
        st.info(f"""
        **📊 基本統計**
        - 資料期間：7月 - 10月
        - 總記錄數：{len(df):,} 筆
        - 活動數量：{df['行銷活動名稱'].nunique()} 個
        - 廣告組數：{df['廣告組合名稱'].nunique()} 個
        - 單一廣告數：{df['廣告名稱'].nunique()} 個
        """)

    with summary_col2:
        # 計算 ROI
        total_revenue = df['購買轉換值'].sum() if '購買轉換值' in df.columns else 0
        total_spend = metrics['total_spend']
        roi = ((total_revenue - total_spend) / total_spend * 100) if total_spend > 0 else 0

        st.success(f"""
        **💰 投放成效**
        - 總花費：${total_spend:,.0f}
        - 總營收：${total_revenue:,.0f}
        - ROI：{roi:.1f}%
        - 平均 ROAS：{metrics['avg_roas']:.2f}x
        - {'✅ 獲利' if roi > 0 else '❌ 虧損'}
        """)

    with summary_col3:
        # 品質評估
        if '綜合品質分數' in df.columns:
            high_quality = len(df[df['綜合品質分數'] >= 2.5])
            medium_quality = len(df[(df['綜合品質分數'] >= 2.0) & (df['綜合品質分數'] < 2.5)])
            low_quality = len(df[df['綜合品質分數'] < 2.0])

            st.warning(f"""
            **⚡ 廣告品質**
            - 高品質（≥2.5）：{high_quality} 筆
            - 中品質（2.0-2.5）：{medium_quality} 筆
            - 低品質（<2.0）：{low_quality} 筆
            - 優化建議：{'✅ 表現良好' if high_quality > len(df) * 0.5 else '⚠️ 需提升品質'}
            """)
        else:
            st.warning("品質分數資料不完整")

if __name__ == "__main__":
    show_performance_dashboard()
