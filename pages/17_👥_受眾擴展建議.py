import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.data_loader import load_meta_ads_data
from utils.llm_service import get_llm_service
from utils.rag_service import RAGService
import json

st.set_page_config(page_title="受眾擴展建議", page_icon="👥", layout="wide")

def analyze_audience_performance(df):
    """分析受眾表現"""
    # 按受眾特徵分組分析
    audience_metrics = []

    # 按年齡分組
    if '年齡' in df.columns:
        age_groups = df.groupby('年齡').agg({
            '購買 ROAS（廣告投資報酬率）': 'mean',
            '花費金額 (TWD)': 'sum',
            '購買次數': 'sum',
            'CTR（全部）': 'mean',
            '每次購買的成本': 'mean'
        }).reset_index()
        age_groups['受眾類型'] = '年齡'
        age_groups['受眾'] = age_groups['年齡']
        audience_metrics.append(age_groups)

    # 按性別分組
    if '性別' in df.columns:
        gender_groups = df.groupby('性別').agg({
            '購買 ROAS（廣告投資報酬率）': 'mean',
            '花費金額 (TWD)': 'sum',
            '購買次數': 'sum',
            'CTR（全部）': 'mean',
            '每次購買的成本': 'mean'
        }).reset_index()
        gender_groups['受眾類型'] = '性別'
        gender_groups['受眾'] = gender_groups['性別']
        audience_metrics.append(gender_groups)

    # 按目標受眾分組
    if '目標' in df.columns:
        target_groups = df.groupby('目標').agg({
            '購買 ROAS（廣告投資報酬率）': 'mean',
            '花費金額 (TWD)': 'sum',
            '購買次數': 'sum',
            'CTR（全部）': 'mean',
            '每次購買的成本': 'mean'
        }).reset_index()
        target_groups['受眾類型'] = '目標'
        target_groups['受眾'] = target_groups['目標']
        audience_metrics.append(target_groups)

    if audience_metrics:
        return pd.concat(audience_metrics, ignore_index=True)
    return pd.DataFrame()

def get_top_audiences(df, min_roas=3.0, min_spend=1000):
    """獲取高效受眾組合"""
    # 找出高效的年齡 x 性別組合
    if '年齡' in df.columns and '性別' in df.columns:
        audience_combos = df.groupby(['年齡', '性別', '目標']).agg({
            '購買 ROAS（廣告投資報酬率）': 'mean',
            '花費金額 (TWD)': 'sum',
            '購買次數': 'sum',
            'CTR（全部）': 'mean',
            '每次購買的成本': 'mean',
            '觸及人數': 'sum'
        }).reset_index()

        # 篩選高效受眾
        top_audiences = audience_combos[
            (audience_combos['購買 ROAS（廣告投資報酬率）'] >= min_roas) &
            (audience_combos['花費金額 (TWD)'] >= min_spend)
        ].sort_values('購買 ROAS（廣告投資報酬率）', ascending=False)

        return top_audiences

    return pd.DataFrame()

