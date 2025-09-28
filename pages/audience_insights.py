import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from utils.data_loader import load_meta_ads_data

def show_audience_insights():
    """顯示受眾洞察頁面"""
    st.markdown("# 👥 受眾洞察")
    st.markdown("分析不同受眾群體的表現，優化受眾定位策略")

    # 載入數據
    df = load_meta_ads_data()
    if df is None:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    # 受眾維度分析
    st.markdown("## 📊 受眾維度分析")

    tabs = st.tabs(["🎂 年齡層分析", "⚧ 性別分析", "🔄 交叉分析", "🎯 受眾表現矩陣"])

    with tabs[0]:
        show_age_analysis(df)

    with tabs[1]:
        show_gender_analysis(df)

    with tabs[2]:
        show_cross_analysis(df)

    with tabs[3]:
        show_audience_performance_matrix(df)

    st.markdown("---")

    # 受眾建議系統
    st.markdown("## 💡 智能受眾建議")
    show_audience_recommendations(df)

    st.markdown("---")

    # 受眾趨勢分析
    st.markdown("## 📈 受眾趨勢分析")
    show_audience_trends(df)

def show_age_analysis(df):
    """顯示年齡層分析"""
    st.markdown("### 🎂 年齡層效能分析")

    if '年齡' not in df.columns:
        st.warning("數據中缺少年齡資訊")
        return

    # 年齡層統計
    age_stats = df.groupby('年齡').agg({
        '花費金額 (TWD)': 'sum',
        '購買次數': 'sum',
        '購買 ROAS（廣告投資報酬率）': 'mean',
        'CTR（全部）': 'mean',
        '觸及人數': 'sum',
        '每次購買的成本': 'mean'
    }).reset_index()

    if age_stats.empty:
        st.info("暫無年齡層數據")
        return

    # 計算轉換率
    age_stats['轉換率 (%)'] = (age_stats['購買次數'] / age_stats['觸及人數'] * 100).fillna(0)

    col1, col2 = st.columns(2)

    with col1:
        # 年齡層 ROAS 比較
        fig_age_roas = px.bar(
            age_stats,
            x='年齡',
            y='購買 ROAS（廣告投資報酬率）',
            title="年齡層 ROAS 表現",
            color='購買 ROAS（廣告投資報酬率）',
            color_continuous_scale='RdYlGn',
            text='購買 ROAS（廣告投資報酬率）'
        )
        fig_age_roas.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig_age_roas.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_age_roas, use_container_width=True)

    with col2:
        # 年齡層花費分佈
        fig_age_spend = px.pie(
            age_stats,
            values='花費金額 (TWD)',
            names='年齡',
            title="年齡層花費分佈",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_age_spend.update_traces(textposition='inside', textinfo='percent+label')
        fig_age_spend.update_layout(height=400)
        st.plotly_chart(fig_age_spend, use_container_width=True)

    # 年齡層詳細數據表
    st.markdown("#### 📋 年齡層詳細數據")
    st.dataframe(
        age_stats.round(2),
        use_container_width=True,
        column_config={
            "年齡": st.column_config.TextColumn("年齡層", width="small"),
            "花費金額 (TWD)": st.column_config.NumberColumn("花費金額", format="%d"),
            "購買次數": st.column_config.NumberColumn("購買次數", format="%d"),
            "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
            "CTR（全部）": st.column_config.NumberColumn("CTR (%)", format="%.2f"),
            "觸及人數": st.column_config.NumberColumn("觸及人數", format="%d"),
            "每次購買的成本": st.column_config.NumberColumn("CPA", format="%.0f"),
            "轉換率 (%)": st.column_config.NumberColumn("轉換率", format="%.3f")
        }
    )

    # 年齡層洞察
    best_age = age_stats.loc[age_stats['購買 ROAS（廣告投資報酬率）'].idxmax()]
    worst_age = age_stats.loc[age_stats['購買 ROAS（廣告投資報酬率）'].idxmin()]

    col_insight1, col_insight2 = st.columns(2)

    with col_insight1:
        st.success(f"""
        **🏆 最佳表現年齡層：{best_age['年齡']}**
        - ROAS：{best_age['購買 ROAS（廣告投資報酬率）']:.2f}
        - 轉換率：{best_age['轉換率 (%)']:.3f}%
        - CPA：${best_age['每次購買的成本']:.0f}
        - 建議：增加此年齡層的預算投入
        """)

    with col_insight2:
        st.warning(f"""
        **⚠️ 需改善年齡層：{worst_age['年齡']}**
        - ROAS：{worst_age['購買 ROAS（廣告投資報酬率）']:.2f}
        - 轉換率：{worst_age['轉換率 (%)']:.3f}%
        - CPA：${worst_age['每次購買的成本']:.0f}
        - 建議：優化創意或考慮暫停投放
        """)

def show_gender_analysis(df):
    """顯示性別分析"""
    st.markdown("### ⚧ 性別效能分析")

    if '性別' not in df.columns:
        st.warning("數據中缺少性別資訊")
        return

    # 性別統計
    gender_stats = df.groupby('性別').agg({
        '花費金額 (TWD)': 'sum',
        '購買次數': 'sum',
        '購買 ROAS（廣告投資報酬率）': 'mean',
        'CTR（全部）': 'mean',
        '觸及人數': 'sum',
        '每次購買的成本': 'mean'
    }).reset_index()

    if gender_stats.empty:
        st.info("暫無性別數據")
        return

    # 計算轉換率
    gender_stats['轉換率 (%)'] = (gender_stats['購買次數'] / gender_stats['觸及人數'] * 100).fillna(0)

    col1, col2 = st.columns(2)

    with col1:
        # 性別 ROAS 比較
        fig_gender_roas = px.bar(
            gender_stats,
            x='性別',
            y='購買 ROAS（廣告投資報酬率）',
            title="性別 ROAS 表現",
            color='性別',
            color_discrete_map={'男性': '#4285F4', '女性': '#EA4335', '未知': '#FBBC04'},
            text='購買 ROAS（廣告投資報酬率）'
        )
        fig_gender_roas.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig_gender_roas.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_gender_roas, use_container_width=True)

    with col2:
        # 性別轉換率比較
        fig_gender_conv = px.bar(
            gender_stats,
            x='性別',
            y='轉換率 (%)',
            title="性別轉換率表現",
            color='性別',
            color_discrete_map={'男性': '#4285F4', '女性': '#EA4335', '未知': '#FBBC04'},
            text='轉換率 (%)'
        )
        fig_gender_conv.update_traces(texttemplate='%{text:.3f}%', textposition='outside')
        fig_gender_conv.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_gender_conv, use_container_width=True)

    # 性別詳細數據表
    st.markdown("#### 📋 性別詳細數據")
    st.dataframe(
        gender_stats.round(2),
        use_container_width=True,
        column_config={
            "性別": st.column_config.TextColumn("性別", width="small"),
            "花費金額 (TWD)": st.column_config.NumberColumn("花費金額", format="%d"),
            "購買次數": st.column_config.NumberColumn("購買次數", format="%d"),
            "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
            "CTR（全部）": st.column_config.NumberColumn("CTR (%)", format="%.2f"),
            "觸及人數": st.column_config.NumberColumn("觸及人數", format="%d"),
            "每次購買的成本": st.column_config.NumberColumn("CPA", format="%.0f"),
            "轉換率 (%)": st.column_config.NumberColumn("轉換率", format="%.3f")
        }
    )

