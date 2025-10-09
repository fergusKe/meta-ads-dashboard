import streamlit as st
import pandas as pd
from datetime import datetime
from utils.data_loader import load_meta_ads_data
from utils.agents.daily_check_agent import DailyCheckAgent
from utils.ui_feedback import queue_completion_message, render_completion_message
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="智能 Agent 巡檢", page_icon="🤖", layout="wide")

def display_problem_campaigns(problems):
    """顯示問題活動"""
    if not problems:
        st.success("✅ 未發現問題活動")
        return

    st.error(f"🚨 發現 {len(problems)} 個問題活動")

    # 轉換為 DataFrame 顯示
    data = []
    for p in problems:
        data.append({
            '活動名稱': p.campaign_name,
            'ROAS': p.roas,
            '花費': f"NT$ {p.spend:,.0f}",
            '購買次數': p.purchases,
            '問題類型': p.issue_type,
            '嚴重程度': p.severity,
            '根本原因': p.root_cause
        })

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)

def display_recommendations(recommendations):
    """顯示優化建議"""
    if not recommendations:
        return

    st.markdown("### 💡 優化建議")

    # 按優先級分組
    high_priority = [r for r in recommendations if '🔴' in r.priority]
    medium_priority = [r for r in recommendations if '🟡' in r.priority]
    low_priority = [r for r in recommendations if '🟢' in r.priority]

    for priority_list, title in [
        (high_priority, "🔴 高優先級建議"),
        (medium_priority, "🟡 中優先級建議"),
        (low_priority, "🟢 低優先級建議")
    ]:
        if priority_list:
            st.markdown(f"#### {title}")
            for rec in priority_list:
                with st.expander(f"{rec.priority} {rec.action}", expanded=('🔴' in rec.priority)):
                    st.markdown(f"**目標**: {rec.target}")
                    st.markdown(f"**預期效果**: {rec.expected_impact}")

                    st.markdown("**執行步驟**:")
                    for i, step in enumerate(rec.execution_steps, 1):
                        st.markdown(f"{i}. {step}")

