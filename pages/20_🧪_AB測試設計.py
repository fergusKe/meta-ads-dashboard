import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.data_loader import load_meta_ads_data
from utils.llm_service import get_llm_service
from utils.rag_service import RAGService
import json
from scipy import stats

st.set_page_config(page_title="A/B 測試設計", page_icon="🧪", layout="wide")

def calculate_sample_size(baseline_rate, mde, alpha=0.05, power=0.8):
    """
    計算所需樣本數

    Args:
        baseline_rate: 基準轉換率
        mde: 最小可檢測效應 (Minimum Detectable Effect)
        alpha: 顯著性水準 (通常 0.05)
        power: 統計功效 (通常 0.8)

    Returns:
        每組所需樣本數
    """
    from scipy.stats import norm

    p1 = baseline_rate
    p2 = baseline_rate * (1 + mde)

    z_alpha = norm.ppf(1 - alpha/2)
    z_beta = norm.ppf(power)

    p_avg = (p1 + p2) / 2

    n = (z_alpha * np.sqrt(2 * p_avg * (1 - p_avg)) + z_beta * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2)))**2 / (p1 - p2)**2

    return int(np.ceil(n))

def estimate_test_duration(sample_size, avg_daily_traffic):
    """估算測試所需時間"""
    days_needed = sample_size / avg_daily_traffic
    return int(np.ceil(days_needed))

def calculate_confidence_interval(conversions, visitors, confidence=0.95):
    """計算信賴區間"""
    if visitors == 0:
        return 0, 0

    rate = conversions / visitors
    z = stats.norm.ppf((1 + confidence) / 2)
    margin = z * np.sqrt(rate * (1 - rate) / visitors)

    return max(0, rate - margin), min(1, rate + margin)

def analyze_existing_ab_tests(df):
    """分析現有的素材變化（可視為自然 A/B 測試）"""
    # 按標題分組，看不同標題的表現
    if '標題' in df.columns:
        headline_performance = df.groupby('標題').agg({
            '花費金額 (TWD)': 'sum',
            '購買 ROAS（廣告投資報酬率）': 'mean',
            '購買次數': 'sum',
            'CTR（全部）': 'mean',
            '連結點擊次數': 'sum'
        }).reset_index()

        headline_performance['轉換率'] = (
            headline_performance['購買次數'] /
            headline_performance['連結點擊次數'] * 100
        ).fillna(0)

        # 只保留有足夠數據的標題
        headline_performance = headline_performance[
            (headline_performance['花費金額 (TWD)'] >= 500) &
            (headline_performance['連結點擊次數'] >= 50)
        ].sort_values('購買 ROAS（廣告投資報酬率）', ascending=False)

        return headline_performance

    return pd.DataFrame()

