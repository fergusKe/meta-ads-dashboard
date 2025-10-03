import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from openai import OpenAI
import os
from utils.data_loader import load_meta_ads_data

st.set_page_config(page_title="智能投放策略", page_icon="🎯", layout="wide")

def analyze_top_performing_ads(df):
    """分析表現最佳的廣告"""
    if df is None or df.empty:
        return {}

    # 先篩選有效的廣告數據
    # 只保留有實際購買轉換的廣告（ROAS > 0 且購買次數 > 0）
    valid_ads = df[
        (df['購買 ROAS（廣告投資報酬率）'] > 0) &
        (df['購買次數'] > 0) &
        (df['觸及人數'] > 0) &
        (df['花費金額 (TWD)'] > 0)
    ].copy()

    if valid_ads.empty:
        return {
            'top_campaigns': [],
            'avg_roas': 0,
            'avg_ctr': 0,
            'avg_conversion': 0,
            'common_ages': {},
            'common_genders': {},
            'common_objectives': {}
        }

    # 計算轉換率
    valid_ads['轉換率'] = (valid_ads['購買次數'] / valid_ads['觸及人數']) * 100

    # 正規化分數 (0-100)
    max_roas = valid_ads['購買 ROAS（廣告投資報酬率）'].max()
    max_ctr = valid_ads['CTR（全部）'].max()
    max_conversion = valid_ads['轉換率'].max()

    if max_roas > 0:
        roas_norm = (valid_ads['購買 ROAS（廣告投資報酬率）'] / max_roas) * 40
    else:
        roas_norm = 0

    if max_ctr > 0:
        ctr_norm = (valid_ads['CTR（全部）'] / max_ctr) * 30
    else:
        ctr_norm = 0

    if max_conversion > 0:
        conversion_norm = (valid_ads['轉換率'] / max_conversion) * 30
    else:
        conversion_norm = 0

    valid_ads['綜合評分'] = roas_norm + ctr_norm + conversion_norm

    # 取得前5名表現最佳的廣告
    top_ads = valid_ads.nlargest(5, '綜合評分')

    analysis = {
        'top_campaigns': top_ads[['行銷活動名稱', '廣告組合名稱', '目標', '年齡', '性別',
                                  '購買 ROAS（廣告投資報酬率）', 'CTR（全部）', '轉換率', '綜合評分']].to_dict('records'),
        'avg_roas': top_ads['購買 ROAS（廣告投資報酬率）'].mean(),
        'avg_ctr': top_ads['CTR（全部）'].mean(),
        'avg_conversion': top_ads['轉換率'].mean(),
        'common_ages': top_ads['年齡'].value_counts().head(3).to_dict(),
        'common_genders': top_ads['性別'].value_counts().to_dict(),
        'common_objectives': top_ads['目標'].value_counts().head(3).to_dict()
    }

    return analysis