def create_health_gauge(score):
    """創建健康分數儀表板"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "整體健康分數", 'font': {'size': 24}},
        delta={'reference': 70, 'increasing': {'color': "green"}},
        gauge={
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "darkblue"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 50], 'color': '#ffcccc'},
                {'range': [50, 70], 'color': '#ffffcc'},
                {'range': [70, 100], 'color': '#ccffcc'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 70
            }
        }
    ))

    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=60, b=20)
    )

    return fig

def main():
    st.title("🤖 智能 Agent 每日巡檢")
    st.markdown("""
    使用 **Pydantic AI** 開發的自主 Agent，自動檢查所有廣告活動並提供優化建議。

    **特色**：
    - ✅ 完全型別安全（Pydantic models）
    - ✅ 自主分析和決策
    - ✅ 結構化輸出
    - ✅ 整合現有 RAG 服務
    - ✅ 可觀測性追蹤（Logfire）
    """)

    # 載入數據
    df = load_meta_ads_data()
    if df is None:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    # 主要內容
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("## 📊 當前狀態")

        # 快速指標
        total_spend = df['花費金額 (TWD)'].sum()
        total_campaigns = df['行銷活動名稱'].nunique()
        avg_roas = df['購買 ROAS（廣告投資報酬率）'].mean()

        metric_col1, metric_col2, metric_col3 = st.columns(3)
        with metric_col1:
            st.metric("總活動數", total_campaigns)
        with metric_col2:
            st.metric("總花費", f"NT$ {total_spend:,.0f}")
        with metric_col3:
            st.metric("平均 ROAS", f"{avg_roas:.2f}")

    with col2:
        st.markdown("## 🎯 執行 Agent 巡檢")

        # Agent 資訊
        with st.expander("ℹ️ Agent 資訊", expanded=False):
            st.markdown("""
            **框架**: Pydantic AI
            **模型**: GPT-4o-mini
            **工具數量**: 4 個
            - 獲取活動摘要
            - 獲取活動表現
            - 識別低 ROAS 活動
            - 計算風險金額

            **輸出**: 完全型別安全的結構化結果
            """)

        st.markdown("### ⚙️ 巡檢設定")

        # 1. 日期範圍篩選
        date_range_option = st.selectbox(
            "📅 分析時間範圍",
            ["最近 7 天", "最近 30 天", "最近 60 天", "最近 90 天", "全部數據"],
            index=1,  # 預設：最近 30 天
            help="只分析指定時間範圍內的廣告活動"
        )

        # 根據選擇篩選數據
        if date_range_option != "全部數據":
            from datetime import datetime, timedelta

            days_map = {
                "最近 7 天": 7,
                "最近 30 天": 30,
                "最近 60 天": 60,
                "最近 90 天": 90
            }

            days = days_map[date_range_option]
            cutoff_date = datetime.now() - timedelta(days=days)

            # 篩選數據（使用 assign 避免 DataFrame fragmentation）
            if '開始' in df.columns:
                df_with_date = df.assign(開始_dt=pd.to_datetime(df['開始'], errors='coerce'))
                df_filtered = df_with_date[df_with_date['開始_dt'] >= cutoff_date].copy()

                if len(df_filtered) == 0:
                    st.warning(f"⚠️ {date_range_option}內沒有數據，將使用全部數據")
                    df_filtered = df
                else:
                    original_count = df['行銷活動名稱'].nunique()
                    filtered_count = df_filtered['行銷活動名稱'].nunique()
                    st.info(f"✅ 已篩選：{filtered_count} 個活動（原 {original_count} 個）")
                    df = df_filtered

        # 2. 效能目標設定
        col_roas, col_cpa = st.columns(2)

        with col_roas:
            target_roas = st.number_input(
                "🎯 目標 ROAS",
                min_value=1.0,
                max_value=10.0,
                value=3.0,
                step=0.5,
                help="低於此值的活動將被標記為問題"
            )

        with col_cpa:
            max_cpa = st.number_input(
                "💰 最大 CPA (TWD)",
                min_value=100,
                max_value=5000,
                value=500,
                step=50,
                help="高於此值的活動將被標記為問題"
            )

        st.markdown("---")

        # 3. 執行按鈕
        if st.button("🚀 開始 Agent 巡檢", type="primary", use_container_width=True):
            # 執行 Agent
            with st.spinner("🤖 Agent 正在自主分析所有廣告活動..."):
                try:
                    # 抑制 Agent 的調試輸出
                    import sys
                    import io
                    from contextlib import redirect_stdout, redirect_stderr

                    # 創建空的輸出緩衝區
                    stdout_buffer = io.StringIO()
                    stderr_buffer = io.StringIO()

                    # 重定向標準輸出和錯誤輸出
                    with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                        # 創建並執行 Agent
                        agent = DailyCheckAgent()
                        result = agent.run_daily_check_sync(
                            df=df,
                            target_roas=target_roas,
                            max_cpa=max_cpa
                        )

                    # 儲存結果
                    st.session_state['agent_result'] = result
                    st.session_state['agent_run_time'] = datetime.now()
                    queue_completion_message("daily_check_agent", "✅ Agent 巡檢完成！")
                    # 不使用 st.rerun()，直接在下方顯示結果

                except Exception as e:
                    st.error(f"❌ Agent 執行失敗: {str(e)}")
                    st.exception(e)

    # 顯示結果
    if 'agent_result' in st.session_state:
        st.markdown("---")
        render_completion_message("daily_check_agent")

        result = st.session_state['agent_result']
        run_time = st.session_state.get('agent_run_time', datetime.now())

        st.caption(f"最後執行時間：{run_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # 執行摘要
        st.markdown("## 📋 執行摘要")
        st.info(result.summary)

        # 健康分數和關鍵指標
        col1, col2 = st.columns([1, 2])

        with col1:
            # 健康分數儀表板
            fig = create_health_gauge(result.health_score)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("### 📊 關鍵指標")

            metric_col1, metric_col2, metric_col3 = st.columns(3)
            with metric_col1:
                st.metric("檢查活動數", result.total_campaigns)

            with metric_col2:
                st.metric("問題活動", len(result.problem_campaigns))

            with metric_col3:
                st.metric("緊急問題", len(result.urgent_issues))

            # 風險金額
            st.markdown("---")
            risk_color = "inverse" if result.estimated_risk_amount > 10000 else "normal"
            st.metric(
                "⚠️ 估計風險金額",
                f"NT$ {result.estimated_risk_amount:,.0f}",
                delta=f"占總花費 {(result.estimated_risk_amount/result.total_spend*100):.1f}%" if result.total_spend > 0 else "0%",
                delta_color=risk_color
            )

            st.caption("持續投放低效活動可能浪費的預算")

        st.markdown("---")

        # 緊急問題
        if result.urgent_issues:
            st.markdown("## 🚨 緊急問題")
            for issue in result.urgent_issues:
                st.error(f"⚠️ {issue}")

            st.markdown("---")

        # 問題活動
        st.markdown("## 🔍 問題活動分析")
        display_problem_campaigns(result.problem_campaigns)

        st.markdown("---")

        # 優化建議
        display_recommendations(result.recommendations)

        st.markdown("---")

        # 下載報告
        st.markdown("## 💾 匯出報告")

        # 生成 Markdown 報告
        report_md = f"""# Agent 巡檢報告

