import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.data_loader import load_meta_ads_data, filter_data_by_date_range
from utils.llm_service import get_llm_service
from utils.rag_service import RAGService
import numpy as np
import json

def show_optimization_recommendations():
    """顯示即時優化建議頁面"""
    st.markdown("# ⚡ 即時優化建議")
    st.markdown("基於數據分析的智能廣告優化建議，幫助您提升投放效果")

    # 載入數據
    df = load_meta_ads_data()
    if df is None:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    # 應用與其他頁面相同的日期篩選邏輯
    filtered_df = df.copy()
    if '分析報告開始' in df.columns and '分析報告結束' in df.columns:
        report_start_dates = df['分析報告開始'].dropna()
        report_end_dates = df['分析報告結束'].dropna()

        if not report_start_dates.empty and not report_end_dates.empty:
            report_start = report_start_dates.min()
            report_end = report_end_dates.max()

            filtered_df = df[
                (df['開始'] >= report_start) &
                (df['開始'] <= report_end)
            ].copy()

    if filtered_df.empty:
        st.warning("所選時間範圍內暫無數據")
        return

    # 分析設定
    st.markdown("## ⚙️ 分析設定")
    analysis_col1, analysis_col2, analysis_col3 = st.columns(3)

    with analysis_col1:
        target_roas = st.number_input("目標 ROAS", min_value=1.0, max_value=10.0, value=3.0, step=0.1)

    with analysis_col2:
        max_cpa = st.number_input("最大 CPA (TWD)", min_value=100, max_value=1000, value=300, step=50)

    with analysis_col3:
        min_daily_budget = st.number_input("最小日預算 (TWD)", min_value=100, max_value=5000, value=500, step=100)

    st.markdown("---")

    # 即時分析結果
    analysis_results = analyze_performance(filtered_df, target_roas, max_cpa)

    # 優化建議標籤頁
    tab1, tab2, tab3, tab4 = st.tabs(["🚨 緊急建議", "📈 效能優化", "💰 預算調整", "🎯 策略建議"])

    with tab1:
        st.markdown("### 🚨 需要立即處理的問題")
        urgent_recommendations = generate_urgent_recommendations(analysis_results, target_roas, max_cpa)

        if urgent_recommendations:
            for i, rec in enumerate(urgent_recommendations):
                create_recommendation_card(rec, f"urgent_{i}")

            # 🤖 AI 緊急問題分析
            llm_service = get_llm_service()
            if llm_service.is_available():
                st.markdown("---")
                st.markdown("#### 🤖 AI 深度緊急分析")

                if st.button("🚨 開始 AI 緊急分析", type="primary", key="urgent_ai_analysis"):
                    with st.spinner("AI 正在分析緊急問題..."):
                        urgent_analysis = generate_ai_urgent_analysis(
                            filtered_df,
                            urgent_recommendations,
                            target_roas,
                            max_cpa
                        )

                        if urgent_analysis and "error" not in urgent_analysis:
                            st.success("✅ AI 緊急分析完成！")
                            st.markdown(urgent_analysis)
                        else:
                            st.error("分析失敗，請稍後再試")
        else:
            st.success("✅ 沒有發現需要緊急處理的問題")

        # 問題活動詳情
        st.markdown("#### 📋 問題活動詳情")
        problem_campaigns = identify_problem_campaigns(filtered_df, target_roas, max_cpa)

        if not problem_campaigns.empty:
            st.dataframe(
                problem_campaigns,
                use_container_width=True,
                column_config={
                    "行銷活動名稱": st.column_config.TextColumn("活動名稱", width="medium"),
                    "問題類型": st.column_config.TextColumn("問題", width="small"),
                    "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
                    "每次購買的成本": st.column_config.NumberColumn("CPA", format="%.0f"),
                    "花費金額 (TWD)": st.column_config.NumberColumn("花費", format="%.0f"),
                    "建議動作": st.column_config.TextColumn("建議", width="large")
                }
            )

            # 🤖 AI 深度根因分析
            st.markdown("---")
            st.markdown("#### 🤖 AI 深度根因分析")

            llm_service = get_llm_service()

            if llm_service.is_available():
                # RAG 增強選項
                use_rag = st.checkbox(
                    "🧠 啟用智能增強（參考歷史成功案例）",
                    value=True,
                    help="使用 RAG 技術從歷史高效廣告中學習優化策略"
                )

                st.info("💡 **AI 功能已啟用** - 選擇要分析的廣告，AI 會提供專屬優化建議")

                # 準備更詳細的選單選項
                campaign_options = []
                campaign_data_map = {}

                for idx, row in problem_campaigns.iterrows():
                    # 建立易讀的選項標籤
                    roas = row['購買 ROAS（廣告投資報酬率）']
                    spend = row['花費金額 (TWD)']
                    problem_type = row['問題類型']
                    campaign_name = row['行銷活動名稱']

                    # 從完整數據中取得更多資訊（廣告組合、廣告名稱）
                    full_data = filtered_df[filtered_df['行銷活動名稱'] == campaign_name]

                    if not full_data.empty:
                        first_row = full_data.iloc[0]
                        ad_set_name = first_row.get('廣告組合名稱', '')
                        ad_name = first_row.get('廣告名稱', '')

                        # 建立完整的廣告階層顯示
                        # 格式：行銷活動 > 廣告組合 > 廣告
                        hierarchy_parts = []

                        if campaign_name:
                            hierarchy_parts.append(campaign_name[:30])  # 限制長度

                        if ad_set_name and ad_set_name != campaign_name:
                            hierarchy_parts.append(ad_set_name[:30])

                        if ad_name and ad_name != campaign_name and ad_name != ad_set_name:
                            hierarchy_parts.append(ad_name[:30])

                        display_name = " > ".join(hierarchy_parts)
                    else:
                        display_name = campaign_name[:60]

                    # 組合完整標籤（包含關鍵指標）
                    # 格式：💰 $花費 | ROAS x.xx | 問題類型 | 廣告階層
                    option_label = f"💰${spend:,.0f} | ROAS {roas:.2f} | {problem_type} | {display_name}"

                    campaign_options.append({
                        'label': option_label,
                        'spend': spend,  # 用於排序
                        'data': row,
                        'name': campaign_name
                    })

                # 按照花費排序（花費高的優先顯示）
                sorted_options = sorted(campaign_options, key=lambda x: x['spend'], reverse=True)

                # 建立選項列表和映射
                option_labels = [opt['label'] for opt in sorted_options]
                for opt in sorted_options:
                    campaign_data_map[opt['label']] = {
                        'data': opt['data'],
                        'name': opt['name']
                    }

                selected_option = st.selectbox(
                    "選擇要深度分析的廣告",
                    options=option_labels,
                    help="已按花費由高到低排序。格式：💰花費 | ROAS | 問題類型 | 行銷活動 > 廣告組合 > 廣告"
                )

                # 取得對應的廣告數據
                selected_campaign_info = campaign_data_map[selected_option]
                selected_campaign = selected_campaign_info['name']
                selected_campaign_data = selected_campaign_info['data']

                if st.button("🔍 開始 AI 分析", type="primary"):
                    with st.spinner(f"AI 正在分析「{selected_campaign}」..."):
                        # 取得該廣告在完整數據中的詳細資訊
                        full_campaign_data = filtered_df[
                            filtered_df['行銷活動名稱'] == selected_campaign
                        ]

                        ai_analysis = generate_ai_root_cause_analysis_single(
                            selected_campaign_data,
                            full_campaign_data,
                            filtered_df,
                            target_roas,
                            max_cpa,
                            use_rag=use_rag
                        )

                        if ai_analysis and "error" not in ai_analysis:
                            st.success(f"✅ AI 已完成「{selected_campaign}」的深度分析！")

                            # 顯示分析結果
                            display_ai_analysis(ai_analysis, selected_campaign)
                        else:
                            st.error(ai_analysis if isinstance(ai_analysis, str) else ai_analysis.get("error", "分析失敗"))
            else:
                st.warning("⚠️ AI 功能未啟用。請設定 OPENAI_API_KEY 以使用 AI 深度分析功能。")
                with st.expander("📖 如何設定 API Key"):
                    st.markdown("""
                    **方法 1：使用環境變數**
                    ```bash
                    export OPENAI_API_KEY='your-api-key-here'
                    ```

                    **方法 2：使用 .env 檔案**
                    在專案根目錄建立 `.env` 檔案：
                    ```
                    OPENAI_API_KEY=your-api-key-here
                    ```

                    **方法 3：使用 Streamlit Secrets**
                    在 `.streamlit/secrets.toml` 中加入：
                    ```
                    OPENAI_API_KEY = "your-api-key-here"
                    ```
                    """)
        else:
            st.info("所有活動表現正常")

    with tab2:
        st.markdown("### 📈 效能優化建議")

        # 高表現活動推薦
        st.markdown("#### 🌟 高表現活動 - 建議擴大投資")
        top_performers = identify_top_performers(filtered_df, target_roas)

        if not top_performers.empty:
            performance_chart = create_performance_chart(top_performers)
            if performance_chart:
                st.plotly_chart(performance_chart, use_container_width=True)

            # 具體建議
            for idx, campaign in top_performers.iterrows():
                with st.expander(f"🚀 {campaign['行銷活動名稱']} - 擴大建議"):
                    rec_col1, rec_col2, rec_col3 = st.columns(3)

                    with rec_col1:
                        current_spend = campaign['花費金額 (TWD)']
                        suggested_increase = min(current_spend * 0.3, 5000)  # 建議增加30%或最多5000
                        st.metric("當前花費", f"${current_spend:,.0f}")
                        st.success(f"建議增加：${suggested_increase:,.0f}")

                    with rec_col2:
                        current_roas = campaign['購買 ROAS（廣告投資報酬率）']
                        st.metric("當前 ROAS", f"{current_roas:.2f}")
                        st.success(f"表現優異 (目標: {target_roas:.1f})")

                    with rec_col3:
                        potential_purchases = suggested_increase / campaign['每次購買的成本'] if campaign['每次購買的成本'] > 0 else 0
                        st.metric("預估新增購買", f"{potential_purchases:.0f} 次")
                        st.info(f"投資回報率：{current_roas:.1f}x")

        else:
            st.info("目前沒有符合擴大條件的高表現活動")

        # 低效活動優化
        st.markdown("#### ⚠️ 低效活動 - 優化建議")
        underperformers = identify_underperformers(filtered_df, target_roas, max_cpa)

        if not underperformers.empty:
            for idx, campaign in underperformers.iterrows():
                with st.expander(f"🔧 {campaign['行銷活動名稱']} - 優化建議"):
                    issue_analysis = analyze_campaign_issues(campaign, target_roas, max_cpa)

                    opt_col1, opt_col2 = st.columns(2)

                    with opt_col1:
                        st.markdown("**問題診斷：**")
                        for issue in issue_analysis['issues']:
                            st.error(f"❌ {issue}")

                    with opt_col2:
                        st.markdown("**優化方案：**")
                        for solution in issue_analysis['solutions']:
                            st.success(f"✅ {solution}")

            # 🤖 AI 效能優化分析
            llm_service = get_llm_service()
            if llm_service.is_available():
                st.markdown("---")
                st.markdown("#### 🤖 AI 效能優化深度分析")

                if st.button("📈 開始 AI 效能分析", type="primary", key="performance_ai_analysis"):
                    with st.spinner("AI 正在分析效能優化機會..."):
                        performance_analysis = generate_ai_performance_analysis(
                            filtered_df,
                            top_performers,
                            underperformers,
                            target_roas
                        )

                        if performance_analysis and "error" not in performance_analysis:
                            st.success("✅ AI 效能分析完成！")
                            st.markdown(performance_analysis)
                        else:
                            st.error("分析失敗，請稍後再試")
        else:
            st.success("所有活動效能表現良好")

    with tab3:
        st.markdown("### 💰 預算調整建議")

        # 預算重新分配建議
        budget_recommendations = generate_budget_recommendations(filtered_df, target_roas)

        budget_col1, budget_col2 = st.columns(2)

        with budget_col1:
            st.markdown("#### 📊 當前預算分配")
            current_budget_chart = create_budget_distribution_chart(filtered_df)
            if current_budget_chart:
                st.plotly_chart(current_budget_chart, use_container_width=True)

        with budget_col2:
            st.markdown("#### 🎯 建議預算分配")
            recommended_budget_chart = create_recommended_budget_chart(budget_recommendations)
            if recommended_budget_chart:
                st.plotly_chart(recommended_budget_chart, use_container_width=True)

        # 預算調整詳情
        st.markdown("#### 💡 具體預算調整建議")

        if budget_recommendations:
            budget_df = pd.DataFrame(budget_recommendations)

            # 計算總變化
            total_increase = budget_df[budget_df['調整方向'] == '增加']['調整金額'].sum()
            total_decrease = budget_df[budget_df['調整方向'] == '減少']['調整金額'].sum()

            summary_col1, summary_col2, summary_col3 = st.columns(3)

            with summary_col1:
                st.metric("總增加預算", f"${total_increase:,.0f}")

            with summary_col2:
                st.metric("總減少預算", f"${total_decrease:,.0f}")

            with summary_col3:
                net_change = total_increase - total_decrease
                st.metric("淨變化", f"${net_change:+,.0f}")

            # 詳細調整表格
            st.dataframe(
                budget_df,
                use_container_width=True,
                column_config={
                    "活動名稱": st.column_config.TextColumn("活動名稱", width="medium"),
                    "當前預算": st.column_config.NumberColumn("當前預算", format="$%.0f"),
                    "建議預算": st.column_config.NumberColumn("建議預算", format="$%.0f"),
                    "調整金額": st.column_config.NumberColumn("調整金額", format="$%.0f"),
                    "調整方向": st.column_config.TextColumn("方向", width="small"),
                    "原因": st.column_config.TextColumn("調整原因", width="large")
                }
            )

            # 🤖 AI 預算優化分析
            llm_service = get_llm_service()
            if llm_service.is_available():
                st.markdown("---")
                st.markdown("#### 🤖 AI 智能預算優化分析")

                if st.button("💰 開始 AI 預算分析", type="primary", key="budget_ai_analysis"):
                    with st.spinner("AI 正在分析預算優化策略..."):
                        budget_analysis = generate_ai_budget_analysis(
                            filtered_df,
                            budget_recommendations,
                            target_roas
                        )

                        if budget_analysis and "error" not in budget_analysis:
                            st.success("✅ AI 預算分析完成！")
                            st.markdown(budget_analysis)
                        else:
                            st.error("分析失敗，請稍後再試")

    with tab4:
        st.markdown("### 🎯 策略優化建議")

        # 整體策略分析
        strategy_analysis = analyze_overall_strategy(filtered_df, target_roas)

        strategy_col1, strategy_col2 = st.columns(2)

        with strategy_col1:
            st.markdown("#### 📊 整體表現評估")

            overall_roas = filtered_df['購買 ROAS（廣告投資報酬率）'].mean()
            total_spend = filtered_df['花費金額 (TWD)'].sum()
            total_purchases = filtered_df['購買次數'].sum()

            if overall_roas >= target_roas:
                st.success(f"🎉 整體 ROAS ({overall_roas:.2f}) 達到目標 ({target_roas:.1f})")
            else:
                st.warning(f"⚠️ 整體 ROAS ({overall_roas:.2f}) 低於目標 ({target_roas:.1f})")

            # 投資效率分析
            efficiency_score = calculate_efficiency_score(filtered_df)
            efficiency_level = "高" if efficiency_score > 0.8 else "中" if efficiency_score > 0.5 else "低"

            st.metric("投資效率評分", f"{efficiency_level}", delta=f"{efficiency_score:.2f}")

        with strategy_col2:
            st.markdown("#### 🚀 策略優化方向")

            strategic_recommendations = generate_strategic_recommendations(strategy_analysis)

            for rec in strategic_recommendations:
                if rec['priority'] == 'high':
                    st.error(f"🔥 **高優先級**: {rec['title']}")
                elif rec['priority'] == 'medium':
                    st.warning(f"⚡ **中優先級**: {rec['title']}")
                else:
                    st.info(f"💡 **低優先級**: {rec['title']}")

                st.write(rec['description'])
                st.markdown("---")

        # 行業基準比較
        st.markdown("#### 📈 行業基準比較")

        benchmark_comparison = compare_with_benchmarks(filtered_df)

        benchmark_col1, benchmark_col2, benchmark_col3 = st.columns(3)

        with benchmark_col1:
            st.metric(
                "ROAS vs 行業平均",
                f"{benchmark_comparison['roas']['current']:.2f}",
                delta=f"{benchmark_comparison['roas']['vs_benchmark']:+.2f}"
            )

        with benchmark_col2:
            st.metric(
                "CTR vs 行業平均",
                f"{benchmark_comparison['ctr']['current']:.2f}%",
                delta=f"{benchmark_comparison['ctr']['vs_benchmark']:+.2f}%"
            )

        with benchmark_col3:
            st.metric(
                "CPA vs 行業平均",
                f"${benchmark_comparison['cpa']['current']:.0f}",
                delta=f"${benchmark_comparison['cpa']['vs_benchmark']:+.0f}"
            )

        # 下一步行動計劃
        st.markdown("#### 📋 下一步行動計劃")

        action_plan = generate_action_plan(analysis_results, strategy_analysis)

        for i, action in enumerate(action_plan, 1):
            with st.expander(f"步驟 {i}: {action['title']}"):
                st.markdown(f"**優先級**: {action['priority']}")
                st.markdown(f"**預估時間**: {action['timeline']}")
                st.markdown(f"**預期影響**: {action['impact']}")
                st.markdown(f"**執行步驟**:")
                for step in action['steps']:
                    st.write(f"• {step}")

