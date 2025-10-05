import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from utils.data_loader import load_meta_ads_data
from utils.llm_service import get_llm_service
import json
import io

st.set_page_config(page_title="自動化報告", page_icon="📄", layout="wide")

def calculate_period_metrics(df, period_start, period_end):
    """計算特定期間的指標"""
    period_data = df[
        (df['開始'] >= period_start) &
        (df['開始'] <= period_end)
    ]

    if period_data.empty:
        return None

    metrics = {
        "花費": period_data['花費金額 (TWD)'].sum(),
        "觸及人數": period_data['觸及人數'].sum(),
        "點擊次數": period_data['連結點擊次數'].sum(),
        "購買次數": period_data['購買次數'].sum(),
        "營收": period_data['花費金額 (TWD)'].sum() * period_data['購買 ROAS（廣告投資報酬率）'].mean(),
        "ROAS": period_data['購買 ROAS（廣告投資報酬率）'].mean(),
        "CTR": period_data['CTR（全部）'].mean(),
        "CPA": period_data['每次購買的成本'].mean(),
        "轉換率": (period_data['購買次數'].sum() / period_data['連結點擊次數'].sum() * 100) if period_data['連結點擊次數'].sum() > 0 else 0
    }

    return metrics

def get_top_performing_campaigns(df, period_start, period_end, limit=5):
    """獲取表現最好的活動"""
    period_data = df[
        (df['開始'] >= period_start) &
        (df['開始'] <= period_end)
    ]

    campaign_performance = period_data.groupby('行銷活動名稱').agg({
        '花費金額 (TWD)': 'sum',
        '購買 ROAS（廣告投資報酬率）': 'mean',
        '購買次數': 'sum',
        'CTR（全部）': 'mean'
    }).reset_index()

    return campaign_performance.nlargest(limit, '購買 ROAS（廣告投資報酬率）')

def get_underperforming_campaigns(df, period_start, period_end, limit=5):
    """獲取需要改進的活動"""
    period_data = df[
        (df['開始'] >= period_start) &
        (df['開始'] <= period_end)
    ]

    campaign_performance = period_data.groupby('行銷活動名稱').agg({
        '花費金額 (TWD)': 'sum',
        '購買 ROAS（廣告投資報酬率）': 'mean',
        '購買次數': 'sum',
        'CTR（全部）': 'mean'
    }).reset_index()

    # 篩選有足夠花費的活動
    campaign_performance = campaign_performance[
        campaign_performance['花費金額 (TWD)'] >= 1000
    ]

    return campaign_performance.nsmallest(limit, '購買 ROAS（廣告投資報酬率）')

def identify_key_events(df, period_start, period_end):
    """識別關鍵事件"""
    period_data = df[
        (df['開始'] >= period_start) &
        (df['開始'] <= period_end)
    ]

    events = []

    # 檢查是否有新活動上線
    if '開始' in period_data.columns:
        new_campaigns = period_data[
            period_data['開始'] >= period_start
        ]['行銷活動名稱'].unique()

        if len(new_campaigns) > 0:
            events.append({
                '類型': '🆕 新活動上線',
                '描述': f"上線 {len(new_campaigns)} 個新活動",
                '詳情': ', '.join(new_campaigns[:3])
            })

    # 檢查是否有異常高花費
    avg_daily_spend = period_data.groupby('開始')['花費金額 (TWD)'].sum().mean()
    max_daily_spend = period_data.groupby('開始')['花費金額 (TWD)'].sum().max()

    if max_daily_spend > avg_daily_spend * 1.5:
        events.append({
            '類型': '💰 預算異常',
            '描述': f"單日花費達 NT$ {max_daily_spend:,.0f}（平均 {avg_daily_spend:,.0f}）",
            '詳情': '建議檢查預算設定'
        })

    # 檢查是否有 ROAS 突破
    high_roas_campaigns = period_data[
        period_data['購買 ROAS（廣告投資報酬率）'] >= 5.0
    ]

    if not high_roas_campaigns.empty:
        events.append({
            '類型': '🎉 表現突破',
            '描述': f"{len(high_roas_campaigns)} 個廣告 ROAS >= 5.0",
            '詳情': high_roas_campaigns['行銷活動名稱'].iloc[0] if len(high_roas_campaigns) > 0 else ''
        })

    return events

