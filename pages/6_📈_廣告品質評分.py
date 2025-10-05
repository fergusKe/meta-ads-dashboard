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
    get_sorted_ad_options,
    format_ad_display_name,
    display_ad_performance_table,
    get_ad_details_for_analysis
)
from utils.llm_service import get_llm_service
import json

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

        # 添加廣告階層顯示
        low_quality_ads['廣告階層'] = low_quality_ads.apply(format_ad_display_name, axis=1)

        # 計算低分項目數
        low_quality_ads['低分項目數'] = (
            (low_quality_ads['品質排名'] == '平均以下').astype(int) +
            (low_quality_ads['互動率排名'] == '平均以下').astype(int) +
            (low_quality_ads['轉換率排名'] == '平均以下').astype(int)
        )

        # 排序並限制顯示數量
        low_quality_sorted = low_quality_ads.sort_values(
            ['低分項目數', '花費金額 (TWD)'],
            ascending=[False, False]
        ).head(20)

        # 顯示低分廣告表格
        st.dataframe(
            low_quality_sorted[[
                '廣告階層', '品質排名', '互動率排名', '轉換率排名',
                '低分項目數', '花費金額 (TWD)', 'CTR（全部）',
                '購買 ROAS（廣告投資報酬率）', '綜合品質分數'
            ]],
            use_container_width=True,
            column_config={
                "廣告階層": "廣告",
                "品質排名": "品質",
                "互動率排名": "互動率",
                "轉換率排名": "轉換率",
                "低分項目數": st.column_config.NumberColumn("低分項目", format="%d"),
                "花費金額 (TWD)": st.column_config.NumberColumn("總花費", format="$%d"),
                "CTR（全部）": st.column_config.NumberColumn("CTR (%)", format="%.2f"),
                "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
                "綜合品質分數": st.column_config.NumberColumn("綜合分數", format="%.2f")
            },
            hide_index=True
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

    # AI 改善計劃生成
    if not low_quality_ads.empty:
        st.markdown("### 🤖 AI 品質改善計劃")

        if st.button("🔍 為低分廣告生成 AI 改善計劃", key="quality_ai_plan"):
            with st.spinner("AI 正在分析低分廣告並生成改善計劃..."):
                try:
                    # 初始化 LLM 服務
                    llm_service = LLMService()

                    # 分析低分廣告的共同問題
                    quality_issues = (low_quality_ads['品質排名'] == '平均以下').sum()
                    engagement_issues = (low_quality_ads['互動率排名'] == '平均以下').sum()
                    conversion_issues = (low_quality_ads['轉換率排名'] == '平均以下').sum()

                    # 獲取平均指標
                    avg_roas = low_quality_ads['購買 ROAS（廣告投資報酬率）'].mean()
                    avg_ctr = low_quality_ads['CTR（全部）'].mean()
                    total_spend = low_quality_ads['花費金額 (TWD)'].sum()

                    # 對比高品質廣告
                    high_quality_comparison = ""
                    high_quality_ads_temp = df[
                        (df['品質排名'] == '平均以上') &
                        (df['互動率排名'] == '平均以上') &
                        (df['轉換率排名'] == '平均以上')
                    ]

                    if not high_quality_ads_temp.empty:
                        high_avg_roas = high_quality_ads_temp['購買 ROAS（廣告投資報酬率）'].mean()
                        high_avg_ctr = high_quality_ads_temp['CTR（全部）'].mean()
                        high_quality_comparison = f"""
**高品質廣告對比**：
- 高品質平均 ROAS：{high_avg_roas:.2f}（低分廣告：{avg_roas:.2f}）
- 高品質平均 CTR：{high_avg_ctr:.2f}%（低分廣告：{avg_ctr:.2f}%）
- ROAS 差距：{((high_avg_roas - avg_roas) / avg_roas * 100):.1f}%
"""

                    # 構建 Prompt
                    prompt = f"""
你是一位專業的 Meta 廣告品質優化專家，請為以下低品質廣告制定改善計劃：

**低品質廣告現況**：
- 低分廣告數：{len(low_quality_ads)} 個
- 總花費：${total_spend:,.0f}
- 平均 ROAS：{avg_roas:.2f}
- 平均 CTR：{avg_ctr:.2f}%

**問題分布**：
- 品質排名低：{quality_issues} 個
- 互動率排名低：{engagement_issues} 個
- 轉換率排名低：{conversion_issues} 個

{high_quality_comparison}

請提供：

1. **根本問題診斷**
   - 分析為什麼這些廣告品質低
   - 最嚴重的 3 個問題
   - 每個問題背後的根本原因

2. **30天改善計劃**（分3個階段）

   **第 1-10 天（快速修復）**：
   - 具體行動（3-5 項）
   - 預期改善：品質排名提升到「平均」
   - 檢查指標

   **第 11-20 天（深度優化）**：
   - 具體行動（3-5 項）
   - 預期改善：ROAS 提升 20-30%
   - 檢查指標

   **第 21-30 天（系統性提升）**：
   - 具體行動（3-5 項）
   - 預期改善：達到「平均以上」
   - 檢查指標

3. **立即可執行的 5 個行動**
   - 每個行動只需 30 分鐘內完成
   - 標註優先級（P0/P1/P2）
   - 預期立即效果

4. **資源需求評估**
   - 需要的預算（如需額外素材）
   - 需要的時間投入
   - 需要的人力配置

請使用繁體中文，語氣專業但易懂。格式使用 Markdown，重點使用粗體標註。提供的行動方案要具體、可執行。
"""

                    # 調用 LLM
                    analysis = llm_service.generate_insights(
                        prompt=prompt,
                        model="gpt-3.5-turbo",
                        max_tokens=2000,
                        temperature=0.7
                    )

                    # 顯示分析結果
                    st.success("✅ AI 改善計劃生成完成")
                    st.markdown(analysis)

                    # 額外建議
                    st.info(f"""
💡 **執行建議**：
1. **立即執行「立即可執行的 5 個行動」**（今天就開始）
2. **設定每週檢查點**：每週五檢查進度
3. **記錄改善效果**：建立改善追蹤表格
4. **持續監控**：使用本頁面追蹤品質排名變化

**潛在 ROI**：
- 如果 ROAS 提升 30%：額外營收約 ${total_spend * avg_roas * 0.3:,.0f}
- 如果品質提升到「平均以上」：CTR 可能提升 20-40%

**成本估算**：API 調用成本約 $0.01 USD
                    """)

                except Exception as e:
                    st.error(f"""
**❌ AI 分析失敗**

錯誤訊息：{str(e)}

可能原因：
- OpenAI API Key 未設定或無效
- API 配額不足
- 網路連線問題

請檢查 .env 檔案中的 OPENAI_API_KEY 設定。
                    """)

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

        # 添加廣告階層顯示
        high_quality_ads['廣告階層'] = high_quality_ads.apply(format_ad_display_name, axis=1)

        # 使用 display_top_bottom_ads 顯示品質對比
        st.markdown("### 📊 品質對比：Top 10 vs Bottom 10")

        # 顯示所有有品質評分的廣告對比
        if '綜合品質分數' in quality_df.columns:
            display_top_bottom_ads(
                quality_df,
                metric='綜合品質分數',
                top_n=10
            )

        # 顯示三星品質廣告詳細表格
        st.markdown("### 🌟 三星品質廣告詳情")
        display_ad_performance_table(
            high_quality_ads,
            title="",
            sort_by='roas',
            top_n=20,
            columns=[
                '廣告階層', '品質排名', '互動率排名', '轉換率排名',
                '綜合品質分數', '花費金額 (TWD)', 'CTR（全部）',
                '購買 ROAS（廣告投資報酬率）', '購買次數'
            ]
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

    # ========== 第五部分：查看特定廣告的品質詳情 ==========
    st.markdown("## 🔍 查看特定廣告的品質詳情")

    # 讓用戶選擇低品質廣告進行深入分析
    if not low_quality_ads.empty:
        st.markdown("### ⚠️ 選擇低品質廣告查看詳情與改善建議")

        # 使用 get_sorted_ad_options 生成選項
        option_labels, data_map = get_sorted_ad_options(
            low_quality_ads,
            sort_by='custom',
            custom_sort_columns=['低分項目數', '花費金額 (TWD)'],
            custom_sort_ascending=[False, False],
            top_n=30
        )

        selected_ad = st.selectbox(
            "選擇要分析的低品質廣告",
            options=option_labels,
            help="已按「低分項目數」和「花費金額」排序，優先顯示最需要改善的廣告"
        )

        if selected_ad:
            ad_data = data_map[selected_ad]

            # 顯示廣告基本資訊
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**廣告階層**：{ad_data.get('廣告階層', '未知')}")
                st.markdown(f"**品質排名**：{ad_data.get('品質排名', '未知')}")
                st.markdown(f"**互動率排名**：{ad_data.get('互動率排名', '未知')}")
                st.markdown(f"**轉換率排名**：{ad_data.get('轉換率排名', '未知')}")

            with col2:
                roas = ad_data.get('購買 ROAS（廣告投資報酬率）', 0)
                cpa = ad_data.get('每次購買的成本', 0)
                ctr = ad_data.get('CTR（全部）', 0)
                quality_score = ad_data.get('綜合品質分數', 0)

                st.metric("ROAS", f"{roas:.2f}")
                st.metric("CPA", f"${cpa:.0f}")
                st.metric("CTR", f"{ctr:.2f}%")
                st.metric("綜合品質分數", f"{quality_score:.2f}")

            with col3:
                spend = ad_data.get('花費金額 (TWD)', 0)
                purchases = ad_data.get('購買次數', 0)
                impressions = ad_data.get('曝光次數', 0)
                frequency = ad_data.get('頻率', 0)

                st.metric("花費", f"${spend:,.0f}")
                st.metric("購買次數", f"{purchases:.0f}")
                st.metric("曝光次數", f"{impressions:,.0f}")
                st.metric("頻率", f"{frequency:.2f}")

            # 顯示受眾和素材資訊
            st.markdown("### 📋 受眾與素材資訊")

            detail_col1, detail_col2 = st.columns(2)

            with detail_col1:
                st.markdown("**受眾資訊**")
                st.markdown(f"- 年齡：{ad_data.get('年齡', '未知')}")
                st.markdown(f"- 性別：{ad_data.get('性別', '未知')}")
                st.markdown(f"- 地區：{ad_data.get('地區', '未知')}")
                st.markdown(f"- 出價類型：{ad_data.get('出價類型', '未知')}")

            with detail_col2:
                st.markdown("**廣告素材**")
                headline = ad_data.get('headline', '未知')
                cta = ad_data.get('call_to_action_type', '未知')
                st.markdown(f"- Headline：{headline[:50]}..." if len(str(headline)) > 50 else f"- Headline：{headline}")
                st.markdown(f"- CTA：{cta}")

                if '內文' in ad_data and pd.notna(ad_data.get('內文')):
                    body = str(ad_data.get('內文', ''))
                    st.text_area("內文", value=body[:200], disabled=True, height=100)

            # 品質問題診斷與改善建議
            st.markdown("### 💡 品質問題診斷與改善建議")

            low_score_count = ad_data.get('低分項目數', 0)

            if low_score_count >= 3:
                st.error(f"""
**🚨 嚴重警告：三項品質指標皆低於平均**

這個廣告在品質、互動率、轉換率三方面都需要立即改善，建議：

**立即行動**：
1. **暫停或降低預算**：避免浪費更多廣告費用
2. **全面檢視素材**：圖片、文案、著陸頁是否有問題
3. **重新定位受眾**：當前受眾可能完全不適合此產品

**改善步驟**：
- 參考高品質廣告（三星品質）的素材風格
- 檢查著陸頁與廣告一致性
- 測試不同的受眾組合
- 確保廣告內容真實、無誤導

**預期成效**：完整改善後，ROAS 可望提升 50-100%
                """)

            elif ad_data.get('品質排名') == '平均以下':
                st.warning(f"""
**⚠️ 品質排名低**

可能原因：
- 廣告素材品質不佳（圖片模糊、文案錯誤）
- 廣告內容與著陸頁不一致
- 用戶反饋負面（隱藏按鈕、誤導資訊）

**改善建議**：
1. 使用高解析度圖片/影片（至少 1080p）
2. 確保文案清晰、準確、無誤導
3. 檢查著陸頁載入速度（< 3 秒）
4. 確保行動裝置友善體驗
5. 移除任何隱藏或誤導性內容

**預期時間**：1-2 週見效
**預期改善**：品質排名提升至「平均」或「平均以上」
                """)

            elif ad_data.get('互動率排名') == '平均以下':
                st.warning(f"""
**⚠️ 互動率排名低**

可能原因：
- 素材不吸引目標受眾
- Headline 不夠吸引人
- CTA 不明確或不吸引人

**改善建議**：
1. 測試不同 Headline（參考高 ROAS 廣告）
2. 使用更強烈的 CTA（如「立即購買」、「限時優惠」）
3. 測試不同素材風格（圖片 vs 影片、明亮 vs 深色）
4. A/B 測試受眾組合
5. 參考當前 CTR：{ctr:.2f}%，目標提升至 2-3%

**預期時間**：1 週見效
**預期改善**：CTR 提升 30-50%
                """)

            elif ad_data.get('轉換率排名') == '平均以下':
                st.warning(f"""
**⚠️ 轉換率排名低**

可能原因：
- 著陸頁與廣告不一致
- 價格不具競爭力或不清楚
- 結帳流程複雜
- 缺乏信任元素

**改善建議**：
1. 確保著陸頁與廣告訊息完全一致
2. 優化價格顯示與優惠策略
3. 簡化結帳流程（減少步驟、提供多種支付方式）
4. 增加信任元素（客戶評價、保證、安全認證）
5. 當前 CPA：${cpa:.0f}，目標降低至 ${cpa*0.7:.0f}

**預期時間**：2-3 週見效（需要著陸頁改善）
**預期改善**：轉換率提升 20-40%，CPA 降低 20-30%
                """)

    st.markdown("---")

    # ========== 第六部分：優化建議總結 ==========
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

    st.markdown("---")

    # ========== 第七部分：AI 品質改善計畫 ==========
    st.markdown("## 🤖 AI 品質改善計畫")
    st.info("💡 讓 AI 為所有低品質廣告生成個別化的改善計畫")

    if st.button("🚀 生成 AI 改善計畫", type="primary", use_container_width=True):
        if not low_quality_ads.empty:
            with st.spinner("AI 正在為低品質廣告生成改善計畫..."):
                ai_plan = generate_ai_quality_improvement_plan(df, low_quality_ads, high_quality_ads)

                if ai_plan and not ai_plan.startswith("❌") and not ai_plan.startswith("⚠️"):
                    st.markdown("### 📊 AI 改善計畫")
                    st.markdown(ai_plan)
                else:
                    st.error(ai_plan if ai_plan else "AI 分析失敗")
        else:
            st.success("🎉 目前沒有低品質廣告需要改善！")


def generate_ai_quality_improvement_plan(all_ads, low_quality_ads, high_quality_ads):
    """
    生成 AI 品質改善計畫

    分析低品質廣告與高品質廣告的差異，
    為每個低品質廣告類型提供具體的改善計畫
    """
    llm_service = get_llm_service()

    if not llm_service.is_available():
        return "❌ AI 功能目前無法使用，請設定 OPENAI_API_KEY"

    # 準備低品質廣告統計
    low_quality_stats = {
        "總數": len(low_quality_ads),
        "總花費": low_quality_ads['花費金額 (TWD)'].sum(),
        "平均ROAS": low_quality_ads['購買 ROAS（廣告投資報酬率）'].mean(),
        "平均CPA": low_quality_ads['每次購買的成本'].mean(),
        "平均CTR": low_quality_ads['CTR（全部）'].mean(),
        "品質低於平均數": (low_quality_ads['品質排名'] == '平均以下').sum(),
        "互動率低於平均數": (low_quality_ads['互動率排名'] == '平均以下').sum(),
        "轉換率低於平均數": (low_quality_ads['轉換率排名'] == '平均以下').sum(),
        "三項全低數": low_quality_ads['低分項目數'].eq(3).sum()
    }

    # 準備高品質廣告統計
    high_quality_stats = {
        "總數": len(high_quality_ads),
        "平均ROAS": high_quality_ads['購買 ROAS（廣告投資報酬率）'].mean(),
        "平均CPA": high_quality_ads['每次購買的成本'].mean(),
        "平均CTR": high_quality_ads['CTR（全部）'].mean()
    }

    # 分析低品質廣告的主要問題類型
    problem_types = []
    if low_quality_stats['品質低於平均數'] > 0:
        problem_types.append(f"品質排名低 ({low_quality_stats['品質低於平均數']} 個廣告)")
    if low_quality_stats['互動率低於平均數'] > 0:
        problem_types.append(f"互動率低 ({low_quality_stats['互動率低於平均數']} 個廣告)")
    if low_quality_stats['轉換率低於平均數'] > 0:
        problem_types.append(f"轉換率低 ({low_quality_stats['轉換率低於平均數']} 個廣告)")

    # 構建 prompt
    prompt = f"""
請為以下 Meta 廣告品質問題提供完整的改善計畫。

## 低品質廣告現狀
- **總數**：{low_quality_stats['總數']} 個廣告
- **總花費**：${low_quality_stats['總花費']:,.0f} TWD
- **平均 ROAS**：{low_quality_stats['平均ROAS']:.2f}
- **平均 CPA**：${low_quality_stats['平均CPA']:.0f}
- **平均 CTR**：{low_quality_stats['平均CTR']:.2%}

## 主要問題分布
- 三項品質指標全低：{low_quality_stats['三項全低數']} 個廣告（最嚴重）
- {', '.join(problem_types)}

## 高品質廣告表現（對照參考）
- **總數**：{high_quality_stats['總數']} 個廣告
- **平均 ROAS**：{high_quality_stats['平均ROAS']:.2f}
- **平均 CPA**：${high_quality_stats['平均CPA']:.0f}
- **平均 CTR**：{high_quality_stats['平均CTR']:.2%}

## 效能差距
- ROAS 差距：{high_quality_stats['平均ROAS'] - low_quality_stats['平均ROAS']:.2f}x
- CPA 差距：${low_quality_stats['平均CPA'] - high_quality_stats['平均CPA']:.0f}（低品質更貴）
- CTR 差距：{(high_quality_stats['平均CTR'] - low_quality_stats['平均CTR']) * 100:.2f}%

## 請提供以下改善計畫：

### 1. 緊急處理方案（1-3 天）
針對三項全低的 {low_quality_stats['三項全低數']} 個廣告，提供立即行動建議：
- 預算調整策略
- 是否暫停/降低出價
- 快速優化步驟

### 2. 分類改善計畫（1-2 週）
針對不同問題類型，提供具體改善步驟：
- **品質排名低**：素材、著陸頁、用戶體驗優化
- **互動率低**：標題、文案、CTA、受眾優化
- **轉換率低**：著陸頁、價格、信任元素優化

每個類型提供：
- 診斷檢查清單（3-5 項）
- 改善行動步驟（優先序排列）
- 預期改善效果（量化指標）

### 3. 長期品質提升策略（1 個月）
- 如何建立品質監控機制
- 如何預防新廣告出現品質問題
- 如何持續優化至高品質水準

### 4. 預期成效與時間表
- **短期（1 週）**：預期達成的改善
- **中期（2-4 週）**：預期達成的改善
- **長期（1-3 個月）**：預期達成的改善
- 估算可節省的廣告費用與提升的 ROI

### 5. 具體執行檢查清單
提供一個可立即執行的 checklist（10-15 項），包含：
- ☐ 檢查項目
- ☐ 執行步驟
- ☐ 負責人/時程
- ☐ 完成標準

請用繁體中文回答，語氣專業但易懂，提供可執行的具體建議，使用 Markdown 格式。
"""

    return llm_service.generate_insights(
        prompt=prompt,
        model="gpt-4o-mini",
        max_tokens=2500,
        temperature=0.7
    )


if __name__ == "__main__":
    show_quality_score_analysis()
