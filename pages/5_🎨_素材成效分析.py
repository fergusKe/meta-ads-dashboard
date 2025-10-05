import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import sys
from pathlib import Path
from collections import Counter
import re

# 添加父目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_loader import load_meta_ads_data
from utils.ad_display import (
    display_top_bottom_ads,
    get_sorted_ad_options,
    format_ad_display_name,
    display_ad_performance_table
)
from utils.llm_service import get_llm_service
import json

def show_creative_analysis():
    """顯示素材成效分析頁面"""
    st.markdown("# 🎨 素材成效分析")
    st.markdown("深度分析廣告素材表現，包含 Headline、CTA、文案及疲勞度偵測")

    # 載入數據
    df = load_meta_ads_data()
    if df is None or df.empty:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    # 篩選有素材資訊的數據
    creative_df = df[
        (df['headline'].notna() & (df['headline'] != '未知')) |
        (df['內文'].notna() & (df['內文'] != '未知')) |
        (df['call_to_action_type'].notna() & (df['call_to_action_type'] != '未知'))
    ].copy()

    if creative_df.empty:
        st.warning("⚠️ 沒有素材相關數據")
        return

    st.info(f"📊 找到 {len(creative_df)} 筆包含素材資訊的廣告記錄")

    st.markdown("---")

    # ========== 第一部分：Headline 分析 ==========
    st.markdown("## 📝 Headline 分析")

    headline_df = creative_df[creative_df['headline'].notna() & (creative_df['headline'] != '未知')].copy()

    if not headline_df.empty:
        # 計算 headline 長度
        headline_df['headline_length'] = headline_df['headline'].astype(str).str.len()

        tab1, tab2, tab3 = st.tabs(["📊 高成效 Headline", "📏 長度分析", "🔤 關鍵字分析"])

        with tab1:
            st.markdown("### 🏆 Top 10 高 ROAS Headline")

            # 聚合相同 headline 的數據
            headline_summary = headline_df.groupby('headline').agg({
                '花費金額 (TWD)': 'sum',
                '購買次數': 'sum',
                '購買 ROAS（廣告投資報酬率）': 'mean',
                'CTR（全部）': 'mean',
                '曝光次數': 'sum'
            }).reset_index()

            # 篩選有足夠曝光的 headline
            headline_summary = headline_summary[headline_summary['曝光次數'] >= 1000]

            if not headline_summary.empty:
                top_headlines = headline_summary.sort_values('購買 ROAS（廣告投資報酬率）', ascending=False).head(10)

                # 長條圖
                fig_headline = px.bar(
                    top_headlines,
                    y='headline',
                    x='購買 ROAS（廣告投資報酬率）',
                    orientation='h',
                    title="Top 10 高 ROAS Headline",
                    color='購買 ROAS（廣告投資報酬率）',
                    color_continuous_scale='RdYlGn',
                    text='購買 ROAS（廣告投資報酬率）',
                    hover_data=['花費金額 (TWD)', 'CTR（全部）', '購買次數']
                )
                fig_headline.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                fig_headline.update_layout(
                    height=500,
                    yaxis={'categoryorder': 'total ascending'},
                    xaxis_title="ROAS"
                )
                st.plotly_chart(fig_headline, use_container_width=True)

                # 顯示最佳 Headline 範例
                st.markdown("#### ✨ 最佳 Headline 範例")
                best_headline = top_headlines.iloc[0]
                st.success(f"""
**最佳 Headline**：{best_headline['headline']}

- 📈 ROAS：{best_headline['購買 ROAS（廣告投資報酬率）']:.2f}
- 💰 總花費：{best_headline['花費金額 (TWD)']:,.0f} TWD
- 🛒 購買次數：{best_headline['購買次數']:.0f}
- 👆 CTR：{best_headline['CTR（全部）']:.2f}%
                """)

                # 🎯 顯示使用這個 Headline 的廣告列表
                st.markdown("#### 🎯 使用此 Headline 的廣告")

                # 找出使用最佳 Headline 的所有廣告
                ads_with_best_headline = headline_df[
                    headline_df['headline'] == best_headline['headline']
                ].copy()

                if not ads_with_best_headline.empty:
                    # 使用廣告顯示組件
                    display_ad_performance_table(
                        ads_with_best_headline,
                        title="",
                        sort_by='roas',
                        columns=[
                            '廣告階層',
                            '購買 ROAS（廣告投資報酬率）',
                            '花費金額 (TWD)',
                            'CTR（全部）',
                            '購買次數',
                            '目標'
                        ]
                    )

                    st.info(f"💡 共有 {len(ads_with_best_headline)} 個廣告使用此 Headline")
                else:
                    st.warning("找不到使用此 Headline 的廣告詳細資訊")
            else:
                st.warning("⚠️ 沒有足夠曝光量（≥1000）的 Headline 數據")

        with tab2:
            st.markdown("### 📏 Headline 長度 vs 成效")

            # 長度分組
            headline_df['length_group'] = pd.cut(
                headline_df['headline_length'],
                bins=[0, 20, 40, 60, 80, 200],
                labels=['很短(0-20)', '短(21-40)', '中(41-60)', '長(61-80)', '很長(81+)']
            )

            length_analysis = headline_df.groupby('length_group', observed=True).agg({
                '購買 ROAS（廣告投資報酬率）': 'mean',
                'CTR（全部）': 'mean',
                '花費金額 (TWD)': 'sum',
                '購買次數': 'sum'
            }).reset_index()

            # 雙軸圖
            fig_length = make_subplots(specs=[[{"secondary_y": True}]])

            fig_length.add_trace(
                go.Bar(
                    name='平均 ROAS',
                    x=length_analysis['length_group'].astype(str),
                    y=length_analysis['購買 ROAS（廣告投資報酬率）'],
                    marker_color='#3498db'
                ),
                secondary_y=False
            )

            fig_length.add_trace(
                go.Scatter(
                    name='平均 CTR',
                    x=length_analysis['length_group'].astype(str),
                    y=length_analysis['CTR（全部）'],
                    mode='lines+markers',
                    marker=dict(size=10, color='#e74c3c'),
                    line=dict(width=3)
                ),
                secondary_y=True
            )

            fig_length.update_layout(
                title="Headline 長度 vs ROAS & CTR",
                xaxis_title="Headline 長度",
                hovermode='x unified',
                height=450
            )
            fig_length.update_yaxes(title_text="平均 ROAS", secondary_y=False)
            fig_length.update_yaxes(title_text="平均 CTR (%)", secondary_y=True)

            st.plotly_chart(fig_length, use_container_width=True)

            # 長度分布
            col1, col2 = st.columns(2)

            with col1:
                fig_dist = px.histogram(
                    headline_df,
                    x='headline_length',
                    nbins=30,
                    title="Headline 長度分布",
                    labels={'headline_length': 'Headline 長度（字元數）'},
                    color_discrete_sequence=['#9b59b6']
                )
                fig_dist.update_layout(height=350)
                st.plotly_chart(fig_dist, use_container_width=True)

            with col2:
                st.metric("平均 Headline 長度", f"{headline_df['headline_length'].mean():.1f} 字元")
                st.metric("最佳長度區間",
                         length_analysis.loc[length_analysis['購買 ROAS（廣告投資報酬率）'].idxmax(), 'length_group'])
                st.metric("CTR 最高長度區間",
                         length_analysis.loc[length_analysis['CTR（全部）'].idxmax(), 'length_group'])

        with tab3:
            st.markdown("### 🔤 高成效關鍵字分析")

            # 從高 ROAS headline 提取關鍵字
            high_roas_headlines = headline_df[
                headline_df['購買 ROAS（廣告投資報酬率）'] >= headline_df['購買 ROAS（廣告投資報酬率）'].quantile(0.75)
            ]

            if not high_roas_headlines.empty:
                # 提取所有詞彙（簡單分詞：按空格和標點符號）
                all_words = []
                for headline in high_roas_headlines['headline'].astype(str):
                    # 移除標點符號，分割單詞
                    words = re.findall(r'\b\w+\b', headline.lower())
                    # 過濾掉太短的詞和數字
                    words = [w for w in words if len(w) > 2 and not w.isdigit()]
                    all_words.extend(words)

                # 統計詞頻
                word_counts = Counter(all_words)
                top_words = word_counts.most_common(20)

                if top_words:
                    word_df = pd.DataFrame(top_words, columns=['關鍵字', '出現次數'])

                    fig_words = px.bar(
                        word_df,
                        y='關鍵字',
                        x='出現次數',
                        orientation='h',
                        title="高 ROAS Headline 常見關鍵字 Top 20",
                        color='出現次數',
                        color_continuous_scale='Viridis'
                    )
                    fig_words.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig_words, use_container_width=True)

                    st.info(f"💡 在前 25% 高 ROAS 的 Headline 中，最常見的關鍵字為：**{', '.join([w[0] for w in top_words[:5]])}**")
                else:
                    st.warning("⚠️ 無法提取關鍵字")
            else:
                st.warning("⚠️ 沒有足夠的高 ROAS Headline 數據")

    st.markdown("---")

    # ========== 第二部分：CTA 分析 ==========
    st.markdown("## 🔘 CTA 按鈕分析")

    cta_df = creative_df[creative_df['call_to_action_type'].notna() & (creative_df['call_to_action_type'] != '未知')].copy()

    if not cta_df.empty:
        cta_col1, cta_col2 = st.columns(2)

        with cta_col1:
            # CTA 類型分布
            cta_dist = cta_df['call_to_action_type'].value_counts().head(10)

            fig_cta_dist = px.pie(
                values=cta_dist.values,
                names=cta_dist.index,
                title="CTA 類型使用分布（Top 10）",
                hole=0.4
            )
            fig_cta_dist.update_layout(height=400)
            st.plotly_chart(fig_cta_dist, use_container_width=True)

        with cta_col2:
            # CTA 類型成效對比
            cta_performance = cta_df.groupby('call_to_action_type').agg({
                '花費金額 (TWD)': 'sum',
                '購買次數': 'sum',
                '購買 ROAS（廣告投資報酬率）': 'mean',
                'CTR（全部）': 'mean',
                '曝光次數': 'sum'
            }).reset_index()

            # 篩選有足夠數據的 CTA
            cta_performance = cta_performance[cta_performance['曝光次數'] >= 500].sort_values('購買 ROAS（廣告投資報酬率）', ascending=False).head(10)

            fig_cta_roas = px.bar(
                cta_performance,
                y='call_to_action_type',
                x='購買 ROAS（廣告投資報酬率）',
                orientation='h',
                title="CTA 類型 ROAS 排名（Top 10）",
                color='購買 ROAS（廣告投資報酬率）',
                color_continuous_scale='RdYlGn',
                text='購買 ROAS（廣告投資報酬率）'
            )
            fig_cta_roas.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig_cta_roas.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_cta_roas, use_container_width=True)

        # CTA 轉換率對比
        st.markdown("### 📊 CTA 類型詳細成效")

        cta_conversion = cta_df.groupby('call_to_action_type').agg({
            '花費金額 (TWD)': 'sum',
            '購買次數': 'sum',
            '購買 ROAS（廣告投資報酬率）': 'mean',
            'CTR（全部）': 'mean',
            '每次購買的成本': 'mean',
            '觸及人數': 'sum'
        }).reset_index()

        # 計算轉換率
        cta_conversion['轉換率'] = (cta_conversion['購買次數'] / cta_conversion['觸及人數'] * 100).round(2)

        # 排序並顯示
        cta_conversion = cta_conversion.sort_values('購買 ROAS（廣告投資報酬率）', ascending=False).head(15)

        st.dataframe(
            cta_conversion,
            use_container_width=True,
            column_config={
                "call_to_action_type": "CTA 類型",
                "花費金額 (TWD)": st.column_config.NumberColumn("花費", format="%d"),
                "購買次數": st.column_config.NumberColumn("購買", format="%d"),
                "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
                "CTR（全部）": st.column_config.NumberColumn("CTR (%)", format="%.2f"),
                "每次購買的成本": st.column_config.NumberColumn("CPA", format="%.0f"),
                "轉換率": st.column_config.NumberColumn("轉換率 (%)", format="%.2f")
            }
        )

        # 最佳 CTA 推薦
        if not cta_conversion.empty:
            best_cta = cta_conversion.iloc[0]
            st.success(f"""
💡 **最佳 CTA 推薦**：{best_cta['call_to_action_type']}

- ROAS：{best_cta['購買 ROAS（廣告投資報酬率）']:.2f}
- CTR：{best_cta['CTR（全部）']:.2f}%
- 轉換率：{best_cta['轉換率']:.2f}%
            """)

    st.markdown("---")

    # ========== 第三部分：廣告文案分析 ==========
    st.markdown("## ✍️ 廣告文案分析")

    body_df = creative_df[creative_df['內文'].notna() & (creative_df['內文'] != '未知')].copy()

    if not body_df.empty:
        # 計算文案長度
        body_df['body_length'] = body_df['內文'].astype(str).str.len()

        # 偵測 Emoji
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE)

        body_df['has_emoji'] = body_df['內文'].astype(str).apply(lambda x: bool(emoji_pattern.search(x)))

        body_col1, body_col2 = st.columns(2)

        with body_col1:
            # 文案長度 vs ROAS
            body_df['length_group'] = pd.cut(
                body_df['body_length'],
                bins=[0, 50, 100, 150, 200, 1000],
                labels=['極短(0-50)', '短(51-100)', '中(101-150)', '長(151-200)', '極長(201+)']
            )

            length_perf = body_df.groupby('length_group', observed=True).agg({
                '購買 ROAS（廣告投資報酬率）': 'mean',
                'CTR（全部）': 'mean'
            }).reset_index()

            fig_body_length = px.bar(
                length_perf,
                x='length_group',
                y='購買 ROAS（廣告投資報酬率）',
                title="文案長度 vs ROAS",
                color='購買 ROAS（廣告投資報酬率）',
                color_continuous_scale='RdYlGn',
                text='購買 ROAS（廣告投資報酬率）',
                labels={'length_group': '文案長度'}
            )
            fig_body_length.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig_body_length.update_layout(height=400)
            st.plotly_chart(fig_body_length, use_container_width=True)

        with body_col2:
            # Emoji 使用 vs 成效
            emoji_perf = body_df.groupby('has_emoji').agg({
                '購買 ROAS（廣告投資報酬率）': 'mean',
                'CTR（全部）': 'mean',
                '花費金額 (TWD)': 'sum'
            }).reset_index()

            emoji_perf['emoji_label'] = emoji_perf['has_emoji'].map({True: '有 Emoji', False: '無 Emoji'})

            fig_emoji = go.Figure()

            fig_emoji.add_trace(go.Bar(
                name='平均 ROAS',
                x=emoji_perf['emoji_label'],
                y=emoji_perf['購買 ROAS（廣告投資報酬率）'],
                marker_color=['#f39c12', '#3498db'],
                text=emoji_perf['購買 ROAS（廣告投資報酬率）'].round(2),
                textposition='outside'
            ))

            fig_emoji.update_layout(
                title="Emoji 使用 vs ROAS",
                xaxis_title="",
                yaxis_title="平均 ROAS",
                height=400,
                showlegend=False
            )
            st.plotly_chart(fig_emoji, use_container_width=True)

        # 高成效文案範例
        st.markdown("### ✨ 高成效文案範例")

        top_bodies = body_df.nlargest(5, '購買 ROAS（廣告投資報酬率）')

        for idx, row in top_bodies.iterrows():
            with st.expander(f"📝 範例 {idx+1} - ROAS: {row['購買 ROAS（廣告投資報酬率）']:.2f}"):
                st.markdown(f"**文案內容**：{row['內文'][:200]}...")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("ROAS", f"{row['購買 ROAS（廣告投資報酬率）']:.2f}")
                with col2:
                    st.metric("CTR", f"{row['CTR（全部）']:.2f}%")
                with col3:
                    st.metric("購買次數", f"{row['購買次數']:.0f}")

    st.markdown("---")

    # ========== 第四部分：素材疲勞度偵測 ==========
    st.markdown("## 🔄 素材疲勞度偵測")

    if '投放天數' in creative_df.columns:
        fatigue_df = creative_df[creative_df['投放天數'] > 0].copy()

        if not fatigue_df.empty:
            # 計算 CTR 下降趨勢
            fatigue_df['days_group'] = pd.cut(
                fatigue_df['投放天數'],
                bins=[0, 7, 14, 21, 30, 60, 1000],
                labels=['0-7天', '8-14天', '15-21天', '22-30天', '31-60天', '60天+']
            )

            fatigue_trend = fatigue_df.groupby('days_group', observed=True).agg({
                'CTR（全部）': 'mean',
                '購買 ROAS（廣告投資報酬率）': 'mean',
                '廣告名稱': 'count'
            }).reset_index()

            fatigue_trend.columns = ['投放天數', '平均 CTR', '平均 ROAS', '廣告數量']

            # 疲勞度趨勢圖
            fig_fatigue = make_subplots(specs=[[{"secondary_y": True}]])

            fig_fatigue.add_trace(
                go.Scatter(
                    name='平均 CTR',
                    x=fatigue_trend['投放天數'].astype(str),
                    y=fatigue_trend['平均 CTR'],
                    mode='lines+markers',
                    marker=dict(size=10, color='#3498db'),
                    line=dict(width=3)
                ),
                secondary_y=False
            )

            fig_fatigue.add_trace(
                go.Scatter(
                    name='平均 ROAS',
                    x=fatigue_trend['投放天數'].astype(str),
                    y=fatigue_trend['平均 ROAS'],
                    mode='lines+markers',
                    marker=dict(size=10, color='#e74c3c'),
                    line=dict(width=3)
                ),
                secondary_y=True
            )

            fig_fatigue.update_layout(
                title="素材疲勞度趨勢（CTR & ROAS vs 投放天數）",
                xaxis_title="投放天數",
                hovermode='x unified',
                height=450
            )
            fig_fatigue.update_yaxes(title_text="平均 CTR (%)", secondary_y=False)
            fig_fatigue.update_yaxes(title_text="平均 ROAS", secondary_y=True)

            st.plotly_chart(fig_fatigue, use_container_width=True)

            # 需要更換的素材預警
            st.markdown("### ⚠️ 素材更換建議")

            # 找出投放超過 30 天且 CTR 低於平均的廣告
            avg_ctr = fatigue_df['CTR（全部）'].mean()
            tired_ads = fatigue_df[
                (fatigue_df['投放天數'] > 30) &
                (fatigue_df['CTR（全部）'] < avg_ctr)
            ].copy()

            if not tired_ads.empty:
                tired_summary = tired_ads.groupby('廣告名稱').agg({
                    '投放天數': 'max',
                    'CTR（全部）': 'mean',
                    '購買 ROAS（廣告投資報酬率）': 'mean',
                    '花費金額 (TWD)': 'sum'
                }).reset_index().sort_values('投放天數', ascending=False).head(20)

                st.warning(f"🚨 發現 {len(tired_ads)} 筆可能疲勞的廣告（投放 >30 天且 CTR 低於平均 {avg_ctr:.2f}%）")

                st.dataframe(
                    tired_summary,
                    use_container_width=True,
                    column_config={
                        "廣告名稱": "廣告",
                        "投放天數": st.column_config.NumberColumn("投放天數", format="%d 天"),
                        "CTR（全部）": st.column_config.NumberColumn("CTR (%)", format="%.2f"),
                        "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
                        "花費金額 (TWD)": st.column_config.NumberColumn("總花費", format="%d")
                    }
                )

                st.info("""
💡 **素材輪替建議**：
1. 暫停或降低投放超過 60 天且 CTR 持續下降的廣告
2. 複製高成效素材，更換新的圖片或影片
3. 測試不同的 Headline 和 CTA 組合
4. 考慮更新文案以符合當前趨勢或季節性
                """)
            else:
                st.success("✅ 目前沒有明顯疲勞的素材，表現良好！")

    st.markdown("---")

    # ========== 第五部分：整體素材對比與詳細查看 ==========
    st.markdown("## 📊 整體素材對比")

    # Top 10 vs Bottom 10 廣告對比
    display_top_bottom_ads(
        creative_df,
        metric='購買 ROAS（廣告投資報酬率）',
        top_n=10
    )

    st.markdown("---")

    # ========== 選擇廣告查看詳細素材 ==========
    st.markdown("## 🔍 查看特定廣告的素材細節")

    st.info("💡 選擇廣告後，可以查看完整的 Headline、文案、CTA、受眾等資訊")

    # 取得排序後的廣告選項
    option_labels, data_map = get_sorted_ad_options(
        creative_df,
        sort_by='roas',
        top_n=50  # 只顯示前 50 個
    )

    if option_labels:
        selected_ad = st.selectbox(
            "選擇要查看的廣告",
            options=option_labels,
            help="已按 ROAS 排序，優先顯示高效廣告"
        )

        if selected_ad:
            ad_data = data_map[selected_ad]

            # 顯示廣告詳細資訊
            st.markdown("### 📋 廣告詳細資訊")

            detail_col1, detail_col2 = st.columns([2, 1])

            with detail_col1:
                st.markdown("#### 📝 素材內容")

                # Headline
                headline = ad_data.get('headline', '未知')
                if pd.notna(headline) and headline != '未知':
                    st.markdown(f"**Headline**：{headline}")
                    st.caption(f"長度：{len(str(headline))} 字元")

                # 內文
                body = ad_data.get('內文', '')
                if pd.notna(body) and body:
                    st.markdown(f"**內文**：")
                    st.text_area("", value=body, height=150, disabled=True, label_visibility="collapsed")
                    st.caption(f"長度：{len(str(body))} 字元")

                # CTA
                cta = ad_data.get('call_to_action_type', '未知')
                if pd.notna(cta) and cta != '未知':
                    st.markdown(f"**CTA 按鈕**：`{cta}`")

            with detail_col2:
                st.markdown("#### 📊 表現數據")

                st.metric("ROAS", f"{ad_data.get('購買 ROAS（廣告投資報酬率）', 0):.2f}")
                st.metric("花費", f"${ad_data.get('花費金額 (TWD)', 0):,.0f}")
                st.metric("CTR", f"{ad_data.get('CTR（全部）', 0):.2f}%")
                st.metric("購買次數", f"{ad_data.get('購買次數', 0):.0f}")

                st.markdown("#### 👥 受眾資訊")
                st.write(f"**目標受眾**：{ad_data.get('目標', '未知')}")
                st.write(f"**年齡**：{ad_data.get('年齡', '未知')}")
                st.write(f"**性別**：{ad_data.get('性別', '未知')}")

                # 品質評分
                quality = ad_data.get('品質排名', '未知')
                engagement = ad_data.get('互動率排名', '未知')
                conversion = ad_data.get('轉換率排名', '未知')

                if quality != '未知' or engagement != '未知' or conversion != '未知':
                    st.markdown("#### ⭐ 品質評分")
                    st.write(f"**品質排名**：{quality}")
                    st.write(f"**互動率排名**：{engagement}")
                    st.write(f"**轉換率排名**：{conversion}")

            # 學習建議
            st.markdown("---")
            st.markdown("### 💡 學習建議")

            roas = ad_data.get('購買 ROAS（廣告投資報酬率）', 0)
            if roas >= 3.0:
                st.success(f"""
**🏆 這是高效廣告（ROAS {roas:.2f}）- 值得學習**

建議學習重點：
1. **Headline 風格**：分析用詞、長度、訴求點
2. **文案結構**：開頭、中段、結尾如何組織
3. **受眾定位**：這個受眾群組為什麼有效
4. **CTA 選擇**：為什麼選擇這個 CTA 類型

📌 **行動方案**：複製此廣告的成功要素，應用到新廣告
                """)
            elif roas < 2.0:
                st.warning(f"""
**⚠️ 這是低效廣告（ROAS {roas:.2f}）- 需要優化**

可能問題：
1. **Headline 吸引力不足**？對比高效廣告的 Headline
2. **文案未打中受眾痛點**？重新思考價值主張
3. **CTA 不夠明確**？測試其他 CTA 類型
4. **受眾不精準**？嘗試縮小受眾範圍

📌 **行動方案**：參考 Top 10 高效廣告，重新設計素材
                """)
            else:
                st.info(f"""
**✅ 這是中等效能廣告（ROAS {roas:.2f}）- 有優化空間**

優化方向：
1. 參考 Top 10 廣告的 Headline 關鍵字
2. 測試不同的 CTA 按鈕
3. 優化文案長度和結構
4. A/B 測試受眾群組

📌 **行動方案**：小幅調整素材，測試成效
                """)
    else:
        st.warning("沒有可用的廣告數據")

    st.markdown("---")

    # ========== 第六部分：AI 成功模式分析 ==========
    st.markdown("## 🤖 AI 成功模式分析")

    st.markdown("""
    使用 AI 深度分析高效素材的共同特徵，找出可複製的成功模式。
    """)

    if st.button("🔍 使用 AI 分析成功素材模式", key="creative_ai_analysis"):
        with st.spinner("AI 正在分析高效素材的成功模式..."):
            try:
                # 初始化 LLM 服務
                llm_service = LLMService()

                # 獲取高 ROAS 素材
                high_roas_ads = creative_df[creative_df['購買 ROAS（廣告投資報酬率）'] >= 3.0].copy()

                if high_roas_ads.empty:
                    st.warning("沒有找到 ROAS >= 3.0 的廣告素材")
                else:
                    # 分析 Headline
                    top_headlines = high_roas_ads.nlargest(10, '購買 ROAS（廣告投資報酬率）')['headline'].tolist()

                    # 分析 CTA
                    cta_dist = high_roas_ads['call_to_action_type'].value_counts().head(5).to_dict()

                    # 分析長度
                    avg_headline_length = high_roas_ads['headline'].str.len().mean()
                    avg_body_length = high_roas_ads['內文'].str.len().mean() if '內文' in high_roas_ads.columns else 0

                    # 分析數字指標
                    avg_roas = high_roas_ads['購買 ROAS（廣告投資報酬率）'].mean()
                    avg_ctr = high_roas_ads['CTR（全部）'].mean()
                    total_purchases = high_roas_ads['購買次數'].sum()

                    # 構建 Prompt
                    prompt = f"""
你是一位專業的廣告文案分析師，請分析以下高效廣告素材的共同特徵：

**高效素材數據**（ROAS >= 3.0）：
- 樣本數：{len(high_roas_ads)} 個廣告
- 平均 ROAS：{avg_roas:.2f}
- 平均 CTR：{avg_ctr:.2f}%
- 總購買次數：{total_purchases:.0f}

**Top 10 Headline 範例**：
{chr(10).join([f'{i+1}. {h}' for i, h in enumerate(top_headlines[:10])])}

**最常使用的 CTA**：
{chr(10).join([f'- {cta}: {count} 次' for cta, count in list(cta_dist.items())[:5]])}

**平均長度**：
- Headline：{avg_headline_length:.0f} 字元
- 內文：{avg_body_length:.0f} 字元

請提供：

1. **成功 Headline 共同特徵**（3-5 個關鍵模式）
   - 用詞風格（如：數字、問句、行動導向）
   - 結構特點
   - 情感訴求

2. **可複製的文案公式**
   - 提供 3 個具體的 Headline 模板
   - 每個模板說明適用場景
   - 提供填空範例

3. **CTA 優化建議**
   - 為什麼這些 CTA 有效
   - 在什麼情境下使用
   - 搭配什麼樣的文案最好

4. **立即可用的行動方案**
   - 3 個可以立即測試的新 Headline
   - 基於成功模式，但有所創新
   - 說明為什麼預期會有效

請使用繁體中文，語氣專業但易懂。格式使用 Markdown，重點使用粗體標註。提供的範例要具體且可直接使用。
"""

                    # 調用 LLM
                    analysis = llm_service.generate_insights(
                        prompt=prompt,
                        model="gpt-3.5-turbo",
                        max_tokens=2000,
                        temperature=0.7
                    )

                    # 顯示分析結果
                    st.success("✅ AI 分析完成")
                    st.markdown(analysis)

                    # 額外建議
                    st.info(f"""
💡 **使用建議**：
1. 參考「可複製的文案公式」創建新廣告
2. 測試「立即可用的行動方案」中的 3 個 Headline
3. 在 A/B 測試中使用推薦的 CTA 組合
4. 定期（每 2 週）重新分析，確保跟上趨勢

**成本估算**：約 ${len(high_roas_ads) * 0.001:.3f} USD（使用 GPT-3.5 Turbo）
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

    # ========== 第七部分：優化建議總結 ==========
    st.markdown("## 💡 素材優化建議總結")

    rec_col1, rec_col2 = st.columns(2)

    with rec_col1:
        st.success("""
**✅ 最佳實踐**

1. **Headline**：
   - 使用長度適中的標題（建議 40-60 字元）
   - 包含高成效關鍵字
   - 清晰傳達價值主張

2. **CTA**：
   - 優先使用數據驗證的高 ROAS CTA 類型
   - 確保 CTA 與廣告目標一致
   - 測試不同 CTA 對受眾的影響

3. **文案**：
   - 適度使用 Emoji 增加吸引力
   - 文案長度根據產品複雜度調整
   - 展示高成效文案的共同特徵
        """)

    with rec_col2:
        st.warning("""
**⚠️ 需改善項目**

1. **疲勞素材**：
   - 定期更換投放超過 30 天的素材
   - 監控 CTR 下降趨勢
   - 建立素材輪替機制

2. **低效素材**：
   - 暫停 ROAS < 1.0 的素材
   - 分析失敗原因（標題、文案、CTA）
   - 重新設計並 A/B 測試

3. **測試機會**：
   - 測試不同長度的 Headline
   - 嘗試新的 CTA 類型
   - 實驗 Emoji 使用策略
        """)

    st.markdown("---")

    # ========== 第八部分：AI 深度洞察 ==========
    st.markdown("## 🤖 AI 深度洞察")
    st.info("💡 使用 AI 分析高效與低效素材的差異，提供可執行的優化建議")

    if st.button("🚀 生成 AI 深度洞察", type="primary", use_container_width=True):
        with st.spinner("AI 正在分析素材數據..."):
            ai_insights = generate_ai_creative_insights(df, high_roas_creatives, low_roas_creatives)

            if ai_insights and not ai_insights.startswith("❌") and not ai_insights.startswith("⚠️"):
                st.markdown("### 📊 AI 分析結果")
                st.markdown(ai_insights)
            else:
                st.error(ai_insights if ai_insights else "AI 分析失敗")


def generate_ai_creative_insights(all_creatives, high_roas_creatives, low_roas_creatives):
    """
    生成 AI 素材洞察

    分析高效素材（前 25%）與低效素材（後 25%）的差異，
    提供具體可執行的優化建議
    """
    llm_service = get_llm_service()

    if not llm_service.is_available():
        return "❌ AI 功能目前無法使用，請設定 OPENAI_API_KEY"

    # 準備數據摘要
    high_roas_summary = {
        "count": len(high_roas_creatives),
        "avg_roas": high_roas_creatives['ROAS'].mean() if len(high_roas_creatives) > 0 else 0,
        "avg_ctr": high_roas_creatives['CTR'].mean() if len(high_roas_creatives) > 0 else 0,
        "avg_cpc": high_roas_creatives['CPC'].mean() if len(high_roas_creatives) > 0 else 0,
        "common_ctas": high_roas_creatives['CTA類型'].value_counts().head(3).to_dict() if len(high_roas_creatives) > 0 else {},
        "avg_headline_len": high_roas_creatives['Headline長度'].mean() if len(high_roas_creatives) > 0 and 'Headline長度' in high_roas_creatives.columns else 0,
        "avg_emoji_count": high_roas_creatives['文案Emoji數'].mean() if len(high_roas_creatives) > 0 and '文案Emoji數' in high_roas_creatives.columns else 0
    }

    low_roas_summary = {
        "count": len(low_roas_creatives),
        "avg_roas": low_roas_creatives['ROAS'].mean() if len(low_roas_creatives) > 0 else 0,
        "avg_ctr": low_roas_creatives['CTR'].mean() if len(low_roas_creatives) > 0 else 0,
        "avg_cpc": low_roas_creatives['CPC'].mean() if len(low_roas_creatives) > 0 else 0,
        "common_ctas": low_roas_creatives['CTA類型'].value_counts().head(3).to_dict() if len(low_roas_creatives) > 0 else {},
        "avg_headline_len": low_roas_creatives['Headline長度'].mean() if len(low_roas_creatives) > 0 and 'Headline長度' in low_roas_creatives.columns else 0,
        "avg_emoji_count": low_roas_creatives['文案Emoji數'].mean() if len(low_roas_creatives) > 0 and '文案Emoji數' in low_roas_creatives.columns else 0
    }

    # 構建 prompt
    prompt = f"""
請分析以下 Meta 廣告素材數據，找出高效與低效素材的關鍵差異。

## 高效素材數據（前 25% ROAS）
- 數量：{high_roas_summary['count']} 個素材
- 平均 ROAS：{high_roas_summary['avg_roas']:.2f}
- 平均 CTR：{high_roas_summary['avg_ctr']:.2%}
- 平均 CPC：${high_roas_summary['avg_cpc']:.2f}
- 常見 CTA：{json.dumps(high_roas_summary['common_ctas'], ensure_ascii=False)}
- 平均 Headline 長度：{high_roas_summary['avg_headline_len']:.0f} 字元
- 平均 Emoji 數量：{high_roas_summary['avg_emoji_count']:.1f} 個

## 低效素材數據（後 25% ROAS）
- 數量：{low_roas_summary['count']} 個素材
- 平均 ROAS：{low_roas_summary['avg_roas']:.2f}
- 平均 CTR：{low_roas_summary['avg_ctr']:.2%}
- 平均 CPC：${low_roas_summary['avg_cpc']:.2f}
- 常見 CTA：{json.dumps(low_roas_summary['common_ctas'], ensure_ascii=False)}
- 平均 Headline 長度：{low_roas_summary['avg_headline_len']:.0f} 字元
- 平均 Emoji 數量：{low_roas_summary['avg_emoji_count']:.1f} 個

## 請提供以下分析：

### 1. 成功素材的共同特徵（3-5 點）
找出高效素材在 CTA、標題長度、文案風格、Emoji 使用等方面的共同模式

### 2. 失敗素材的常見問題（3-5 點）
分析低效素材可能存在的問題和改善空間

### 3. 具體優化建議（5 個）
基於數據差異，提供可立即執行的素材優化行動，格式：
- **建議標題**：具體做法 + 預期效果

### 4. A/B 測試提案（2-3 個）
建議值得測試的素材變因，例如：
- 測試變因：CTA 類型（SHOP_NOW vs LEARN_MORE）
- 假設：SHOP_NOW 可能提升 20% 轉換率
- 測試方法：各分配 50% 預算，執行 7 天

### 5. 下一波素材方向
基於成功模式，建議下一波廣告素材的創意方向

請用繁體中文回答，語氣專業但易懂，使用 Markdown 格式。
"""

    return llm_service.generate_insights(
        prompt=prompt,
        model="gpt-4o-mini",
        max_tokens=2000,
        temperature=0.7
    )


if __name__ == "__main__":
    show_creative_analysis()