def generate_audience_expansion_recommendations(top_audiences, all_data, use_rag=False):
    """使用 LLM + RAG 生成受眾擴展建議"""
    llm_service = get_llm_service()

    if not llm_service.is_available():
        return {"error": "LLM 服務目前無法使用"}

    # 準備高效受眾數據
    top_audiences_list = []
    for idx, row in top_audiences.head(5).iterrows():
        top_audiences_list.append({
            "年齡": str(row.get('年齡', '未知')),
            "性別": str(row.get('性別', '未知')),
            "目標受眾": str(row.get('目標', '未知')),
            "ROAS": f"{row.get('購買 ROAS（廣告投資報酬率）', 0):.2f}",
            "花費": f"NT$ {row.get('花費金額 (TWD)', 0):,.0f}",
            "購買次數": f"{row.get('購買次數', 0):.0f}",
            "CTR": f"{row.get('CTR（全部）', 0):.2f}%"
        })

    # 計算整體統計
    overall_stats = {
        "平均ROAS": f"{all_data['購買 ROAS（廣告投資報酬率）'].mean():.2f}",
        "總花費": f"NT$ {all_data['花費金額 (TWD)'].sum():,.0f}",
        "總購買": f"{all_data['購買次數'].sum():.0f}",
        "平均CTR": f"{all_data['CTR（全部）'].mean():.2f}%"
    }

    # RAG 增強：獲取歷史成功案例
    rag_context = ""
    if use_rag:
        try:
            rag = RAGService()
            if rag.load_knowledge_base("ad_creatives"):
                # 搜尋高效受眾案例
                query = "高 ROAS 受眾組合和特徵"
                similar_ads = rag.search_similar_ads(query, k=5)

                if similar_ads:
                    rag_context = "\n\n## 📚 歷史成功受眾案例\n\n"
                    for i, doc in enumerate(similar_ads, 1):
                        age = doc.metadata.get('age', '未知')
                        gender = doc.metadata.get('gender', '未知')
                        roas = doc.metadata.get('roas', 0)
                        ctr = doc.metadata.get('ctr', 0)
                        rag_context += f"### 案例 {i}（ROAS {roas:.2f}）\n"
                        rag_context += f"- 受眾：年齡 {age}，性別 {gender}\n"
                        rag_context += f"- CTR：{ctr:.2f}%\n"
                        rag_context += f"- 標題：{doc.metadata.get('headline', '未知')[:50]}\n\n"
                    rag_context += "**請參考以上案例的受眾特徵模式。**\n"
        except Exception as e:
            pass

    # 建構 Prompt
    prompt = f"""
你是專業的 Meta 廣告受眾策略顧問。請根據以下數據提供受眾擴展建議。

## 目前高效受眾（ROAS ≥ 3.0）
{json.dumps(top_audiences_list, ensure_ascii=False, indent=2)}

## 整體表現
{json.dumps(overall_stats, ensure_ascii=False, indent=2)}{rag_context}

## 請提供以下分析：

### 1. 🔍 高效受眾特徵分析
分析目前表現最好的受眾共同特徵：
- 年齡層特點
- 性別偏好
- 興趣/目標受眾模式
- 成功因素

### 2. 👥 受眾擴展建議（5-8 個新受眾）

**對每個建議受眾請提供**：
- 🎯 **受眾描述**：年齡、性別、興趣組合
- 📊 **相似度**：與現有高效受眾的相似程度（高/中/低）
- 💰 **預期 ROAS**：預估表現（樂觀/保守估計）
- 🧪 **測試策略**：
  - 建議測試預算（TWD）
  - 測試期長度（天數）
  - 成功指標（何時擴大/暫停）
- 🚦 **優先級**：🔴 高 / 🟡 中 / 🟢 低

### 3. 💡 Lookalike 受眾建議
基於高效受眾，推薦 Lookalike 受眾策略：
- 建議使用哪些來源受眾
- 相似度百分比（1%-10%）
- 地理位置建議
- 預期規模和表現

### 4. ⚠️ 避免的受眾
基於數據，建議避免或謹慎測試的受眾類型，並說明原因。

### 5. 📋 執行計畫
30 天受眾擴展路線圖：
- Week 1：優先測試哪些受眾
- Week 2-3：持續優化
- Week 4：擴大成功受眾

請以清晰、專業、可執行的方式回答，使用繁體中文。
重點是**數據驅動的具體建議**，不要泛泛而談。
"""

    # 調用 LLM
    response = llm_service.generate_insights(
        prompt,
        model="gpt-3.5-turbo",
        max_tokens=2500,
        temperature=0.7
    )

    return response

def display_audience_recommendations(recommendations):
    """顯示受眾擴展建議"""
    st.markdown("### 🤖 AI 受眾擴展建議")

    # 使用容器顯示建議
    with st.container():
        st.markdown(recommendations)

