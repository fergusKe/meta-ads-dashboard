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

def show_quality_score_analysis():
    """顯示廣告品質評分分析頁面"""
    st.markdown("# 📈 廣告品質評分")
    st.markdown("深度分析廣告品質排名、識別低分預警並挖掘高品質廣告特徵")

    # 載入數據
    df = load_meta_ads_data()
    if df is None or df.empty:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    # 檢查品質相關欄位
    quality_columns = ['品質排名', '互動率排名', '轉換率排名']
    if not all(col in df.columns for col in quality_columns):
        st.error("數據缺少品質排名欄位")
        return

    st.info("""
    💡 **品質排名說明**：Meta 會評估廣告的品質、互動率和轉換率排名。
    - **平均以上**：廣告表現優於大多數競爭對手
    - **平均**：廣告表現與市場平均水平相當
    - **平均以下**：廣告需要優化
    - **未知**：數據不足或 Meta 未提供評分
    """)

    # 篩選有品質評分的數據（排除「未知」）
    quality_df = df[
        (df['品質排名'] != '未知') |
        (df['互動率排名'] != '未知') |
        (df['轉換率排名'] != '未知')
    ].copy()

    st.markdown(f"📊 共 {len(quality_df)} 筆有品質評分的記錄（佔總數 {len(quality_df)/len(df)*100:.1f}%）")

    st.markdown("---")

    # ========== 第一部分：品質排名儀表板 ==========
    st.markdown("## 🏆 品質排名儀表板")

    rank_col1, rank_col2, rank_col3 = st.columns(3)

    # 定義顏色映射
    color_map = {
        '平均以上': '#2ecc71',
        '平均': '#f39c12',
        '平均以下': '#e74c3c',
        '未知': '#95a5a6'
    }

    with rank_col1:
        # 品質排名分布
        quality_dist = df['品質排名'].value_counts()
        fig_quality = go.Figure(data=[go.Pie(
            labels=quality_dist.index,
            values=quality_dist.values,
            hole=0.4,
            marker=dict(colors=[color_map.get(label, '#95a5a6') for label in quality_dist.index])
        )])
        fig_quality.update_layout(
            title="品質排名分布",
            height=300,
            showlegend=True
        )
        st.plotly_chart(fig_quality, use_container_width=True)

        # 顯示佔比
        if '平均以上' in quality_dist.index:
            st.metric("平均以上佔比", f"{quality_dist['平均以上']/quality_dist.sum()*100:.1f}%")

    with rank_col2:
        # 互動率排名分布
        engagement_dist = df['互動率排名'].value_counts()
        fig_engagement = go.Figure(data=[go.Pie(
            labels=engagement_dist.index,
            values=engagement_dist.values,
            hole=0.4,
            marker=dict(colors=[color_map.get(label, '#95a5a6') for label in engagement_dist.index])
        )])
        fig_engagement.update_layout(
            title="互動率排名分布",
            height=300,
            showlegend=True
        )
        st.plotly_chart(fig_engagement, use_container_width=True)

        if '平均以上' in engagement_dist.index:
            st.metric("平均以上佔比", f"{engagement_dist['平均以上']/engagement_dist.sum()*100:.1f}%")

    with rank_col3:
        # 轉換率排名分布
        conversion_dist = df['轉換率排名'].value_counts()
        fig_conversion = go.Figure(data=[go.Pie(
            labels=conversion_dist.index,
            values=conversion_dist.values,
            hole=0.4,
            marker=dict(colors=[color_map.get(label, '#95a5a6') for label in conversion_dist.index])
        )])
        fig_conversion.update_layout(
            title="轉換率排名分布",
            height=300,
            showlegend=True
        )
        st.plotly_chart(fig_conversion, use_container_width=True)

        if '平均以上' in conversion_dist.index:
            st.metric("平均以上佔比", f"{conversion_dist['平均以上']/conversion_dist.sum()*100:.1f}%")

    # 綜合品質評分
    if '綜合品質分數' in df.columns:
        st.markdown("### 📊 綜合品質評分分布")

        score_df = df[df['綜合品質分數'] > 0].copy()

        if not score_df.empty:
            fig_score_dist = px.histogram(
                score_df,
                x='綜合品質分數',
                nbins=30,
                title="綜合品質分數分布（0-3分，轉換率權重50%）",
                labels={'綜合品質分數': '綜合品質分數'},
                color_discrete_sequence=['#3498db']
            )
            fig_score_dist.update_layout(height=350)
            st.plotly_chart(fig_score_dist, use_container_width=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("平均分數", f"{score_df['綜合品質分數'].mean():.2f}")
            with col2:
                st.metric("中位數", f"{score_df['綜合品質分數'].median():.2f}")
            with col3:
                st.metric("最高分", f"{score_df['綜合品質分數'].max():.2f}")

    # 品質趨勢（按月）
    if '年月' in df.columns:
        st.markdown("### 📅 品質趨勢（按月）")

        monthly_quality = df.groupby('年月').agg({
            '品質排名_分數': 'mean',
            '互動率排名_分數': 'mean',
            '轉換率排名_分數': 'mean',
            '綜合品質分數': 'mean'
        }).reset_index()

        fig_trend = go.Figure()

        fig_trend.add_trace(go.Scatter(
            name='品質排名',
            x=monthly_quality['年月'],
            y=monthly_quality['品質排名_分數'],
            mode='lines+markers',
            line=dict(width=2, color='#3498db')
        ))

        fig_trend.add_trace(go.Scatter(
            name='互動率排名',
            x=monthly_quality['年月'],
            y=monthly_quality['互動率排名_分數'],
            mode='lines+markers',
            line=dict(width=2, color='#2ecc71')
        ))

        fig_trend.add_trace(go.Scatter(
            name='轉換率排名',
            x=monthly_quality['年月'],
            y=monthly_quality['轉換率排名_分數'],
            mode='lines+markers',
            line=dict(width=2, color='#e74c3c')
        ))

        fig_trend.add_trace(go.Scatter(
            name='綜合品質分數',
            x=monthly_quality['年月'],
            y=monthly_quality['綜合品質分數'],
            mode='lines+markers',
            line=dict(width=3, color='#9b59b6', dash='dash')
        ))

        fig_trend.update_layout(
            title="各品質指標月度趨勢",
            xaxis_title="月份",
            yaxis_title="平均分數",
            hovermode='x unified',
            height=400
        )

        st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown("---")

    # ========== 第二部分：低分廣告預警 ==========
    st.markdown("## ⚠️ 低分廣告預警")

    # 找出「平均以下」的廣告
    low_quality_ads = df[
        (df['品質排名'] == '平均以下') |
        (df['互動率排名'] == '平均以下') |
        (df['轉換率排名'] == '平均以下')
    ].copy()

    if not low_quality_ads.empty:
        st.warning(f"🚨 發現 {len(low_quality_ads)} 筆低分廣告（至少一項排名為「平均以下」）")

        # 按廣告聚合
        low_ads_summary = low_quality_ads.groupby('廣告名稱').agg({
            '品質排名': lambda x: x.mode()[0] if not x.empty else '未知',
            '互動率排名': lambda x: x.mode()[0] if not x.empty else '未知',
            '轉換率排名': lambda x: x.mode()[0] if not x.empty else '未知',
            '花費金額 (TWD)': 'sum',
            'CTR（全部）': 'mean',
            '購買 ROAS（廣告投資報酬率）': 'mean',
            '綜合品質分數': 'mean'
        }).reset_index()

        # 計算低分項目數
        low_ads_summary['低分項目數'] = (
            (low_ads_summary['品質排名'] == '平均以下').astype(int) +
            (low_ads_summary['互動率排名'] == '平均以下').astype(int) +
            (low_ads_summary['轉換率排名'] == '平均以下').astype(int)
        )

        # 排序：優先顯示低分項目多且花費高的
        low_ads_summary = low_ads_summary.sort_values(
            ['低分項目數', '花費金額 (TWD)'],
            ascending=[False, False]
        ).head(20)

        st.dataframe(
            low_ads_summary,
            use_container_width=True,
            column_config={
                "廣告名稱": "廣告",
                "品質排名": "品質",
                "互動率排名": "互動率",
                "轉換率排名": "轉換率",
                "低分項目數": st.column_config.NumberColumn("低分項目", format="%d"),
                "花費金額 (TWD)": st.column_config.NumberColumn("總花費", format="%d"),
                "CTR（全部）": st.column_config.NumberColumn("CTR (%)", format="%.2f"),
                "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
                "綜合品質分數": st.column_config.NumberColumn("綜合分數", format="%.2f")
            }
        )

        # 低分原因分析
        st.markdown("### 🔍 低分原因分析")

        reason_col1, reason_col2 = st.columns(2)

        with reason_col1:
            # 低分項目統計
            low_count = pd.DataFrame({
                '評分項目': ['品質排名', '互動率排名', '轉換率排名'],
                '低分數量': [
                    (low_quality_ads['品質排名'] == '平均以下').sum(),
                    (low_quality_ads['互動率排名'] == '平均以下').sum(),
                    (low_quality_ads['轉換率排名'] == '平均以下').sum()
                ]
            })

            fig_low_count = px.bar(
                low_count,
                x='評分項目',
                y='低分數量',
                title="各項目低分數量",
                color='低分數量',
                color_continuous_scale='Reds',
                text='低分數量'
            )
            fig_low_count.update_traces(textposition='outside')
            fig_low_count.update_layout(height=350)
            st.plotly_chart(fig_low_count, use_container_width=True)

        with reason_col2:
            # 低分廣告的成效對比
            avg_metrics = df.agg({
                'CTR（全部）': 'mean',
                '購買 ROAS（廣告投資報酬率）': 'mean',
                '每次購買的成本': 'mean'
            })

            low_metrics = low_quality_ads.agg({
                'CTR（全部）': 'mean',
                '購買 ROAS（廣告投資報酬率）': 'mean',
                '每次購買的成本': 'mean'
            })

            comparison_df = pd.DataFrame({
                '指標': ['CTR (%)', 'ROAS', 'CPA'],
                '低分廣告': [low_metrics['CTR（全部）'], low_metrics['購買 ROAS（廣告投資報酬率）'], low_metrics['每次購買的成本']],
                '整體平均': [avg_metrics['CTR（全部）'], avg_metrics['購買 ROAS（廣告投資報酬率）'], avg_metrics['每次購買的成本']]
            })

            fig_comparison = go.Figure()

            fig_comparison.add_trace(go.Bar(
                name='低分廣告',
                x=comparison_df['指標'],
                y=comparison_df['低分廣告'],
                marker_color='#e74c3c'
            ))

            fig_comparison.add_trace(go.Bar(
                name='整體平均',
                x=comparison_df['指標'],
                y=comparison_df['整體平均'],
                marker_color='#3498db'
            ))

            fig_comparison.update_layout(
                title="低分廣告 vs 整體平均成效",
                barmode='group',
                height=350
            )

            st.plotly_chart(fig_comparison, use_container_width=True)

        # 具體改善方向
        st.markdown("### 💡 改善方向")

        improve_col1, improve_col2, improve_col3 = st.columns(3)

        with improve_col1:
            st.error("""
**品質排名低**

可能原因：
- 廣告素材品質不佳
- 隱藏資訊或誤導內容
- 用戶反饋負面

改善方向：
✅ 使用高解析度圖片/影片
✅ 確保文案真實準確
✅ 改善著陸頁體驗
            """)

        with improve_col2:
            st.error("""
**互動率排名低**

可能原因：
- 素材不吸引人
- 目標受眾不精準
- CTA 不明確

改善方向：
✅ 測試不同素材風格
✅ 重新定義受眾
✅ 優化標題和文案
            """)

        with improve_col3:
            st.error("""
**轉換率排名低**

可能原因：
- 著陸頁與廣告不符
- 價格不具競爭力
- 結帳流程複雜

改善方向：
✅ 優化著陸頁一致性
✅ 調整價格策略
✅ 簡化購買流程
            """)

    else:
        st.success("✅ 太棒了！目前沒有「平均以下」的廣告")

    st.markdown("---")

    # ========== 第三部分：高品質廣告特徵 ==========
    st.markdown("## 🎯 高品質廣告特徵")

    # 找出三項排名都是「平均以上」的廣告
    high_quality_ads = df[
        (df['品質排名'] == '平均以上') &
        (df['互動率排名'] == '平均以上') &
        (df['轉換率排名'] == '平均以上')
    ].copy()

    if not high_quality_ads.empty:
        st.success(f"🌟 發現 {len(high_quality_ads)} 筆「三星品質」廣告（三項排名皆為「平均以上」）")

        # 高品質廣告成效
        high_summary = high_quality_ads.groupby('行銷活動名稱').agg({
            '花費金額 (TWD)': 'sum',
            '購買次數': 'sum',
            '購買 ROAS（廣告投資報酬率）': 'mean',
            'CTR（全部）': 'mean',
            '每次購買的成本': 'mean',
            '廣告名稱': 'count'
        }).reset_index()

        high_summary.columns = ['行銷活動名稱', '花費', '購買次數', '平均 ROAS', '平均 CTR', '平均 CPA', '廣告數']
        high_summary = high_summary.sort_values('平均 ROAS', ascending=False).head(10)

        st.dataframe(
            high_summary,
            use_container_width=True,
            column_config={
                "行銷活動名稱": "活動名稱",
                "花費": st.column_config.NumberColumn("花費", format="%d"),
                "購買次數": st.column_config.NumberColumn("購買", format="%d"),
                "平均 ROAS": st.column_config.NumberColumn("ROAS", format="%.2f"),
                "平均 CTR": st.column_config.NumberColumn("CTR (%)", format="%.2f"),
                "平均 CPA": st.column_config.NumberColumn("CPA", format="%.0f"),
                "廣告數": st.column_config.NumberColumn("廣告數", format="%d")
            }
        )

        # 高品質廣告特徵分析
        st.markdown("### 🔍 共同特徵分析")

        feature_col1, feature_col2 = st.columns(2)

        with feature_col1:
            # 受眾分析
            if '年齡' in high_quality_ads.columns and '性別' in high_quality_ads.columns:
                audience_analysis = high_quality_ads.groupby(['年齡', '性別']).agg({
                    '購買 ROAS（廣告投資報酬率）': 'mean',
                    '廣告名稱': 'count'
                }).reset_index()

                audience_analysis = audience_analysis.sort_values('購買 ROAS（廣告投資報酬率）', ascending=False).head(10)

                fig_audience = px.bar(
                    audience_analysis,
                    x='年齡',
                    y='購買 ROAS（廣告投資報酬率）',
                    color='性別',
                    title="高品質廣告 - 最佳受眾組合",
                    barmode='group',
                    text='購買 ROAS（廣告投資報酬率）'
                )
                fig_audience.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                fig_audience.update_layout(height=400)
                st.plotly_chart(fig_audience, use_container_width=True)

        with feature_col2:
            # 出價策略分析
            if '出價類型' in high_quality_ads.columns:
                bid_analysis = high_quality_ads.groupby('出價類型').agg({
                    '購買 ROAS（廣告投資報酬率）': 'mean',
                    '花費金額 (TWD)': 'sum',
                    '廣告名稱': 'count'
                }).reset_index()

                bid_analysis = bid_analysis.sort_values('購買 ROAS（廣告投資報酬率）', ascending=False)

                fig_bid = px.pie(
                    bid_analysis,
                    values='花費金額 (TWD)',
                    names='出價類型',
                    title="高品質廣告 - 出價策略分布",
                    hole=0.4
                )
                fig_bid.update_layout(height=400)
                st.plotly_chart(fig_bid, use_container_width=True)

        # 可複製的成功模式
        st.markdown("### ✅ 可複製的成功模式")

        # 計算高品質廣告的平均指標
        high_avg = high_quality_ads.agg({
            'CTR（全部）': 'mean',
            '購買 ROAS（廣告投資報酬率）': 'mean',
            '每次購買的成本': 'mean',
            '頻率': 'mean'
        })

        pattern_col1, pattern_col2 = st.columns(2)

        with pattern_col1:
            st.success(f"""
**📊 高品質廣告平均指標**

- CTR：{high_avg['CTR（全部）']:.2f}%
- ROAS：{high_avg['購買 ROAS（廣告投資報酬率）']:.2f}
- CPA：{high_avg['每次購買的成本']:.0f} TWD
- 頻率：{high_avg['頻率']:.2f}
            """)

        with pattern_col2:
            # 找出最常見的受眾和出價組合
            if '年齡' in high_quality_ads.columns and '出價類型' in high_quality_ads.columns:
                best_age = high_quality_ads['年齡'].mode()[0] if not high_quality_ads['年齡'].mode().empty else '未知'
                best_bid = high_quality_ads['出價類型'].mode()[0] if not high_quality_ads['出價類型'].mode().empty else '未知'

                st.info(f"""
**🎯 最佳組合推薦**

- 最常見年齡層：{best_age}
- 最常見出價策略：{best_bid}
- 建議頻率上限：{high_avg['頻率']:.0f}-{high_avg['頻率']*1.5:.0f}

**複製步驟**：
1. 使用類似的受眾設定
2. 採用相同的出價策略
3. 參考高 ROAS 的素材風格
4. 控制頻率避免過度曝光
                """)

    else:
        st.warning("⚠️ 目前沒有「三星品質」廣告，建議參考「平均以上」廣告的特徵")

    st.markdown("---")

    # ========== 第四部分：品質 vs 成效關聯 ==========
    st.markdown("## 📊 品質 vs 成效關聯")

    if '綜合品質分數' in df.columns:
        score_df = df[df['綜合品質分數'] > 0].copy()

        if not score_df.empty:
            scatter_col1, scatter_col2 = st.columns(2)

            with scatter_col1:
                # 品質分數 vs ROAS
                fig_quality_roas = px.scatter(
                    score_df,
                    x='綜合品質分數',
                    y='購買 ROAS（廣告投資報酬率）',
                    color='品質排名',
                    size='花費金額 (TWD)',
                    hover_data=['行銷活動名稱', '廣告組合名稱'],
                    title="品質分數 vs ROAS",
                    color_discrete_map=color_map
                )
                fig_quality_roas.add_hline(
                    y=score_df['購買 ROAS（廣告投資報酬率）'].mean(),
                    line_dash="dash",
                    line_color="gray",
                    annotation_text=f"平均 ROAS: {score_df['購買 ROAS（廣告投資報酬率）'].mean():.2f}"
                )
                fig_quality_roas.update_layout(height=450)
                st.plotly_chart(fig_quality_roas, use_container_width=True)

            with scatter_col2:
                # 轉換率排名 vs CPA
                fig_conversion_cpa = px.scatter(
                    score_df,
                    x='轉換率排名_分數',
                    y='每次購買的成本',
                    color='轉換率排名',
                    size='購買次數',
                    hover_data=['行銷活動名稱', '廣告組合名稱'],
                    title="轉換率排名分數 vs CPA",
                    color_discrete_map=color_map
                )
                fig_conversion_cpa.add_hline(
                    y=score_df['每次購買的成本'].median(),
                    line_dash="dash",
                    line_color="gray",
                    annotation_text=f"CPA 中位數: {score_df['每次購買的成本'].median():.0f}"
                )
                fig_conversion_cpa.update_layout(height=450)
                st.plotly_chart(fig_conversion_cpa, use_container_width=True)

            # 互動率排名 vs 購買率
            st.markdown("### 📈 互動率排名 vs 轉換表現")

            engagement_perf = score_df.groupby('互動率排名').agg({
                '購買次數': 'sum',
                '觸及人數': 'sum',
                'CTR（全部）': 'mean',
                '購買 ROAS（廣告投資報酬率）': 'mean'
            }).reset_index()

            engagement_perf['轉換率'] = (engagement_perf['購買次數'] / engagement_perf['觸及人數'] * 100).round(2)

            fig_engagement_conv = go.Figure()

            fig_engagement_conv.add_trace(go.Bar(
                name='平均 CTR',
                x=engagement_perf['互動率排名'],
                y=engagement_perf['CTR（全部）'],
                marker_color='#3498db',
                yaxis='y'
            ))

            fig_engagement_conv.add_trace(go.Scatter(
                name='轉換率',
                x=engagement_perf['互動率排名'],
                y=engagement_perf['轉換率'],
                mode='lines+markers',
                marker=dict(size=12, color='#e74c3c'),
                line=dict(width=3),
                yaxis='y2'
            ))

            fig_engagement_conv.update_layout(
                title="互動率排名 vs CTR & 轉換率",
                xaxis_title="互動率排名",
                yaxis=dict(title='平均 CTR (%)', side='left'),
                yaxis2=dict(title='轉換率 (%)', side='right', overlaying='y'),
                hovermode='x unified',
                height=400
            )

            st.plotly_chart(fig_engagement_conv, use_container_width=True)

    st.markdown("---")

    # ========== 第五部分：優化建議總結 ==========
    st.markdown("## 💡 品質優化建議總結")

    summary_col1, summary_col2 = st.columns(2)

    with summary_col1:
        st.success("""
**✅ 提升品質排名**

1. **素材品質**：
   - 使用高解析度圖片/影片
   - 確保文案清晰準確
   - 避免誤導或隱藏資訊

2. **用戶體驗**：
   - 優化著陸頁載入速度
   - 確保行動裝置友善
   - 簡化購買流程

3. **相關性**：
   - 廣告與著陸頁內容一致
   - 精準定位目標受眾
   - 使用相關關鍵字
        """)

    with summary_col2:
        st.success("""
**✅ 提升互動率與轉換率**

1. **互動率優化**：
   - 測試吸引人的標題
   - 使用明確的 CTA
   - 嘗試不同素材風格

2. **轉換率優化**：
   - 優化價格與優惠策略
   - 提供清晰的產品資訊
   - 建立信任感（評價、保證）

3. **持續測試**：
   - A/B 測試不同組合
   - 監控品質趨勢變化
   - 快速調整低分廣告
        """)

if __name__ == "__main__":
    show_quality_score_analysis()
