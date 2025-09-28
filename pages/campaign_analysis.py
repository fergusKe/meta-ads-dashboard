import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from utils.data_loader import load_meta_ads_data

def show_campaign_analysis():
    """顯示活動分析頁面"""
    st.markdown("# 🎯 活動分析")
    st.markdown("針對個別行銷活動進行深度分析，協助優化活動策略")

    # 載入數據
    df = load_meta_ads_data()
    if df is None:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    # 活動選擇與篩選
    st.markdown("## 🔍 活動篩選設定")

    col1, col2, col3 = st.columns(3)

    with col1:
        # 活動多選
        available_campaigns = sorted(df['行銷活動名稱'].unique().tolist())
        selected_campaigns = st.multiselect(
            "選擇活動 (可多選)",
            available_campaigns,
            default=available_campaigns[:5] if len(available_campaigns) >= 5 else available_campaigns,
            help="最多選擇10個活動進行分析"
        )

    with col2:
        # 投遞狀態篩選
        available_status = df['投遞狀態'].unique().tolist()
        selected_status = st.multiselect(
            "投遞狀態篩選",
            available_status,
            default=available_status
        )

    with col3:
        # 目標類型篩選
        available_objectives = df['目標'].unique().tolist()
        selected_objectives = st.multiselect(
            "目標類型篩選",
            available_objectives,
            default=available_objectives
        )

    # 篩選數據
    filtered_df = df[
        (df['行銷活動名稱'].isin(selected_campaigns)) &
        (df['投遞狀態'].isin(selected_status)) &
        (df['目標'].isin(selected_objectives))
    ]

    if filtered_df.empty:
        st.warning("⚠️ 當前篩選條件下沒有數據，請調整篩選條件。")
        return

    st.info(f"📊 當前篩選結果：{len(filtered_df)} 筆記錄，{filtered_df['行銷活動名稱'].nunique()} 個活動")

    st.markdown("---")

    # 活動效能排行榜
    st.markdown("## 🏆 活動效能排行榜")

    ranking_tabs = st.tabs(["🥇 ROAS 排行", "💰 花費排行", "🛒 轉換排行", "⚠️ 需優化排行"])

    with ranking_tabs[0]:
        st.markdown("### Top 10 ROAS 最佳活動")
        top_roas = create_campaign_ranking(filtered_df, '購買 ROAS（廣告投資報酬率）', 'ROAS', ascending=False)
        if not top_roas.empty:
            display_ranking_chart(top_roas, '購買 ROAS（廣告投資報酬率）', 'ROAS', 'RdYlGn')
        else:
            st.info("暫無 ROAS 數據")

    with ranking_tabs[1]:
        st.markdown("### Top 10 花費最高活動")
        top_spend = create_campaign_ranking(filtered_df, '花費金額 (TWD)', '花費金額', ascending=False)
        if not top_spend.empty:
            display_ranking_chart(top_spend, '花費金額 (TWD)', '花費金額 (TWD)', 'Blues')
        else:
            st.info("暫無花費數據")

    with ranking_tabs[2]:
        st.markdown("### Top 10 轉換次數最多活動")
        top_conversions = create_campaign_ranking(filtered_df, '購買次數', '轉換次數', ascending=False)
        if not top_conversions.empty:
            display_ranking_chart(top_conversions, '購買次數', '購買次數', 'Greens')
        else:
            st.info("暫無轉換數據")

    with ranking_tabs[3]:
        st.markdown("### Bottom 5 需要優化的活動")
        bottom_roas = create_campaign_ranking(filtered_df, '購買 ROAS（廣告投資報酬率）', 'ROAS', ascending=True, top_n=5)
        if not bottom_roas.empty:
            display_ranking_chart(bottom_roas, '購買 ROAS（廣告投資報酬率）', 'ROAS', 'Reds')

            with st.expander("💡 優化建議"):
                st.markdown("""
                **針對低 ROAS 活動的建議：**
                1. **暫停表現最差的活動** - ROAS < 1.0
                2. **調整受眾定位** - 縮小至高轉換群體
                3. **優化創意素材** - 參考高效活動的創意元素
                4. **降低出價** - 控制獲客成本
                5. **重新設定目標** - 改為較容易達成的轉換目標
                """)
        else:
            st.info("暫無需優化的活動")

    st.markdown("---")

    # 單一活動詳細分析
    st.markdown("## 🔍 單一活動詳細分析")

    selected_campaign = st.selectbox(
        "選擇要詳細分析的活動",
        selected_campaigns,
        help="選擇一個活動進行深度分析"
    )

    if selected_campaign:
        campaign_df = filtered_df[filtered_df['行銷活動名稱'] == selected_campaign]
        show_single_campaign_analysis(campaign_df, selected_campaign)

    st.markdown("---")

    # 活動對比功能
    st.markdown("## ⚖️ 活動對比分析")

    compare_campaigns = st.multiselect(
        "選擇要對比的活動 (2-4個)",
        selected_campaigns,
        default=selected_campaigns[:2] if len(selected_campaigns) >= 2 else [],
        help="選擇2-4個活動進行並排比較"
    )

    if len(compare_campaigns) >= 2:
        show_campaign_comparison(filtered_df, compare_campaigns)
    else:
        st.info("請選擇至少2個活動進行對比分析")

