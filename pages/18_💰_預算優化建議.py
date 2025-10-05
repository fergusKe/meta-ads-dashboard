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

st.set_page_config(page_title="預算優化建議", page_icon="💰", layout="wide")

def analyze_budget_efficiency(df):
    """分析預算使用效率"""
    # 按活動分組分析預算效率
    campaign_budget = df.groupby('行銷活動名稱').agg({
        '花費金額 (TWD)': 'sum',
        '購買 ROAS（廣告投資報酬率）': 'mean',
        '購買次數': 'sum',
        '每次購買的成本': 'mean',
        'CTR（全部）': 'mean',
        '觸及人數': 'sum'
    }).reset_index()

    # 計算效率分數（ROAS * 購買次數 / 花費）
    campaign_budget['效率分數'] = (
        campaign_budget['購買 ROAS（廣告投資報酬率）'] *
        campaign_budget['購買次數'] /
        (campaign_budget['花費金額 (TWD)'] / 1000)  # 標準化為每千元
    )

    # 計算投資報酬
    campaign_budget['總營收估計'] = (
        campaign_budget['花費金額 (TWD)'] *
        campaign_budget['購買 ROAS（廣告投資報酬率）']
    )

    campaign_budget['利潤估計'] = (
        campaign_budget['總營收估計'] - campaign_budget['花費金額 (TWD)']
    )

    return campaign_budget.sort_values('效率分數', ascending=False)

def identify_budget_opportunities(budget_analysis, min_roas=3.0):
    """識別預算優化機會"""
    opportunities = []

    # 1. 高效但預算不足的活動（應增加預算）
    high_performers = budget_analysis[
        (budget_analysis['購買 ROAS（廣告投資報酬率）'] >= min_roas)
    ].sort_values('花費金額 (TWD)', ascending=True)

    if not high_performers.empty:
        for idx, row in high_performers.head(3).iterrows():
            opportunities.append({
                '活動名稱': row['行銷活動名稱'],
                '機會類型': '🚀 增加預算',
                'ROAS': row['購買 ROAS（廣告投資報酬率）'],
                '當前花費': row['花費金額 (TWD)'],
                '建議': f"ROAS {row['購買 ROAS（廣告投資報酬率）']:.2f}，建議增加預算 30-50%",
                '優先級': '🔴 高'
            })

    # 2. 低效且高花費的活動（應減少預算或暫停）
    low_performers = budget_analysis[
        (budget_analysis['購買 ROAS（廣告投資報酬率）'] < min_roas * 0.5) &
        (budget_analysis['花費金額 (TWD)'] > budget_analysis['花費金額 (TWD)'].median())
    ].sort_values('花費金額 (TWD)', ascending=False)

    if not low_performers.empty:
        for idx, row in low_performers.head(3).iterrows():
            opportunities.append({
                '活動名稱': row['行銷活動名稱'],
                '機會類型': '⚠️ 減少預算',
                'ROAS': row['購買 ROAS（廣告投資報酬率）'],
                '當前花費': row['花費金額 (TWD)'],
                '建議': f"ROAS 僅 {row['購買 ROAS（廣告投資報酬率）']:.2f}，建議減少 50% 或暫停",
                '優先級': '🔴 高'
            })

    # 3. 中等表現但可優化的活動
    medium_performers = budget_analysis[
        (budget_analysis['購買 ROAS（廣告投資報酬率）'] >= min_roas * 0.5) &
        (budget_analysis['購買 ROAS（廣告投資報酬率）'] < min_roas)
    ].sort_values('效率分數', ascending=False)

    if not medium_performers.empty:
        for idx, row in medium_performers.head(2).iterrows():
            opportunities.append({
                '活動名稱': row['行銷活動名稱'],
                '機會類型': '🔧 優化測試',
                'ROAS': row['購買 ROAS（廣告投資報酬率）'],
                '當前花費': row['花費金額 (TWD)'],
                '建議': f"ROAS {row['購買 ROAS（廣告投資報酬率）']:.2f}，先優化素材/受眾再考慮加預算",
                '優先級': '🟡 中'
            })

    return pd.DataFrame(opportunities)