def generate_ab_test_recommendations(test_objective, current_performance, use_rag=False):
    """使用 AI + RAG 生成 A/B 測試建議"""
    llm_service = get_llm_service()

    if not llm_service.is_available():
        return {"error": "LLM 服務目前無法使用"}

    # RAG 增強：獲取歷史成功案例
    rag_context = ""
    if use_rag:
        try:
            rag = RAGService()
            if rag.load_knowledge_base("ad_creatives"):
                # 根據測試目標搜尋相關案例
                if test_objective == "提升 CTR":
                    query = "高 CTR 的標題和素材特徵"
                elif test_objective == "提升轉換率":
                    query = "高轉換率的廣告內文和 CTA"
                elif test_objective == "提升 ROAS":
                    query = "高 ROAS 的受眾和投放策略"
                else:
                    query = "廣告優化最佳實踐"

                similar_ads = rag.search_similar_ads(query, k=3)

                if similar_ads:
                    rag_context = "\n\n## 📚 歷史成功案例參考\n\n"
                    for i, doc in enumerate(similar_ads, 1):
                        rag_context += f"### 案例 {i}\n"
                        rag_context += f"{doc.page_content}\n\n"
                    rag_context += "**請參考以上案例設計測試變因。**\n"
        except Exception as e:
            pass

    # 建構 Prompt
    prompt = f"""
你是專業的廣告 A/B 測試設計專家。請針對以下測試目標提供測試設計建議。

## 測試目標
{test_objective}

## 當前表現
{json.dumps(current_performance, ensure_ascii=False, indent=2)}{rag_context}

## 請提供以下內容：

### 1. 🎯 測試策略

**測試假設**：
- 我們相信改變 [X] 會提升 [Y]
- 原因是：[基於數據的理由]

**成功指標**：
- 主要指標（Primary Metric）
- 次要指標（Secondary Metrics）
- 護欄指標（Guardrail Metrics - 不能惡化的指標）

### 2. 🧪 A/B 測試方案（3-5 個）

**對每個測試方案提供**：
- 🔬 **測試變因**：要測試什麼（標題/內文/CTA/受眾/素材）
- 📋 **變體設計**：
  - 控制組（A）：當前版本
  - 實驗組（B、C...）：具體的變體內容
- 📊 **預期效果**：預估可提升多少（保守估計）
- ⏱️ **測試時間**：建議測試多久
- 💰 **預算分配**：每組建議預算
- 🚦 **優先級**：🔴 高 / 🟡 中 / 🟢 低

### 3. 📐 測試設計細節

**樣本分配**：
- 流量分配比例（50/50 或其他）
- 是否需要預熱期
- 排除條件

**統計要求**：
- 所需樣本數估算
- 最小測試時間
- 顯著性水準建議

### 4. ⚠️ 注意事項

**避免的錯誤**：
- 同時測試太多變因
- 樣本數不足就下結論
- 測試時間太短
- 忽略外部因素（節日、促銷）

**風險管理**：
- 如何控制風險
- 何時應該提前停止測試
- 如何處理異常值

### 5. 📋 執行檢查清單

測試前：
- [ ] 明確定義成功指標
- [ ] 計算所需樣本數
- [ ] 設定追蹤機制
- [ ] 團隊溝通測試計畫

測試中：
- [ ] 監控指標變化
- [ ] 檢查數據品質
- [ ] 記錄異常事件

測試後：
- [ ] 統計顯著性檢驗
- [ ] 分析次要指標
- [ ] 撰寫測試報告
- [ ] 決策：採用/放棄/再測試

### 6. 💡 進階建議

- 如何設計多變量測試（MVT）
- 何時使用漸進式推出（Gradual Rollout）
- 長期測試 vs 短期測試的選擇

請以清晰、專業、可執行的方式回答，使用繁體中文。
重點是**具體可執行的測試設計**，包含實際的文案/受眾範例。
"""

    # 調用 LLM
    response = llm_service.generate_insights(
        prompt,
        model="gpt-3.5-turbo",
        max_tokens=3000,
        temperature=0.7
    )

    return response