def analyze_performance(df, target_roas, max_cpa):
    """分析整體表現"""
    if df.empty:
        return {}

    analysis = {
        'total_campaigns': len(df),
        'avg_roas': df['購買 ROAS（廣告投資報酬率）'].mean(),
        'total_spend': df['花費金額 (TWD)'].sum(),
        'total_purchases': df['購買次數'].sum(),
        'avg_cpa': df['每次購買的成本'].mean(),
        'high_performers': len(df[df['購買 ROAS（廣告投資報酬率）'] >= target_roas]),
        'poor_performers': len(df[df['購買 ROAS（廣告投資報酬率）'] < 1.0]),
        'expensive_campaigns': len(df[df['每次購買的成本'] > max_cpa])
    }

    analysis['performance_rate'] = (analysis['high_performers'] / analysis['total_campaigns'] * 100) if analysis['total_campaigns'] > 0 else 0

    return analysis

def generate_urgent_recommendations(analysis, target_roas, max_cpa):
    """生成緊急建議"""
    recommendations = []

    if analysis['poor_performers'] > 0:
        recommendations.append({
            'type': 'critical',
            'title': f'有 {analysis["poor_performers"]} 個活動 ROAS < 1.0',
            'description': '這些活動正在虧損，建議立即暫停或大幅調整',
            'action': '立即檢視並暫停虧損活動',
            'impact': '防止進一步虧損',
            'urgency': 'high'
        })

    if analysis['expensive_campaigns'] > 0:
        recommendations.append({
            'type': 'warning',
            'title': f'有 {analysis["expensive_campaigns"]} 個活動 CPA > ${max_cpa}',
            'description': '這些活動的獲客成本過高，需要優化',
            'action': '調整目標受眾或創意素材',
            'impact': '降低獲客成本',
            'urgency': 'medium'
        })

    if analysis['avg_roas'] < target_roas:
        recommendations.append({
            'type': 'warning',
            'title': f'整體 ROAS ({analysis["avg_roas"]:.2f}) 低於目標 ({target_roas:.1f})',
            'description': '需要全面檢視投放策略',
            'action': '重新評估目標受眾和預算分配',
            'impact': '提升整體投資回報',
            'urgency': 'medium'
        })

    if analysis['performance_rate'] < 50:
        recommendations.append({
            'type': 'warning',
            'title': f'只有 {analysis["performance_rate"]:.1f}% 的活動達到目標',
            'description': '大部分活動表現不佳，需要策略性調整',
            'action': '分析成功活動特徵並複製',
            'impact': '提升整體成功率',
            'urgency': 'high'
        })

    return recommendations