def create_campaign_ranking(df, metric_column, metric_name, ascending=False, top_n=10):
    """創建活動排行榜"""
    if df.empty or metric_column not in df.columns:
        return pd.DataFrame()

    ranking = df.groupby('行銷活動名稱').agg({
        metric_column: 'mean' if 'ROAS' in metric_column or 'CTR' in metric_column else 'sum',
        '花費金額 (TWD)': 'sum',
        '購買次數': 'sum',
        '觸及人數': 'sum'
    }).reset_index()

    ranking = ranking.sort_values(metric_column, ascending=ascending).head(top_n)
    return ranking

def display_ranking_chart(ranking_df, metric_column, metric_name, color_scale):
    """顯示排行榜圖表"""
    fig = px.bar(
        ranking_df,
        x=metric_column,
        y='行銷活動名稱',
        orientation='h',
        title=f"{metric_name} 排行榜",
        color=metric_column,
        color_continuous_scale=color_scale,
        text=metric_column
    )

    fig.update_traces(texttemplate='%{text:.2f}' if 'ROAS' in metric_name or 'CTR' in metric_name else '%{text:,.0f}',
                     textposition='outside')
    fig.update_layout(
        height=400,
        yaxis={'categoryorder': 'total ascending'},
        showlegend=False,
        xaxis_title=metric_name,
        yaxis_title=""
    )

    st.plotly_chart(fig, use_container_width=True)

    # 顯示數據表格
    st.dataframe(
        ranking_df.round(2),
        use_container_width=True,
        column_config={
            "行銷活動名稱": st.column_config.TextColumn("活動名稱", width="large"),
            metric_column: st.column_config.NumberColumn(metric_name, format="%.2f" if 'ROAS' in metric_name else "%d"),
            "花費金額 (TWD)": st.column_config.NumberColumn("花費金額", format="%d"),
            "購買次數": st.column_config.NumberColumn("購買次數", format="%d"),
            "觸及人數": st.column_config.NumberColumn("觸及人數", format="%d")
        }
    )

