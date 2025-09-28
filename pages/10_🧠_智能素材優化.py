import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import openai
import os
from utils.data_loader import load_meta_ads_data, calculate_summary_metrics

st.set_page_config(page_title="智能素材優化", page_icon="🧠", layout="wide")

def analyze_creative_performance(df):
    """分析素材表現"""
    if df is None or df.empty:
        return {}

    # 分析不同素材類型的表現
    creative_analysis = {}

    # 按廣告活動分析
    if '行銷活動名稱' in df.columns:
        campaign_performance = df.groupby('行銷活動名稱').agg({
            '購買 ROAS（廣告投資報酬率）': 'mean',
            'CTR（全部）': 'mean',
            '每次購買的成本': 'mean',
            '花費金額 (TWD)': 'sum',
            '購買次數': 'sum',
            '觸及人數': 'sum'
        }).round(2)

        creative_analysis['campaign_performance'] = campaign_performance

    # 分析受眾表現
    if '目標' in df.columns:
        audience_performance = df.groupby('目標').agg({
            '購買 ROAS（廣告投資報酬率）': 'mean',
            'CTR（全部）': 'mean',
            '每次購買的成本': 'mean',
            '觸及人數': 'sum'
        }).round(2)

        creative_analysis['audience_performance'] = audience_performance

    # 計算表現評分
    df_with_scores = df.copy()
    if '購買 ROAS（廣告投資報酬率）' in df.columns:
        # ROAS 評分 (權重 40%)
        roas_score = np.clip((df['購買 ROAS（廣告投資報酬率）'] / 3.0) * 40, 0, 40)

        # CTR 評分 (權重 30%)
        ctr_mean = df['CTR（全部）'].mean()
        ctr_score = np.clip((df['CTR（全部）'] / ctr_mean) * 30, 0, 30) if ctr_mean > 0 else 0

        # 轉換率評分 (權重 30%)
        df['轉換率'] = df['購買次數'] / df['觸及人數'] * 100
        conversion_mean = df['轉換率'].mean()
        conversion_score = np.clip((df['轉換率'] / conversion_mean) * 30, 0, 30) if conversion_mean > 0 else 0

        # 總評分
        df_with_scores['素材評分'] = roas_score + ctr_score + conversion_score
        creative_analysis['scored_campaigns'] = df_with_scores

    return creative_analysis

def identify_optimization_opportunities(df):
    """識別優化機會"""
    if df is None or df.empty:
        return []

    opportunities = []

    # 低表現活動識別
    if '購買 ROAS（廣告投資報酬率）' in df.columns:
        low_roas = df[df['購買 ROAS（廣告投資報酬率）'] < 1.5]
        if not low_roas.empty:
            for _, campaign in low_roas.iterrows():
                opportunities.append({
                    'type': '低ROAS優化',
                    'campaign': campaign.get('行銷活動名稱', '未知'),
                    'current_roas': campaign.get('購買 ROAS（廣告投資報酬率）', 0),
                    'priority': 'high',
                    'recommendation': '建議調整目標、優化文案或素材設計'
                })

    # 高花費低效果識別
    if '花費金額 (TWD)' in df.columns:
        high_spend = df.nlargest(5, '花費金額 (TWD)')
        for _, campaign in high_spend.iterrows():
            roas = campaign.get('購買 ROAS（廣告投資報酬率）', 0)
            if roas < 2.0:
                opportunities.append({
                    'type': '高預算低效優化',
                    'campaign': campaign.get('行銷活動名稱', '未知'),
                    'spend': campaign.get('花費金額 (TWD)', 0),
                    'current_roas': roas,
                    'priority': 'high',
                    'recommendation': '考慮暫停或大幅調整該活動，重新分配預算'
                })

    # CTR 優化機會
    if 'CTR（全部）' in df.columns:
        avg_ctr = df['CTR（全部）'].mean()
        low_ctr = df[df['CTR（全部）'] < avg_ctr * 0.7]
        if not low_ctr.empty:
            for _, campaign in low_ctr.iterrows():
                opportunities.append({
                    'type': 'CTR優化',
                    'campaign': campaign.get('行銷活動名稱', '未知'),
                    'current_ctr': campaign.get('CTR（全部）', 0),
                    'avg_ctr': avg_ctr,
                    'priority': 'medium',
                    'recommendation': '優化廣告圖片和標題，增強視覺吸引力'
                })

    return opportunities