def create_recommendation_card(recommendation, key):
    """創建建議卡片"""
    if recommendation['urgency'] == 'high':
        st.error(f"🚨 **{recommendation['title']}**")
    elif recommendation['urgency'] == 'medium':
        st.warning(f"⚠️ **{recommendation['title']}**")
    else:
        st.info(f"💡 **{recommendation['title']}**")

    with st.expander("查看詳細建議"):
        st.write(f"**問題描述**: {recommendation['description']}")
        st.write(f"**建議行動**: {recommendation['action']}")
        st.write(f"**預期影響**: {recommendation['impact']}")

def identify_problem_campaigns(df, target_roas, max_cpa):
    """識別問題活動"""
    if df.empty:
        return pd.DataFrame()

    problems = []

    for idx, campaign in df.iterrows():
        issues = []
        suggestions = []

        if campaign['購買 ROAS（廣告投資報酬率）'] < 1.0:
            issues.append("虧損")
            suggestions.append("立即暫停或調整策略")
        elif campaign['購買 ROAS（廣告投資報酬率）'] < target_roas:
            issues.append("低ROAS")
            suggestions.append("優化受眾或創意")

        if campaign['每次購買的成本'] > max_cpa:
            issues.append("高CPA")
            suggestions.append("降低競價或改善轉換率")

        if campaign['購買次數'] == 0 and campaign['花費金額 (TWD)'] > 0:
            issues.append("無轉換")
            suggestions.append("檢查落地頁和追蹤設定")

        if issues:
            problems.append({
                '行銷活動名稱': campaign['行銷活動名稱'],
                '問題類型': ' / '.join(issues),
                '購買 ROAS（廣告投資報酬率）': campaign['購買 ROAS（廣告投資報酬率）'],
                '每次購買的成本': campaign['每次購買的成本'],
                '花費金額 (TWD)': campaign['花費金額 (TWD)'],
                '建議動作': ' | '.join(suggestions)
            })

    return pd.DataFrame(problems)