def simulate_budget_reallocation(budget_analysis, total_budget=None):
    """模擬預算重新分配"""
    if total_budget is None:
        total_budget = budget_analysis['花費金額 (TWD)'].sum()

    # 按效率分數重新分配預算
    budget_analysis['建議預算佔比'] = (
        budget_analysis['效率分數'] /
        budget_analysis['效率分數'].sum()
    )

    budget_analysis['建議預算'] = (
        budget_analysis['建議預算佔比'] * total_budget
    )

    budget_analysis['預算變化'] = (
        budget_analysis['建議預算'] - budget_analysis['花費金額 (TWD)']
    )

    budget_analysis['預算變化百分比'] = (
        budget_analysis['預算變化'] / budget_analysis['花費金額 (TWD)'] * 100
    )

    # 預估新 ROAS（假設效率維持）
    budget_analysis['預估新營收'] = (
        budget_analysis['建議預算'] *
        budget_analysis['購買 ROAS（廣告投資報酬率）']
    )

    return budget_analysis

def generate_budget_optimization_recommendations(budget_analysis, opportunities, use_rag=False):
    """使用 LLM + RAG 生成預算優化建議"""
    llm_service = get_llm_service()

    if not llm_service.is_available():
        return {"error": "LLM 服務目前無法使用"}

    # 準備數據摘要
    total_spend = budget_analysis['花費金額 (TWD)'].sum()
    total_revenue = budget_analysis['總營收估計'].sum()
    overall_roas = total_revenue / total_spend if total_spend > 0 else 0
    total_profit = budget_analysis['利潤估計'].sum()

    summary = {
        "總花費": f"NT$ {total_spend:,.0f}",
        "總營收": f"NT$ {total_revenue:,.0f}",
        "整體ROAS": f"{overall_roas:.2f}",
        "總利潤": f"NT$ {total_profit:,.0f}",
        "活動數量": len(budget_analysis)
    }

    # Top 5 高效活動
    top5 = budget_analysis.head(5)[
        ['行銷活動名稱', '花費金額 (TWD)', '購買 ROAS（廣告投資報酬率）', '效率分數']
    ].to_dict('records')

    # Bottom 5 低效活動
    bottom5 = budget_analysis.tail(5)[
        ['行銷活動名稱', '花費金額 (TWD)', '購買 ROAS（廣告投資報酬率）', '效率分數']
    ].to_dict('records')

    # 預算機會
    opps_dict = opportunities.head(5).to_dict('records') if not opportunities.empty else []

    # RAG 增強：獲取歷史預算優化案例
    rag_context = ""
    if use_rag:
        try:
            rag = RAGService()
            if rag.load_knowledge_base("ad_creatives"):
                # 搜尋高 ROAS 案例的預算策略
                query = "高 ROAS 廣告的預算和投放策略"
                similar_ads = rag.search_similar_ads(query, k=3)

                if similar_ads:
                    rag_context = "\n\n## 📚 歷史高效預算案例\n\n"
                    for i, doc in enumerate(similar_ads, 1):
                        roas = doc.metadata.get('roas', 0)
                        purchases = doc.metadata.get('purchases', 0)
                        rag_context += f"### 案例 {i}（ROAS {roas:.2f}，購買 {purchases:.0f}）\n"
                        rag_context += f"- 受眾：{doc.metadata.get('age', '未知')} / {doc.metadata.get('gender', '未知')}\n"
                        rag_context += f"- CTR：{doc.metadata.get('ctr', 0):.2f}%\n\n"
                    rag_context += "**請參考以上案例的投放策略。**\n"
        except Exception as e:
            pass

    # 建構 Prompt
    prompt = f"""
你是專業的 Meta 廣告預算優化顧問。請根據以下數據提供預算優化建議。

## 整體預算表現
{json.dumps(summary, ensure_ascii=False, indent=2)}

## Top 5 高效活動
{json.dumps(top5, ensure_ascii=False, indent=2)}

## Bottom 5 低效活動
{json.dumps(bottom5, ensure_ascii=False, indent=2)}

## 已識別的預算機會
{json.dumps(opps_dict, ensure_ascii=False, indent=2)}{rag_context}

## 請提供以下分析：

### 1. 📊 預算配置診斷
分析目前預算配置的問題：
- 預算是否過度分散？
- 高效活動是否獲得足夠預算？
- 低效活動是否佔用過多預算？
- 整體 ROAS 改善空間

### 2. 💰 預算重新分配建議

**對每個需要調整的活動**：
- 🎯 **活動名稱**
- 📊 **當前狀況**：花費、ROAS、效率
- 🔄 **建議動作**：增加/減少/維持/暫停
- 💵 **建議預算**：具體金額（TWD）
- 📈 **預期效果**：ROAS 預期變化
- 🚦 **優先級**：🔴 高 / 🟡 中 / 🟢 低
- ⏱️ **執行時機**：立即/本週/下週

### 3. 🎯 預算擴展策略
對於高效活動，提供預算擴展建議：
- 漸進式擴展計畫（避免 ROAS 驟降）
- 每次增加多少預算
- 觀察期多長
- 何時繼續擴展/停止擴展

### 4. 🛡️ 風險控制
預算調整的風險管理：
- 設定止損點
- 監控指標
- 回滾計畫

### 5. 📋 30 天執行路線圖
分階段預算優化計畫：
- Week 1：立即調整（緊急）
- Week 2：測試優化
- Week 3：擴展成功項目
- Week 4：持續監控和微調

### 6. 💡 預期改善
如果執行建議，預估：
- 整體 ROAS 提升幅度
- 總營收增加
- 利潤改善
- 需要調整的預算規模

請以清晰、專業、可執行的方式回答，使用繁體中文。
重點是**具體的預算金額和執行計畫**，不要泛泛而談。
"""

    # 調用 LLM
    response = llm_service.generate_insights(
        prompt,
        model="gpt-3.5-turbo",
        max_tokens=2500,
        temperature=0.7
    )

    return response