def show_single_campaign_analysis(campaign_df, campaign_name):
    """顯示單一活動詳細分析"""
    if campaign_df.empty:
        st.warning("該活動暫無數據")
        return

    st.markdown(f"### 📋 活動：{campaign_name}")

    # 活動基本資訊
    info_col1, info_col2 = st.columns(2)

    with info_col1:
        # 基本資訊
        total_spend = campaign_df['花費金額 (TWD)'].sum()
        total_purchases = campaign_df['購買次數'].sum()
        avg_roas = campaign_df['購買 ROAS（廣告投資報酬率）'].mean()
        total_reach = campaign_df['觸及人數'].sum()

        st.info(f"""
        **📊 基本資訊**
        - 投放狀態：{campaign_df['投遞狀態'].iloc[0]}
        - 目標類型：{campaign_df['目標'].iloc[0]}
        - 投放期間：{campaign_df['開始'].min().strftime('%Y-%m-%d') if '開始' in campaign_df.columns and not campaign_df['開始'].isna().all() else '未知'}
          至 {campaign_df['結束時間'].max().strftime('%Y-%m-%d') if '結束時間' in campaign_df.columns and not campaign_df['結束時間'].isna().all() else '未知'}
        - 廣告組數：{campaign_df['廣告組合名稱'].nunique()}
        """)

    with info_col2:
        # 核心 KPI
        conversion_rate = (total_purchases / total_reach * 100) if total_reach > 0 else 0
        avg_cpa = campaign_df['每次購買的成本'].mean()

        st.success(f"""
        **💰 核心 KPI**
        - 總花費：${total_spend:,.0f} TWD
        - 總購買：{total_purchases:.0f} 次
        - 平均 ROAS：{avg_roas:.2f}
        - 平均 CPA：${avg_cpa:.0f} TWD
        - 觸及人數：{total_reach:,.0f}
        - 轉換率：{conversion_rate:.3f}%
        """)

    # 廣告組合表現對比
    st.markdown("#### 📊 廣告組合表現對比")

    ad_group_performance = campaign_df.groupby('廣告組合名稱').agg({
        '購買 ROAS（廣告投資報酬率）': 'mean',
        '花費金額 (TWD)': 'sum',
        '購買次數': 'sum',
        'CTR（全部）': 'mean',
        '每次購買的成本': 'mean'
    }).reset_index()

    if not ad_group_performance.empty:
        # 廣告組 ROAS 對比圖
        fig_adgroup = px.bar(
            ad_group_performance,
            x='廣告組合名稱',
            y='購買 ROAS（廣告投資報酬率）',
            title="廣告組合 ROAS 表現",
            color='購買 ROAS（廣告投資報酬率）',
            color_continuous_scale='RdYlGn'
        )
        fig_adgroup.update_layout(height=400, xaxis_tickangle=-45)
        st.plotly_chart(fig_adgroup, use_container_width=True)

        # 廣告組數據表格
        st.dataframe(
            ad_group_performance.round(2),
            use_container_width=True,
            column_config={
                "廣告組合名稱": st.column_config.TextColumn("廣告組合", width="large"),
                "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
                "花費金額 (TWD)": st.column_config.NumberColumn("花費", format="%d"),
                "購買次數": st.column_config.NumberColumn("購買次數", format="%d"),
                "CTR（全部）": st.column_config.NumberColumn("CTR (%)", format="%.2f"),
                "每次購買的成本": st.column_config.NumberColumn("CPA", format="%.0f")
            }
        )

    # 日期效能趨勢
    if '開始' in campaign_df.columns and not campaign_df['開始'].isna().all():
        st.markdown("#### 📈 效能趨勢分析")

        # 只使用有效的日期和數據
        valid_campaign_data = campaign_df.dropna(subset=['開始'])
        valid_campaign_data = valid_campaign_data[
            (valid_campaign_data['花費金額 (TWD)'] > 0) |
            (valid_campaign_data['購買次數'] > 0) |
            (valid_campaign_data['購買 ROAS（廣告投資報酬率）'] > 0)
        ]

        if not valid_campaign_data.empty:
            daily_trend = valid_campaign_data.groupby(valid_campaign_data['開始'].dt.date).agg({
                '購買 ROAS（廣告投資報酬率）': 'mean',
                '花費金額 (TWD)': 'sum',
                '購買次數': 'sum'
            }).reset_index()

            # 過濾掉沒有實際數據的日期
            daily_trend = daily_trend[
                (daily_trend['花費金額 (TWD)'] > 0) |
                (daily_trend['購買次數'] > 0) |
                (daily_trend['購買 ROAS（廣告投資報酬率）'] > 0)
            ]

        if not daily_trend.empty and len(daily_trend) > 1:
            fig_trend = make_subplots(
                rows=2, cols=1,
                subplot_titles=('ROAS 趨勢', '花費 vs 轉換趨勢'),
                specs=[[{"secondary_y": False}], [{"secondary_y": True}]]
            )

            # ROAS 趨勢
            fig_trend.add_trace(
                go.Scatter(
                    x=daily_trend['開始'],
                    y=daily_trend['購買 ROAS（廣告投資報酬率）'],
                    name='ROAS',
                    line=dict(color='blue')
                ),
                row=1, col=1
            )

            # 花費趨勢
            fig_trend.add_trace(
                go.Bar(
                    x=daily_trend['開始'],
                    y=daily_trend['花費金額 (TWD)'],
                    name='花費',
                    yaxis='y3',
                    opacity=0.7
                ),
                row=2, col=1
            )

            # 轉換趨勢
            fig_trend.add_trace(
                go.Scatter(
                    x=daily_trend['開始'],
                    y=daily_trend['購買次數'],
                    name='購買次數',
                    yaxis='y4',
                    line=dict(color='green')
                ),
                row=2, col=1
            )

            # 設定 X 軸範圍為實際數據範圍
            if not daily_trend.empty:
                fig_trend.update_layout(
                    height=600,
                    title="活動效能時間趨勢",
                    xaxis=dict(range=[daily_trend['開始'].min(), daily_trend['開始'].max()]),
                    xaxis2=dict(range=[daily_trend['開始'].min(), daily_trend['開始'].max()])
                )

            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("此活動暫無足夠的趨勢數據")

