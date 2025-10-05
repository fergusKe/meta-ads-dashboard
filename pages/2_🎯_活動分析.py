import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import sys
from pathlib import Path

# 添加父目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_loader import load_meta_ads_data
from utils.ad_display import (
    display_top_bottom_ads,
    format_ad_display_name
)

def show_campaign_analysis():
    """顯示活動分析頁面 - 升級版"""
    st.markdown("# 🎯 活動分析")
    st.markdown("深度分析行銷活動效能，整合廣告品質評分與三層級分析")

    # 載入數據
    df = load_meta_ads_data()
    if df is None or df.empty:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    # 確保預算欄位為數值型態
    budget_columns = ['廣告組合預算', '行銷活動預算', '日預算']
    for col in budget_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # ========== 第一部分：活動篩選 ==========
    st.markdown("## 🔍 活動篩選設定")

    col1, col2, col3 = st.columns(3)

    with col1:
        available_campaigns = sorted(df['行銷活動名稱'].unique().tolist())
        selected_campaigns = st.multiselect(
            "選擇活動（可多選）",
            available_campaigns,
            default=available_campaigns[:5] if len(available_campaigns) >= 5 else available_campaigns
        )

    with col2:
        available_status = df['投遞狀態'].unique().tolist()
        selected_status = st.multiselect(
            "投遞狀態",
            available_status,
            default=available_status
        )

    with col3:
        # 品質排名篩選
        if '品質排名' in df.columns:
            quality_options = ['全部', '平均以上', '平均', '平均以下']
            selected_quality = st.selectbox(
                "品質排名篩選",
                quality_options
            )
        else:
            selected_quality = '全部'

    # 篩選數據
    filtered_df = df[
        (df['行銷活動名稱'].isin(selected_campaigns)) &
        (df['投遞狀態'].isin(selected_status))
    ]

    # 品質篩選
    if selected_quality != '全部' and '品質排名' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['品質排名'] == selected_quality]

    if filtered_df.empty:
        st.warning("⚠️ 當前篩選條件下沒有數據")
        return

    st.info(f"📊 篩選結果：{len(filtered_df)} 筆記錄，{filtered_df['行銷活動名稱'].nunique()} 個活動")

    st.markdown("---")

    # ========== 第二部分：廣告品質評分分析 ==========
    st.markdown("## 🏆 廣告品質評分分析")

    st.info("""
    💡 **品質排名說明**：Meta 會評估廣告的品質、互動率和轉換率排名（平均以上/平均/平均以下）。
    若顯示「未知」表示該廣告尚未累積足夠數據或 Meta 未提供排名評分。
    """)

    if all(col in filtered_df.columns for col in ['品質排名', '互動率排名', '轉換率排名']):
        quality_col1, quality_col2, quality_col3 = st.columns(3)

        with quality_col1:
            # 品質排名分布
            quality_dist = filtered_df['品質排名'].value_counts()
            fig_quality = go.Figure(data=[go.Pie(
                labels=quality_dist.index,
                values=quality_dist.values,
                hole=0.4,
                marker=dict(colors=['#2ecc71', '#f39c12', '#e74c3c'])
            )])
            fig_quality.update_layout(
                title="品質排名分布",
                height=300,
                showlegend=True
            )
            st.plotly_chart(fig_quality, use_container_width=True)

        with quality_col2:
            # 互動率排名分布
            engagement_dist = filtered_df['互動率排名'].value_counts()
            fig_engagement = go.Figure(data=[go.Pie(
                labels=engagement_dist.index,
                values=engagement_dist.values,
                hole=0.4,
                marker=dict(colors=['#2ecc71', '#f39c12', '#e74c3c'])
            )])
            fig_engagement.update_layout(
                title="互動率排名分布",
                height=300,
                showlegend=True
            )
            st.plotly_chart(fig_engagement, use_container_width=True)

        with quality_col3:
            # 轉換率排名分布
            conversion_dist = filtered_df['轉換率排名'].value_counts()
            fig_conversion = go.Figure(data=[go.Pie(
                labels=conversion_dist.index,
                values=conversion_dist.values,
                hole=0.4,
                marker=dict(colors=['#2ecc71', '#f39c12', '#e74c3c'])
            )])
            fig_conversion.update_layout(
                title="轉換率排名分布",
                height=300,
                showlegend=True
            )
            st.plotly_chart(fig_conversion, use_container_width=True)

        # 品質排名 vs 成效關聯分析
        st.markdown("### 🔗 品質排名 vs 成效關聯")

        scatter_col1, scatter_col2 = st.columns(2)

        with scatter_col1:
            # 品質分數 vs ROAS
            if '綜合品質分數' in filtered_df.columns:
                fig_quality_roas = px.scatter(
                    filtered_df,
                    x='綜合品質分數',
                    y='購買 ROAS（廣告投資報酬率）',
                    color='品質排名',
                    size='花費金額 (TWD)',
                    hover_data=['行銷活動名稱', '廣告組合名稱'],
                    title="品質分數 vs ROAS",
                    color_discrete_map={'平均以上': '#2ecc71', '平均': '#f39c12', '平均以下': '#e74c3c'}
                )
                fig_quality_roas.update_layout(height=400)
                st.plotly_chart(fig_quality_roas, use_container_width=True)

        with scatter_col2:
            # 轉換率排名 vs CPA
            fig_conversion_cpa = px.scatter(
                filtered_df,
                x='轉換率排名_分數',
                y='每次購買的成本',
                color='轉換率排名',
                size='購買次數',
                hover_data=['行銷活動名稱', '廣告組合名稱'],
                title="轉換率排名 vs CPA",
                color_discrete_map={'平均以上': '#2ecc71', '平均': '#f39c12', '平均以下': '#e74c3c'}
            )
            fig_conversion_cpa.update_layout(height=400)
            st.plotly_chart(fig_conversion_cpa, use_container_width=True)

        # 最佳品質組合識別
        st.markdown("### ⭐ 最佳品質組合")

        best_quality = filtered_df[
            (filtered_df['品質排名'] == '平均以上') &
            (filtered_df['互動率排名'] == '平均以上') &
            (filtered_df['轉換率排名'] == '平均以上')
        ]

        if not best_quality.empty:
            best_summary = best_quality.groupby('行銷活動名稱').agg({
                '花費金額 (TWD)': 'sum',
                '購買次數': 'sum',
                '購買 ROAS（廣告投資報酬率）': 'mean'
            }).reset_index().sort_values('購買 ROAS（廣告投資報酬率）', ascending=False).head(5)

            st.success(f"🎯 發現 {len(best_quality)} 筆「三星品質」廣告（三項排名皆平均以上）")
            st.dataframe(
                best_summary.round(2),
                use_container_width=True,
                column_config={
                    "行銷活動名稱": "活動名稱",
                    "花費金額 (TWD)": st.column_config.NumberColumn("花費", format="%d"),
                    "購買次數": st.column_config.NumberColumn("購買", format="%d"),
                    "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f")
                }
            )
        else:
            st.warning("⚠️ 目前沒有「三星品質」的廣告（建議提升廣告品質）")

    st.markdown("---")

    # ========== 第三部分：三層級深度分析 ==========
    st.markdown("## 📊 三層級效能分析")

    level_tabs = st.tabs(["📌 Level 1：行銷活動", "📂 Level 2：廣告組合", "🎯 Level 3：單一廣告"])

    with level_tabs[0]:
        st.markdown("### 行銷活動層級分析")

        # 活動聚合數據
        campaign_summary = filtered_df.groupby('行銷活動名稱').agg({
            '花費金額 (TWD)': 'sum',
            '觸及人數': 'sum',
            '購買次數': 'sum',
            '購買 ROAS（廣告投資報酬率）': 'mean',
            '每次購買的成本': 'mean',
            '綜合品質分數': 'mean' if '綜合品質分數' in filtered_df.columns else 'count'
        }).reset_index()

        # 計算轉換率
        campaign_summary['轉換率'] = (campaign_summary['購買次數'] / campaign_summary['觸及人數'] * 100)

        # ROAS vs 花費氣泡圖
        fig_campaign_bubble = px.scatter(
            campaign_summary,
            x='花費金額 (TWD)',
            y='購買 ROAS（廣告投資報酬率）',
            size='購買次數',
            color='綜合品質分數' if '綜合品質分數' in campaign_summary.columns else '轉換率',
            hover_data=['行銷活動名稱', '轉換率'],
            title="活動效能氣泡圖（花費 vs ROAS）",
            labels={'花費金額 (TWD)': '花費 (TWD)', '購買 ROAS（廣告投資報酬率）': 'ROAS'},
            color_continuous_scale='RdYlGn'
        )
        fig_campaign_bubble.update_layout(height=500)
        st.plotly_chart(fig_campaign_bubble, use_container_width=True)

        # Top 活動排行
        st.markdown("#### 🏆 Top 10 活動排行")

        ranking_metric = st.radio(
            "排序指標",
            ['ROAS', '購買次數', '花費金額', '轉換率'],
            horizontal=True
        )

        metric_map = {
            'ROAS': '購買 ROAS（廣告投資報酬率）',
            '購買次數': '購買次數',
            '花費金額': '花費金額 (TWD)',
            '轉換率': '轉換率'
        }

        top_campaigns = campaign_summary.sort_values(metric_map[ranking_metric], ascending=False).head(10)

        fig_ranking = px.bar(
            top_campaigns,
            y='行銷活動名稱',
            x=metric_map[ranking_metric],
            orientation='h',
            title=f"Top 10 {ranking_metric}",
            color=metric_map[ranking_metric],
            color_continuous_scale='Blues',
            text=metric_map[ranking_metric]
        )
        fig_ranking.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig_ranking.update_layout(height=450, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_ranking, use_container_width=True)

    with level_tabs[1]:
        st.markdown("### 廣告組合層級分析")

        # 選擇活動查看其廣告組
        campaign_for_adsets = st.selectbox(
            "選擇活動查看廣告組表現",
            selected_campaigns
        )

        if campaign_for_adsets:
            adset_df = filtered_df[filtered_df['行銷活動名稱'] == campaign_for_adsets]

            adset_summary = adset_df.groupby('廣告組合名稱').agg({
                '花費金額 (TWD)': 'sum',
                '購買次數': 'sum',
                '購買 ROAS（廣告投資報酬率）': 'mean',
                '每次購買的成本': 'mean',
                'CTR（全部）': 'mean',
                '品質排名': lambda x: x.mode()[0] if not x.empty else '未知',
                '轉換率排名': lambda x: x.mode()[0] if not x.empty else '未知'
            }).reset_index()

            # 廣告組表現對比
            fig_adset_compare = go.Figure()

            fig_adset_compare.add_trace(go.Bar(
                name='花費',
                x=adset_summary['廣告組合名稱'],
                y=adset_summary['花費金額 (TWD)'],
                yaxis='y',
                marker_color='#3498db'
            ))

            fig_adset_compare.add_trace(go.Scatter(
                name='ROAS',
                x=adset_summary['廣告組合名稱'],
                y=adset_summary['購買 ROAS（廣告投資報酬率）'],
                yaxis='y2',
                mode='lines+markers',
                marker=dict(size=10, color='#e74c3c'),
                line=dict(width=3)
            ))

            fig_adset_compare.update_layout(
                title=f"活動「{campaign_for_adsets}」的廣告組表現",
                xaxis=dict(title='廣告組合', tickangle=-45),
                yaxis=dict(title='花費 (TWD)', side='left'),
                yaxis2=dict(title='ROAS', side='right', overlaying='y'),
                hovermode='x unified',
                height=450
            )

            st.plotly_chart(fig_adset_compare, use_container_width=True)

            # 廣告組詳細表格
            st.dataframe(
                adset_summary.round(2),
                use_container_width=True,
                column_config={
                    "廣告組合名稱": "廣告組",
                    "花費金額 (TWD)": st.column_config.NumberColumn("花費", format="%d"),
                    "購買次數": st.column_config.NumberColumn("購買", format="%d"),
                    "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
                    "每次購買的成本": st.column_config.NumberColumn("CPA", format="%.0f"),
                    "CTR（全部）": st.column_config.NumberColumn("CTR (%)", format="%.2f"),
                    "品質排名": "品質",
                    "轉換率排名": "轉換率"
                }
            )

    with level_tabs[2]:
        st.markdown("### 單一廣告層級分析")

        # 選擇廣告組
        adset_for_ads = st.selectbox(
            "選擇廣告組查看單一廣告",
            filtered_df['廣告組合名稱'].unique().tolist()
        )

        if adset_for_ads:
            ads_df = filtered_df[filtered_df['廣告組合名稱'] == adset_for_ads]

            # 單一廣告表現
            ads_summary = ads_df.groupby('廣告名稱').agg({
                '花費金額 (TWD)': 'sum',
                '購買次數': 'sum',
                '購買 ROAS（廣告投資報酬率）': 'mean',
                'CTR（全部）': 'mean',
                '品質排名': lambda x: x.mode()[0] if not x.empty else '未知',
                '互動率排名': lambda x: x.mode()[0] if not x.empty else '未知',
                '轉換率排名': lambda x: x.mode()[0] if not x.empty else '未知',
                '綜合品質分數': 'mean' if '綜合品質分數' in ads_df.columns else 'count'
            }).reset_index().sort_values('購買 ROAS（廣告投資報酬率）', ascending=False)

            # 顯示前10個廣告
            top_ads = ads_summary.head(10)

            # ROAS 排名
            fig_ads = px.bar(
                top_ads,
                y='廣告名稱',
                x='購買 ROAS（廣告投資報酬率）',
                orientation='h',
                title=f"廣告組「{adset_for_ads}」Top 10 廣告 ROAS",
                color='綜合品質分數' if '綜合品質分數' in top_ads.columns else '購買 ROAS（廣告投資報酬率）',
                color_continuous_scale='RdYlGn',
                text='購買 ROAS（廣告投資報酬率）'
            )
            fig_ads.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig_ads.update_layout(height=450, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_ads, use_container_width=True)

            # 詳細表格
            st.dataframe(
                ads_summary,
                use_container_width=True,
                column_config={
                    "廣告名稱": "廣告",
                    "花費金額 (TWD)": st.column_config.NumberColumn("花費", format="%d"),
                    "購買次數": st.column_config.NumberColumn("購買", format="%d"),
                    "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
                    "CTR（全部）": st.column_config.NumberColumn("CTR (%)", format="%.2f"),
                    "品質排名": "品質",
                    "互動率排名": "互動率",
                    "轉換率排名": "轉換率",
                    "綜合品質分數": st.column_config.NumberColumn("綜合分數", format="%.2f")
                }
            )

    st.markdown("---")

    # ========== 第四部分：出價策略分析 ==========
    st.markdown("## 💰 出價策略分析")

    if '出價類型' in filtered_df.columns:
        bid_col1, bid_col2 = st.columns(2)

        with bid_col1:
            # 出價類型分布
            bid_dist = filtered_df.groupby('出價類型').agg({
                '花費金額 (TWD)': 'sum',
                '購買次數': 'sum',
                '購買 ROAS（廣告投資報酬率）': 'mean'
            }).reset_index()

            fig_bid_dist = px.pie(
                bid_dist,
                values='花費金額 (TWD)',
                names='出價類型',
                title="出價類型花費分布"
            )
            fig_bid_dist.update_layout(height=400)
            st.plotly_chart(fig_bid_dist, use_container_width=True)

        with bid_col2:
            # 出價類型成效對比
            fig_bid_performance = go.Figure()

            fig_bid_performance.add_trace(go.Bar(
                name='平均 ROAS',
                x=bid_dist['出價類型'],
                y=bid_dist['購買 ROAS（廣告投資報酬率）'],
                marker_color='#2ecc71'
            ))

            fig_bid_performance.update_layout(
                title="不同出價類型的平均 ROAS",
                xaxis_title="出價類型",
                yaxis_title="平均 ROAS",
                height=400
            )

            st.plotly_chart(fig_bid_performance, use_container_width=True)

        # 預算 vs ROAS 散點圖
        if '廣告組合預算' in filtered_df.columns:
            st.markdown("### 📊 預算配置 vs ROAS")

            budget_df = filtered_df[filtered_df['廣告組合預算'] > 0].copy()

            if not budget_df.empty:
                fig_budget_roas = px.scatter(
                    budget_df,
                    x='廣告組合預算',
                    y='購買 ROAS（廣告投資報酬率）',
                    color='出價類型',
                    size='購買次數',
                    hover_data=['行銷活動名稱', '廣告組合名稱'],
                    title="預算配置 vs ROAS（標記需調整的活動）",
                    labels={'廣告組合預算': '預算', '購買 ROAS（廣告投資報酬率）': 'ROAS'}
                )

                # 添加基準線（ROAS = 1）
                fig_budget_roas.add_hline(
                    y=1.0,
                    line_dash="dash",
                    line_color="red",
                    annotation_text="損益平衡點（ROAS=1）"
                )

                fig_budget_roas.update_layout(height=500)
                st.plotly_chart(fig_budget_roas, use_container_width=True)

                # 建議調整的活動
                low_roas_high_budget = budget_df[
                    (budget_df['購買 ROAS（廣告投資報酬率）'] < 1.5) &
                    (budget_df['廣告組合預算'] > budget_df['廣告組合預算'].median())
                ]

                if not low_roas_high_budget.empty:
                    st.warning(f"""
                    ⚠️ **發現 {len(low_roas_high_budget)} 筆高預算低 ROAS 的廣告組**

                    建議：降低預算或優化素材/受眾
                    """)

                    problem_summary = low_roas_high_budget.groupby('行銷活動名稱').agg({
                        '廣告組合預算': 'mean',
                        '購買 ROAS（廣告投資報酬率）': 'mean',
                        '花費金額 (TWD)': 'sum'
                    }).reset_index().sort_values('花費金額 (TWD)', ascending=False)

                    st.dataframe(
                        problem_summary.round(2),
                        use_container_width=True,
                        column_config={
                            "行銷活動名稱": "活動名稱",
                            "廣告組合預算": st.column_config.NumberColumn("平均預算", format="%d"),
                            "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("平均 ROAS", format="%.2f"),
                            "花費金額 (TWD)": st.column_config.NumberColumn("總花費", format="%d")
                        }
                    )

    st.markdown("---")

    # ========== 第五部分：活動內廣告表現對比 ==========
    st.markdown("## 📊 活動內廣告表現對比")

    st.markdown("""
    查看所選活動中，哪些具體廣告表現最好/最差。幫助您快速決定預算分配。
    """)

    # 添加廣告階層顯示
    filtered_df['廣告階層'] = filtered_df.apply(format_ad_display_name, axis=1)

    # 顯示 Top/Bottom 廣告
    if not filtered_df.empty:
        display_top_bottom_ads(
            filtered_df,
            metric='購買 ROAS（廣告投資報酬率）',
            top_n=10
        )

        # 預算優化建議
        st.markdown("### 💰 預算優化建議")

        top_ads = filtered_df.nlargest(10, '購買 ROAS（廣告投資報酬率）')
        bottom_ads = filtered_df.nsmallest(10, '購買 ROAS（廣告投資報酬率）')

        top_spend = top_ads['花費金額 (TWD)'].sum()
        bottom_spend = bottom_ads['花費金額 (TWD)'].sum()
        top_roas = top_ads['購買 ROAS（廣告投資報酬率）'].mean()
        bottom_roas = bottom_ads['購買 ROAS（廣告投資報酬率）'].mean()

        col1, col2 = st.columns(2)

        with col1:
            st.success(f"""
**🏆 Top 10 廣告**

- 總花費：${top_spend:,.0f}
- 平均 ROAS：{top_roas:.2f}
- 總購買：{top_ads['購買次數'].sum():.0f} 次

**建議**：
✅ 增加這些廣告的預算
✅ 複製成功素材到新廣告
✅ 擴大類似受眾
            """)

        with col2:
            st.warning(f"""
**⚠️ Bottom 10 廣告**

- 總花費：${bottom_spend:,.0f}
- 平均 ROAS：{bottom_roas:.2f}
- 總購買：{bottom_ads['購買次數'].sum():.0f} 次

**建議**：
❌ 暫停 ROAS < 1.0 的廣告
⚠️ 降低預算或優化素材
💡 將預算轉移到 Top 10
            """)

        # 預算轉移潛力
        if bottom_roas < 1.5 and top_roas > 3.0:
            potential_saving = bottom_spend
            potential_revenue_increase = potential_saving * top_roas

            st.info(f"""
**💡 預算轉移潛力分析**

如果將 Bottom 10 的預算（${potential_saving:,.0f}）轉移到 Top 10 類型的廣告：
- 預期 ROAS：{bottom_roas:.2f}x → {top_roas:.2f}x
- 預期營收增加：${potential_revenue_increase:,.0f}
- 預期利潤增加：${potential_revenue_increase - potential_saving:,.0f}

**建議**：立即執行預算重新分配！
            """)

    st.markdown("---")

    # ========== 第六部分：優化建議 ==========
    st.markdown("## 💡 智能優化建議")

    suggestion_col1, suggestion_col2 = st.columns(2)

    with suggestion_col1:
        st.success("""
        **🎯 高效活動特徵**

        根據分析，表現最佳的活動具有：
        - ✅ 品質排名「平均以上」
        - ✅ 轉換率排名「平均以上」
        - ✅ ROAS > 3.0
        - ✅ 適當的預算配置

        **建議行動**：
        1. 增加高效活動預算
        2. 複製成功素材到其他活動
        3. 擴大高效受眾規模
        """)

    with suggestion_col2:
        st.warning("""
        **⚠️ 需優化活動特徵**

        需要改善的活動通常：
        - ❌ 品質排名「平均以下」
        - ❌ ROAS < 1.5
        - ❌ 高預算但低轉換

        **建議行動**：
        1. 暫停 ROAS < 1.0 的活動
        2. 降低低效活動預算
        3. 重新設計素材與受眾
        4. 測試不同出價策略
        """)

if __name__ == "__main__":
    show_campaign_analysis()
