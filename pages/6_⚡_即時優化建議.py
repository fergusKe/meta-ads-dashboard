import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.data_loader import load_meta_ads_data, filter_data_by_date_range
import numpy as np

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

if __name__ == "__main__":
    show_optimization_recommendations()