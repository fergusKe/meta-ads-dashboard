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

def show_audience_insights():
    """顯示受眾洞察頁面 - 升級版"""
    st.markdown("# 👥 受眾洞察")
    st.markdown("深度分析受眾表現，包含年齡×性別交叉分析與受眾細分策略")

    # 載入數據
    df = load_meta_ads_data()
    if df is None or df.empty:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    # 檢查必要欄位
    if '年齡' not in df.columns or '性別' not in df.columns:
        st.warning("⚠️ 資料中缺少年齡或性別資訊")
        return

    # ========== 第一部分：年齡×性別交叉分析 ==========
    st.markdown("## 🎯 年齡 × 性別交叉分析")

    # 建立交叉分析數據
    cross_analysis = df.groupby(['年齡', '性別']).agg({
        '花費金額 (TWD)': 'sum',
        '觸及人數': 'sum',
        '購買次數': 'sum',
        '購買 ROAS（廣告投資報酬率）': 'mean',
        '每次購買的成本': 'mean',
        'CTR（全部）': 'mean'
    }).reset_index()

    # 計算轉換率
    cross_analysis['轉換率'] = (cross_analysis['購買次數'] / cross_analysis['觸及人數'] * 100)

    heat_col1, heat_col2 = st.columns(2)

    with heat_col1:
        # ROAS 熱力圖
        roas_pivot = cross_analysis.pivot(index='年齡', columns='性別', values='購買 ROAS（廣告投資報酬率）')

        fig_roas_heat = go.Figure(data=go.Heatmap(
            z=roas_pivot.values,
            x=roas_pivot.columns,
            y=roas_pivot.index,
            colorscale='RdYlGn',
            text=roas_pivot.values,
            texttemplate='%{text:.2f}',
            textfont={"size": 14},
            colorbar=dict(title="ROAS")
        ))

        fig_roas_heat.update_layout(
            title="年齡 × 性別 ROAS 熱力圖",
            xaxis_title="性別",
            yaxis_title="年齡",
            height=400
        )

        st.plotly_chart(fig_roas_heat, use_container_width=True)

    with heat_col2:
        # 購買率熱力圖
        conversion_pivot = cross_analysis.pivot(index='年齡', columns='性別', values='轉換率')

        fig_conversion_heat = go.Figure(data=go.Heatmap(
            z=conversion_pivot.values,
            x=conversion_pivot.columns,
            y=conversion_pivot.index,
            colorscale='Blues',
            text=conversion_pivot.values,
            texttemplate='%{text:.2f}%',
            textfont={"size": 14},
            colorbar=dict(title="轉換率 (%)")
        ))

        fig_conversion_heat.update_layout(
            title="年齡 × 性別 轉換率熱力圖",
            xaxis_title="性別",
            yaxis_title="年齡",
            height=400
        )

        st.plotly_chart(fig_conversion_heat, use_container_width=True)

    # 花費分布熱力圖
    st.markdown("### 💰 花費分布熱力圖")

    spend_pivot = cross_analysis.pivot(index='年齡', columns='性別', values='花費金額 (TWD)')

    fig_spend_heat = go.Figure(data=go.Heatmap(
        z=spend_pivot.values,
        x=spend_pivot.columns,
        y=spend_pivot.index,
        colorscale='Oranges',
        text=spend_pivot.values,
        texttemplate='$%{text:,.0f}',
        textfont={"size": 12},
        colorbar=dict(title="花費 (TWD)")
    ))

    fig_spend_heat.update_layout(
        title="年齡 × 性別 花費分布",
        xaxis_title="性別",
        yaxis_title="年齡",
        height=400
    )

    st.plotly_chart(fig_spend_heat, use_container_width=True)

    # ========== 第二部分：最佳受眾組合識別 ==========
    st.markdown("## ⭐ 最佳受眾組合")

    # 計算每個組合的綜合得分
    cross_analysis['綜合得分'] = (
        (cross_analysis['購買 ROAS（廣告投資報酬率）'] / cross_analysis['購買 ROAS（廣告投資報酬率）'].max() * 0.4) +
        (cross_analysis['轉換率'] / cross_analysis['轉換率'].max() * 0.3) +
        (1 - cross_analysis['每次購買的成本'] / cross_analysis['每次購買的成本'].max() * 0.3)
    ) * 100

    # Top 5 最佳組合
    top_audiences = cross_analysis.sort_values('綜合得分', ascending=False).head(5)

    top_col1, top_col2 = st.columns([3, 2])

    with top_col1:
        # 最佳組合長條圖
        top_audiences['組合'] = top_audiences['年齡'] + ' - ' + top_audiences['性別']

        fig_top = px.bar(
            top_audiences,
            x='綜合得分',
            y='組合',
            orientation='h',
            title="Top 5 最佳受眾組合",
            color='綜合得分',
            color_continuous_scale='Greens',
            text='綜合得分'
        )
        fig_top.update_traces(texttemplate='%{text:.1f}', textposition='outside')
        fig_top.update_layout(height=350, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_top, use_container_width=True)

    with top_col2:
        # 最佳組合詳細數據
        st.markdown("#### 📊 詳細數據")
        st.dataframe(
            top_audiences[['年齡', '性別', '購買 ROAS（廣告投資報酬率）', '轉換率', '每次購買的成本']].round(2),
            use_container_width=True,
            column_config={
                "年齡": "年齡",
                "性別": "性別",
                "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
                "轉換率": st.column_config.NumberColumn("轉換率 (%)", format="%.2f"),
                "每次購買的成本": st.column_config.NumberColumn("CPA", format="%.0f")
            },
            hide_index=True
        )

    # 識別高價值受眾（高ROAS + 低CPA）
    st.markdown("### 💎 高價值受眾識別")

    high_value = cross_analysis[
        (cross_analysis['購買 ROAS（廣告投資報酬率）'] > cross_analysis['購買 ROAS（廣告投資報酬率）'].median()) &
        (cross_analysis['每次購買的成本'] < cross_analysis['每次購買的成本'].median())
    ]

    if not high_value.empty:
        fig_high_value = px.scatter(
            cross_analysis,
            x='每次購買的成本',
            y='購買 ROAS（廣告投資報酬率）',
            color='性別',
            size='花費金額 (TWD)',
            hover_data=['年齡', '性別', '轉換率'],
            title="受眾價值矩陣（ROAS vs CPA）",
            labels={'每次購買的成本': 'CPA (TWD)', '購買 ROAS（廣告投資報酬率）': 'ROAS'}
        )

        # 添加象限分隔線
        median_roas = cross_analysis['購買 ROAS（廣告投資報酬率）'].median()
        median_cpa = cross_analysis['每次購買的成本'].median()

        fig_high_value.add_hline(y=median_roas, line_dash="dash", line_color="gray", annotation_text="ROAS中位數")
        fig_high_value.add_vline(x=median_cpa, line_dash="dash", line_color="gray", annotation_text="CPA中位數")

        # 標註高價值區域
        fig_high_value.add_annotation(
            x=cross_analysis['每次購買的成本'].min(),
            y=cross_analysis['購買 ROAS（廣告投資報酬率）'].max(),
            text="💎 高價值區",
            showarrow=False,
            font=dict(size=14, color="green")
        )

        fig_high_value.update_layout(height=500)
        st.plotly_chart(fig_high_value, use_container_width=True)

        st.success(f"✅ 發現 {len(high_value)} 個高價值受眾組合（高ROAS + 低CPA）")

    st.markdown("---")

    # ========== 第三部分：受眾類型對比 ==========
    st.markdown("## 🎭 受眾類型對比")

    audience_tabs = st.tabs(["📊 年齡層分析", "⚧ 性別分析", "🎯 自訂受眾 vs 興趣受眾"])

    with audience_tabs[0]:
        # 年齡層分析
        age_summary = df.groupby('年齡').agg({
            '花費金額 (TWD)': 'sum',
            '購買次數': 'sum',
            '購買 ROAS（廣告投資報酬率）': 'mean',
            'CTR（全部）': 'mean',
            '觸及人數': 'sum'
        }).reset_index()

        age_summary['轉換率'] = (age_summary['購買次數'] / age_summary['觸及人數'] * 100)

        age_col1, age_col2 = st.columns(2)

        with age_col1:
            # 年齡層 ROAS 對比
            fig_age_roas = px.bar(
                age_summary.sort_values('購買 ROAS（廣告投資報酬率）', ascending=False),
                x='年齡',
                y='購買 ROAS（廣告投資報酬率）',
                title="各年齡層 ROAS",
                color='購買 ROAS（廣告投資報酬率）',
                color_continuous_scale='RdYlGn',
                text='購買 ROAS（廣告投資報酬率）'
            )
            fig_age_roas.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig_age_roas.update_layout(height=400)
            st.plotly_chart(fig_age_roas, use_container_width=True)

        with age_col2:
            # 年齡層花費占比
            fig_age_pie = px.pie(
                age_summary,
                values='花費金額 (TWD)',
                names='年齡',
                title="年齡層花費占比"
            )
            fig_age_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_age_pie.update_layout(height=400)
            st.plotly_chart(fig_age_pie, use_container_width=True)

        # 年齡層詳細表格
        st.dataframe(
            age_summary.sort_values('購買 ROAS（廣告投資報酬率）', ascending=False).round(2),
            use_container_width=True,
            column_config={
                "年齡": "年齡層",
                "花費金額 (TWD)": st.column_config.NumberColumn("花費", format="%d"),
                "購買次數": st.column_config.NumberColumn("購買", format="%d"),
                "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
                "CTR（全部）": st.column_config.NumberColumn("CTR (%)", format="%.2f"),
                "觸及人數": st.column_config.NumberColumn("觸及", format="%d"),
                "轉換率": st.column_config.NumberColumn("轉換率 (%)", format="%.2f")
            },
            hide_index=True
        )

    with audience_tabs[1]:
        # 性別分析
        gender_summary = df.groupby('性別').agg({
            '花費金額 (TWD)': 'sum',
            '購買次數': 'sum',
            '購買 ROAS（廣告投資報酬率）': 'mean',
            'CTR（全部）': 'mean',
            '觸及人數': 'sum',
            '每次購買的成本': 'mean'
        }).reset_index()

        gender_summary['轉換率'] = (gender_summary['購買次數'] / gender_summary['觸及人數'] * 100)

        gender_col1, gender_col2 = st.columns(2)

        with gender_col1:
            # 性別成效對比雷達圖
            fig_gender_radar = go.Figure()

            for gender in gender_summary['性別'].unique():
                gender_data = gender_summary[gender_summary['性別'] == gender]

                # 標準化數據
                metrics = {
                    'ROAS': gender_data['購買 ROAS（廣告投資報酬率）'].values[0] / gender_summary['購買 ROAS（廣告投資報酬率）'].max() * 100,
                    'CTR': gender_data['CTR（全部）'].values[0] / gender_summary['CTR（全部）'].max() * 100,
                    '轉換率': gender_data['轉換率'].values[0] / gender_summary['轉換率'].max() * 100,
                    '購買次數': gender_data['購買次數'].values[0] / gender_summary['購買次數'].max() * 100,
                    'CPA效率': (1 - gender_data['每次購買的成本'].values[0] / gender_summary['每次購買的成本'].max()) * 100
                }

                fig_gender_radar.add_trace(go.Scatterpolar(
                    r=list(metrics.values()),
                    theta=list(metrics.keys()),
                    fill='toself',
                    name=gender
                ))

            fig_gender_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                title="性別成效雷達圖（標準化）",
                height=400
            )

            st.plotly_chart(fig_gender_radar, use_container_width=True)

        with gender_col2:
            # 性別詳細對比
            fig_gender_compare = go.Figure()

            fig_gender_compare.add_trace(go.Bar(
                name='花費',
                x=gender_summary['性別'],
                y=gender_summary['花費金額 (TWD)'],
                yaxis='y',
                marker_color='#3498db'
            ))

            fig_gender_compare.add_trace(go.Scatter(
                name='ROAS',
                x=gender_summary['性別'],
                y=gender_summary['購買 ROAS（廣告投資報酬率）'],
                yaxis='y2',
                mode='lines+markers',
                marker=dict(size=12, color='#e74c3c'),
                line=dict(width=3)
            ))

            fig_gender_compare.update_layout(
                title="性別花費 vs ROAS",
                xaxis_title="性別",
                yaxis=dict(title="花費 (TWD)", side='left'),
                yaxis2=dict(title="ROAS", side='right', overlaying='y'),
                height=400
            )

            st.plotly_chart(fig_gender_compare, use_container_width=True)

        # 性別詳細表格
        st.dataframe(
            gender_summary.round(2),
            use_container_width=True,
            column_config={
                "性別": "性別",
                "花費金額 (TWD)": st.column_config.NumberColumn("花費", format="%d"),
                "購買次數": st.column_config.NumberColumn("購買", format="%d"),
                "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
                "CTR（全部）": st.column_config.NumberColumn("CTR (%)", format="%.2f"),
                "觸及人數": st.column_config.NumberColumn("觸及", format="%d"),
                "每次購買的成本": st.column_config.NumberColumn("CPA", format="%.0f"),
                "轉換率": st.column_config.NumberColumn("轉換率 (%)", format="%.2f")
            },
            hide_index=True
        )

    with audience_tabs[2]:
        # 自訂受眾 vs 興趣受眾
        if '包含的自訂廣告受眾' in df.columns:
            # 區分自訂受眾和興趣受眾
            df_temp = df.copy()
            df_temp['受眾類型'] = df_temp['包含的自訂廣告受眾'].apply(
                lambda x: '自訂受眾' if pd.notna(x) and x != '未知' else '興趣受眾'
            )

            audience_type_summary = df_temp.groupby('受眾類型').agg({
                '花費金額 (TWD)': 'sum',
                '購買次數': 'sum',
                '購買 ROAS（廣告投資報酬率）': 'mean',
                'CTR（全部）': 'mean',
                '觸及人數': 'sum',
                '每次購買的成本': 'mean'
            }).reset_index()

            audience_type_summary['轉換率'] = (
                audience_type_summary['購買次數'] / audience_type_summary['觸及人數'] * 100
            )

            # 對比圖
            metrics_compare = ['購買 ROAS（廣告投資報酬率）', 'CTR（全部）', '轉換率', '每次購買的成本']

            fig_audience_type = make_subplots(
                rows=2, cols=2,
                subplot_titles=['ROAS', 'CTR (%)', '轉換率 (%)', 'CPA (TWD)']
            )

            for i, metric in enumerate(metrics_compare):
                row = i // 2 + 1
                col = i % 2 + 1

                fig_audience_type.add_trace(
                    go.Bar(
                        x=audience_type_summary['受眾類型'],
                        y=audience_type_summary[metric],
                        name=metric,
                        showlegend=False,
                        marker_color=['#3498db', '#e74c3c']
                    ),
                    row=row, col=col
                )

            fig_audience_type.update_layout(height=500, title="自訂受眾 vs 興趣受眾成效對比")
            st.plotly_chart(fig_audience_type, use_container_width=True)

            # 詳細表格
            st.dataframe(
                audience_type_summary.round(2),
                use_container_width=True,
                column_config={
                    "受眾類型": "受眾類型",
                    "花費金額 (TWD)": st.column_config.NumberColumn("花費", format="%d"),
                    "購買次數": st.column_config.NumberColumn("購買", format="%d"),
                    "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
                    "CTR（全部）": st.column_config.NumberColumn("CTR (%)", format="%.2f"),
                    "觸及人數": st.column_config.NumberColumn("觸及", format="%d"),
                    "每次購買的成本": st.column_config.NumberColumn("CPA", format="%.0f"),
                    "轉換率": st.column_config.NumberColumn("轉換率 (%)", format="%.2f")
                },
                hide_index=True
            )

            # 推薦受眾類型
            best_type = audience_type_summary.loc[
                audience_type_summary['購買 ROAS（廣告投資報酬率）'].idxmax()
            ]

            st.info(f"""
            **💡 推薦受眾類型：{best_type['受眾類型']}**

            - ROAS：{best_type['購買 ROAS（廣告投資報酬率）']:.2f}
            - 轉換率：{best_type['轉換率']:.2f}%
            - CPA：${best_type['每次購買的成本']:.0f}
            """)
        else:
            st.warning("資料中缺少自訂受眾資訊")

    st.markdown("---")

    # ========== 第四部分：智能受眾建議 ==========
    st.markdown("## 💡 智能受眾建議")

    suggest_col1, suggest_col2 = st.columns(2)

    with suggest_col1:
        st.success("""
        **✅ 建議擴大的受眾**

        根據分析，以下受眾表現優異：
        - 高 ROAS（> 平均）
        - 高轉換率（> 平均）
        - 低 CPA（< 平均）

        **行動方案**：
        1. 增加預算投放
        2. 擴大相似受眾（Lookalike）
        3. 測試更廣泛的年齡區間
        """)

    with suggest_col2:
        st.warning("""
        **⚠️ 建議優化的受眾**

        以下受眾需要優化：
        - 低 ROAS（< 1.5）
        - 低轉換率
        - 高 CPA

        **行動方案**：
        1. 暫停低效受眾
        2. 重新定義受眾條件
        3. 測試新的興趣或行為標籤
        4. 優化素材與文案
        """)

    # 潛力受眾（高CTR但低購買）
    st.markdown("### 🌟 潛力受眾（需優化轉換）")

    potential_audiences = cross_analysis[
        (cross_analysis['CTR（全部）'] > cross_analysis['CTR（全部）'].median()) &
        (cross_analysis['轉換率'] < cross_analysis['轉換率'].median())
    ]

    if not potential_audiences.empty:
        st.warning(f"發現 {len(potential_audiences)} 個潛力受眾（高點擊但低轉換）")

        st.dataframe(
            potential_audiences[['年齡', '性別', 'CTR（全部）', '轉換率', '購買次數']].sort_values('CTR（全部）', ascending=False).round(2),
            use_container_width=True,
            column_config={
                "年齡": "年齡",
                "性別": "性別",
                "CTR（全部）": st.column_config.NumberColumn("CTR (%)", format="%.2f"),
                "轉換率": st.column_config.NumberColumn("轉換率 (%)", format="%.2f"),
                "購買次數": st.column_config.NumberColumn("購買", format="%d")
            },
            hide_index=True
        )

        st.info("""
        **💡 優化建議：**
        - 這些受眾對廣告有興趣（高 CTR），但沒有完成購買
        - 建議優化：Landing Page、產品價格、促銷優惠
        - 可嘗試：重新定向廣告、購物車放棄提醒
        """)

if __name__ == "__main__":
    show_audience_insights()