def main():
    st.title("👥 受眾擴展建議")
    st.markdown("基於高效受眾數據，使用 AI 推薦新的受眾測試機會")

    # 載入數據
    df = load_meta_ads_data()
    if df is None:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    # 側邊欄設定
    st.sidebar.header("⚙️ 分析設定")

    min_roas = st.sidebar.number_input(
        "最低 ROAS 門檻",
        min_value=1.0,
        max_value=10.0,
        value=3.0,
        step=0.5,
        help="篩選高效受眾的 ROAS 門檻"
    )

    min_spend = st.sidebar.number_input(
        "最低花費金額 (TWD)",
        min_value=100,
        max_value=10000,
        value=1000,
        step=500,
        help="篩選有足夠數據量的受眾"
    )

    use_rag = st.sidebar.checkbox(
        "🧠 啟用智能增強（RAG）",
        value=True,
        help="使用 RAG 技術參考歷史成功受眾案例"
    )

    st.sidebar.divider()

    # 主要內容
    tab1, tab2, tab3 = st.tabs(["📊 受眾表現分析", "🎯 高效受眾", "🚀 AI 擴展建議"])

    with tab1:
        st.markdown("## 📊 受眾表現分析")

        # 分析受眾表現
        audience_perf = analyze_audience_performance(df)

        if not audience_perf.empty:
            # 按受眾類型顯示
            for audience_type in audience_perf['受眾類型'].unique():
                st.markdown(f"### {audience_type}別表現")

                type_data = audience_perf[audience_perf['受眾類型'] == audience_type]

                # 視覺化
                fig = make_subplots(
                    rows=1, cols=2,
                    subplot_titles=('ROAS 表現', 'CTR 表現'),
                    specs=[[{"type": "bar"}, {"type": "bar"}]]
                )

                # ROAS 圖表
                fig.add_trace(
                    go.Bar(
                        x=type_data['受眾'],
                        y=type_data['購買 ROAS（廣告投資報酬率）'],
                        name='ROAS',
                        marker_color='lightblue'
                    ),
                    row=1, col=1
                )

                # CTR 圖表
                fig.add_trace(
                    go.Bar(
                        x=type_data['受眾'],
                        y=type_data['CTR（全部）'],
                        name='CTR',
                        marker_color='lightgreen'
                    ),
                    row=1, col=2
                )

                fig.update_layout(height=400, showlegend=False)
                fig.update_xaxes(title_text="受眾", row=1, col=1)
                fig.update_xaxes(title_text="受眾", row=1, col=2)
                fig.update_yaxes(title_text="ROAS", row=1, col=1)
                fig.update_yaxes(title_text="CTR (%)", row=1, col=2)

                st.plotly_chart(fig, use_container_width=True)

                # 數據表格
                st.dataframe(
                    type_data[[
                        '受眾', '購買 ROAS（廣告投資報酬率）',
                        '花費金額 (TWD)', '購買次數', 'CTR（全部）', '每次購買的成本'
                    ]].sort_values('購買 ROAS（廣告投資報酬率）', ascending=False),
                    use_container_width=True,
                    column_config={
                        "受眾": st.column_config.TextColumn("受眾", width="medium"),
                        "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
                        "花費金額 (TWD)": st.column_config.NumberColumn("花費", format="%.0f"),
                        "購買次數": st.column_config.NumberColumn("購買", format="%.0f"),
                        "CTR（全部）": st.column_config.NumberColumn("CTR", format="%.2f%%"),
                        "每次購買的成本": st.column_config.NumberColumn("CPA", format="%.0f")
                    }
                )

                st.divider()
        else:
            st.warning("無法分析受眾表現，請檢查數據是否包含受眾欄位。")

    with tab2:
        st.markdown("## 🎯 高效受眾組合")
        st.info(f"篩選條件：ROAS ≥ {min_roas}，花費 ≥ NT$ {min_spend:,.0f}")

        # 獲取高效受眾
        top_audiences = get_top_audiences(df, min_roas, min_spend)

        if not top_audiences.empty:
            st.markdown(f"### 🏆 找到 {len(top_audiences)} 個高效受眾組合")

            # 顯示前 10 名
            st.dataframe(
                top_audiences.head(10),
                use_container_width=True,
                column_config={
                    "年齡": st.column_config.TextColumn("年齡", width="small"),
                    "性別": st.column_config.TextColumn("性別", width="small"),
                    "目標": st.column_config.TextColumn("目標受眾", width="medium"),
                    "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
                    "花費金額 (TWD)": st.column_config.NumberColumn("花費", format="%.0f"),
                    "購買次數": st.column_config.NumberColumn("購買", format="%.0f"),
                    "CTR（全部）": st.column_config.NumberColumn("CTR", format="%.2f%%"),
                    "每次購買的成本": st.column_config.NumberColumn("CPA", format="%.0f"),
                    "觸及人數": st.column_config.NumberColumn("觸及", format="%.0f")
                }
            )

            # 視覺化 Top 5
            st.markdown("### 📊 Top 5 受眾 ROAS 分佈")
            top5 = top_audiences.head(5).copy()
            top5['受眾標籤'] = top5.apply(
                lambda x: f"{x['年齡']} / {x['性別']} / {x['目標']}", axis=1
            )

            fig = px.bar(
                top5,
                x='受眾標籤',
                y='購買 ROAS（廣告投資報酬率）',
                title='Top 5 高效受眾 ROAS',
                labels={'受眾標籤': '受眾組合', '購買 ROAS（廣告投資報酬率）': 'ROAS'},
                color='購買 ROAS（廣告投資報酬率）',
                color_continuous_scale='Viridis'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.warning(f"未找到符合條件的高效受眾（ROAS ≥ {min_roas}，花費 ≥ NT$ {min_spend:,.0f}）")
            st.info("💡 建議：降低篩選門檻或累積更多數據")

    with tab3:
        st.markdown("## 🚀 AI 受眾擴展建議")

        # 檢查是否有高效受眾
        top_audiences = get_top_audiences(df, min_roas, min_spend)

        if top_audiences.empty:
            st.warning("需要至少 1 個高效受眾才能生成擴展建議。")
            st.info("💡 請在「高效受眾」標籤中調整篩選條件")
            return

        llm_service = get_llm_service()

        if not llm_service.is_available():
            st.error("❌ LLM 服務目前無法使用，請檢查 OPENAI_API_KEY 設定")
            return

        st.info(f"✅ 找到 {len(top_audiences)} 個高效受眾，準備生成擴展建議")

        if use_rag:
            st.success("🧠 智能增強已啟用 - AI 將參考歷史成功受眾案例")

        # 生成建議按鈕
        if st.button("🚀 生成受眾擴展建議", type="primary"):
            with st.spinner("AI 正在分析受眾數據並生成建議..."):
                recommendations = generate_audience_expansion_recommendations(
                    top_audiences,
                    df,
                    use_rag=use_rag
                )

                if isinstance(recommendations, dict) and "error" in recommendations:
                    st.error(f"❌ 生成建議失敗：{recommendations['error']}")
                else:
                    st.success("✅ AI 受眾擴展建議生成完成！")

                    # 顯示建議
                    display_audience_recommendations(recommendations)

                    # 儲存到 session state
                    st.session_state['audience_recommendations'] = recommendations
                    st.session_state['audience_recommendations_time'] = pd.Timestamp.now()

        # 顯示歷史建議
        if 'audience_recommendations' in st.session_state:
            st.markdown("---")
            st.markdown("### 📚 最近生成的建議")

            if 'audience_recommendations_time' in st.session_state:
                gen_time = st.session_state['audience_recommendations_time']
                st.caption(f"生成時間：{gen_time.strftime('%Y-%m-%d %H:%M:%S')}")

            with st.expander("查看完整建議", expanded=False):
                st.markdown(st.session_state['audience_recommendations'])

    # 頁面底部提示
    st.markdown("---")
    st.markdown("""
    ### 💡 使用建議

    **受眾擴展最佳實踐**：
    1. 📊 **數據驅動**：優先測試與高效受眾相似的組合
    2. 🧪 **小步快跑**：每次測試 2-3 個新受眾，避免分散預算
    3. 📈 **持續優化**：每週檢視測試結果，快速決策擴大/暫停
    4. 💰 **預算控制**：新受眾測試預算不超過總預算的 20%
    5. ⏱️ **給予時間**：至少測試 7 天才能判斷受眾表現

    **Lookalike 受眾技巧**：
    - 使用購買者作為來源（最高品質）
    - 1% 相似度最精準但規模小，3-5% 較平衡
    - 定期更新來源受眾（30-60 天）
    """)

if __name__ == "__main__":
    main()