def identify_top_performers(df, target_roas):
    """識別高表現活動"""
    if df.empty:
        return pd.DataFrame()

    # 篩選條件：ROAS >= 目標 且 有購買轉換 且 花費 > 1000
    top_performers = df[
        (df['購買 ROAS（廣告投資報酬率）'] >= target_roas) &
        (df['購買次數'] > 0) &
        (df['花費金額 (TWD)'] > 1000)
    ].copy()

    # 按 ROAS 排序
    top_performers = top_performers.sort_values('購買 ROAS（廣告投資報酬率）', ascending=False)

    return top_performers.head(5)  # 只取前5名

def create_performance_chart(top_performers):
    """創建表現圖表"""
    if top_performers.empty:
        return None

    fig = px.scatter(
        top_performers,
        x='花費金額 (TWD)',
        y='購買 ROAS（廣告投資報酬率）',
        size='購買次數',
        color='購買次數',
        hover_data=['行銷活動名稱'],
        title="高表現活動分析",
        labels={
            '花費金額 (TWD)': '花費金額 (TWD)',
            '購買 ROAS（廣告投資報酬率）': 'ROAS',
            '購買次數': '購買次數'
        }
    )

    fig.update_layout(height=400)
    return fig

def identify_underperformers(df, target_roas, max_cpa):
    """識別低效活動"""
    if df.empty:
        return pd.DataFrame()

    underperformers = df[
        (df['購買 ROAS（廣告投資報酬率）'] < target_roas) |
        (df['每次購買的成本'] > max_cpa)
    ].copy()

    # 排序：先按ROAS升序，再按CPA降序
    underperformers = underperformers.sort_values(['購買 ROAS（廣告投資報酬率）', '每次購買的成本'], ascending=[True, False])

    return underperformers.head(10)  # 只取前10名問題活動

def analyze_campaign_issues(campaign, target_roas, max_cpa):
    """分析活動問題"""
    issues = []
    solutions = []

    current_roas = campaign['購買 ROAS（廣告投資報酬率）']
    current_cpa = campaign['每次購買的成本']
    current_ctr = campaign.get('CTR（全部）', 0)

    if current_roas < 1.0:
        issues.append("嚴重虧損，ROAS < 1.0")
        solutions.append("立即暫停活動並重新評估策略")
    elif current_roas < target_roas:
        issues.append(f"ROAS ({current_roas:.2f}) 低於目標 ({target_roas:.1f})")
        solutions.append("優化受眾定位或提升創意吸引力")

    if current_cpa > max_cpa:
        issues.append(f"CPA (${current_cpa:.0f}) 超過預算 (${max_cpa})")
        solutions.append("降低競價或改善落地頁轉換率")

    if current_ctr < 1.0:
        issues.append(f"CTR ({current_ctr:.2f}%) 過低")
        solutions.append("更新廣告創意或調整受眾")

    if campaign['購買次數'] == 0:
        issues.append("沒有轉換")
        solutions.append("檢查追蹤設定和落地頁體驗")

    return {'issues': issues, 'solutions': solutions}