**執行時間**: {run_time.strftime('%Y-%m-%d %H:%M:%S')}
**檢查日期**: {result.check_date}

## 執行摘要
{result.summary}

## 關鍵指標
- 總活動數: {result.total_campaigns}
- 總花費: NT$ {result.total_spend:,.0f}
- 平均 ROAS: {result.average_roas:.2f}
- 健康分數: {result.health_score}/100

## 風險評估
- 問題活動數: {len(result.problem_campaigns)}
- 緊急問題數: {len(result.urgent_issues)}
- 估計風險金額: NT$ {result.estimated_risk_amount:,.0f}

## 問題活動

"""
        for p in result.problem_campaigns:
            report_md += f"""
### {p.campaign_name}
- ROAS: {p.roas:.2f}
- 花費: NT$ {p.spend:,.0f}
- 購買次數: {p.purchases}
- 問題類型: {p.issue_type}
- 嚴重程度: {p.severity}
- 根本原因: {p.root_cause}

"""

        report_md += "\n## 優化建議\n\n"
        for rec in result.recommendations:
            report_md += f"""
### {rec.priority} {rec.action}
- 目標: {rec.target}
- 預期效果: {rec.expected_impact}

執行步驟:
"""
            for i, step in enumerate(rec.execution_steps, 1):
                report_md += f"{i}. {step}\n"

            report_md += "\n"

        # 下載按鈕
        st.download_button(
            label="📥 下載 Agent 報告 (Markdown)",
            data=report_md,
            file_name=f"agent_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )

    else:
        # 使用說明
        st.markdown("---")
        st.markdown("""
        ## 📖 使用說明

        ### Agent 工作流程

        1. **數據收集**
           - Agent 自動分析所有廣告活動數據
           - 使用 4 個專用工具收集關鍵指標

        2. **問題識別**
           - 自動識別低 ROAS 活動（< 目標 ROAS）
           - 識別高花費低效活動
           - 計算風險金額

        3. **根因分析**
           - Agent 使用 GPT-4 分析問題根本原因
           - 考慮受眾、素材、預算等多個因素

        4. **生成建議**
           - 提供 3-5 個最重要的優化建議
           - 建議包含具體執行步驟
           - 按優先級排序

        5. **健康評分**
           - 綜合評估整體廣告投放健康度
           - 0-100 分制

        ### Agent 優勢

        ✅ **自主決策**: Agent 自己決定調用哪些工具、如何分析
        ✅ **型別安全**: 輸出結構化，保證數據格式正確
        ✅ **可追蹤**: 整合 Logfire 可觀測性（需設定）
        ✅ **可擴展**: 易於添加新工具和功能

        ### 與傳統 LLM 的差異

        | 特性 | 傳統 LLM | Pydantic AI Agent |
        |------|---------|-------------------|
        | **輸出格式** | 文字（可能不穩定） | 結構化（完全型別安全） |
        | **工具調用** | 手動實作 | 自動管理 |
        | **錯誤處理** | 需自己處理 | 內建重試機制 |
        | **可觀測性** | 需額外整合 | 內建 Logfire |
        | **測試友善** | 困難 | 易於 mock 和測試 |

        ### 技術細節

        - **框架**: Pydantic AI 1.0+
        - **LLM**: OpenAI GPT-4o-mini
        - **整合**: 與現有 LangChain RAG 共存
        - **依賴注入**: FastAPI 風格的 deps
        """)

    # 頁面底部
    st.markdown("---")
    st.markdown("""
    ### 💡 最佳實踐

    **使用頻率**：
    - 📅 **每日**: 早上執行，檢查前一天表現
    - 📅 **每週一**: 檢視週報告，規劃本週優化
    - 📅 **活動上線後**: 3-5 天執行一次，監控初期表現

    **搭配使用**：
    - 🔗 結合「即時優化建議」頁面深度分析
    - 🔗 結合「預算優化建議」調整預算分配
    - 🔗 結合「A/B 測試設計」驗證優化假設

    **Agent 未來擴展**：
    - 🚀 自動執行優化（目前只提供建議）
    - 🚀 對話式互動（用戶可以追問）
    - 🚀 多 Agent 協作（數據分析師 + 策略師 + 文案師）
    - 🚀 定時自動執行（每日早上 9 點自動巡檢）
    """)

if __name__ == "__main__":
    main()