def show_cross_analysis(df):
    """顯示年齡 x 性別交叉分析"""
    st.markdown("### 🔄 年齡 x 性別交叉分析")

    if '年齡' not in df.columns or '性別' not in df.columns:
        st.warning("數據中缺少年齡或性別資訊")
        return

    # 交叉分析統計
    cross_stats = df.groupby(['年齡', '性別']).agg({
        '購買 ROAS（廣告投資報酬率）': 'mean',
        '花費金額 (TWD)': 'sum',
        '購買次數': 'sum',
        '觸及人數': 'sum'
    }).reset_index()

    if cross_stats.empty:
        st.info("暫無交叉分析數據")
        return

    # 計算轉換率
    cross_stats['轉換率 (%)'] = (cross_stats['購買次數'] / cross_stats['觸及人數'] * 100).fillna(0)

    # 創建透視表用於熱力圖
    roas_pivot = cross_stats.pivot(index='年齡', columns='性別', values='購買 ROAS（廣告投資報酬率）')
    conversion_pivot = cross_stats.pivot(index='年齡', columns='性別', values='轉換率 (%)')

    col1, col2 = st.columns(2)

    with col1:
        # ROAS 熱力圖
        fig_roas_heatmap = px.imshow(
            roas_pivot,
            title="ROAS 熱力圖 (年齡 x 性別)",
            color_continuous_scale='RdYlGn',
            aspect="auto",
            text_auto=True
        )
        fig_roas_heatmap.update_layout(height=400)
        st.plotly_chart(fig_roas_heatmap, use_container_width=True)

    with col2:
        # 轉換率熱力圖
        fig_conv_heatmap = px.imshow(
            conversion_pivot,
            title="轉換率熱力圖 (年齡 x 性別)",
            color_continuous_scale='Blues',
            aspect="auto",
            text_auto=True
        )
        fig_conv_heatmap.update_layout(height=400)
        st.plotly_chart(fig_conv_heatmap, use_container_width=True)

    # 交叉分析洞察
    best_combo = cross_stats.loc[cross_stats['購買 ROAS（廣告投資報酬率）'].idxmax()]
    worst_combo = cross_stats.loc[cross_stats['購買 ROAS（廣告投資報酬率）'].idxmin()]

    st.markdown("#### 💡 交叉分析洞察")

    col_cross1, col_cross2 = st.columns(2)

    with col_cross1:
        st.success(f"""
        **🎯 最佳受眾組合**
        - 年齡：{best_combo['年齡']}
        - 性別：{best_combo['性別']}
        - ROAS：{best_combo['購買 ROAS（廣告投資報酬率）']:.2f}
        - 轉換率：{best_combo['轉換率 (%)']:.3f}%
        - 花費：${best_combo['花費金額 (TWD)']:,.0f}
        """)

    with col_cross2:
        st.warning(f"""
        **⚠️ 需優化受眾組合**
        - 年齡：{worst_combo['年齡']}
        - 性別：{worst_combo['性別']}
        - ROAS：{worst_combo['購買 ROAS（廣告投資報酬率）']:.2f}
        - 轉換率：{worst_combo['轉換率 (%)']:.3f}%
        - 花費：${worst_combo['花費金額 (TWD)']:,.0f}
        """)