def generate_report_with_ai(report_type, current_metrics, previous_metrics, top_campaigns, underperforming_campaigns, events):
    """使用 AI 生成報告內容"""
    llm_service = get_llm_service()

    if not llm_service.is_available():
        return {"error": "LLM 服務目前無法使用"}

    # 計算變化
    metrics_change = {}
    if previous_metrics:
        for key in current_metrics:
            if key in previous_metrics and previous_metrics[key] != 0:
                change = ((current_metrics[key] - previous_metrics[key]) / previous_metrics[key] * 100)
                metrics_change[key] = f"{change:+.1f}%"
            else:
                metrics_change[key] = "N/A"

    # 建構 Prompt
    prompt = f"""
你是專業的廣告投放分析師，請生成一份專業的{report_type}報告。

## 本期數據（{report_type}）
{json.dumps(current_metrics, ensure_ascii=False, indent=2)}

## 與上期對比
{json.dumps(metrics_change, ensure_ascii=False, indent=2)}

## Top 5 高效活動
{json.dumps(top_campaigns.to_dict('records'), ensure_ascii=False, indent=2)}

## 需改進活動
{json.dumps(underperforming_campaigns.to_dict('records'), ensure_ascii=False, indent=2)}

## 關鍵事件
{json.dumps(events, ensure_ascii=False, indent=2)}

## 請生成以下內容：

### 1. 📊 執行摘要（3-5 句話，給主管看）
用數據說話，突出重點：
- 整體表現如何？
- 最重要的成就是什麼？
- 最需要關注的問題是什麼？

### 2. 📈 關鍵指標分析

**對每個核心指標（花費、ROAS、購買、CTR）**：
- 📊 **數據表現**：本期數據 + 變化趨勢
- 🔍 **分析**：為什麼會有這個變化
- 💡 **洞察**：這代表什麼意義

### 3. 🏆 成功案例

分析 Top 3 高效活動：
- 為什麼表現好？
- 有什麼可以複製的成功要素？
- 如何擴展這些成功？

### 4. ⚠️ 需改善項目

分析表現不佳的活動：
- 主要問題是什麼？
- 根本原因分析
- 具體改善建議（3-5 個可執行步驟）

### 5. 🎯 下期行動計畫

**優先級排序的建議**：
- 🔴 高優先級（立即執行）
- 🟡 中優先級（本週執行）
- 🟢 低優先級（持續觀察）

每個建議包含：
- 具體動作
- 預期效果
- 執行時間

### 6. 💡 策略建議

基於數據趨勢，提供 2-3 個策略級建議：
- 受眾策略調整
- 預算重新分配
- 素材優化方向

請以清晰、專業、數據驅動的方式撰寫，使用繁體中文。
語氣：專業但易懂，適合向主管或客戶報告。
格式：使用 Markdown，包含適當的標題和列表。
"""

    # 調用 LLM
    response = llm_service.generate_insights(
        prompt,
        model="gpt-3.5-turbo",
        max_tokens=3000,
        temperature=0.7
    )

    return response

def export_report_to_markdown(report_content, metrics, period_name):
    """匯出報告為 Markdown 格式"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    markdown_content = f"""# Meta 廣告投放報告 - {period_name}

**生成時間**：{timestamp}
**報告期間**：{period_name}

---

## 📊 數據概覽

| 指標 | 數值 |
|------|------|
| 總花費 | NT$ {metrics['花費']:,.0f} |
| 總觸及 | {metrics['觸及人數']:,.0f} |
| 總點擊 | {metrics['點擊次數']:,.0f} |
| 總購買 | {metrics['購買次數']:.0f} |
| 平均 ROAS | {metrics['ROAS']:.2f} |
| 平均 CTR | {metrics['CTR']:.2f}% |
| 平均 CPA | NT$ {metrics['CPA']:.0f} |
| 轉換率 | {metrics['轉換率']:.2f}% |

---

{report_content}

---

**報告說明**：
- 本報告由 AI 自動生成，基於 Meta 廣告投放數據
- 建議結合實際業務情況進行判斷
- 生成工具：Meta 廣告智能分析儀表板

