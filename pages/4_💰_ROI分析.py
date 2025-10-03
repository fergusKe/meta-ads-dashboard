import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import sys
from pathlib import Path

# 添加父目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_loader import load_meta_ads_data, calculate_summary_metrics

def show_roi_analysis():
    """顯示 ROI 分析頁面 - 升級版"""
    st.markdown("# 💰 ROI 分析")
    st.markdown("完整轉換路徑成本分析，優化投資報酬率")

    # 載入數據
    df = load_meta_ads_data()
    if df is None or df.empty:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    metrics = calculate_summary_metrics(df)

    # ========== 第一部分：ROI 總覽 ==========
    st.markdown("## 📊 ROI 總覽")

    roi_col1, roi_col2, roi_col3, roi_col4 = st.columns(4)

    total_revenue = df['購買轉換值'].sum() if '購買轉換值' in df.columns else 0
    total_spend = metrics['total_spend']
    total_roi = ((total_revenue - total_spend) / total_spend * 100) if total_spend > 0 else 0
    profit = total_revenue - total_spend

    with roi_col1:
        st.metric(
            "總投資",
            f"${total_spend:,.0f}",
            help="廣告總花費"
        )

    with roi_col2:
        st.metric(
            "總營收",
            f"${total_revenue:,.0f}",
            help="購買轉換值總和"
        )

    with roi_col3:
        st.metric(
            "ROI",
            f"{total_roi:+.1f}%",
            delta=f"{'獲利' if total_roi > 0 else '虧損'}",
            help="投資報酬率"
        )

    with roi_col4:
        st.metric(
            "淨利潤",
            f"${profit:+,.0f}",
            delta=f"{'賺' if profit > 0 else '賠'} ${abs(profit):,.0f}",
            help="營收 - 花費"
        )

    st.markdown("---")

    # ========== 第二部分：完整轉換路徑成本分析 ==========
    st.markdown("## 🎯 完整轉換路徑成本分析")

    # 計算各階段成本
    cost_data = {
        '階段': [
            '1. 曝光',
            '2. 點擊',
            '3. 頁面瀏覽',
            '4. 內容瀏覽',
            '5. 加入購物車',
            '6. 開始結帳',
            '7. 完成購買'
        ],
        '數量': [
            metrics['total_impressions'],
            metrics['total_clicks'],
            metrics['total_page_views'],
            metrics['total_content_views'],
            metrics['total_add_to_cart'],
            metrics['total_checkout'],
            metrics['total_purchases']
        ],
        '階段成本': []
    }

    # 計算每階段的平均成本
    cost_data['階段成本'] = [
        (total_spend / metrics['total_impressions'] * 1000) if metrics['total_impressions'] > 0 else 0,  # CPM
        (total_spend / metrics['total_clicks']) if metrics['total_clicks'] > 0 else 0,  # CPC
        (total_spend / metrics['total_page_views']) if metrics['total_page_views'] > 0 else 0,  # 每次頁面瀏覽
        (total_spend / metrics['total_content_views']) if metrics['total_content_views'] > 0 else 0,  # 每次內容瀏覽
        (total_spend / metrics['total_add_to_cart']) if metrics['total_add_to_cart'] > 0 else 0,  # 每次加購
        (total_spend / metrics['total_checkout']) if metrics['total_checkout'] > 0 else 0,  # 每次結帳
        (total_spend / metrics['total_purchases']) if metrics['total_purchases'] > 0 else 0  # CPA
    ]

    # 計算累積成本效率（每階段轉換帶來的價值）
    if metrics['total_purchases'] > 0:
        revenue_per_purchase = total_revenue / metrics['total_purchases']
        cost_data['轉換值'] = [
            revenue_per_purchase * (metrics['total_purchases'] / metrics['total_impressions']) if metrics['total_impressions'] > 0 else 0,
            revenue_per_purchase * (metrics['total_purchases'] / metrics['total_clicks']) if metrics['total_clicks'] > 0 else 0,
            revenue_per_purchase * (metrics['total_purchases'] / metrics['total_page_views']) if metrics['total_page_views'] > 0 else 0,
            revenue_per_purchase * (metrics['total_purchases'] / metrics['total_content_views']) if metrics['total_content_views'] > 0 else 0,
            revenue_per_purchase * (metrics['total_purchases'] / metrics['total_add_to_cart']) if metrics['total_add_to_cart'] > 0 else 0,
            revenue_per_purchase * (metrics['total_purchases'] / metrics['total_checkout']) if metrics['total_checkout'] > 0 else 0,
            revenue_per_purchase
        ]
    else:
        cost_data['轉換值'] = [0] * 7

    cost_df = pd.DataFrame(cost_data)

    cost_col1, cost_col2 = st.columns([3, 2])

    with cost_col1:
        # 成本階梯漏斗圖
        fig_cost_funnel = go.Figure()

        fig_cost_funnel.add_trace(go.Funnel(
            y=cost_df['階段'],
            x=cost_df['階段成本'],
            textposition="inside",
            textinfo="text",
            text=[f"${c:.2f}" for c in cost_df['階段成本']],
            marker=dict(color=['#e74c3c', '#e67e22', '#f39c12', '#f1c40f', '#2ecc71', '#27ae60', '#16a085'])
        ))

        fig_cost_funnel.update_layout(
            title="轉換路徑各階段成本",
            height=500
        )

        st.plotly_chart(fig_cost_funnel, use_container_width=True)

    with cost_col2:
        st.markdown("### 📊 階段成本明細")

        # 顯示成本指標
        st.metric("CPM（千次曝光）", f"${cost_df.loc[0, '階段成本']:.2f}")
        st.metric("CPC（單次點擊）", f"${cost_df.loc[1, '階段成本']:.2f}")
        st.metric("每次頁面瀏覽", f"${cost_df.loc[2, '階段成本']:.2f}")
        st.metric("每次內容瀏覽", f"${cost_df.loc[3, '階段成本']:.2f}")
        st.metric("每次加購", f"${cost_df.loc[4, '階段成本']:.2f}")
        st.metric("每次結帳", f"${cost_df.loc[5, '階段成本']:.2f}")
        st.metric("CPA（每次購買）", f"${cost_df.loc[6, '階段成本']:.2f}")

    # 成本 vs 轉換值對比
    st.markdown("### 💡 成本效益分析")

    fig_cost_value = go.Figure()

    fig_cost_value.add_trace(go.Bar(
        name='階段成本',
        x=cost_df['階段'],
        y=cost_df['階段成本'],
        marker_color='#e74c3c',
        yaxis='y'
    ))

    fig_cost_value.add_trace(go.Scatter(
        name='預期轉換值',
        x=cost_df['階段'],
        y=cost_df['轉換值'],
        mode='lines+markers',
        marker=dict(size=10, color='#2ecc71'),
        line=dict(width=3),
        yaxis='y2'
    ))

    fig_cost_value.update_layout(
        title="各階段成本 vs 預期轉換值",
        xaxis=dict(title="轉換階段", tickangle=-45),
        yaxis=dict(title="階段成本 (TWD)", side='left'),
        yaxis2=dict(title="預期轉換值 (TWD)", side='right', overlaying='y'),
        hovermode='x unified',
        height=450
    )

    st.plotly_chart(fig_cost_value, use_container_width=True)

    # 詳細表格
    st.dataframe(
        cost_df.round(2),
        use_container_width=True,
        column_config={
            "階段": "轉換階段",
            "數量": st.column_config.NumberColumn("階段數量", format="%d"),
            "階段成本": st.column_config.NumberColumn("階段成本 (TWD)", format="%.2f"),
            "轉換值": st.column_config.NumberColumn("預期轉換值 (TWD)", format="%.2f")
        },
        hide_index=True
    )

    st.markdown("---")

    # ========== 第三部分：ROAS 深度分析 ==========
    st.markdown("## 📈 ROAS 深度分析")

    roas_col1, roas_col2 = st.columns(2)

    with roas_col1:
        # ROAS 分布直方圖
        roas_data = df[df['購買 ROAS（廣告投資報酬率）'] > 0]['購買 ROAS（廣告投資報酬率）']

        fig_roas_dist = px.histogram(
            roas_data,
            x=roas_data,
            nbins=30,
            title="ROAS 分布",
            labels={'x': 'ROAS', 'count': '次數'},
            color_discrete_sequence=['#3498db']
        )

        # 添加平均線和中位數線
        mean_roas = roas_data.mean()
        median_roas = roas_data.median()

        fig_roas_dist.add_vline(x=mean_roas, line_dash="dash", line_color="red", annotation_text=f"平均 {mean_roas:.2f}")
        fig_roas_dist.add_vline(x=median_roas, line_dash="dash", line_color="green", annotation_text=f"中位數 {median_roas:.2f}")
        fig_roas_dist.add_vline(x=1.0, line_dash="dot", line_color="orange", annotation_text="損益平衡點")

        fig_roas_dist.update_layout(height=400)
        st.plotly_chart(fig_roas_dist, use_container_width=True)

    with roas_col2:
        # ROAS 分類統計
        roas_categories = pd.cut(
            df['購買 ROAS（廣告投資報酬率）'],
            bins=[-float('inf'), 0, 1, 3, 5, float('inf')],
            labels=['虧損（<0）', '低效（0-1）', '及格（1-3）', '優秀（3-5）', '卓越（>5）']
        )

        roas_category_counts = roas_categories.value_counts().sort_index()

        fig_roas_pie = go.Figure(data=[go.Pie(
            labels=roas_category_counts.index,
            values=roas_category_counts.values,
            hole=0.4,
            marker=dict(colors=['#e74c3c', '#e67e22', '#f39c12', '#2ecc71', '#16a085'])
        )])

        fig_roas_pie.update_layout(
            title="ROAS 分類占比",
            height=400
        )

        st.plotly_chart(fig_roas_pie, use_container_width=True)

    # ROAS vs 花費散點圖
    st.markdown("### 🎯 ROAS vs 花費散點圖")

    campaign_roas_spend = df.groupby('行銷活動名稱').agg({
        '花費金額 (TWD)': 'sum',
        '購買 ROAS（廣告投資報酬率）': 'mean',
        '購買次數': 'sum'
    }).reset_index()

    fig_roas_scatter = px.scatter(
        campaign_roas_spend,
        x='花費金額 (TWD)',
        y='購買 ROAS（廣告投資報酬率）',
        size='購買次數',
        hover_data=['行銷活動名稱'],
        title="花費 vs ROAS（識別最佳投資點）",
        labels={'花費金額 (TWD)': '花費 (TWD)', '購買 ROAS（廣告投資報酬率）': 'ROAS'},
        color='購買 ROAS（廣告投資報酬率）',
        color_continuous_scale='RdYlGn'
    )

    # 添加分隔線
    median_spend = campaign_roas_spend['花費金額 (TWD)'].median()
    median_roas_campaign = campaign_roas_spend['購買 ROAS（廣告投資報酬率）'].median()

    fig_roas_scatter.add_hline(y=median_roas_campaign, line_dash="dash", line_color="gray")
    fig_roas_scatter.add_vline(x=median_spend, line_dash="dash", line_color="gray")

    # 標註最佳投資區（高ROAS + 高花費）
    fig_roas_scatter.add_annotation(
        x=campaign_roas_spend['花費金額 (TWD)'].max() * 0.8,
        y=campaign_roas_spend['購買 ROAS（廣告投資報酬率）'].max() * 0.9,
        text="🌟 最佳投資區",
        showarrow=False,
        font=dict(size=14, color="green")
    )

    fig_roas_scatter.update_layout(height=500)
    st.plotly_chart(fig_roas_scatter, use_container_width=True)

    # 高 ROAS 活動特徵
    st.markdown("### ⭐ 高 ROAS 活動特徵")

    high_roas_campaigns = campaign_roas_spend[
        campaign_roas_spend['購買 ROAS（廣告投資報酬率）'] > campaign_roas_spend['購買 ROAS（廣告投資報酬率）'].quantile(0.75)
    ].sort_values('購買 ROAS（廣告投資報酬率）', ascending=False)

    if not high_roas_campaigns.empty:
        st.success(f"✅ 發現 {len(high_roas_campaigns)} 個高 ROAS 活動（前 25%）")

        st.dataframe(
            high_roas_campaigns,
            use_container_width=True,
            column_config={
                "行銷活動名稱": "活動名稱",
                "花費金額 (TWD)": st.column_config.NumberColumn("花費", format="%d"),
                "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
                "購買次數": st.column_config.NumberColumn("購買", format="%d")
            },
            hide_index=True
        )

        # 分析高 ROAS 活動的共同特徵
        high_roas_data = df[df['行銷活動名稱'].isin(high_roas_campaigns['行銷活動名稱'])]

        if '品質排名' in high_roas_data.columns:
            quality_dist = high_roas_data['品質排名'].value_counts()
            st.info(f"""
            **🔍 高 ROAS 活動的共同特徵：**
            - 品質排名：{quality_dist.idxmax()} 占多數
            - 平均 CTR：{high_roas_data['CTR（全部）'].mean():.2f}%
            - 平均轉換率：{(high_roas_data['購買次數'].sum() / high_roas_data['觸及人數'].sum() * 100):.2f}%
            """)

    st.markdown("---")

    # ========== 第四部分：成本效益優化建議 ==========
    st.markdown("## 💡 成本效益優化建議")

    # 識別高成本低轉換的環節
    st.markdown("### ⚠️ 高成本環節識別")

    # 計算理想成本結構（基於行業標準）
    ideal_costs = {
        'CPM': 100,
        'CPC': 10,
        '每次頁面瀏覽': 15,
        '每次加購': 50,
        '每次結帳': 100,
        'CPA': 300
    }

    actual_costs = {
        'CPM': cost_df.loc[0, '階段成本'],
        'CPC': cost_df.loc[1, '階段成本'],
        '每次頁面瀏覽': cost_df.loc[2, '階段成本'],
        '每次加購': cost_df.loc[4, '階段成本'],
        '每次結帳': cost_df.loc[5, '階段成本'],
        'CPA': cost_df.loc[6, '階段成本']
    }

    comparison_data = []
    for key in ideal_costs.keys():
        difference = actual_costs[key] - ideal_costs[key]
        percentage_diff = (difference / ideal_costs[key] * 100) if ideal_costs[key] > 0 else 0

        comparison_data.append({
            '指標': key,
            '理想成本': ideal_costs[key],
            '實際成本': actual_costs[key],
            '差異': difference,
            '差異%': percentage_diff,
            '狀態': '✅ 良好' if difference <= 0 else ('⚠️ 注意' if percentage_diff < 50 else '❌ 需優化')
        })

    comparison_df = pd.DataFrame(comparison_data)

    st.dataframe(
        comparison_df.round(2),
        use_container_width=True,
        column_config={
            "指標": "成本指標",
            "理想成本": st.column_config.NumberColumn("理想成本", format="%.2f"),
            "實際成本": st.column_config.NumberColumn("實際成本", format="%.2f"),
            "差異": st.column_config.NumberColumn("差異", format="%+.2f"),
            "差異%": st.column_config.NumberColumn("差異%", format="%+.1f%%"),
            "狀態": "狀態"
        },
        hide_index=True
    )

    # 具體優化方向
    st.markdown("### 🎯 具體優化方向")

    optimize_col1, optimize_col2 = st.columns(2)

    with optimize_col1:
        # 找出成本超標最嚴重的環節
        worst_stage = comparison_df.loc[comparison_df['差異%'].idxmax()]

        st.error(f"""
        **⚠️ 最需優化環節：{worst_stage['指標']}**

        - 實際成本：${worst_stage['實際成本']:.2f}
        - 理想成本：${worst_stage['理想成本']:.2f}
        - 超出：{worst_stage['差異%']:+.1f}%

        **優化建議**：
        """)

        if 'CPC' in worst_stage['指標']:
            st.markdown("""
            - 優化廣告素材（提升 CTR）
            - 精準定位受眾
            - 測試不同出價策略
            """)
        elif 'CPA' in worst_stage['指標']:
            st.markdown("""
            - 優化 Landing Page
            - 簡化購買流程
            - 提供促銷優惠
            - 重新定向未完成購買的用戶
            """)
        elif '加購' in worst_stage['指標']:
            st.markdown("""
            - 優化產品頁面
            - 調整價格策略
            - 增加產品評價
            - 提供免運或折扣
            """)

    with optimize_col2:
        # 預算重新分配建議
        st.success("""
        **💰 預算重新分配建議**

        根據 ROAS 分析：
        1. 增加高 ROAS 活動預算（+30%）
        2. 降低低 ROAS 活動預算（-50%）
        3. 暫停 ROAS < 1.0 的活動

        **預期效果**：
        - 整體 ROAS 提升 15-25%
        - CPA 降低 10-15%
        - ROI 增加 20-30%
        """)

    # ROI 瀑布圖
    st.markdown("### 📊 ROI 組成瀑布圖")

    # 計算各組成部分
    waterfall_data = {
        '項目': ['總營收', '廣告花費', '其他成本', '淨利潤'],
        '金額': [total_revenue, -total_spend, 0, profit],
        '類型': ['total', 'relative', 'relative', 'total']
    }

    fig_waterfall = go.Figure(go.Waterfall(
        name="ROI",
        orientation="v",
        measure=waterfall_data['類型'],
        x=waterfall_data['項目'],
        y=waterfall_data['金額'],
        text=[f"${abs(v):,.0f}" for v in waterfall_data['金額']],
        textposition="outside",
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#2ecc71"}},
        decreasing={"marker": {"color": "#e74c3c"}},
        totals={"marker": {"color": "#3498db"}}
    ))

    fig_waterfall.update_layout(
        title="ROI 瀑布圖",
        yaxis_title="金額 (TWD)",
        height=450
    )

    st.plotly_chart(fig_waterfall, use_container_width=True)

if __name__ == "__main__":
    show_roi_analysis()