def show_audience_performance_matrix(df):
    """顯示受眾表現矩陣"""
    st.markdown("### 🎯 受眾表現矩陣分析")

    if '年齡' not in df.columns or '性別' not in df.columns:
        st.warning("數據中缺少完整的受眾資訊")
        return

    # 計算受眾表現矩陣
    audience_matrix = df.groupby(['年齡', '性別']).agg({
        '購買 ROAS（廣告投資報酬率）': 'mean',
        '花費金額 (TWD)': 'sum',
        '購買次數': 'sum',
        '觸及人數': 'sum'
    }).reset_index()

    if audience_matrix.empty:
        st.info("暫無受眾矩陣數據")
        return

    # 計算轉換率
    audience_matrix['轉換率 (%)'] = (audience_matrix['購買次數'] / audience_matrix['觸及人數'] * 100).fillna(0)

    # ROAS vs 花費象限圖
    fig_matrix = px.scatter(
        audience_matrix,
        x='花費金額 (TWD)',
        y='購買 ROAS（廣告投資報酬率）',
        size='購買次數',
        color='轉換率 (%)',
        hover_data=['年齡', '性別'],
        title="受眾表現象限圖 (ROAS vs 花費)",
        labels={
            '花費金額 (TWD)': '花費金額 (TWD)',
            '購買 ROAS（廣告投資報酬率）': 'ROAS',
            '購買次數': '購買次數',
            '轉換率 (%)': '轉換率 (%)'
        },
        color_continuous_scale='RdYlGn'
    )

    # 添加象限分隔線
    avg_spend = audience_matrix['花費金額 (TWD)'].mean()
    avg_roas = audience_matrix['購買 ROAS（廣告投資報酬率）'].mean()

    fig_matrix.add_hline(y=avg_roas, line_dash="dash", line_color="gray", annotation_text="平均 ROAS")
    fig_matrix.add_vline(x=avg_spend, line_dash="dash", line_color="gray", annotation_text="平均花費")

    fig_matrix.update_layout(height=500)
    st.plotly_chart(fig_matrix, use_container_width=True)

    # 象限分析
    st.markdown("#### 📊 象限分析結果")

    # 分類受眾到不同象限
    high_roas_high_spend = audience_matrix[
        (audience_matrix['購買 ROAS（廣告投資報酬率）'] >= avg_roas) &
        (audience_matrix['花費金額 (TWD)'] >= avg_spend)
    ]

    high_roas_low_spend = audience_matrix[
        (audience_matrix['購買 ROAS（廣告投資報酬率）'] >= avg_roas) &
        (audience_matrix['花費金額 (TWD)'] < avg_spend)
    ]

    low_roas_high_spend = audience_matrix[
        (audience_matrix['購買 ROAS（廣告投資報酬率）'] < avg_roas) &
        (audience_matrix['花費金額 (TWD)'] >= avg_spend)
    ]

    low_roas_low_spend = audience_matrix[
        (audience_matrix['購買 ROAS（廣告投資報酬率）'] < avg_roas) &
        (audience_matrix['花費金額 (TWD)'] < avg_spend)
    ]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.success(f"""
        **🌟 明星受眾**
        (高 ROAS + 高花費)

        數量：{len(high_roas_high_spend)} 個
        建議：持續投資，擴大規模
        """)
        if not high_roas_high_spend.empty:
            for _, row in high_roas_high_spend.iterrows():
                st.text(f"• {row['年齡']} {row['性別']}")

    with col2:
        st.info(f"""
        **💎 潛力受眾**
        (高 ROAS + 低花費)

        數量：{len(high_roas_low_spend)} 個
        建議：增加預算投入
        """)
        if not high_roas_low_spend.empty:
            for _, row in high_roas_low_spend.iterrows():
                st.text(f"• {row['年齡']} {row['性別']}")

    with col3:
        st.warning(f"""
        **🔥 燒錢受眾**
        (低 ROAS + 高花費)

        數量：{len(low_roas_high_spend)} 個
        建議：立即優化或暫停
        """)
        if not low_roas_high_spend.empty:
            for _, row in low_roas_high_spend.iterrows():
                st.text(f"• {row['年齡']} {row['性別']}")

    with col4:
        st.error(f"""
        **😴 冷淡受眾**
        (低 ROAS + 低花費)

        數量：{len(low_roas_low_spend)} 個
        建議：暫停或重新定位
        """)
        if not low_roas_low_spend.empty:
            for _, row in low_roas_low_spend.iterrows():
                st.text(f"• {row['年齡']} {row['性別']}")