def main():
    st.title("🧪 A/B 測試設計助手")
    st.markdown("使用 AI 設計科學的 A/B 測試，讓優化有數據依據")

    # 載入數據
    df = load_meta_ads_data()
    if df is None:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    # 主要內容 - 測試目標設定
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🎯 測試目標設定")

        test_objective = st.selectbox(
            "選擇優化目標",
            [
                "提升 CTR（點擊率）",
                "提升轉換率",
                "提升 ROAS",
                "降低 CPA",
                "擴大觸及",
                "自定義目標"
            ]
        )

        if test_objective == "自定義目標":
            custom_objective = st.text_input("請描述測試目標")
            test_objective = custom_objective if custom_objective else "自定義目標"

    with col2:
        st.subheader("⚙️ 進階設定")

        use_rag = st.checkbox(
            "🧠 啟用智能增強（RAG）",
            value=True,
            help="使用 RAG 技術參考歷史成功案例"
        )

        st.info("""
**功能說明**：
- 當前表現分析
- AI 測試設計
- 樣本數計算
- 測試追蹤範本
        """)

    st.divider()

    # 主要內容
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 當前表現",
        "🧪 測試設計",
        "📐 樣本計算器",
        "📈 測試追蹤"
    ])

    with tab1:
        st.markdown("## 📊 當前廣告表現分析")

        # 整體指標
        col1, col2, col3, col4 = st.columns(4)

        avg_ctr = df['CTR（全部）'].mean()
        avg_roas = df['購買 ROAS（廣告投資報酬率）'].mean()
        avg_cpa = df['每次購買的成本'].mean()
        total_clicks = df['連結點擊次數'].sum()
        total_purchases = df['購買次數'].sum()
        conversion_rate = (total_purchases / total_clicks * 100) if total_clicks > 0 else 0

        with col1:
            st.metric("平均 CTR", f"{avg_ctr:.2f}%")

        with col2:
            st.metric("平均 ROAS", f"{avg_roas:.2f}")

        with col3:
            st.metric("平均 CPA", f"NT$ {avg_cpa:.0f}")

        with col4:
            st.metric("整體轉換率", f"{conversion_rate:.2f}%")

        st.divider()

        # 素材表現分析
        st.markdown("### 🎨 素材表現分析（自然 A/B 對比）")

        headline_performance = analyze_existing_ab_tests(df)

        if not headline_performance.empty:
            st.info("💡 以下是不同素材的表現對比，可作為 A/B 測試的參考基準")

            # 顯示 Top 10
            st.dataframe(
                headline_performance.head(10),
                use_container_width=True,
                column_config={
                    "標題": st.column_config.TextColumn("標題", width="large"),
                    "花費金額 (TWD)": st.column_config.NumberColumn("花費", format="%.0f"),
                    "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
                    "購買次數": st.column_config.NumberColumn("購買", format="%.0f"),
                    "CTR（全部）": st.column_config.NumberColumn("CTR", format="%.2f%%"),
                    "轉換率": st.column_config.NumberColumn("轉換率", format="%.2f%%")
                }
            )

            # 視覺化對比
            st.markdown("### 📊 ROAS 對比（Top 10）")

            top10 = headline_performance.head(10)
            fig = px.bar(
                top10,
                x='標題',
                y='購買 ROAS（廣告投資報酬率）',
                title='不同素材的 ROAS 表現',
                labels={'標題': '標題', '購買 ROAS（廣告投資報酬率）': 'ROAS'},
                color='購買 ROAS（廣告投資報酬率）',
                color_continuous_scale='Viridis'
            )
            fig.update_xaxes(tickangle=45)
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

            # 洞察
            best_headline = headline_performance.iloc[0]
            worst_headline = headline_performance.iloc[-1]
            roas_gap = best_headline['購買 ROAS（廣告投資報酬率）'] - worst_headline['購買 ROAS（廣告投資報酬率）']

            st.success(f"""
            📈 **關鍵洞察**：
            - 最佳素材 ROAS：{best_headline['購買 ROAS（廣告投資報酬率）']:.2f}
            - 最差素材 ROAS：{worst_headline['購買 ROAS（廣告投資報酬率）']:.2f}
            - 差距：{roas_gap:.2f}（{(roas_gap/worst_headline['購買 ROAS（廣告投資報酬率）']*100):.1f}%）

            💡 **建議**：通過 A/B 測試找出最佳素材模式，複製成功要素
            """)
        else:
            st.warning("數據不足，無法分析素材表現差異")

    with tab2:
        st.markdown("## 🧪 AI A/B 測試設計建議")

        llm_service = get_llm_service()

        if not llm_service.is_available():
            st.error("❌ LLM 服務目前無法使用，請檢查 OPENAI_API_KEY 設定")
            return

        st.info(f"✅ AI 分析已就緒，測試目標：{test_objective}")

        if use_rag:
            st.success("🧠 智能增強已啟用 - AI 將參考歷史成功案例")

        # 準備當前表現數據
        current_performance = {
            "平均CTR": f"{avg_ctr:.2f}%",
            "平均ROAS": f"{avg_roas:.2f}",
            "平均CPA": f"NT$ {avg_cpa:.0f}",
            "整體轉換率": f"{conversion_rate:.2f}%",
            "每日平均點擊": f"{total_clicks / 30:.0f}",  # 假設 30 天數據
            "每日平均購買": f"{total_purchases / 30:.0f}"
        }

        # 生成測試建議按鈕
        if st.button("🚀 生成 A/B 測試設計", type="primary"):
            with st.spinner(f"AI 正在設計針對「{test_objective}」的 A/B 測試方案..."):
                recommendations = generate_ab_test_recommendations(
                    test_objective,
                    current_performance,
                    use_rag=use_rag
                )

                if isinstance(recommendations, dict) and "error" in recommendations:
                    st.error(f"❌ 生成建議失敗：{recommendations['error']}")
                else:
                    st.success(f"✅ A/B 測試設計完成！")

                    # 顯示建議
                    st.markdown("---")
                    st.markdown(recommendations)

                    # 儲存到 session state
                    st.session_state['ab_test_design'] = recommendations
                    st.session_state['ab_test_objective'] = test_objective
                    st.session_state['ab_test_time'] = pd.Timestamp.now()

        # 顯示歷史設計
        if 'ab_test_design' in st.session_state:
            st.markdown("---")
            st.markdown("### 📚 最近生成的測試設計")

            if 'ab_test_time' in st.session_state:
                gen_time = st.session_state['ab_test_time']
                st.caption(f"生成時間：{gen_time.strftime('%Y-%m-%d %H:%M:%S')}")
                st.caption(f"測試目標：{st.session_state.get('ab_test_objective', '未知')}")

            with st.expander("查看完整測試設計", expanded=False):
                st.markdown(st.session_state['ab_test_design'])

    with tab3:
        st.markdown("## 📐 A/B 測試樣本計算器")

        st.info("💡 使用此工具計算達到統計顯著性所需的樣本數和測試時間")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 輸入參數")

            baseline_metric = st.selectbox(
                "選擇測試指標",
                ["轉換率", "CTR", "ROAS"]
            )

            if baseline_metric == "轉換率":
                baseline_rate = st.number_input(
                    "當前轉換率 (%)",
                    min_value=0.1,
                    max_value=100.0,
                    value=float(conversion_rate),
                    step=0.1,
                    help="當前的轉換率"
                ) / 100
            elif baseline_metric == "CTR":
                baseline_rate = st.number_input(
                    "當前 CTR (%)",
                    min_value=0.1,
                    max_value=100.0,
                    value=float(avg_ctr),
                    step=0.1
                ) / 100
            else:  # ROAS
                baseline_rate = st.number_input(
                    "當前 ROAS",
                    min_value=0.1,
                    max_value=20.0,
                    value=float(avg_roas),
                    step=0.1
                ) / 100  # 標準化為比率

            mde = st.number_input(
                "最小可檢測效應 MDE (%)",
                min_value=1.0,
                max_value=100.0,
                value=10.0,
                step=1.0,
                help="希望能檢測到的最小提升幅度"
            ) / 100

            alpha = st.number_input(
                "顯著性水準 α",
                min_value=0.01,
                max_value=0.10,
                value=0.05,
                step=0.01,
                help="通常使用 0.05（95% 信賴水準）"
            )

            power = st.number_input(
                "統計功效 (Power)",
                min_value=0.70,
                max_value=0.95,
                value=0.80,
                step=0.05,
                help="通常使用 0.80（80% 功效）"
            )

            avg_daily_visitors = st.number_input(
                "平均每日訪客數",
                min_value=10,
                max_value=100000,
                value=int(total_clicks / 30) if total_clicks > 0 else 1000,
                step=100,
                help="每天有多少人會看到廣告"
            )

        with col2:
            st.markdown("### 計算結果")

            # 計算所需樣本數
            try:
                sample_size_per_group = calculate_sample_size(baseline_rate, mde, alpha, power)
                total_sample_size = sample_size_per_group * 2  # A/B 兩組

                # 估算測試時間
                test_duration = estimate_test_duration(total_sample_size, avg_daily_visitors)

                # 顯示結果
                st.success(f"""
                ### 📊 所需樣本數

                - **每組樣本數**：{sample_size_per_group:,}
                - **總樣本數**：{total_sample_size:,}（A + B 組）

                ### ⏱️ 預估測試時間

                - **所需天數**：{test_duration} 天
                - **建議測試期間**：至少 {max(test_duration, 7)} 天
                  （考慮一週週期效應）

                ### 📈 測試參數

                - **基準指標**：{baseline_rate*100:.2f}%
                - **目標提升**：+{mde*100:.1f}%
                - **目標指標**：{baseline_rate*(1+mde)*100:.2f}%
                - **信賴水準**：{(1-alpha)*100:.0f}%
                - **統計功效**：{power*100:.0f}%
                """)

                # 視覺化
                st.markdown("### 📊 樣本數 vs 可檢測效應")

                mde_range = np.arange(0.05, 0.5, 0.05)
                sample_sizes = [calculate_sample_size(baseline_rate, m, alpha, power) for m in mde_range]

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=mde_range * 100,
                    y=sample_sizes,
                    mode='lines+markers',
                    name='所需樣本數'
                ))

                fig.update_layout(
                    title='最小可檢測效應 vs 所需樣本數',
                    xaxis_title='MDE (%)',
                    yaxis_title='每組所需樣本數',
                    height=400
                )

                st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.error(f"計算錯誤：{str(e)}")

    with tab4:
        st.markdown("## 📈 A/B 測試追蹤範本")

        st.info("💡 以下是 A/B 測試執行和追蹤的範本，可複製使用")

        # 測試追蹤表格範本
        st.markdown("### 📋 測試追蹤表格")

        tracking_template = pd.DataFrame({
            '測試項目': ['標題測試 #1', '受眾測試 #2', 'CTA 測試 #3'],
            '開始日期': ['2024-01-15', '2024-01-20', '2024-01-25'],
            '結束日期': ['2024-01-29', '2024-02-03', '2024-02-08'],
            '狀態': ['進行中', '已完成', '計畫中'],
            'A組（控制組）': ['原始標題', '25-34歲女性', '立即購買'],
            'B組（實驗組）': ['新標題A', '35-44歲女性', '限時優惠'],
            '勝出組': ['-', 'B組', '-'],
            'ROAS提升': ['-', '+15%', '-'],
            '備註': ['樣本數達標 80%', '統計顯著 p<0.05', '等待批准']
        })

        st.dataframe(tracking_template, use_container_width=True)

        # 決策檢查清單
        st.markdown("### ✅ 測試決策檢查清單")

        st.markdown("""
        **測試前檢查**：
        - [ ] 明確定義測試假設
        - [ ] 計算所需樣本數
        - [ ] 確定測試時長
        - [ ] 設定追蹤機制
        - [ ] 團隊溝通測試計畫
        - [ ] 準備好 A/B 兩組素材

        **測試中監控**：
        - [ ] 每日檢查數據品質
        - [ ] 監控樣本收集進度
        - [ ] 記錄任何異常事件
        - [ ] 確保流量分配正確

        **測試後分析**：
        - [ ] 確認樣本數足夠
        - [ ] 進行顯著性檢驗
        - [ ] 分析次要指標
        - [ ] 檢查護欄指標
        - [ ] 撰寫測試報告
        - [ ] 決策：採用/放棄/再測試
        """)

        # 常見錯誤
        st.markdown("### ⚠️ 常見 A/B 測試錯誤")

        col1, col2 = st.columns(2)

        with col1:
            st.error("""
            **❌ 要避免的錯誤**：

            1. **提前停止測試**
               - 看到初步好結果就停止
               - 沒達到預定樣本數

            2. **同時測試太多變因**
               - 無法判斷哪個變因有效
               - 需要更大樣本數

            3. **忽略外部因素**
               - 節日、促銷、競品活動
               - 週間 vs 週末差異

            4. **cherry-picking 數據**
               - 只看有利的指標
               - 忽略負面影響
            """)

        with col2:
            st.success("""
            **✅ 最佳實踐**：

            1. **堅持完成測試**
               - 達到預定樣本數
               - 至少測試一個完整週期

            2. **一次測試一個變因**
               - 清楚歸因效果
               - 容易複製成功

            3. **考慮情境因素**
               - 記錄外部事件
               - 季節性調整

            4. **全面評估影響**
               - 檢查所有相關指標
               - 長期效應追蹤
            """)

    # 頁面底部
    st.markdown("---")
    st.markdown("""
    ### 💡 A/B 測試最佳實踐

    **何時該做 A/B 測試**：
    1. 🎯 想要優化特定指標（CTR、轉換率、ROAS）
    2. 📊 有足夠流量支持測試（每天至少 100+ 訪客）
    3. 🤔 有明確的假設要驗證
    4. ⏱️ 願意投入足夠時間等待結果

    **A/B 測試金字塔**：
    ```
          多變量測試（MVT）
         /                  \\
        /   多個 A/B 測試    \\
       /    同時進行          \\
      /                        \\
     /   單一 A/B 測試          \\
    /    （從這裡開始）          \\
    /_______________________________\\
    ```

    **測試優先級**：
    1. 🔴 **高優先級**：標題、主視覺、CTA（影響最大）
    2. 🟡 **中優先級**：內文、受眾、投放時段
    3. 🟢 **低優先級**：按鈕顏色、字體、排版細節

    **記住**：
    - 不是所有改變都需要 A/B 測試
    - 明顯的 bug 修復、法規要求 → 直接改
    - 有爭議的改變、重大決策 → 一定要測試
    """)

if __name__ == "__main__":
    main()