def recommend_target_audiences(df):
    """推薦最佳投放受眾"""
    if df is None or df.empty:
        return {}

    # 先篩選有效的廣告數據（只分析有轉換的廣告）
    valid_ads = df[
        (df['購買 ROAS（廣告投資報酬率）'] > 0) &
        (df['購買次數'] > 0) &
        (df['觸及人數'] > 0) &
        (df['花費金額 (TWD)'] > 0)
    ].copy()

    if valid_ads.empty:
        return {}

    # 按受眾特徵分組分析
    audience_analysis = {}

    # 年齡分析
    age_performance = valid_ads.groupby('年齡').agg({
        '購買 ROAS（廣告投資報酬率）': 'mean',
        'CTR（全部）': 'mean',
        '每次購買的成本': 'mean',
        '花費金額 (TWD)': 'sum',
        '購買次數': 'sum',
        '觸及人數': 'sum'
    }).round(2)

    # 性別分析
    gender_performance = valid_ads.groupby('性別').agg({
        '購買 ROAS（廣告投資報酬率）': 'mean',
        'CTR（全部）': 'mean',
        '每次購買的成本': 'mean',
        '花費金額 (TWD)': 'sum',
        '購買次數': 'sum'
    }).round(2)

    # 目標類型分析
    objective_performance = valid_ads.groupby('目標').agg({
        '購買 ROAS（廣告投資報酬率）': 'mean',
        'CTR（全部）': 'mean',
        '每次購買的成本': 'mean',
        '花費金額 (TWD)': 'sum',
        '購買次數': 'sum'
    }).round(2)

    # 計算受眾組合的表現（年齡+性別）
    audience_combo_performance = valid_ads.groupby(['年齡', '性別']).agg({
        '購買 ROAS（廣告投資報酬率）': 'mean',
        'CTR（全部）': 'mean',
        '每次購買的成本': 'mean',
        '花費金額 (TWD)': 'sum',
        '購買次數': 'sum'
    }).round(2)

    # 計算三維組合表現（年齡+性別+目標）
    full_combo_performance = valid_ads.groupby(['年齡', '性別', '目標']).agg({
        '購買 ROAS（廣告投資報酬率）': 'mean',
        'CTR（全部）': 'mean',
        '每次購買的成本': 'mean',
        '花費金額 (TWD)': 'sum',
        '購買次數': 'sum'
    }).round(2)

    audience_analysis = {
        'age_performance': age_performance,
        'gender_performance': gender_performance,
        'objective_performance': objective_performance,
        'combo_performance': audience_combo_performance,
        'full_combo_performance': full_combo_performance,
        'best_age': age_performance['購買 ROAS（廣告投資報酬率）'].idxmax() if not age_performance.empty else '未知',
        'best_gender': gender_performance['購買 ROAS（廣告投資報酬率）'].idxmax() if not gender_performance.empty else '未知',
        'best_objective': objective_performance['購買 ROAS（廣告投資報酬率）'].idxmax() if not objective_performance.empty else '未知'
    }

    return audience_analysis