def show_audience_recommendations(df):
    """顯示受眾建議系統"""
    if '年齡' not in df.columns or '性別' not in df.columns:
        st.warning("數據中缺少完整的受眾資訊")
        return

    # 計算受眾表現
    audience_performance = df.groupby(['年齡', '性別']).agg({
        '購買 ROAS（廣告投資報酬率）': 'mean',
        '花費金額 (TWD)': 'sum',
        '購買次數': 'sum',
        '觸及人數': 'sum',
        'CTR（全部）': 'mean'
    }).reset_index()

    if audience_performance.empty:
        st.info("暫無受眾數據可供分析")
        return

    # 計算轉換率
    audience_performance['轉換率 (%)'] = (audience_performance['購買次數'] / audience_performance['觸及人數'] * 100).fillna(0)

    col1, col2, col3 = st.columns(3)

    with col1:
        # 建議擴展的受眾
        st.markdown("#### 🚀 建議擴展受眾")
        expand_audiences = audience_performance[
            (audience_performance['購買 ROAS（廣告投資報酬率）'] >= 3.0) &
            (audience_performance['花費金額 (TWD)'] >= 1000)
        ].nlargest(3, '購買 ROAS（廣告投資報酬率）')

        if not expand_audiences.empty:
            for _, audience in expand_audiences.iterrows():
                st.success(f"""
                **{audience['年齡']} {audience['性別']}**
                - ROAS: {audience['購買 ROAS（廣告投資報酬率）']:.2f}
                - 花費: ${audience['花費金額 (TWD)']:,.0f}
                - 建議增加預算 50%
                """)
        else:
            st.info("暫無建議擴展的受眾")

    with col2:
        # 建議暫停的受眾
        st.markdown("#### ⏸️ 建議暫停受眾")
        pause_audiences = audience_performance[
            (audience_performance['購買 ROAS（廣告投資報酬率）'] < 1.0) &
            (audience_performance['花費金額 (TWD)'] >= 500)
        ].nsmallest(3, '購買 ROAS（廣告投資報酬率）')

        if not pause_audiences.empty:
            for _, audience in pause_audiences.iterrows():
                st.error(f"""
                **{audience['年齡']} {audience['性別']}**
                - ROAS: {audience['購買 ROAS（廣告投資報酬率）']:.2f}
                - 花費: ${audience['花費金額 (TWD)']:,.0f}
                - 建議暫停投放
                """)
        else:
            st.info("暫無建議暫停的受眾")

    with col3:
        # 建議測試的新受眾
        st.markdown("#### 🧪 建議測試受眾")
        test_audiences = audience_performance[
            (audience_performance['購買 ROAS（廣告投資報酬率）'] >= 2.0) &
            (audience_performance['花費金額 (TWD)'] < 1000)
        ].nlargest(3, 'CTR（全部）')

        if not test_audiences.empty:
            for _, audience in test_audiences.iterrows():
                st.warning(f"""
                **{audience['年齡']} {audience['性別']}**
                - ROAS: {audience['購買 ROAS（廣告投資報酬率）']:.2f}
                - CTR: {audience['CTR（全部）']:.2f}%
                - 建議小額測試
                """)
        else:
            st.info("暫無建議測試的受眾")

    # 預算重分配建議
    st.markdown("#### 💰 預算重分配建議")

    total_budget = df['花費金額 (TWD)'].sum()
    high_performers = audience_performance[audience_performance['購買 ROAS（廣告投資報酬率）'] >= 3.0]
    low_performers = audience_performance[audience_performance['購買 ROAS（廣告投資報酬率）'] < 1.0]

    if not high_performers.empty and not low_performers.empty:
        reallocation_amount = low_performers['花費金額 (TWD)'].sum() * 0.7  # 70% 的低效預算

        st.info(f"""
        **💡 智能預算重分配方案**

        **從低效受眾轉移預算**：${reallocation_amount:,.0f} TWD
        - 低效受眾總花費：${low_performers['花費金額 (TWD)'].sum():,.0f}
        - 建議轉移比例：70%

        **分配到高效受眾**：
        """)

        for _, audience in high_performers.head(3).iterrows():
            allocation = reallocation_amount * (audience['花費金額 (TWD)'] / high_performers['花費金額 (TWD)'].sum())
            st.text(f"• {audience['年齡']} {audience['性別']}：+${allocation:,.0f}")

        expected_roas_improvement = high_performers['購買 ROAS（廣告投資報酬率）'].mean() - 1.0
        st.success(f"預期整體 ROAS 提升：{expected_roas_improvement:.2f}")