def show_campaign_comparison(df, compare_campaigns):
    """顯示活動對比分析"""
    st.markdown("### ⚖️ 活動並排比較")

    # 準備對比數據
    comparison_data = []
    for campaign in compare_campaigns:
        campaign_df = df[df['行銷活動名稱'] == campaign]
        if not campaign_df.empty:
            comparison_data.append({
                '活動名稱': campaign,
                '總花費 (TWD)': campaign_df['花費金額 (TWD)'].sum(),
                '總購買次數': campaign_df['購買次數'].sum(),
                'ROAS': campaign_df['購買 ROAS（廣告投資報酬率）'].mean(),
                'CPA (TWD)': campaign_df['每次購買的成本'].mean(),
                'CTR (%)': campaign_df['CTR（全部）'].mean(),
                'CPM (TWD)': campaign_df['CPM（每千次廣告曝光成本）'].mean(),
                '觸及人數': campaign_df['觸及人數'].sum(),
                '轉換率 (%)': (campaign_df['購買次數'].sum() / campaign_df['觸及人數'].sum() * 100) if campaign_df['觸及人數'].sum() > 0 else 0
            })

    if not comparison_data:
        st.warning("選中的活動沒有可對比的數據")
        return

    comparison_df = pd.DataFrame(comparison_data)

    # 並排 KPI 比較
    st.markdown("#### 📊 核心指標對比")

    metrics_to_compare = ['ROAS', 'CPA (TWD)', 'CTR (%)', '轉換率 (%)']

    fig_comparison = make_subplots(
        rows=2, cols=2,
        subplot_titles=metrics_to_compare,
        specs=[[{"type": "bar"}, {"type": "bar"}],
               [{"type": "bar"}, {"type": "bar"}]]
    )

    colors = px.colors.qualitative.Set3[:len(compare_campaigns)]

    for i, metric in enumerate(metrics_to_compare):
        row = i // 2 + 1
        col = i % 2 + 1

        fig_comparison.add_trace(
            go.Bar(
                x=comparison_df['活動名稱'],
                y=comparison_df[metric],
                name=metric,
                marker_color=colors,
                showlegend=False
            ),
            row=row, col=col
        )

    fig_comparison.update_layout(height=600, title="活動關鍵指標對比")
    st.plotly_chart(fig_comparison, use_container_width=True)

    # 詳細對比表格
    st.markdown("#### 📋 詳細數據對比")
    st.dataframe(
        comparison_df.round(2),
        use_container_width=True,
        column_config={
            "活動名稱": st.column_config.TextColumn("活動名稱", width="large"),
            "總花費 (TWD)": st.column_config.NumberColumn("總花費", format="%d"),
            "總購買次數": st.column_config.NumberColumn("購買次數", format="%d"),
            "ROAS": st.column_config.NumberColumn("ROAS", format="%.2f"),
            "CPA (TWD)": st.column_config.NumberColumn("CPA", format="%.0f"),
            "CTR (%)": st.column_config.NumberColumn("CTR", format="%.2f"),
            "CPM (TWD)": st.column_config.NumberColumn("CPM", format="%.0f"),
            "觸及人數": st.column_config.NumberColumn("觸及人數", format="%d"),
            "轉換率 (%)": st.column_config.NumberColumn("轉換率", format="%.3f")
        }
    )

    # 效果差異分析
    st.markdown("#### 💡 效果差異分析")

    if len(comparison_df) >= 2:
        best_roas = comparison_df.loc[comparison_df['ROAS'].idxmax()]
        worst_roas = comparison_df.loc[comparison_df['ROAS'].idxmin()]

        roas_diff = best_roas['ROAS'] - worst_roas['ROAS']
        spend_diff = best_roas['總花費 (TWD)'] - worst_roas['總花費 (TWD)']

        col_diff1, col_diff2 = st.columns(2)

        with col_diff1:
            st.success(f"""
            **🏆 最佳表現活動：{best_roas['活動名稱']}**
            - ROAS：{best_roas['ROAS']:.2f}
            - 總花費：${best_roas['總花費 (TWD)']:,.0f}
            - 購買次數：{best_roas['總購買次數']:.0f}
            - 轉換率：{best_roas['轉換率 (%)']:.3f}%
            """)

        with col_diff2:
            st.warning(f"""
            **⚠️ 需改善活動：{worst_roas['活動名稱']}**
            - ROAS：{worst_roas['ROAS']:.2f}
            - 總花費：${worst_roas['總花費 (TWD)']:,.0f}
            - 購買次數：{worst_roas['總購買次數']:.0f}
            - 轉換率：{worst_roas['轉換率 (%)']:.3f}%
            """)

        st.info(f"""
        **🔍 差異分析結果**
        - ROAS 差距：{roas_diff:.2f} ({(roas_diff/worst_roas['ROAS']*100):+.1f}%)
        - 花費差距：${spend_diff:+,.0f} TWD
        - **建議**：將低效活動的預算轉移到高效活動，預期可提升整體 ROAS
        """)

if __name__ == "__main__":
    show_campaign_analysis()