def generate_ai_recommendations(performance_data, opportunities):
    """使用 AI 生成智能建議"""
    try:
        openai.api_key = os.getenv('OPENAI_API_KEY')
        if not openai.api_key:
            return "無法連接 AI 服務，請檢查 API 設定"

        # 準備數據摘要
        data_summary = f"""
總活動數: {len(performance_data) if performance_data else 0}
優化機會數: {len(opportunities)}
主要問題: {', '.join([opp['type'] for opp in opportunities[:3]])}
"""

        prompt = f"""
作為廣告優化專家，請基於以下耘初茶食的 Meta 廣告數據分析，提供具體的素材優化建議：

數據摘要：
{data_summary}

主要優化機會：
{opportunities[:5]}

請提供：
1. 素材設計優化建議
2. 文案改進方向
3. 受眾定位調整
4. 預算分配建議
5. A/B測試策略

要求簡潔實用，每個建議不超過50字。
"""

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是專業的數位廣告優化顧問，專精於Meta廣告優化。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.7
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"AI 建議生成失敗：{str(e)}"

def create_performance_radar_chart(campaign_data):
    """創建表現雷達圖"""
    if campaign_data is None or campaign_data.empty:
        return None

    # 選取前5名活動
    top_campaigns = campaign_data.nlargest(5, '購買 ROAS（廣告投資報酬率）')

    fig = go.Figure()

    for _, campaign in top_campaigns.iterrows():
        campaign_name = campaign.get('行銷活動名稱', '未知')[:15] + "..."

        # 正規化指標 (0-100)
        roas_norm = min(campaign.get('購買 ROAS（廣告投資報酬率）', 0) / 5.0 * 100, 100)
        ctr_norm = min(campaign.get('CTR（全部）', 0) * 100 * 10, 100)
        conversion_rate = (campaign.get('購買次數', 0) / max(campaign.get('觸及人數', 1), 1)) * 1000
        conversion_norm = min(conversion_rate, 100)

        fig.add_trace(go.Scatterpolar(
            r=[roas_norm, ctr_norm, conversion_norm, 80, 60],  # 添加兩個固定維度
            theta=['ROAS', 'CTR', '轉換率', '觸及品質', '成本效益'],
            fill='toself',
            name=campaign_name
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=True,
        title="活動表現雷達圖"
    )

    return fig

def create_optimization_priority_chart(opportunities):
    """創建優化優先級圖表"""
    if not opportunities:
        return None

    # 按優先級分組
    priority_counts = {'high': 0, 'medium': 0, 'low': 0}
    for opp in opportunities:
        priority = opp.get('priority', 'medium')
        priority_counts[priority] += 1

    fig = go.Figure(data=[
        go.Bar(
            x=['高優先級', '中優先級', '低優先級'],
            y=[priority_counts['high'], priority_counts['medium'], priority_counts['low']],
            marker_color=['#ff4444', '#ffaa00', '#44ff44']
        )
    ])

    fig.update_layout(
        title="優化機會優先級分布",
        xaxis_title="優先級",
        yaxis_title="機會數量",
        height=300
    )

    return fig

def create_budget_reallocation_chart(df):
    """創建預算重新分配建議圖表"""
    if df is None or df.empty:
        return None

    # 計算當前預算分配和建議分配
    campaign_performance = df.groupby('行銷活動名稱').agg({
        '花費金額 (TWD)': 'sum',
        '購買 ROAS（廣告投資報酬率）': 'mean'
    }).round(2)

    # 只顯示前8個活動
    top_campaigns = campaign_performance.nlargest(8, '花費金額 (TWD)')

    current_spend = top_campaigns['花費金額 (TWD)']
    roas = top_campaigns['購買 ROAS（廣告投資報酬率）']

    # 簡單的預算重新分配邏輯：ROAS > 2.0 的增加預算，ROAS < 1.5 的減少預算
    suggested_spend = current_spend.copy()
    total_budget = current_spend.sum()

    for campaign in top_campaigns.index:
        campaign_roas = roas[campaign]
        if campaign_roas > 2.0:
            suggested_spend[campaign] = current_spend[campaign] * 1.2
        elif campaign_roas < 1.5:
            suggested_spend[campaign] = current_spend[campaign] * 0.8

    # 正規化至原總預算
    suggested_spend = suggested_spend * (total_budget / suggested_spend.sum())

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name='當前預算',
        x=top_campaigns.index,
        y=current_spend,
        marker_color='lightblue'
    ))

    fig.add_trace(go.Bar(
        name='建議預算',
        x=top_campaigns.index,
        y=suggested_spend,
        marker_color='orange'
    ))

    fig.update_layout(
        title="預算重新分配建議",
        xaxis_title="廣告活動",
        yaxis_title="預算 (TWD)",
        barmode='group',
        height=400
    )

    return fig