def show_audience_trends(df):
    """顯示受眾趨勢分析"""
    if '月' not in df.columns:
        st.warning("數據中缺少時間資訊")
        return

    col1, col2 = st.columns(2)

    with col1:
        # 月份受眾表現變化
        st.markdown("#### 📅 月份受眾表現趨勢")

        if '年齡' in df.columns and '月' in df.columns:
            # 只使用有效的 ROAS 數據
            valid_trend_data = df.dropna(subset=['購買 ROAS（廣告投資報酬率）', '年齡', '月'])
            valid_trend_data = valid_trend_data[valid_trend_data['購買 ROAS（廣告投資報酬率）'] > 0]

            if not valid_trend_data.empty:
                monthly_age_trend = valid_trend_data.groupby(['月', '年齡'])['購買 ROAS（廣告投資報酬率）'].mean().reset_index()

                # 只保留有數據的月份
                monthly_age_trend = monthly_age_trend[monthly_age_trend['購買 ROAS（廣告投資報酬率）'] > 0]

                if not monthly_age_trend.empty and len(monthly_age_trend['月'].unique()) > 1:
                    fig_monthly_age = px.line(
                        monthly_age_trend,
                        x='月',
                        y='購買 ROAS（廣告投資報酬率）',
                        color='年齡',
                        title="年齡層 ROAS 月度趨勢",
                        markers=True
                    )
                    fig_monthly_age.update_layout(height=400)
                    st.plotly_chart(fig_monthly_age, use_container_width=True)
                else:
                    st.info("暫無足夠的月度趨勢數據")
            else:
                st.info("暫無有效的趨勢數據")

    with col2:
        # 受眾疲勞度監控
        st.markdown("#### 😴 受眾疲勞度監控")

        if '頻率' in df.columns:
            fatigue_analysis = df.groupby(['年齡', '性別']).agg({
                '頻率': 'mean',
                'CTR（全部）': 'mean',
                '購買 ROAS（廣告投資報酬率）': 'mean'
            }).reset_index()

            if not fatigue_analysis.empty:
                fig_fatigue = px.scatter(
                    fatigue_analysis,
                    x='頻率',
                    y='CTR（全部）',
                    size='購買 ROAS（廣告投資報酬率）',
                    color='購買 ROAS（廣告投資報酬率）',
                    hover_data=['年齡', '性別'],
                    title="頻率 vs CTR 關係",
                    color_continuous_scale='RdYlGn_r'
                )
                fig_fatigue.update_layout(height=400)
                st.plotly_chart(fig_fatigue, use_container_width=True)

                # 疲勞警報
                high_frequency = fatigue_analysis[fatigue_analysis['頻率'] > 3.0]
                if not high_frequency.empty:
                    st.warning(f"""
                    **⚠️ 高頻率警報**

                    以下受眾群組頻率過高（>3.0）：
                    """)
                    for _, row in high_frequency.iterrows():
                        st.text(f"• {row['年齡']} {row['性別']} - 頻率: {row['頻率']:.1f}")

    # 受眾生命週期分析
    st.markdown("#### 🔄 受眾生命週期分析")

    if '開始' in df.columns and not df['開始'].isna().all():
        # 只使用有效數據計算投放天數
        df_lifecycle = df.dropna(subset=['開始', '購買 ROAS（廣告投資報酬率）']).copy()

        # 如果有結束時間就使用，否則使用分析報告結束時間
        if '結束時間' in df_lifecycle.columns and not df_lifecycle['結束時間'].isna().all():
            df_lifecycle['投放天數'] = (df_lifecycle['結束時間'] - df_lifecycle['開始']).dt.days + 1
        elif '分析報告結束' in df_lifecycle.columns:
            df_lifecycle['投放天數'] = (df_lifecycle['分析報告結束'] - df_lifecycle['開始']).dt.days + 1
        else:
            # 使用預設投放天數
            df_lifecycle['投放天數'] = 1

        # 過濾異常的投放天數
        df_lifecycle = df_lifecycle[
            (df_lifecycle['投放天數'] > 0) &
            (df_lifecycle['投放天數'] <= 365) &
            (df_lifecycle['購買 ROAS（廣告投資報酬率）'] > 0)
        ]

        if not df_lifecycle.empty and '年齡' in df_lifecycle.columns and '性別' in df_lifecycle.columns:
            lifecycle_analysis = df_lifecycle.groupby(['年齡', '性別']).agg({
                '投放天數': 'mean',
                '購買 ROAS（廣告投資報酬率）': 'mean',
                'CTR（全部）': 'mean'
            }).reset_index()

            # 過濾有效數據
            lifecycle_analysis = lifecycle_analysis.dropna()
            lifecycle_analysis = lifecycle_analysis[lifecycle_analysis['購買 ROAS（廣告投資報酬率）'] > 0]

            if not lifecycle_analysis.empty and len(lifecycle_analysis) > 1:
                fig_lifecycle = px.scatter(
                    lifecycle_analysis,
                    x='投放天數',
                    y='購買 ROAS（廣告投資報酬率）',
                    size='CTR（全部）',
                    color='CTR（全部）',
                    hover_data=['年齡', '性別'],
                    title="受眾生命週期 vs ROAS",
                    color_continuous_scale='Blues'
                )
                fig_lifecycle.update_layout(height=400)
                st.plotly_chart(fig_lifecycle, use_container_width=True)
            else:
                st.info("暫無足夠的生命週期數據")

            with st.expander("💡 生命週期洞察"):
                st.markdown("""
                **如何解讀生命週期圖表：**
                - **X軸**：平均投放天數
                - **Y軸**：ROAS 表現
                - **氣泡大小**：CTR 高低

                **最佳實務**：
                - 投放天數過長且 ROAS 下降 = 受眾疲勞
                - 短期高 ROAS = 潛力受眾，值得擴展
                - 長期穩定 ROAS = 核心受眾，持續投資
                """)

if __name__ == "__main__":
    show_audience_insights()