def main():
    st.title("💰 預算優化建議")
    st.markdown("基於數據分析，使用 AI 提供智能預算分配和優化建議")

    # 載入數據
    df = load_meta_ads_data()
    if df is None:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    # 分析設定區域（移到主要內容區）
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### ⚙️ 分析設定")

        target_roas = st.number_input(
            "目標 ROAS",
            min_value=1.0,
            max_value=10.0,
            value=3.0,
            step=0.5,
            help="用於判斷高效/低效活動的 ROAS 門檻"
        )

        use_rag = st.checkbox(
            "🧠 啟用智能增強（RAG）",
            value=True,
            help="使用 RAG 技術參考歷史成功案例"
        )

    with col2:
        st.markdown("### 📊 功能說明")
        st.info("""
        **預算優化分析**

        - 識別高效活動（增加預算）
        - 識別低效活動（減少預算）
        - 模擬預算重新分配
        - AI 生成優化建議
        """)

    st.divider()

    # 分析預算效率
    budget_analysis = analyze_budget_efficiency(df)
    opportunities = identify_budget_opportunities(budget_analysis, target_roas)

    # 主要內容
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 預算概覽",
        "🎯 預算機會",
        "🔄 重新分配模擬",
        "🤖 AI 優化建議"
    ])

    with tab1:
        st.markdown("## 📊 預算使用概覽")

        # 整體指標
        col1, col2, col3, col4 = st.columns(4)

        total_spend = budget_analysis['花費金額 (TWD)'].sum()
        total_revenue = budget_analysis['總營收估計'].sum()
        overall_roas = total_revenue / total_spend if total_spend > 0 else 0
        total_profit = budget_analysis['利潤估計'].sum()

        with col1:
            st.metric("總花費", f"NT$ {total_spend:,.0f}")

        with col2:
            st.metric("總營收估計", f"NT$ {total_revenue:,.0f}")

        with col3:
            st.metric("整體 ROAS", f"{overall_roas:.2f}")

        with col4:
            profit_color = "normal" if total_profit >= 0 else "inverse"
            st.metric(
                "總利潤估計",
                f"NT$ {total_profit:,.0f}",
                delta=f"{(total_profit/total_spend*100):.1f}%" if total_spend > 0 else "0%"
            )

        st.divider()

        # 預算分佈圖
        st.markdown("### 💰 預算分佈與效率")

        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('預算分佈 (Top 10)', '效率分數 (Top 10)'),
            specs=[[{"type": "bar"}, {"type": "bar"}]]
        )

        top10 = budget_analysis.head(10)

        # 預算分佈
        fig.add_trace(
            go.Bar(
                x=top10['行銷活動名稱'],
                y=top10['花費金額 (TWD)'],
                name='花費',
                marker_color='lightblue'
            ),
            row=1, col=1
        )

        # 效率分數
        fig.add_trace(
            go.Bar(
                x=top10['行銷活動名稱'],
                y=top10['效率分數'],
                name='效率分數',
                marker_color='lightgreen'
            ),
            row=1, col=2
        )

        fig.update_xaxes(title_text="活動", tickangle=45, row=1, col=1)
        fig.update_xaxes(title_text="活動", tickangle=45, row=1, col=2)
        fig.update_yaxes(title_text="花費 (TWD)", row=1, col=1)
        fig.update_yaxes(title_text="效率分數", row=1, col=2)
        fig.update_layout(height=500, showlegend=False)

        st.plotly_chart(fig, use_container_width=True)

        # 散點圖：花費 vs ROAS
        st.markdown("### 📈 花費 vs ROAS 關係")

        fig_scatter = px.scatter(
            budget_analysis,
            x='花費金額 (TWD)',
            y='購買 ROAS（廣告投資報酬率）',
            size='購買次數',
            color='效率分數',
            hover_data=['行銷活動名稱'],
            labels={
                '花費金額 (TWD)': '花費 (TWD)',
                '購買 ROAS（廣告投資報酬率）': 'ROAS',
                '效率分數': '效率分數'
            },
            color_continuous_scale='Viridis'
        )

        # 添加目標 ROAS 參考線
        fig_scatter.add_hline(
            y=target_roas,
            line_dash="dash",
            line_color="red",
            annotation_text=f"目標 ROAS {target_roas}",
            annotation_position="right"
        )

        fig_scatter.update_layout(height=500)
        st.plotly_chart(fig_scatter, use_container_width=True)

        # 詳細數據表
        st.markdown("### 📋 活動預算詳情")
        st.dataframe(
            budget_analysis[[
                '行銷活動名稱', '花費金額 (TWD)', '購買 ROAS（廣告投資報酬率）',
                '購買次數', '每次購買的成本', '效率分數', '利潤估計'
            ]],
            use_container_width=True,
            column_config={
                "行銷活動名稱": st.column_config.TextColumn("活動名稱", width="large"),
                "花費金額 (TWD)": st.column_config.NumberColumn("花費", format="%.0f"),
                "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
                "購買次數": st.column_config.NumberColumn("購買", format="%.0f"),
                "每次購買的成本": st.column_config.NumberColumn("CPA", format="%.0f"),
                "效率分數": st.column_config.NumberColumn("效率分數", format="%.2f"),
                "利潤估計": st.column_config.NumberColumn("利潤", format="%.0f")
            }
        )

    with tab2:
        st.markdown("## 🎯 預算優化機會")

        if not opportunities.empty:
            st.success(f"✅ 發現 {len(opportunities)} 個預算優化機會")

            # 按優先級分組顯示
            for priority in ['🔴 高', '🟡 中', '🟢 低']:
                priority_opps = opportunities[opportunities['優先級'] == priority]

                if not priority_opps.empty:
                    st.markdown(f"### {priority}優先級")

                    for idx, opp in priority_opps.iterrows():
                        with st.container():
                            col1, col2, col3 = st.columns([2, 1, 2])

                            with col1:
                                st.markdown(f"**{opp['機會類型']}**")
                                st.write(f"活動：{opp['活動名稱'][:50]}")

                            with col2:
                                st.metric("ROAS", f"{opp['ROAS']:.2f}")
                                st.caption(f"花費：NT$ {opp['當前花費']:,.0f}")

                            with col3:
                                st.info(opp['建議'])

                            st.divider()
        else:
            st.info("目前沒有發現明顯的預算優化機會")

    with tab3:
        st.markdown("## 🔄 預算重新分配模擬")

        st.info("💡 基於效率分數重新分配預算，讓高效活動獲得更多資源")

        # 模擬重新分配
        reallocation = simulate_budget_reallocation(budget_analysis)

        # 顯示建議變化最大的活動
        st.markdown("### 📊 建議調整幅度最大的活動")

        # 增加預算最多
        increase_most = reallocation.nlargest(5, '預算變化')
        st.markdown("#### 🚀 建議增加預算")
        st.dataframe(
            increase_most[[
                '行銷活動名稱', '花費金額 (TWD)', '建議預算',
                '預算變化', '預算變化百分比', '購買 ROAS（廣告投資報酬率）'
            ]],
            use_container_width=True,
            column_config={
                "行銷活動名稱": st.column_config.TextColumn("活動", width="large"),
                "花費金額 (TWD)": st.column_config.NumberColumn("當前預算", format="%.0f"),
                "建議預算": st.column_config.NumberColumn("建議預算", format="%.0f"),
                "預算變化": st.column_config.NumberColumn("變化金額", format="%.0f"),
                "預算變化百分比": st.column_config.NumberColumn("變化%", format="%.1f%%"),
                "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f")
            }
        )

        # 減少預算最多
        decrease_most = reallocation.nsmallest(5, '預算變化')
        st.markdown("#### ⚠️ 建議減少預算")
        st.dataframe(
            decrease_most[[
                '行銷活動名稱', '花費金額 (TWD)', '建議預算',
                '預算變化', '預算變化百分比', '購買 ROAS（廣告投資報酬率）'
            ]],
            use_container_width=True,
            column_config={
                "行銷活動名稱": st.column_config.TextColumn("活動", width="large"),
                "花費金額 (TWD)": st.column_config.NumberColumn("當前預算", format="%.0f"),
                "建議預算": st.column_config.NumberColumn("建議預算", format="%.0f"),
                "預算變化": st.column_config.NumberColumn("變化金額", format="%.0f"),
                "預算變化百分比": st.column_config.NumberColumn("變化%", format="%.1f%%"),
                "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f")
            }
        )

        # 預期效果
        st.markdown("### 📈 預期效果")

        current_revenue = reallocation['總營收估計'].sum()
        new_revenue = reallocation['預估新營收'].sum()
        revenue_improvement = ((new_revenue - current_revenue) / current_revenue * 100) if current_revenue > 0 else 0

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("當前總營收", f"NT$ {current_revenue:,.0f}")
        with col2:
            st.metric(
                "預估新營收",
                f"NT$ {new_revenue:,.0f}",
                delta=f"+{revenue_improvement:.1f}%"
            )
        with col3:
            st.metric("營收增加", f"NT$ {(new_revenue - current_revenue):,.0f}")

    with tab4:
        st.markdown("## 🤖 AI 預算優化建議")

        llm_service = get_llm_service()

        if not llm_service.is_available():
            st.error("❌ LLM 服務目前無法使用，請檢查 OPENAI_API_KEY 設定")
            return

        st.info("✅ AI 分析已就緒")

        if use_rag:
            st.success("🧠 智能增強已啟用 - AI 將參考歷史成功案例")

        # 生成建議按鈕
        if st.button("🚀 生成 AI 預算優化建議", type="primary"):
            with st.spinner("AI 正在分析預算數據並生成優化建議..."):
                recommendations = generate_budget_optimization_recommendations(
                    budget_analysis,
                    opportunities,
                    use_rag=use_rag
                )

                if isinstance(recommendations, dict) and "error" in recommendations:
                    st.error(f"❌ 生成建議失敗：{recommendations['error']}")
                else:
                    st.success("✅ AI 預算優化建議生成完成！")

                    # 顯示建議
                    st.markdown("### 🤖 AI 預算優化建議")
                    st.markdown(recommendations)

                    # 儲存到 session state
                    st.session_state['budget_recommendations'] = recommendations
                    st.session_state['budget_recommendations_time'] = pd.Timestamp.now()

        # 顯示歷史建議
        if 'budget_recommendations' in st.session_state:
            st.markdown("---")
            st.markdown("### 📚 最近生成的建議")

            if 'budget_recommendations_time' in st.session_state:
                gen_time = st.session_state['budget_recommendations_time']
                st.caption(f"生成時間：{gen_time.strftime('%Y-%m-%d %H:%M:%S')}")

            with st.expander("查看完整建議", expanded=False):
                st.markdown(st.session_state['budget_recommendations'])

    # 頁面底部提示
    st.markdown("---")
    st.markdown("""
    ### 💡 預算優化最佳實踐

    **預算調整原則**：
    1. 📊 **數據驅動**：基於 ROAS 和轉換數據，不憑感覺
    2. 🐢 **小步快跑**：每次調整 20-30%，避免劇烈變動
    3. ⏱️ **給予時間**：調整後觀察 3-7 天才判斷效果
    4. 🎯 **聚焦高效**：80% 預算給 ROAS >= 目標的活動
    5. 🧪 **保留測試預算**：10-15% 用於測試新策略

    **預算擴展技巧**：
    - 高效活動每次增加 20-30% 預算
    - 監控 ROAS 是否下降超過 10%
    - 如果下降，暫停擴展，優化受眾/素材
    - 擴展週期：每 7-10 天評估一次

    **風險控制**：
    - 設定每日預算上限
    - ROAS 跌破目標 20% 時自動降預算
    - 保留應急預算應對突發機會
    """)

if __name__ == "__main__":
    main()