def main():
    st.title("🧠 智能素材優化")
    st.markdown("運用 AI 智能分析優化廣告素材表現")

    # 載入數據
    df = load_meta_ads_data()

    if df is None:
        st.error("❌ 無法載入數據，請檢查數據檔案")
        return

    # 分析素材表現
    creative_analysis = analyze_creative_performance(df)
    opportunities = identify_optimization_opportunities(df)

    # 主要指標概覽
    st.subheader("📊 素材表現總覽")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_campaigns = len(df['行銷活動名稱'].unique()) if '行銷活動名稱' in df.columns else 0
        st.metric("總活動數", total_campaigns)

    with col2:
        optimization_opportunities = len(opportunities)
        st.metric("優化機會", optimization_opportunities, delta=f"{optimization_opportunities} 個")

    with col3:
        avg_roas = df['購買 ROAS（廣告投資報酬率）'].mean() if '購買 ROAS（廣告投資報酬率）' in df.columns else 0
        st.metric("平均 ROAS", f"{avg_roas:.2f}")

    with col4:
        high_priority_ops = len([opp for opp in opportunities if opp.get('priority') == 'high'])
        st.metric("高優先級優化", high_priority_ops, delta="需立即處理" if high_priority_ops > 0 else "良好")

    # 主要內容區域
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 智能分析", "📈 表現視覺化", "💡 AI 建議", "🔧 優化工具"])

    with tab1:
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("🔍 優化機會識別")

            if opportunities:
                for i, opp in enumerate(opportunities[:10]):  # 顯示前10個機會
                    priority_color = {
                        'high': '🔴',
                        'medium': '🟡',
                        'low': '🟢'
                    }.get(opp.get('priority', 'medium'), '🟡')

                    with st.container():
                        st.write(f"{priority_color} **{opp.get('type', '優化機會')}**")
                        st.write(f"活動：{opp.get('campaign', '未知')}")

                        if 'current_roas' in opp:
                            st.write(f"當前 ROAS：{opp.get('current_roas', 0):.2f}")

                        if 'current_ctr' in opp:
                            st.write(f"當前 CTR：{opp.get('current_ctr', 0):.3f}%")

                        st.info(f"💡 建議：{opp.get('recommendation', '需要進一步分析')}")
                        st.divider()

            else:
                st.success("🎉 太棒了！目前沒有發現明顯的優化機會，您的廣告表現良好。")

        with col2:
            st.subheader("📊 快速統計")

            # 優化優先級分布
            if opportunities:
                priority_chart = create_optimization_priority_chart(opportunities)
                if priority_chart:
                    st.plotly_chart(priority_chart, use_container_width=True)

            # 表現分級
            if 'scored_campaigns' in creative_analysis:
                scored_df = creative_analysis['scored_campaigns']
                if '素材評分' in scored_df.columns:
                    excellent = len(scored_df[scored_df['素材評分'] >= 80])
                    good = len(scored_df[(scored_df['素材評分'] >= 60) & (scored_df['素材評分'] < 80)])
                    needs_improvement = len(scored_df[scored_df['素材評分'] < 60])

                    st.write("**素材表現分級：**")
                    st.write(f"🌟 優秀 (80+)：{excellent} 個活動")
                    st.write(f"👍 良好 (60-79)：{good} 個活動")
                    st.write(f"⚠️ 需改善 (<60)：{needs_improvement} 個活動")

    with tab2:
        st.subheader("📈 表現視覺化分析")

        # 活動表現雷達圖
        if 'campaign_performance' in creative_analysis:
            radar_chart = create_performance_radar_chart(creative_analysis['campaign_performance'])
            if radar_chart:
                st.plotly_chart(radar_chart, use_container_width=True)

        # 預算重新分配建議
        col1, col2 = st.columns(2)

        with col1:
            budget_chart = create_budget_reallocation_chart(df)
            if budget_chart:
                st.plotly_chart(budget_chart, use_container_width=True)

        with col2:
            # 受眾表現分析
            if 'audience_performance' in creative_analysis:
                audience_df = creative_analysis['audience_performance']
                if not audience_df.empty:
                    fig = px.scatter(
                        audience_df.reset_index(),
                        x='CTR（全部）',
                        y='購買 ROAS（廣告投資報酬率）',
                        size='觸及人數',
                        hover_name='目標',
                        title="受眾表現分析"
                    )
                    st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("💡 AI 智能建議")

        with st.spinner("AI 正在分析您的廣告數據..."):
            ai_recommendations = generate_ai_recommendations(
                creative_analysis.get('campaign_performance'),
                opportunities
            )

        st.markdown("### 🤖 AI 專家建議")
        st.markdown(ai_recommendations)

        # 行動計劃
        st.markdown("### 📋 建議行動計劃")

        action_plan = [
            "🎯 **立即行動**：處理高優先級優化機會",
            "📊 **數據監控**：設定關鍵指標警報",
            "🧪 **A/B測試**：測試新的素材變化",
            "💰 **預算調整**：根據 ROAS 重新分配預算",
            "📈 **效果追蹤**：每周檢視優化效果"
        ]

        for action in action_plan:
            st.markdown(f"- {action}")

    with tab4:
        st.subheader("🔧 優化工具箱")

        # 素材 A/B 測試建議
        st.markdown("### 🧪 A/B 測試建議")

        test_categories = {
            "圖片測試": [
                "產品特寫 vs 生活場景",
                "明亮色調 vs 溫暖色調",
                "單一產品 vs 多產品組合",
                "人物使用 vs 純產品展示"
            ],
            "文案測試": [
                "情感訴求 vs 理性訴求",
                "長文案 vs 短文案",
                "問句開頭 vs 陳述句開頭",
                "急迫性語言 vs 溫和語言"
            ],
            "CTA測試": [
                "立即購買 vs 了解更多",
                "馬上行動 vs 現在開始",
                "限時優惠 vs 永久優惠",
                "免費試用 vs 立即購買"
            ]
        }

        cols = st.columns(3)
        for i, (category, tests) in enumerate(test_categories.items()):
            with cols[i]:
                st.write(f"**{category}**")
                for test in tests:
                    st.write(f"• {test}")

        # 優化檢查清單
        st.markdown("### ✅ 優化檢查清單")

        checklist_items = [
            "圖片品質是否清晰且具有吸引力",
            "文案是否突出產品核心價值",
            "目標定位是否精確",
            "廣告時間安排是否最佳",
            "預算分配是否合理",
            "著陸頁體驗是否順暢",
            "追蹤碼設定是否正確",
            "競爭對手分析是否充分"
        ]

        for item in checklist_items:
            checked = st.checkbox(item, key=f"checklist_{item}")

        # 優化模板下載
        st.markdown("### 📄 優化模板")

        template_data = {
            "優化項目": ["活動A文案", "活動B圖片", "活動C受眾"],
            "當前表現": ["ROAS 1.2", "CTR 0.8%", "CPA $150"],
            "優化目標": ["ROAS > 2.0", "CTR > 1.5%", "CPA < $100"],
            "行動計劃": ["重寫主標題", "更換產品圖", "縮小受眾範圍"],
            "預期改善": ["+67%", "+87%", "-33%"],
            "執行時間": ["本週", "下週", "下週"]
        }

        template_df = pd.DataFrame(template_data)
        st.dataframe(template_df, use_container_width=True)

        csv = template_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 下載優化計劃模板",
            data=csv,
            file_name=f"優化計劃模板_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

    # 實時監控建議
    st.subheader("📡 實時監控建議")

    monitoring_tips = [
        "🕐 **監控頻率**：每日檢查關鍵指標，每週深度分析",
        "🎯 **關鍵指標**：重點關注 ROAS、CTR、CPA 變化趨勢",
        "📊 **警報設定**：ROAS < 1.5 或 CTR < 平均值 50% 時立即通知",
        "🔄 **調整週期**：小幅調整每 3-5 天，大幅調整每 1-2 週",
        "📈 **效果評估**：至少觀察 7 天數據才做效果判斷"
    ]

    for tip in monitoring_tips:
        st.markdown(f"- {tip}")

if __name__ == "__main__":
    main()