def generate_targeted_content_strategy(top_ads, audience_recommendations):
    """基於最佳廣告和受眾生成內容策略"""
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return "無法連接 OpenAI API，請檢查 API 設定"

        client = OpenAI(api_key=api_key)

        # 準備分析摘要
        top_ad_summary = ""
        if top_ads and 'top_campaigns' in top_ads:
            for i, ad in enumerate(top_ads['top_campaigns'][:3], 1):
                top_ad_summary += f"""
{i}. 活動：{ad.get('行銷活動名稱', '未知')}
   - 目標受眾：{ad.get('年齡', '未知')} {ad.get('性別', '未知')}
   - ROAS：{ad.get('購買 ROAS（廣告投資報酬率）', 0):.2f}
   - CTR：{ad.get('CTR（全部）', 0):.3f}%
   - 轉換率：{ad.get('轉換率', 0):.2f}%
"""

        audience_summary = ""
        if audience_recommendations:
            audience_summary = f"""
最佳年齡層：{audience_recommendations.get('best_age', '未知')}
最佳性別：{audience_recommendations.get('best_gender', '未知')}
最佳目標類型：{audience_recommendations.get('best_objective', '未知')}
"""

        prompt = f"""
作為耘初茶食的廣告策略專家，請基於以下數據分析，提供具體的投放策略建議：

表現最佳的廣告分析：
{top_ad_summary}

受眾分析結果：
{audience_summary}

請提供：
1. 下一波廣告投放的受眾建議（年齡、性別、興趣）
2. 針對該受眾的文案方向建議（3個不同角度）
3. 視覺設計建議（圖片風格、色調、元素）
4. 預算分配建議
5. 投放時機建議

要求簡潔實用，每個建議不超過50字。
"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是專業的數位廣告策略顧問，專精於Meta廣告投放策略。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"策略生成失敗：{str(e)}"

def create_performance_comparison_chart(df):
    """創建表現對比圖表"""
    if df is None or df.empty:
        return None

    # 先篩選有效的廣告數據
    valid_ads = df[
        (df['購買 ROAS（廣告投資報酬率）'] > 0) &
        (df['購買次數'] > 0) &
        (df['觸及人數'] > 0) &
        (df['花費金額 (TWD)'] > 0)
    ].copy()

    if valid_ads.empty:
        return None

    # 計算轉換率
    valid_ads['轉換率'] = (valid_ads['購買次數'] / valid_ads['觸及人數']) * 100

    # 正規化分數
    max_roas = valid_ads['購買 ROAS（廣告投資報酬率）'].max()
    max_ctr = valid_ads['CTR（全部）'].max()
    max_conversion = valid_ads['轉換率'].max()

    if max_roas > 0:
        roas_norm = (valid_ads['購買 ROAS（廣告投資報酬率）'] / max_roas) * 40
    else:
        roas_norm = 0

    if max_ctr > 0:
        ctr_norm = (valid_ads['CTR（全部）'] / max_ctr) * 30
    else:
        ctr_norm = 0

    if max_conversion > 0:
        conversion_norm = (valid_ads['轉換率'] / max_conversion) * 30
    else:
        conversion_norm = 0

    valid_ads['綜合評分'] = roas_norm + ctr_norm + conversion_norm

    # 取前10名
    top_ads = valid_ads.nlargest(10, '綜合評分')

    fig = go.Figure()

    # 添加氣泡圖
    fig.add_trace(go.Scatter(
        x=top_ads['購買 ROAS（廣告投資報酬率）'],
        y=top_ads['CTR（全部）'] * 100,
        mode='markers',
        marker=dict(
            size=top_ads['花費金額 (TWD)'] / 1000,  # 按花費大小調整氣泡大小
            sizemin=8,  # 最小氣泡大小
            color=top_ads['綜合評分'],
            colorscale='Plasma',  # 改用更明亮的顏色配置
            showscale=True,
            colorbar=dict(title="綜合評分"),
            line=dict(color='white', width=2),  # 添加白色邊框
            opacity=0.8  # 稍微透明以便重疊時能看到
        ),
        text=top_ads['行銷活動名稱'],
        hovertemplate='<b>%{text}</b><br>' +
                      'ROAS: %{x:.2f}<br>' +
                      'CTR: %{y:.3f}%<br>' +
                      '花費: NT$ %{marker.size}k<br>' +
                      '綜合評分: %{marker.color:.1f}<br>' +
                      '<extra></extra>',
        name='廣告表現'
    ))

    fig.update_layout(
        title='廣告表現對比分析（氣泡大小 = 花費金額）',
        xaxis_title='購買 ROAS',
        yaxis_title='CTR (%)',
        height=500
    )

    return fig

def create_audience_performance_chart(audience_analysis):
    """創建受眾表現圖表"""
    if not audience_analysis or 'age_performance' not in audience_analysis:
        return None

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('年齡層 ROAS 表現', '性別 ROAS 表現', '年齡層 CTR 表現', '性別 CTR 表現'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )

    # 年齡層 ROAS
    age_data = audience_analysis['age_performance']
    fig.add_trace(
        go.Bar(x=age_data.index, y=age_data['購買 ROAS（廣告投資報酬率）'], name='年齡層 ROAS'),
        row=1, col=1
    )

    # 性別 ROAS
    gender_data = audience_analysis['gender_performance']
    fig.add_trace(
        go.Bar(x=gender_data.index, y=gender_data['購買 ROAS（廣告投資報酬率）'], name='性別 ROAS'),
        row=1, col=2
    )

    # 年齡層 CTR
    fig.add_trace(
        go.Bar(x=age_data.index, y=age_data['CTR（全部）'] * 100, name='年齡層 CTR'),
        row=2, col=1
    )

    # 性別 CTR
    fig.add_trace(
        go.Bar(x=gender_data.index, y=gender_data['CTR（全部）'] * 100, name='性別 CTR'),
        row=2, col=2
    )

    fig.update_layout(height=600, showlegend=False, title_text="受眾表現詳細分析")
    return fig

def main():
    st.title("🎯 智能投放策略")
    st.markdown("基於數據洞察的精準投放策略制定")

    # 載入數據
    df = load_meta_ads_data()

    if df is None:
        st.error("❌ 無法載入數據，請檢查數據檔案")
        return

    # 主要分析
    st.header("🏆 表現最佳廣告分析")

    top_ads_analysis = analyze_top_performing_ads(df)

    if top_ads_analysis and 'top_campaigns' in top_ads_analysis:
        # 顯示前5名廣告
        st.subheader("📊 TOP 5 表現最佳廣告")

        top_campaigns_df = pd.DataFrame(top_ads_analysis['top_campaigns'])

        # 格式化顯示
        for i, campaign in enumerate(top_campaigns_df.to_dict('records'), 1):
            with st.container():
                st.markdown(f"### 🥇 第 {i} 名")

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        "ROAS",
                        f"{campaign.get('購買 ROAS（廣告投資報酬率）', 0):.2f}",
                        delta=f"平均: {top_ads_analysis.get('avg_roas', 0):.2f}"
                    )

                with col2:
                    st.metric(
                        "CTR",
                        f"{campaign.get('CTR（全部）', 0):.3f}%",
                        delta=f"平均: {top_ads_analysis.get('avg_ctr', 0):.3f}%"
                    )

                with col3:
                    st.metric(
                        "轉換率",
                        f"{campaign.get('轉換率', 0):.2f}%",
                        delta=f"平均: {top_ads_analysis.get('avg_conversion', 0):.2f}%"
                    )

                with col4:
                    st.metric(
                        "綜合評分",
                        f"{campaign.get('綜合評分', 0):.1f}",
                        delta="滿分: 100"
                    )

                # 受眾資訊
                st.info(f"📋 **活動名稱**：{campaign.get('行銷活動名稱', '未知')}")
                st.info(f"🎯 **目標受眾**：{campaign.get('年齡', '未知')} {campaign.get('性別', '未知')} | 目標：{campaign.get('目標', '未知')}")

                st.divider()

        # 表現對比圖表
        performance_chart = create_performance_comparison_chart(df)
        if performance_chart:
            st.plotly_chart(performance_chart, use_container_width=True)

    # 受眾推薦分析
    st.header("👥 最佳投放受眾推薦")

    audience_recommendations = recommend_target_audiences(df)

    if audience_recommendations:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("🎯 推薦年齡層")
            st.success(f"**{audience_recommendations.get('best_age', '未知')}**")

            if 'age_performance' in audience_recommendations:
                age_data = audience_recommendations['age_performance']
                best_age = audience_recommendations.get('best_age')
                if best_age in age_data.index:
                    st.metric("平均 ROAS", f"{age_data.loc[best_age, '購買 ROAS（廣告投資報酬率）']:.2f}")
                    st.metric("平均 CTR", f"{age_data.loc[best_age, 'CTR（全部）'] * 100:.3f}%")

        with col2:
            st.subheader("⚧️ 推薦性別")
            st.success(f"**{audience_recommendations.get('best_gender', '未知')}**")

            if 'gender_performance' in audience_recommendations:
                gender_data = audience_recommendations['gender_performance']
                best_gender = audience_recommendations.get('best_gender')
                if best_gender in gender_data.index:
                    st.metric("平均 ROAS", f"{gender_data.loc[best_gender, '購買 ROAS（廣告投資報酬率）']:.2f}")
                    st.metric("平均 CTR", f"{gender_data.loc[best_gender, 'CTR（全部）'] * 100:.3f}%")

        with col3:
            st.subheader("🎪 推薦目標類型")
            st.success(f"**{audience_recommendations.get('best_objective', '未知')}**")

            if 'objective_performance' in audience_recommendations:
                obj_data = audience_recommendations['objective_performance']
                best_obj = audience_recommendations.get('best_objective')
                if best_obj in obj_data.index:
                    st.metric("平均 ROAS", f"{obj_data.loc[best_obj, '購買 ROAS（廣告投資報酬率）']:.2f}")
                    st.metric("平均 CTR", f"{obj_data.loc[best_obj, 'CTR（全部）'] * 100:.3f}%")

        # 受眾表現圖表
        audience_chart = create_audience_performance_chart(audience_recommendations)
        if audience_chart:
            st.plotly_chart(audience_chart, use_container_width=True)

        # 完整受眾組合分析
        st.subheader("🔥 完整受眾組合表現分析")
        if 'combo_performance' in audience_recommendations:
            combo_data = audience_recommendations['combo_performance']
            if not combo_data.empty:
                # 按ROAS排序，顯示前10名組合
                top_combos = combo_data.sort_values('購買 ROAS（廣告投資報酬率）', ascending=False).head(10)

                st.markdown("### 📊 TOP 10 受眾組合表現")

                # 創建表格顯示
                combo_display = []
                for idx, (combo_name, combo_data_row) in enumerate(top_combos.iterrows(), 1):
                    age, gender = combo_name
                    combo_display.append({
                        '排名': f"#{idx}",
                        '年齡層': age,
                        '性別': gender,
                        'ROAS': f"{combo_data_row['購買 ROAS（廣告投資報酬率）']:.2f}",
                        'CTR (%)': f"{combo_data_row['CTR（全部）'] * 100:.3f}",
                        'CPA (TWD)': f"{combo_data_row['每次購買的成本']:.0f}",
                        '總花費 (TWD)': f"{combo_data_row['花費金額 (TWD)']:,.0f}",
                        '購買次數': f"{combo_data_row['購買次數']:.0f}"
                    })

                combo_df = pd.DataFrame(combo_display)
                st.dataframe(combo_df, use_container_width=True, hide_index=True)

                # 顯示最佳組合詳情
                best_combo = top_combos.iloc[0]
                best_combo_name = top_combos.index[0]

                st.success(f"🎯 **表現最佳組合**：{best_combo_name[0]} + {best_combo_name[1]}")

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("ROAS", f"{best_combo['購買 ROAS（廣告投資報酬率）']:.2f}")
                with col2:
                    st.metric("CTR", f"{best_combo['CTR（全部）'] * 100:.3f}%")
                with col3:
                    st.metric("CPA", f"NT$ {best_combo['每次購買的成本']:.0f}")
                with col4:
                    st.metric("總購買次數", f"{best_combo['購買次數']:.0f}")

                # 組合效益分析
                st.markdown("### 💡 組合效益洞察")

                # 計算平均值
                avg_roas = top_combos['購買 ROAS（廣告投資報酬率）'].mean()
                avg_ctr = top_combos['CTR（全部）'].mean() * 100
                avg_cpa = top_combos['每次購買的成本'].mean()

                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"""
                    **💰 投資效益分析**
                    - 最高 ROAS：{top_combos['購買 ROAS（廣告投資報酬率）'].max():.2f}
                    - 平均 ROAS：{avg_roas:.2f}
                    - ROAS 標準差：{top_combos['購買 ROAS（廣告投資報酬率）'].std():.2f}
                    """)

                with col2:
                    st.info(f"""
                    **🎯 點擊效益分析**
                    - 最高 CTR：{top_combos['CTR（全部）'].max() * 100:.3f}%
                    - 平均 CTR：{avg_ctr:.3f}%
                    - 最低 CPA：NT$ {top_combos['每次購買的成本'].min():.0f}
                    """)

        # 完整三維組合分析
        st.subheader("🎯 完整投放組合策略（年齡+性別+目標）")
        if 'full_combo_performance' in audience_recommendations:
            full_combo_data = audience_recommendations['full_combo_performance']
            if not full_combo_data.empty:
                # 按ROAS排序，顯示前15名組合
                top_full_combos = full_combo_data.sort_values('購買 ROAS（廣告投資報酬率）', ascending=False).head(15)

                st.markdown("### 🚀 TOP 15 完整投放策略組合")

                # 創建表格顯示
                full_combo_display = []
                for idx, (combo_name, combo_data_row) in enumerate(top_full_combos.iterrows(), 1):
                    age, gender, objective = combo_name
                    # 計算效益評級
                    roas_value = combo_data_row['購買 ROAS（廣告投資報酬率）']
                    if roas_value >= 5:
                        grade = "🏆 優秀"
                    elif roas_value >= 3:
                        grade = "🥈 良好"
                    elif roas_value >= 2:
                        grade = "🥉 普通"
                    else:
                        grade = "📉 待改善"

                    full_combo_display.append({
                        '排名': f"#{idx}",
                        '年齡層': age,
                        '性別': gender,
                        '投放目標': objective,
                        'ROAS': f"{roas_value:.2f}",
                        'CTR (%)': f"{combo_data_row['CTR（全部）'] * 100:.3f}",
                        'CPA (TWD)': f"{combo_data_row['每次購買的成本']:.0f}",
                        '總花費 (TWD)': f"{combo_data_row['花費金額 (TWD)']:,.0f}",
                        '購買次數': f"{combo_data_row['購買次數']:.0f}",
                        '效益評級': grade
                    })

                full_combo_df = pd.DataFrame(full_combo_display)
                st.dataframe(full_combo_df, use_container_width=True, hide_index=True)

                # 最佳完整組合詳情
                best_full_combo = top_full_combos.iloc[0]
                best_full_combo_name = top_full_combos.index[0]

                st.success(f"🎯 **最佳完整投放策略**：{best_full_combo_name[0]} + {best_full_combo_name[1]} + {best_full_combo_name[2]}")

                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("ROAS", f"{best_full_combo['購買 ROAS（廣告投資報酬率）']:.2f}")
                with col2:
                    st.metric("CTR", f"{best_full_combo['CTR（全部）'] * 100:.3f}%")
                with col3:
                    st.metric("CPA", f"NT$ {best_full_combo['每次購買的成本']:.0f}")
                with col4:
                    st.metric("總花費", f"NT$ {best_full_combo['花費金額 (TWD)']:,.0f}")
                with col5:
                    st.metric("購買次數", f"{best_full_combo['購買次數']:.0f}")

                # 策略建議
                st.markdown("### 💡 投放策略建議")
                best_age, best_gender, best_objective = best_full_combo_name

                strategy_text = f"""
                **🎯 推薦投放策略組合：**
                - **目標受眾**：{best_age} {best_gender}
                - **投放目標**：{best_objective}
                - **預期ROAS**：{best_full_combo['購買 ROAS（廣告投資報酬率）']:.2f}
                - **預期CTR**：{best_full_combo['CTR（全部）'] * 100:.3f}%
                - **預期CPA**：NT$ {best_full_combo['每次購買的成本']:.0f}

                **📊 為什麼選擇這個組合：**
                1. 在所有測試組合中 ROAS 表現最佳
                2. CTR 表現{"優秀" if best_full_combo['CTR（全部）'] * 100 > 1 else "良好"}
                3. 購買成本{"較低" if best_full_combo['每次購買的成本'] < 500 else "合理"}
                4. 已有{best_full_combo['購買次數']:.0f}次成功購買轉換驗證
                """

                st.info(strategy_text)

    # AI 投放策略建議
    st.header("🤖 AI 投放策略建議")

    with st.spinner("AI 正在分析數據並生成投放策略..."):
        ai_strategy = generate_targeted_content_strategy(top_ads_analysis, audience_recommendations)

    if ai_strategy:
        st.markdown("### 🎯 個人化投放策略")
        st.markdown(ai_strategy)

    # 實用工具
    st.header("🛠️ 實用投放工具")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📝 快速文案生成")
        if st.button("🚀 基於最佳受眾生成文案", use_container_width=True):
            if audience_recommendations and 'full_combo_performance' in audience_recommendations:
                full_combo_data = audience_recommendations['full_combo_performance']
                if not full_combo_data.empty:
                    best_combo = full_combo_data.sort_values('購買 ROAS（廣告投資報酬率）', ascending=False).index[0]
                    best_age, best_gender, best_objective = best_combo

                    # 跳轉到 AI 文案生成頁面並預填完整參數
                    st.session_state.target_audience = f"{best_age} {best_gender}"
                    st.session_state.campaign_objective = best_objective
                    st.session_state.auto_generate_copy = True  # 設置自動生成標記
                    st.session_state.navigate_to = "✍️ AI 文案生成"
                    st.rerun()

    with col2:
        st.subheader("🎨 智能圖片設計")
        if st.button("🎨 基於最佳受眾生成圖片", use_container_width=True):
            if audience_recommendations and 'full_combo_performance' in audience_recommendations:
                full_combo_data = audience_recommendations['full_combo_performance']
                if not full_combo_data.empty:
                    best_combo = full_combo_data.sort_values('購買 ROAS（廣告投資報酬率）', ascending=False).index[0]
                    best_age, best_gender, best_objective = best_combo

                    # 跳轉到 AI 圖片生成頁面並預填完整參數
                    st.session_state.target_audience = f"{best_age} {best_gender}"
                    st.session_state.campaign_objective = best_objective
                    st.session_state.auto_generate_image = True  # 設置自動生成標記
                    st.session_state.navigate_to = "🎨 AI 圖片生成"
                    st.rerun()

    # 投放檢查清單
    st.header("✅ 投放前檢查清單")

    # 動態生成檢查清單
    checklist_items = []

    if audience_recommendations and 'full_combo_performance' in audience_recommendations:
        full_combo_data = audience_recommendations['full_combo_performance']
        if not full_combo_data.empty:
            best_combo = full_combo_data.sort_values('購買 ROAS（廣告投資報酬率）', ascending=False).index[0]
            best_age, best_gender, best_objective = best_combo
            best_roas = full_combo_data.sort_values('購買 ROAS（廣告投資報酬率）', ascending=False).iloc[0]['購買 ROAS（廣告投資報酬率）']

            checklist_items = [
                f"✅ 已確認最佳完整組合：{best_age} {best_gender} + {best_objective}",
                f"✅ 目標ROAS設定：{best_roas:.2f}（基於歷史最佳表現）",
                "✅ 文案已針對目標受眾優化",
                "✅ 圖片風格符合受眾偏好",
                "✅ 預算分配基於歷史表現數據",
                "✅ 投放時間設定完成",
                "✅ 轉換追蹤設定正確",
                "✅ A/B 測試計劃準備就緒（測試不同創意素材）"
            ]
        else:
            checklist_items = [
                "⚠️ 無法分析受眾組合，請檢查數據",
                "✅ 文案已針對目標受眾優化",
                "✅ 圖片風格符合受眾偏好",
                "✅ 預算分配基於歷史表現數據",
                "✅ 投放時間設定完成",
                "✅ 轉換追蹤設定正確",
                "✅ A/B 測試計劃準備就緒"
            ]
    else:
        checklist_items = [
            "⚠️ 無法載入受眾數據",
            "✅ 文案已針對目標受眾優化",
            "✅ 圖片風格符合受眾偏好",
            "✅ 預算分配基於歷史表現數據",
            "✅ 投放時間設定完成",
            "✅ 轉換追蹤設定正確",
            "✅ A/B 測試計劃準備就緒"
        ]

    for item in checklist_items:
        st.markdown(f"- {item}")

if __name__ == "__main__":
    main()