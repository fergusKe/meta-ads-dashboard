import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import sys
from pathlib import Path

# 添加父目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_loader import load_meta_ads_data

def show_funnel_optimization():
    """顯示轉換漏斗優化頁面"""
    st.markdown("# 🔄 轉換漏斗優化")
    st.markdown("深度分析轉換路徑，識別流失環節並提供優化建議")

    # 載入數據
    df = load_meta_ads_data()
    if df is None or df.empty:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    st.markdown("---")

    # ========== 第一部分：詳細漏斗流失分析 ==========
    st.markdown("## 📉 完整轉換漏斗分析")

    # 計算整體漏斗數據
    funnel_stages = {
        '觸及': df['觸及人數'].sum(),
        '曝光': df['曝光次數'].sum(),
        '點擊': df['連結點擊次數'].sum() if '連結點擊次數' in df.columns else 0,
        '頁面瀏覽': df['連結頁面瀏覽次數'].sum() if '連結頁面瀏覽次數' in df.columns else 0,
        '內容瀏覽': df['內容瀏覽次數'].sum() if '內容瀏覽次數' in df.columns else 0,
        '加入購物車': df['加到購物車次數'].sum() if '加到購物車次數' in df.columns else 0,
        '開始結帳': df['開始結帳次數'].sum() if '開始結帳次數' in df.columns else 0,
        '完成購買': df['購買次數'].sum() if '購買次數' in df.columns else 0
    }

    # 移除值為 0 的階段
    funnel_stages = {k: v for k, v in funnel_stages.items() if v > 0}

    funnel_df = pd.DataFrame(list(funnel_stages.items()), columns=['階段', '數量'])
    funnel_df['流失數量'] = funnel_df['數量'].diff(-1).fillna(0).abs()
    funnel_df['流失率'] = (funnel_df['流失數量'] / funnel_df['數量'] * 100).round(2)
    funnel_df['轉換率'] = (funnel_df['數量'] / funnel_df['數量'].iloc[0] * 100).round(2)

    # 主要漏斗圖
    fig_main_funnel = go.Figure(go.Funnel(
        y=funnel_df['階段'],
        x=funnel_df['數量'],
        textposition="inside",
        textinfo="value+percent initial",
        marker=dict(
            color=['#2ecc71', '#27ae60', '#3498db', '#2980b9', '#9b59b6', '#8e44ad', '#e67e22', '#d35400'][:len(funnel_df)]
        ),
        connector=dict(line=dict(color='gray', width=2))
    ))

    fig_main_funnel.update_layout(
        title="整體轉換漏斗（8 階段）",
        height=600
    )

    st.plotly_chart(fig_main_funnel, use_container_width=True)

    # 流失分析表格
    st.markdown("### 📊 各階段流失詳情")

    col1, col2 = st.columns(2)

    with col1:
        st.dataframe(
            funnel_df,
            use_container_width=True,
            column_config={
                "階段": "轉換階段",
                "數量": st.column_config.NumberColumn("人數/次數", format="%d"),
                "流失數量": st.column_config.NumberColumn("流失數", format="%d"),
                "流失率": st.column_config.NumberColumn("流失率 (%)", format="%.2f%%"),
                "轉換率": st.column_config.NumberColumn("轉換率 (%)", format="%.2f%%")
            }
        )

    with col2:
        # 找出最大流失點
        max_loss_idx = funnel_df['流失率'].idxmax()
        max_loss_stage = funnel_df.loc[max_loss_idx, '階段']
        max_loss_rate = funnel_df.loc[max_loss_idx, '流失率']

        st.error(f"""
### ⚠️ 最大流失點

**{max_loss_stage}** 階段流失率最高：**{max_loss_rate:.2f}%**

流失人數：{funnel_df.loc[max_loss_idx, '流失數量']:,.0f}
        """)

        # 異常流失點（流失率 > 50%）
        high_loss_stages = funnel_df[funnel_df['流失率'] > 50]

        if not high_loss_stages.empty:
            st.warning(f"""
### 🚨 高流失階段（>50%）

共 {len(high_loss_stages)} 個階段需要重點優化：
{', '.join(high_loss_stages['階段'].tolist())}
            """)

    # 瀑布圖顯示流失
    st.markdown("### 💧 流失瀑布圖")

    waterfall_values = [funnel_df['數量'].iloc[0]]
    for loss in funnel_df['流失數量'].iloc[:-1]:
        waterfall_values.append(-loss)

    waterfall_text = [f"{int(v):,}" for v in waterfall_values]

    fig_waterfall = go.Figure(go.Waterfall(
        name="流失分析",
        orientation="v",
        measure=["absolute"] + ["relative"] * (len(funnel_df) - 1),
        x=funnel_df['階段'],
        y=waterfall_values,
        text=waterfall_text,
        textposition="outside",
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        decreasing={"marker": {"color": "#e74c3c"}},
        increasing={"marker": {"color": "#2ecc71"}},
        totals={"marker": {"color": "#3498db"}}
    ))

    fig_waterfall.update_layout(
        title="轉換漏斗流失瀑布圖",
        showlegend=False,
        height=500
    )

    st.plotly_chart(fig_waterfall, use_container_width=True)

    st.markdown("---")

    # ========== 第二部分：分群漏斗對比 ==========
    st.markdown("## 🎯 分群漏斗對比")

    comparison_tabs = st.tabs(["👥 受眾分群", "📊 活動分群", "💰 ROAS 分群"])

    with comparison_tabs[0]:
        st.markdown("### 受眾年齡層漏斗對比")

        if '年齡' in df.columns:
            age_groups = df['年齡'].value_counts().head(4).index.tolist()

            fig_age_funnel = go.Figure()

            for age in age_groups:
                age_df = df[df['年齡'] == age]

                age_funnel = {
                    '觸及': age_df['觸及人數'].sum(),
                    '點擊': age_df['連結點擊次數'].sum() if '連結點擊次數' in age_df.columns else 0,
                    '加購': age_df['加到購物車次數'].sum() if '加到購物車次數' in age_df.columns else 0,
                    '購買': age_df['購買次數'].sum() if '購買次數' in age_df.columns else 0
                }

                # 計算轉換率
                if age_funnel['觸及'] > 0:
                    conversion_rates = [
                        100,  # 觸及基準
                        age_funnel['點擊'] / age_funnel['觸及'] * 100 if age_funnel['觸及'] > 0 else 0,
                        age_funnel['加購'] / age_funnel['觸及'] * 100 if age_funnel['觸及'] > 0 else 0,
                        age_funnel['購買'] / age_funnel['觸及'] * 100 if age_funnel['觸及'] > 0 else 0
                    ]

                    fig_age_funnel.add_trace(go.Scatter(
                        name=f"{age} 歲",
                        x=['觸及', '點擊', '加購', '購買'],
                        y=conversion_rates,
                        mode='lines+markers',
                        line=dict(width=3),
                        marker=dict(size=10)
                    ))

            fig_age_funnel.update_layout(
                title="不同年齡層轉換率對比（以觸及為基準 100%）",
                xaxis_title="轉換階段",
                yaxis_title="相對轉換率 (%)",
                hovermode='x unified',
                height=450
            )

            st.plotly_chart(fig_age_funnel, use_container_width=True)

    with comparison_tabs[1]:
        st.markdown("### 活動類型漏斗對比")

        # 選擇 Top 5 活動
        top_campaigns = df.groupby('行銷活動名稱')['花費金額 (TWD)'].sum().nlargest(5).index.tolist()

        selected_campaigns = st.multiselect(
            "選擇要對比的活動（最多 5 個）",
            top_campaigns,
            default=top_campaigns[:3]
        )

        if selected_campaigns:
            fig_campaign_funnel = go.Figure()

            for campaign in selected_campaigns:
                campaign_df = df[df['行銷活動名稱'] == campaign]

                campaign_funnel_values = [
                    campaign_df['觸及人數'].sum(),
                    campaign_df['連結點擊次數'].sum() if '連結點擊次數' in campaign_df.columns else 0,
                    campaign_df['加到購物車次數'].sum() if '加到購物車次數' in campaign_df.columns else 0,
                    campaign_df['購買次數'].sum() if '購買次數' in campaign_df.columns else 0
                ]

                # 計算百分比
                if campaign_funnel_values[0] > 0:
                    campaign_funnel_pct = [v / campaign_funnel_values[0] * 100 for v in campaign_funnel_values]

                    fig_campaign_funnel.add_trace(go.Scatter(
                        name=campaign[:30] + "..." if len(campaign) > 30 else campaign,
                        x=['觸及', '點擊', '加購', '購買'],
                        y=campaign_funnel_pct,
                        mode='lines+markers',
                        line=dict(width=3),
                        marker=dict(size=10)
                    ))

            fig_campaign_funnel.update_layout(
                title="不同活動轉換漏斗對比",
                xaxis_title="轉換階段",
                yaxis_title="轉換率 (%)",
                hovermode='x unified',
                height=450
            )

            st.plotly_chart(fig_campaign_funnel, use_container_width=True)

    with comparison_tabs[2]:
        st.markdown("### 高 ROAS vs 低 ROAS 漏斗差異")

        # 按 ROAS 分組
        roas_threshold = df['購買 ROAS（廣告投資報酬率）'].median()

        high_roas_df = df[df['購買 ROAS（廣告投資報酬率）'] >= roas_threshold]
        low_roas_df = df[df['購買 ROAS（廣告投資報酬率）'] < roas_threshold]

        comparison_data = []

        for group_name, group_df in [('高 ROAS (≥中位數)', high_roas_df), ('低 ROAS (<中位數)', low_roas_df)]:
            reach = group_df['觸及人數'].sum()
            if reach > 0:
                comparison_data.append({
                    '分組': group_name,
                    '點擊率': group_df['連結點擊次數'].sum() / reach * 100 if '連結點擊次數' in group_df.columns else 0,
                    '加購率': group_df['加到購物車次數'].sum() / reach * 100 if '加到購物車次數' in group_df.columns else 0,
                    '購買率': group_df['購買次數'].sum() / reach * 100 if '購買次數' in group_df.columns else 0
                })

        comparison_df = pd.DataFrame(comparison_data)

        fig_roas_compare = go.Figure()

        for col in ['點擊率', '加購率', '購買率']:
            fig_roas_compare.add_trace(go.Bar(
                name=col,
                x=comparison_df['分組'],
                y=comparison_df[col],
                text=comparison_df[col].round(2),
                textposition='outside'
            ))

        fig_roas_compare.update_layout(
            title=f"高 ROAS vs 低 ROAS 轉換率對比（中位數 = {roas_threshold:.2f}）",
            barmode='group',
            xaxis_title="",
            yaxis_title="轉換率 (%)",
            height=450
        )

        st.plotly_chart(fig_roas_compare, use_container_width=True)

        # 關鍵差異分析
        if not comparison_df.empty and len(comparison_df) >= 2:
            high_click = comparison_df[comparison_df['分組'].str.contains('高')]['點擊率'].values[0]
            low_click = comparison_df[comparison_df['分組'].str.contains('低')]['點擊率'].values[0]
            click_diff = ((high_click - low_click) / low_click * 100) if low_click > 0 else 0

            high_purchase = comparison_df[comparison_df['分組'].str.contains('高')]['購買率'].values[0]
            low_purchase = comparison_df[comparison_df['分組'].str.contains('低')]['購買率'].values[0]
            purchase_diff = ((high_purchase - low_purchase) / low_purchase * 100) if low_purchase > 0 else 0

            st.info(f"""
### 🔍 關鍵發現

- **點擊率差異**：高 ROAS 活動比低 ROAS 活動高 {click_diff:.1f}%
- **購買率差異**：高 ROAS 活動比低 ROAS 活動高 {purchase_diff:.1f}%

**啟示**：高 ROAS 活動在整個漏斗中都有更好的表現，特別是購買轉換環節。
            """)

    st.markdown("---")

    # ========== 第三部分：階段優化建議 ==========
    st.markdown("## 💡 階段優化建議")

    # 計算各階段轉換率
    if funnel_df['數量'].iloc[0] > 0:
        click_rate = (funnel_df[funnel_df['階段'] == '點擊']['數量'].values[0] / funnel_df['數量'].iloc[0] * 100) if '點擊' in funnel_df['階段'].values else 0
        page_view_rate = (funnel_df[funnel_df['階段'] == '頁面瀏覽']['流失率'].values[0]) if '頁面瀏覽' in funnel_df['階段'].values else 0
        add_cart_rate = (funnel_df[funnel_df['階段'] == '加入購物車']['流失率'].values[0]) if '加入購物車' in funnel_df['階段'].values else 0
        checkout_rate = (funnel_df[funnel_df['階段'] == '開始結帳']['流失率'].values[0]) if '開始結帳' in funnel_df['階段'].values else 0

        suggestions = []

        # 點擊階段建議
        if click_rate < 2:
            suggestions.append({
                '階段': '點擊',
                '問題': f'CTR 過低（{click_rate:.2f}%）',
                '建議': '優化廣告素材、標題與目標受眾',
                '優先級': '🔴 高'
            })

        # 頁面瀏覽階段建議
        if page_view_rate > 40:
            suggestions.append({
                '階段': '頁面瀏覽',
                '問題': f'高流失率（{page_view_rate:.2f}%）',
                '建議': '檢查 Landing Page 載入速度與相關性',
                '優先級': '🔴 高'
            })

        # 加購階段建議
        if add_cart_rate > 50:
            suggestions.append({
                '階段': '加入購物車',
                '問題': f'高流失率（{add_cart_rate:.2f}%）',
                '建議': '優化產品頁面、價格與產品描述',
                '優先級': '🟡 中'
            })

        # 結帳階段建議
        if checkout_rate > 30:
            suggestions.append({
                '階段': '結帳',
                '問題': f'高流失率（{checkout_rate:.2f}%）',
                '建議': '簡化結帳流程、提供多元支付方式',
                '優先級': '🟡 中'
            })

        if suggestions:
            st.warning("### ⚠️ 需要優化的階段")
            suggestions_df = pd.DataFrame(suggestions)
            st.dataframe(suggestions_df, use_container_width=True)
        else:
            st.success("✅ 各階段轉換表現良好！")

    # 詳細優化建議
    st.markdown("### 📋 詳細優化行動方案")

    action_col1, action_col2 = st.columns(2)

    with action_col1:
        st.info("""
**🎯 點擊階段優化**

1. **素材優化**：
   - 使用高品質圖片/影片
   - 測試不同視覺風格
   - 添加動態元素

2. **標題優化**：
   - 強調價值主張
   - 使用行動導向詞彙
   - A/B 測試不同長度

3. **受眾優化**：
   - 重新定義目標受眾
   - 排除無效受眾
   - 使用類似受眾擴展
        """)

        st.info("""
**🛒 加購階段優化**

1. **產品頁優化**：
   - 清晰的產品資訊
   - 高質量產品圖片
   - 客戶評價與評分

2. **價格策略**：
   - 測試不同價格點
   - 提供限時優惠
   - 顯示價值對比

3. **信任建立**：
   - 安全付款標誌
   - 退貨保證
   - 品牌故事
        """)

    with action_col2:
        st.info("""
**📄 頁面瀏覽階段優化**

1. **Landing Page**：
   - 優化載入速度
   - 確保行動裝置友善
   - 清晰的導航

2. **內容一致性**：
   - 廣告與頁面訊息一致
   - 強調廣告中的賣點
   - 使用相同視覺元素

3. **用戶體驗**：
   - 減少彈出視窗
   - 清晰的 CTA 按鈕
   - 簡化資訊架構
        """)

        st.info("""
**💳 結帳階段優化**

1. **流程簡化**：
   - 減少必填欄位
   - 提供訪客結帳
   - 一頁式結帳

2. **支付方式**：
   - 多元支付選項
   - 顯示支付安全標誌
   - 支援行動支付

3. **信任強化**：
   - 明確運費資訊
   - 預期送達時間
   - 客服聯繫方式
        """)

    st.markdown("---")

    # ========== 第四部分：A/B 測試建議 ==========
    st.markdown("## 🧪 A/B 測試建議")

    # 根據漏斗表現建議測試項目
    test_recommendations = []

    # 基於最大流失點推薦測試
    if max_loss_stage == '點擊':
        test_recommendations.append({
            '測試項目': '廣告素材 A/B 測試',
            '測試內容': '靜態圖片 vs 影片 vs 輪播廣告',
            '預期改善': '點擊率提升 15-30%',
            '優先級': '🔴 高',
            '預計時長': '7-14 天'
        })
        test_recommendations.append({
            '測試項目': 'Headline A/B 測試',
            '測試內容': '不同長度與風格的標題',
            '預期改善': '點擊率提升 10-20%',
            '優先級': '🟡 中',
            '預計時長': '7-14 天'
        })

    elif max_loss_stage == '頁面瀏覽':
        test_recommendations.append({
            '測試項目': 'Landing Page A/B 測試',
            '測試內容': '不同版本的著陸頁設計',
            '預期改善': '頁面停留提升 20-40%',
            '優先級': '🔴 高',
            '預計時長': '14-21 天'
        })

    elif max_loss_stage in ['加入購物車', '內容瀏覽']:
        test_recommendations.append({
            '測試項目': '價格呈現 A/B 測試',
            '測試內容': '原價 vs 折扣價 vs 組合優惠',
            '預期改善': '加購率提升 15-25%',
            '優先級': '🔴 高',
            '預計時長': '14-21 天'
        })

    elif max_loss_stage == '開始結帳':
        test_recommendations.append({
            '測試項目': '結帳流程 A/B 測試',
            '測試內容': '單頁結帳 vs 多步驟結帳',
            '預期改善': '結帳完成率提升 10-20%',
            '優先級': '🔴 高',
            '預計時長': '14-21 天'
        })

    # 通用測試建議
    test_recommendations.append({
        '測試項目': 'CTA 按鈕 A/B 測試',
        '測試內容': '不同顏色、文字與位置',
        '預期改善': '整體轉換率提升 5-15%',
        '優先級': '🟢 低',
        '預計時長': '7-14 天'
    })

    test_recommendations.append({
        '測試項目': '受眾分群 A/B 測試',
        '測試內容': '不同年齡層與興趣組合',
        '預期改善': 'ROAS 提升 10-25%',
        '優先級': '🟡 中',
        '預計時長': '14-21 天'
    })

    test_df = pd.DataFrame(test_recommendations)

    st.dataframe(
        test_df,
        use_container_width=True,
        column_config={
            "測試項目": "測試項目",
            "測試內容": "測試內容",
            "預期改善": "預期改善",
            "優先級": "優先級",
            "預計時長": "預計時長"
        }
    )

    st.success(f"""
💡 **A/B 測試最佳實踐**

1. **單一變數測試**：每次只測試一個變數，確保結果可歸因
2. **足夠樣本量**：確保每個版本至少有 1000 次曝光
3. **統計顯著性**：等待達到 95% 信心水準再做決策
4. **持續優化**：將獲勝版本作為新基準，持續測試改進
    """)

    st.markdown("---")

    # ========== 第五部分：總結 ==========
    st.markdown("## 📊 漏斗優化總結")

    summary_col1, summary_col2, summary_col3 = st.columns(3)

    with summary_col1:
        overall_conversion = (funnel_df['數量'].iloc[-1] / funnel_df['數量'].iloc[0] * 100) if len(funnel_df) > 0 else 0
        st.metric("整體轉換率", f"{overall_conversion:.2f}%")

    with summary_col2:
        avg_loss_rate = funnel_df['流失率'].mean()
        st.metric("平均流失率", f"{avg_loss_rate:.2f}%")

    with summary_col3:
        critical_stages = len(funnel_df[funnel_df['流失率'] > 50])
        st.metric("高流失階段數", f"{critical_stages} 個")

    st.info("""
### 🎯 下一步行動

1. **立即行動**：優化最大流失點，快速見效
2. **中期規劃**：執行 A/B 測試，驗證改善方案
3. **長期追蹤**：定期監控漏斗變化，持續優化

**預期成果**：透過優化流失率前 3 名的階段，整體轉換率可提升 20-40%
    """)

if __name__ == "__main__":
    show_funnel_optimization()