def generate_budget_recommendations(df, target_roas):
    """生成預算建議"""
    if df.empty:
        return []

    recommendations = []

    for idx, campaign in df.iterrows():
        current_spend = campaign['花費金額 (TWD)']
        current_roas = campaign['購買 ROAS（廣告投資報酬率）']

        adjustment = 0
        direction = "維持"
        reason = ""

        if current_roas >= target_roas * 1.2:  # 表現超優
            adjustment = current_spend * 0.3  # 增加30%
            direction = "增加"
            reason = f"ROAS ({current_roas:.2f}) 表現優異，建議擴大投資"
        elif current_roas >= target_roas:  # 達標
            adjustment = current_spend * 0.1  # 小幅增加10%
            direction = "增加"
            reason = f"ROAS ({current_roas:.2f}) 達標，建議適度增加"
        elif current_roas >= 1.0:  # 勉強盈利
            adjustment = current_spend * 0.2  # 減少20%
            direction = "減少"
            reason = f"ROAS ({current_roas:.2f}) 偏低，建議減少投資"
        else:  # 虧損
            adjustment = current_spend * 0.5  # 大幅減少50%
            direction = "減少"
            reason = f"ROAS ({current_roas:.2f}) 虧損，建議大幅減少或暫停"

        if adjustment > 0:
            recommendations.append({
                '活動名稱': campaign['行銷活動名稱'],
                '當前預算': current_spend,
                '建議預算': current_spend + adjustment if direction == "增加" else current_spend - adjustment,
                '調整金額': adjustment,
                '調整方向': direction,
                '原因': reason
            })

    return recommendations

def create_budget_distribution_chart(df):
    """創建預算分配圖表"""
    if df.empty:
        return None

    # 取前10大花費活動
    top_spenders = df.nlargest(10, '花費金額 (TWD)')

    fig = px.pie(
        values=top_spenders['花費金額 (TWD)'],
        names=top_spenders['行銷活動名稱'],
        title="當前預算分配 (Top 10)"
    )

    fig.update_layout(height=400)
    return fig

def create_recommended_budget_chart(budget_recommendations):
    """創建建議預算圖表"""
    if not budget_recommendations:
        return None

    df_budget = pd.DataFrame(budget_recommendations)

    fig = px.pie(
        values=df_budget['建議預算'],
        names=df_budget['活動名稱'],
        title="建議預算分配"
    )

    fig.update_layout(height=400)
    return fig

def analyze_overall_strategy(df, target_roas):
    """分析整體策略"""
    if df.empty:
        return {}

    return {
        'avg_roas': df['購買 ROAS（廣告投資報酬率）'].mean(),
        'total_campaigns': len(df),
        'successful_campaigns': len(df[df['購買 ROAS（廣告投資報酬率）'] >= target_roas]),
        'total_spend': df['花費金額 (TWD)'].sum(),
        'total_purchases': df['購買次數'].sum(),
        'avg_ctr': df['CTR（全部）'].mean(),
        'avg_cpm': df['CPM（每千次廣告曝光成本）'].mean()
    }

def calculate_efficiency_score(df):
    """計算效率評分"""
    if df.empty:
        return 0.0

    # 綜合多個指標計算效率分數
    roas_score = min(df['購買 ROAS（廣告投資報酬率）'].mean() / 3.0, 1.0)  # 以3.0為滿分
    ctr_score = min(df['CTR（全部）'].mean() / 2.0, 1.0)  # 以2%為滿分
    conversion_rate = df['購買次數'].sum() / df['觸及人數'].sum() if df['觸及人數'].sum() > 0 else 0
    conv_score = min(conversion_rate * 100, 1.0)  # 以1%為滿分

    # 加權平均
    efficiency = (roas_score * 0.5 + ctr_score * 0.3 + conv_score * 0.2)
    return efficiency

def generate_strategic_recommendations(strategy_analysis):
    """生成策略建議"""
    recommendations = []

    success_rate = strategy_analysis['successful_campaigns'] / strategy_analysis['total_campaigns'] if strategy_analysis['total_campaigns'] > 0 else 0

    if success_rate < 0.3:
        recommendations.append({
            'priority': 'high',
            'title': '成功率過低，需要重新評估整體策略',
            'description': '不到30%的活動達到目標，建議暫停表現差的活動，專注於成功活動的擴展'
        })

    if strategy_analysis['avg_roas'] < 2.0:
        recommendations.append({
            'priority': 'high',
            'title': '整體ROAS偏低，需要提升轉換效率',
            'description': '平均ROAS低於2.0，建議優化落地頁、提升產品吸引力或調整定價策略'
        })

    if strategy_analysis['avg_ctr'] < 1.0:
        recommendations.append({
            'priority': 'medium',
            'title': 'CTR偏低，創意素材需要更新',
            'description': '點擊率低於1%，建議測試新的廣告創意、文案或視覺元素'
        })

    if len(recommendations) == 0:
        recommendations.append({
            'priority': 'low',
            'title': '整體表現良好，建議進行細節優化',
            'description': '繼續監控表現並進行A/B測試以持續改善'
        })

    return recommendations

def compare_with_benchmarks(df):
    """與行業基準比較"""
    if df.empty:
        return {}

    # 行業基準（示例值）
    benchmarks = {
        'roas': 2.5,
        'ctr': 1.8,
        'cpa': 350
    }

    current = {
        'roas': df['購買 ROAS（廣告投資報酬率）'].mean(),
        'ctr': df['CTR（全部）'].mean(),
        'cpa': df['每次購買的成本'].mean()
    }

    comparison = {}
    for metric in benchmarks:
        comparison[metric] = {
            'current': current[metric],
            'benchmark': benchmarks[metric],
            'vs_benchmark': current[metric] - benchmarks[metric]
        }

    return comparison

def generate_action_plan(analysis_results, strategy_analysis):
    """生成行動計劃"""
    actions = []

    if analysis_results.get('poor_performers', 0) > 0:
        actions.append({
            'title': '暫停虧損活動',
            'priority': '高',
            'timeline': '立即執行',
            'impact': '防止進一步虧損',
            'steps': [
                '檢視所有ROAS < 1.0的活動',
                '分析虧損原因',
                '暫停表現最差的活動',
                '保留部分預算用於測試優化'
            ]
        })

    if analysis_results.get('performance_rate', 0) < 50:
        actions.append({
            'title': '複製成功活動策略',
            'priority': '高',
            'timeline': '1-2天',
            'impact': '提升整體成功率',
            'steps': [
                '分析高表現活動的共同特徵',
                '提取成功的受眾、創意、預算設定',
                '將成功策略應用到新活動',
                '逐步測試和優化'
            ]
        })

    actions.append({
        'title': '優化創意素材',
        'priority': '中',
        'timeline': '3-5天',
        'impact': '提升點擊率和轉換率',
        'steps': [
            '分析當前創意的表現數據',
            '設計新的廣告文案和視覺元素',
            '進行A/B測試',
            '保留表現最好的版本'
        ]
    })

    actions.append({
        'title': '調整受眾策略',
        'priority': '中',
        'timeline': '1週',
        'impact': '降低CPA，提升ROAS',
        'steps': [
            '分析當前受眾的轉換表現',
            '測試新的受眾群體',
            '調整年齡、興趣、行為定位',
            '監控並優化受眾組合'
        ]
    })

    return actions