"""
    return markdown_content

def main():
    st.title("📄 自動化報告生成")
    st.markdown("使用 AI 自動生成專業的週報/月報，節省報告撰寫時間")

    # 載入數據
    df = load_meta_ads_data()
    if df is None:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    # 報告設定區域（移到主要內容區）
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### ⚙️ 報告設定")

        # 報告類型
        report_type = st.selectbox(
            "報告類型",
            ["週報", "月報", "自定義期間"]
        )

        # 日期範圍選擇
        if report_type == "週報":
            # 預設最近一週
            default_end = df['開始'].max() if '開始' in df.columns else datetime.now()
            default_start = default_end - timedelta(days=7)
            previous_start = default_start - timedelta(days=7)
            previous_end = default_start - timedelta(days=1)
            period_name = f"週報 ({default_start.strftime('%Y-%m-%d')} ~ {default_end.strftime('%Y-%m-%d')})"

        elif report_type == "月報":
            # 預設最近一個月
            default_end = df['開始'].max() if '開始' in df.columns else datetime.now()
            default_start = default_end - timedelta(days=30)
            previous_start = default_start - timedelta(days=30)
            previous_end = default_start - timedelta(days=1)
            period_name = f"月報 ({default_start.strftime('%Y-%m-%d')} ~ {default_end.strftime('%Y-%m-%d')})"

        else:  # 自定義期間
            date_col1, date_col2 = st.columns(2)
            with date_col1:
                default_start = st.date_input("開始日期", value=datetime.now() - timedelta(days=7))
            with date_col2:
                default_end = st.date_input("結束日期", value=datetime.now())

            default_start = pd.Timestamp(default_start)
            default_end = pd.Timestamp(default_end)

            # 計算對比期間（相同長度）
            period_length = (default_end - default_start).days
            previous_end = default_start - timedelta(days=1)
            previous_start = previous_end - timedelta(days=period_length)

            period_name = f"自定義期間 ({default_start.strftime('%Y-%m-%d')} ~ {default_end.strftime('%Y-%m-%d')})"

        st.info(f"📅 分析期間：{period_name}")

    with col2:
        st.markdown("### 📊 功能說明")
        st.info("""
        **自動化報告功能**

        - 生成專業週報/月報
        - AI 分析數據趨勢
        - 提供優化建議
        - 支援匯出 Markdown

        **節省時間**：原本 1-2 小時的報告，5 分鐘完成！
        """)

    st.divider()

    # 主要內容
    tab1, tab2, tab3 = st.tabs(["📊 數據預覽", "🤖 生成報告", "💾 匯出報告"])

    with tab1:
        st.markdown(f"## 📊 {period_name} 數據預覽")

        # 計算本期和上期指標
        current_metrics = calculate_period_metrics(df, default_start, default_end)
        previous_metrics = calculate_period_metrics(df, previous_start, previous_end)

        if not current_metrics:
            st.warning("所選期間內沒有數據")
            return

        # 顯示指標對比
        st.markdown("### 📈 關鍵指標")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            delta_spend = ((current_metrics['花費'] - previous_metrics['花費']) / previous_metrics['花費'] * 100) if previous_metrics and previous_metrics['花費'] > 0 else 0
            st.metric(
                "總花費",
                f"NT$ {current_metrics['花費']:,.0f}",
                delta=f"{delta_spend:+.1f}%"
            )

        with col2:
            delta_roas = ((current_metrics['ROAS'] - previous_metrics['ROAS']) / previous_metrics['ROAS'] * 100) if previous_metrics and previous_metrics['ROAS'] > 0 else 0
            st.metric(
                "平均 ROAS",
                f"{current_metrics['ROAS']:.2f}",
                delta=f"{delta_roas:+.1f}%"
            )

        with col3:
            delta_purchases = ((current_metrics['購買次數'] - previous_metrics['購買次數']) / previous_metrics['購買次數'] * 100) if previous_metrics and previous_metrics['購買次數'] > 0 else 0
            st.metric(
                "總購買",
                f"{current_metrics['購買次數']:.0f}",
                delta=f"{delta_purchases:+.1f}%"
            )

        with col4:
            delta_ctr = ((current_metrics['CTR'] - previous_metrics['CTR']) / previous_metrics['CTR'] * 100) if previous_metrics and previous_metrics['CTR'] > 0 else 0
            st.metric(
                "平均 CTR",
                f"{current_metrics['CTR']:.2f}%",
                delta=f"{delta_ctr:+.1f}%"
            )

        st.divider()

        # 趨勢圖
        st.markdown("### 📈 趨勢分析")

        period_data = df[
            (df['開始'] >= default_start) &
            (df['開始'] <= default_end)
        ]

        if not period_data.empty:
            # 每日數據
            daily_metrics = period_data.groupby('開始').agg({
                '花費金額 (TWD)': 'sum',
                '購買 ROAS（廣告投資報酬率）': 'mean',
                '購買次數': 'sum'
            }).reset_index()

            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('每日花費', '每日 ROAS', '每日購買次數', '累積花費'),
                specs=[
                    [{"type": "scatter"}, {"type": "scatter"}],
                    [{"type": "scatter"}, {"type": "scatter"}]
                ]
            )

            # 每日花費
            fig.add_trace(
                go.Scatter(
                    x=daily_metrics['開始'],
                    y=daily_metrics['花費金額 (TWD)'],
                    mode='lines+markers',
                    name='花費',
                    line=dict(color='blue')
                ),
                row=1, col=1
            )

            # 每日 ROAS
            fig.add_trace(
                go.Scatter(
                    x=daily_metrics['開始'],
                    y=daily_metrics['購買 ROAS（廣告投資報酬率）'],
                    mode='lines+markers',
                    name='ROAS',
                    line=dict(color='green')
                ),
                row=1, col=2
            )

            # 每日購買
            fig.add_trace(
                go.Scatter(
                    x=daily_metrics['開始'],
                    y=daily_metrics['購買次數'],
                    mode='lines+markers',
                    name='購買',
                    line=dict(color='orange')
                ),
                row=2, col=1
            )

            # 累積花費
            daily_metrics['累積花費'] = daily_metrics['花費金額 (TWD)'].cumsum()
            fig.add_trace(
                go.Scatter(
                    x=daily_metrics['開始'],
                    y=daily_metrics['累積花費'],
                    mode='lines',
                    name='累積花費',
                    fill='tozeroy',
                    line=dict(color='purple')
                ),
                row=2, col=2
            )

            fig.update_layout(height=700, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        # Top 活動
        st.markdown("### 🏆 表現最佳活動")
        top_campaigns = get_top_performing_campaigns(df, default_start, default_end, limit=5)

        if not top_campaigns.empty:
            st.dataframe(
                top_campaigns,
                use_container_width=True,
                column_config={
                    "行銷活動名稱": st.column_config.TextColumn("活動名稱", width="large"),
                    "花費金額 (TWD)": st.column_config.NumberColumn("花費", format="%.0f"),
                    "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
                    "購買次數": st.column_config.NumberColumn("購買", format="%.0f"),
                    "CTR（全部）": st.column_config.NumberColumn("CTR", format="%.2f%%")
                }
            )

        # 需改進活動
        st.markdown("### ⚠️ 需改進活動")
        underperforming = get_underperforming_campaigns(df, default_start, default_end, limit=5)

        if not underperforming.empty:
            st.dataframe(
                underperforming,
                use_container_width=True,
                column_config={
                    "行銷活動名稱": st.column_config.TextColumn("活動名稱", width="large"),
                    "花費金額 (TWD)": st.column_config.NumberColumn("花費", format="%.0f"),
                    "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
                    "購買次數": st.column_config.NumberColumn("購買", format="%.0f"),
                    "CTR（全部）": st.column_config.NumberColumn("CTR", format="%.2f%%")
                }
            )

        # 關鍵事件
        st.markdown("### 📌 關鍵事件")
        events = identify_key_events(df, default_start, default_end)

        if events:
            for event in events:
                st.info(f"**{event['類型']}**: {event['描述']}\n\n{event['詳情']}")
        else:
            st.success("本期無特殊事件")

    with tab2:
        st.markdown(f"## 🤖 AI 生成 {report_type}")

        llm_service = get_llm_service()

        if not llm_service.is_available():
            st.error("❌ LLM 服務目前無法使用，請檢查 OPENAI_API_KEY 設定")
            return

        st.info(f"✅ AI 分析已就緒，準備生成{report_type}")

        # 計算數據
        current_metrics = calculate_period_metrics(df, default_start, default_end)
        previous_metrics = calculate_period_metrics(df, previous_start, previous_end)
        top_campaigns = get_top_performing_campaigns(df, default_start, default_end)
        underperforming = get_underperforming_campaigns(df, default_start, default_end)
        events = identify_key_events(df, default_start, default_end)

        # 生成報告按鈕
        if st.button(f"🚀 生成 AI {report_type}", type="primary"):
            with st.spinner(f"AI 正在分析數據並生成{report_type}..."):
                report = generate_report_with_ai(
                    report_type,
                    current_metrics,
                    previous_metrics,
                    top_campaigns,
                    underperforming,
                    events
                )

                if isinstance(report, dict) and "error" in report:
                    st.error(f"❌ 生成報告失敗：{report['error']}")
                else:
                    st.success(f"✅ {report_type}生成完成！")

                    # 顯示報告
                    st.markdown("---")
                    st.markdown(report)

                    # 儲存到 session state
                    st.session_state['generated_report'] = report
                    st.session_state['report_metrics'] = current_metrics
                    st.session_state['report_period'] = period_name
                    st.session_state['report_time'] = pd.Timestamp.now()

        # 顯示歷史報告
        if 'generated_report' in st.session_state:
            st.markdown("---")
            st.markdown("### 📚 最近生成的報告")

            if 'report_time' in st.session_state:
                gen_time = st.session_state['report_time']
                st.caption(f"生成時間：{gen_time.strftime('%Y-%m-%d %H:%M:%S')}")

            with st.expander("查看完整報告", expanded=False):
                st.markdown(st.session_state['generated_report'])

    with tab3:
        st.markdown("## 💾 匯出報告")

        if 'generated_report' not in st.session_state:
            st.warning("請先在「生成報告」標籤中生成報告")
            return

        st.success("✅ 報告已生成，可以匯出")

        # 匯出格式選擇
        export_format = st.radio(
            "選擇匯出格式",
            ["Markdown (.md)", "純文字 (.txt)"]
        )

        # 生成匯出內容
        markdown_content = export_report_to_markdown(
            st.session_state['generated_report'],
            st.session_state['report_metrics'],
            st.session_state['report_period']
        )

        # 預覽
        st.markdown("### 📄 報告預覽")
        with st.expander("查看匯出內容", expanded=True):
            st.markdown(markdown_content)

        # 下載按鈕
        if export_format == "Markdown (.md)":
            filename = f"Meta廣告報告_{st.session_state['report_period']}_{datetime.now().strftime('%Y%m%d')}.md"
            st.download_button(
                label="📥 下載 Markdown 報告",
                data=markdown_content,
                file_name=filename,
                mime="text/markdown"
            )
        else:
            filename = f"Meta廣告報告_{st.session_state['report_period']}_{datetime.now().strftime('%Y%m%d')}.txt"
            st.download_button(
                label="📥 下載純文字報告",
                data=markdown_content,
                file_name=filename,
                mime="text/plain"
            )

        st.markdown("---")

        # 使用建議
        st.markdown("""
        ### 💡 使用建議

        **報告用途**：
        - 📧 **郵件報告**：直接複製內容寄送給主管/客戶
        - 📊 **週會簡報**：作為週會討論的數據基礎
        - 📝 **工作記錄**：保存為文件追蹤投放歷史
        - 🔄 **優化依據**：根據 AI 建議執行優化動作

        **最佳實踐**：
        - 🗓️ **定期生成**：每週一生成上週週報
        - 📈 **趨勢追蹤**：保存每期報告，觀察長期趨勢
        - 🎯 **行動導向**：重點關注「下期行動計畫」並執行
        - 🤝 **團隊分享**：與團隊共享報告，對齊目標
        """)

    # 頁面底部
    st.markdown("---")
    st.markdown("""
    ### 📌 自動化報告功能說明

    **核心價值**：
    1. ⏱️ **節省時間**：5 分鐘生成原本需 1-2 小時的專業報告
    2. 🎯 **數據驅動**：基於真實數據，AI 自動分析趨勢和問題
    3. 📊 **專業格式**：適合向主管/客戶報告的專業格式
    4. 💡 **可執行建議**：不只呈現數據，還提供具體優化建議

    **報告內容**：
    - 執行摘要（給主管的 3-5 句重點）
    - 關鍵指標分析（花費、ROAS、購買、CTR）
    - 成功案例分析（為什麼成功？如何複製？）
    - 需改善項目（問題診斷 + 改善方案）
    - 下期行動計畫（優先級排序的具體建議）
    - 策略建議（受眾、預算、素材優化方向）
    """)

if __name__ == "__main__":
    main()