def generate_ai_root_cause_analysis_single(campaign_data, full_campaign_data, all_campaigns_df, target_roas, max_cpa, use_rag=False):
    """
    使用 AI 針對單一廣告進行深度根因分析

    Args:
        campaign_data: 選擇的活動數據（Series）
        full_campaign_data: 該活動的完整數據（DataFrame，可能有多筆記錄）
        all_campaigns_df: 所有活動 DataFrame（用於對比）
        target_roas: 目標 ROAS
        max_cpa: 最大 CPA
        use_rag: 是否使用 RAG 增強（參考歷史成功案例）

    Returns:
        AI 分析結果
    """
    llm_service = get_llm_service()

    if not llm_service.is_available():
        return "AI 服務目前無法使用"

    # 準備該廣告的詳細數據
    campaign_name = campaign_data['行銷活動名稱']

    # 從完整數據中取得更多資訊
    if not full_campaign_data.empty:
        full_data = full_campaign_data.iloc[0]

        campaign_details = {
            "活動名稱": campaign_name,
            "問題類型": campaign_data['問題類型'],
            "表現數據": {
                "ROAS": f"{campaign_data['購買 ROAS（廣告投資報酬率）']:.2f}",
                "CPA": f"{campaign_data['每次購買的成本']:.0f}",
                "花費": f"{campaign_data['花費金額 (TWD)']:,.0f}",
                "CTR": f"{full_data.get('CTR（全部）', 0):.2f}%",
                "購買次數": f"{full_data.get('購買次數', 0):.0f}",
                "觸及人數": f"{full_data.get('觸及人數', 0):,.0f}",
                "點擊次數": f"{full_data.get('連結點擊次數', 0):,.0f}",
            },
            "受眾資訊": {
                "目標受眾": full_data.get('目標', '未知'),
                "年齡": full_data.get('年齡', '未知'),
                "性別": full_data.get('性別', '未知'),
            },
            "廣告素材": {
                "標題": full_data.get('標題', '未知')[:100] if pd.notna(full_data.get('標題')) else '未知',
                "內文": full_data.get('內文', '未知')[:200] if pd.notna(full_data.get('內文')) else '未知',
            },
            "品質評分": {
                "品質排名": full_data.get('品質排名', '未知'),
                "互動率排名": full_data.get('互動率排名', '未知'),
                "轉換率排名": full_data.get('轉換率排名', '未知'),
            }
        }
    else:
        campaign_details = {
            "活動名稱": campaign_name,
            "問題類型": campaign_data['問題類型'],
            "ROAS": f"{campaign_data['購買 ROAS（廣告投資報酬率）']:.2f}",
            "CPA": f"{campaign_data['每次購買的成本']:.0f}",
            "花費": f"{campaign_data['花費金額 (TWD)']:,.0f}"
        }

    # 準備對比數據（高表現活動參考）
    high_performers = all_campaigns_df[
        all_campaigns_df['購買 ROAS（廣告投資報酬率）'] >= target_roas
    ]

    if not high_performers.empty:
        avg_high_performer = {
            "平均ROAS": f"{high_performers['購買 ROAS（廣告投資報酬率）'].mean():.2f}",
            "平均CTR": f"{high_performers['CTR（全部）'].mean():.2f}%",
            "平均CPA": f"{high_performers['每次購買的成本'].mean():.0f}",
        }
    else:
        avg_high_performer = {"說明": "目前沒有達標活動可供參考"}

    # 整體平均數據
    overall_avg = {
        "平均ROAS": f"{all_campaigns_df['購買 ROAS（廣告投資報酬率）'].mean():.2f}",
        "平均CTR": f"{all_campaigns_df['CTR（全部）'].mean():.2f}%",
        "平均CPA": f"{all_campaigns_df['每次購買的成本'].mean():.0f}",
    }

    # RAG 增強：獲取歷史成功案例
    rag_context = ""
    if use_rag:
        try:
            rag = RAGService()
            if rag.load_knowledge_base("ad_creatives"):
                # 根據該廣告的受眾和問題類型搜尋相關成功案例
                if not full_campaign_data.empty:
                    full_data = full_campaign_data.iloc[0]
                    audience = full_data.get('目標', '未知')
                    age = full_data.get('年齡', '未知')
                    gender = full_data.get('性別', '未知')

                    # 構建搜尋查詢
                    query = f"高 ROAS 廣告，受眾：{audience}，年齡：{age}，性別：{gender}"
                else:
                    query = "高 ROAS 廣告優化策略"

                # 獲取相似案例
                similar_ads = rag.search_similar_ads(query, k=3)

                if similar_ads:
                    rag_context = "\n\n## 📚 歷史成功案例參考\n\n"
                    for i, doc in enumerate(similar_ads, 1):
                        rag_context += f"### 案例 {i}（ROAS {doc.metadata.get('roas', 0):.2f}）\n"
                        rag_context += f"{doc.page_content}\n\n"
                    rag_context += "**請參考以上案例的成功要素，提供具體可行的優化建議。**\n"
        except Exception as e:
            # RAG 失敗時靜默處理，不影響主要分析
            pass

    # 建構 Prompt
    prompt = f"""
你是專業的 Meta 廣告投放顧問。請針對以下**單一廣告活動**進行深度分析。

## 目標設定
- 目標 ROAS: {target_roas}
- 最大 CPA: ${max_cpa}

## 待分析廣告活動
{json.dumps(campaign_details, ensure_ascii=False, indent=2)}

## 對比數據
### 高表現活動平均（ROAS ≥ {target_roas}）
{json.dumps(avg_high_performer, ensure_ascii=False, indent=2)}

### 整體活動平均
{json.dumps(overall_avg, ensure_ascii=False, indent=2)}{rag_context}

## 請提供以下專屬分析：

### 1. 🔍 根因診斷
針對**這個廣告**，分析表現不佳的根本原因：
- 對比高表現活動，找出關鍵差異
- 檢查受眾、素材、品質評分
- 判斷是哪個環節出問題（觸及→點擊→轉換）

### 2. 💡 優化方案（3-5 個具體建議）
針對**這個廣告**，提供可執行的優化建議：

**每個建議請包含**：
- 🎯 **優化項目**：要改什麼
- 📋 **具體步驟**：怎麼改（3-5 個步驟）
- 📊 **預期效果**：ROAS 預期提升幅度
- ⏱️ **執行時間**：需要多久
- 🚦 **優先級**：🔴 高 / 🟡 中 / 🟢 低

### 3. ⚠️ 風險提示
執行這些優化時要注意什麼？

### 4. ⚡ 快速勝利
找出 1 個可以**今天就執行且效果明顯**的優化動作。

### 5. 📈 預期改善路徑
如果按照建議執行，預期這個廣告的表現會如何改善？（列出階段性目標）

請以清晰、專業、可執行的方式回答，使用繁體中文。
重點是**針對這個廣告的專屬建議**，不要泛泛而談。
"""

    # 調用 LLM（使用 GPT-3.5 Turbo 以節省成本）
    response = llm_service.generate_insights(
        prompt,
        model="gpt-3.5-turbo",
        max_tokens=2000,  # 增加 token 數以獲得更詳細的分析
        temperature=0.7
    )

    return response

def display_ai_analysis(analysis_text, campaign_name):
    """
    顯示 AI 分析結果

    Args:
        analysis_text: AI 生成的分析文字
        campaign_name: 廣告活動名稱
    """
    # 使用 expander 組織內容
    with st.expander(f"📊 「{campaign_name}」完整 AI 分析報告", expanded=True):
        st.markdown(analysis_text)

    # 提供下載選項
    col1, col2 = st.columns([3, 1])

    with col2:
        st.download_button(
            label="📥 下載分析報告",
            data=f"廣告活動：{campaign_name}\n生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{analysis_text}",
            file_name=f"ai_analysis_{campaign_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )

    # 提示後續動作
    st.info("💡 **建議**：將分析報告下載後，與團隊討論執行計畫，並追蹤優化成效。")

def generate_ai_urgent_analysis(df, urgent_recommendations, target_roas, max_cpa):
    """
    使用 AI 對緊急問題進行深度分析

    Args:
        df: 廣告數據 DataFrame
        urgent_recommendations: 緊急建議列表
        target_roas: 目標 ROAS
        max_cpa: 最大 CPA

    Returns:
        AI 分析結果（Markdown 格式）
    """
    llm_service = get_llm_service()

    if not llm_service.is_available():
        return {"error": "AI 服務目前無法使用"}

    # 準備緊急問題摘要
    urgent_summary = []
    for rec in urgent_recommendations:
        urgent_summary.append({
            "類型": rec['type'],
            "標題": rec['title'],
            "描述": rec['description'],
            "緊急程度": rec['urgency']
        })

    # 取得問題廣告清單
    problem_ads = df[
        (df['購買 ROAS（廣告投資報酬率）'] < 1.0) |
        (df['每次購買的成本'] > max_cpa)
    ]

    # 計算關鍵統計數據
    total_problem_spend = problem_ads['花費金額 (TWD)'].sum()
    total_spend = df['花費金額 (TWD)'].sum()
    problem_spend_ratio = (total_problem_spend / total_spend * 100) if total_spend > 0 else 0

    # 建構 Prompt
    prompt = f"""
你是專業的 Meta 廣告危機處理顧問。當前廣告帳戶出現緊急問題，需要立即處理。

## 🔴 緊急問題概況
{json.dumps(urgent_summary, ensure_ascii=False, indent=2)}

## 📊 問題嚴重程度
- 問題廣告數量：{len(problem_ads)} 個（佔總數 {len(problem_ads)/len(df)*100:.1f}%）
- 問題廣告花費：${total_problem_spend:,.0f}（佔總花費 {problem_spend_ratio:.1f}%）
- 整體平均 ROAS：{df['購買 ROAS（廣告投資報酬率）'].mean():.2f}（目標：{target_roas}）

## 問題廣告詳情（花費最高的前 3 個）
{problem_ads.nlargest(3, '花費金額 (TWD)')[['行銷活動名稱', '購買 ROAS（廣告投資報酬率）', '每次購買的成本', '花費金額 (TWD)']].to_dict('records') if not problem_ads.empty else '無'}

## 請提供：

### 1. ⚡ 立即行動方案（今天就要執行）
針對最嚴重的問題，提供 1-3 個**今天**就必須執行的緊急措施：
- 🎯 具體動作（例如：暫停哪些廣告）
- 💰 預期挽回損失金額
- ⏱️ 執行時間（以分鐘計）

### 2. 🔍 根本原因診斷
分析為什麼會出現這些緊急問題：
- 是受眾問題？創意疲勞？競爭加劇？
- 有沒有共同模式（例如：同一類受眾都表現不佳）

### 3. 📋 優先處理順序
將所有問題廣告按緊急程度排序，說明：
- 哪些要立即暫停
- 哪些要降低預算
- 哪些可以嘗試優化

### 4. 🛡️ 防範措施
如何避免未來再次出現類似問題：
- 監控哪些指標
- 設定什麼警報
- 多久檢視一次

請以清晰、簡潔、可立即執行的方式回答。重點是**快速止血，減少損失**。
使用繁體中文，使用 Markdown 格式，加上適當的 emoji。
"""

    # 調用 LLM
    response = llm_service.generate_insights(
        prompt,
        model="gpt-4o-mini",
        max_tokens=1500,
        temperature=0.7
    )

    return response

def generate_ai_performance_analysis(df, top_performers, underperformers, target_roas):
    """
    使用 AI 分析效能優化機會

    Args:
        df: 完整廣告數據 DataFrame
        top_performers: 高表現活動 DataFrame
        underperformers: 低效活動 DataFrame
        target_roas: 目標 ROAS

    Returns:
        AI 分析結果（Markdown 格式）
    """
    llm_service = get_llm_service()

    if not llm_service.is_available():
        return {"error": "AI 服務目前無法使用"}

    # 分析高表現活動的共同特徵
    if not top_performers.empty:
        top_features = {
            "平均ROAS": f"{top_performers['購買 ROAS（廣告投資報酬率）'].mean():.2f}",
            "平均CTR": f"{top_performers['CTR（全部）'].mean():.2f}%",
            "平均CPA": f"${top_performers['每次購買的成本'].mean():.0f}",
            "主要受眾": top_performers['目標'].value_counts().head(3).to_dict() if '目標' in top_performers.columns else {},
            "主要活動類型": top_performers['行銷活動名稱'].head(3).tolist()
        }
    else:
        top_features = {"說明": "沒有高表現活動"}

    # 分析低效活動的共同問題
    if not underperformers.empty:
        low_features = {
            "平均ROAS": f"{underperformers['購買 ROAS（廣告投資報酬率）'].mean():.2f}",
            "平均CTR": f"{underperformers['CTR（全部）'].mean():.2f}%",
            "平均CPA": f"${underperformers['每次購買的成本'].mean():.0f}",
            "主要受眾": underperformers['目標'].value_counts().head(3).to_dict() if '目標' in underperformers.columns else {},
            "問題活動數": len(underperformers)
        }
    else:
        low_features = {"說明": "沒有低效活動"}

    # 建構 Prompt
    prompt = f"""
你是專業的 Meta 廣告效能優化顧問。請分析以下數據，找出成功模式並複製到低效活動。

## 📊 整體狀況
- 總活動數：{len(df)}
- 高表現活動：{len(top_performers)} 個（ROAS ≥ {target_roas}）
- 低效活動：{len(underperformers)} 個
- 整體平均 ROAS：{df['購買 ROAS（廣告投資報酬率）'].mean():.2f}

## ✅ 高表現活動特徵
{json.dumps(top_features, ensure_ascii=False, indent=2)}

## ❌ 低效活動特徵
{json.dumps(low_features, ensure_ascii=False, indent=2)}

## 請提供：

### 1. 🔍 成功模式分析
高表現活動有哪些共同特徵？
- 受眾特徵（年齡、性別、興趣）
- 創意風格
- 預算設定
- 投放時機

### 2. 📋 複製成功策略
如何將成功模式應用到低效活動？
提供 3-5 個具體可執行的優化方案：
- 🎯 優化目標（例如：將受眾從A改為B）
- 📝 執行步驟（1-2-3步驟）
- 📈 預期提升（ROAS 從 X 提升到 Y）
- ⏱️ 測試時長（需要跑多久才能看到效果）

### 3. ⚠️ 避免的陷阱
有哪些常見錯誤？
- 哪些受眾不適合
- 哪些創意風格效果不佳
- 預算設定的盲點

### 4. 🚀 快速勝利機會
找出 1-2 個可以快速提升效能的方法（7天內見效）。

請以清晰、具體、可執行的方式回答。
使用繁體中文，使用 Markdown 格式，加上適當的 emoji。
"""

    # 調用 LLM
    response = llm_service.generate_insights(
        prompt,
        model="gpt-4o-mini",
        max_tokens=1500,
        temperature=0.7
    )

    return response

def generate_ai_budget_analysis(df, budget_recommendations, target_roas):
    """
    使用 AI 分析預算優化策略

    Args:
        df: 完整廣告數據 DataFrame
        budget_recommendations: 預算調整建議列表
        target_roas: 目標 ROAS

    Returns:
        AI 分析結果（Markdown 格式）
    """
    llm_service = get_llm_service()

    if not llm_service.is_available():
        return {"error": "AI 服務目前無法使用"}

    # 準備預算調整摘要
    total_budget = df['花費金額 (TWD)'].sum()
    total_increase = sum([rec['調整金額'] for rec in budget_recommendations if rec['調整方向'] == '增加'])
    total_decrease = sum([rec['調整金額'] for rec in budget_recommendations if rec['調整方向'] == '減少'])

    # 分析歷史數據趨勢
    high_roas_campaigns = df[df['購買 ROAS（廣告投資報酬率）'] >= target_roas]
    low_roas_campaigns = df[df['購買 ROAS（廣告投資報酬率）'] < target_roas]

    # 取得前3個建議增加預算的活動
    increase_recommendations = [rec for rec in budget_recommendations if rec['調整方向'] == '增加'][:3]
    decrease_recommendations = [rec for rec in budget_recommendations if rec['調整方向'] == '減少'][:3]

    # 建構 Prompt
    prompt = f"""
你是專業的 Meta 廣告預算優化顧問。請分析以下預算分配數據，提供智能預算調整策略。

## 📊 當前預算狀況
- 總預算：${total_budget:,.0f}
- 建議增加：${total_increase:,.0f}
- 建議減少：${total_decrease:,.0f}
- 淨變化：${total_increase - total_decrease:+,.0f}

## 🎯 活動表現分布
- 高表現活動（ROAS ≥ {target_roas}）：{len(high_roas_campaigns)} 個（總花費 ${high_roas_campaigns['花費金額 (TWD)'].sum():,.0f}）
- 低表現活動（ROAS < {target_roas}）：{len(low_roas_campaigns)} 個（總花費 ${low_roas_campaigns['花費金額 (TWD)'].sum():,.0f}）

## ⬆️ 建議增加預算的活動（Top 3）
{json.dumps(increase_recommendations, ensure_ascii=False, indent=2) if increase_recommendations else '無'}

## ⬇️ 建議減少預算的活動（Top 3）
{json.dumps(decrease_recommendations, ensure_ascii=False, indent=2) if decrease_recommendations else '無'}

## 請提供：

### 1. 📈 預算優化策略
基於歷史數據，提供預算重新分配方案：
- **核心策略**：重點投資哪些活動？減少哪些？
- **分配比例**：建議的預算分配百分比
- **執行時機**：何時調整預算最佳？

### 2. 🔮 預測與風險評估
針對建議的預算調整：
- **預期 ROAS 變化**：
  - 增加預算後，ROAS 會如何變化？（考慮受眾飽和）
  - 減少預算後，會損失多少轉換？
- **風險因素**：
  - 受眾飽和風險（增加預算可能導致 ROAS 下降）
  - 競爭加劇風險
  - 季節性影響
- **信心區間**：預測的可信度（高/中/低）

### 3. 💡 分階段執行計畫
不要一次調整太多，提供漸進式方案：

**第1階段（立即執行）**：
- 調整哪些活動
- 調整幅度（建議先調整 20-30%）
- 觀察期（3-5天）
- 成功指標（ROAS 維持在 X 以上）

**第2階段（若第1階段成功）**：
- 進一步調整方案
- 擴大調整幅度
- 新增測試活動

**第3階段（優化穩定後）**：
- 持續優化建議
- 新受眾測試

### 4. ⚠️ 注意事項
- 哪些活動不建議大幅調整預算？為什麼？
- 調整預算後需要監控哪些指標？
- 多久重新評估一次？

請以清晰、具體、可執行的方式回答。重點是**避免盲目加預算導致 ROAS 下降**。
使用繁體中文，使用 Markdown 格式，加上適當的 emoji。
"""

    # 調用 LLM
    response = llm_service.generate_insights(
        prompt,
        model="gpt-4o-mini",
        max_tokens=2000,
        temperature=0.7
    )

    return response

if __name__ == "__main__":
    show_optimization_recommendations()