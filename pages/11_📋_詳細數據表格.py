import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from utils.data_loader import load_meta_ads_data, filter_data_by_date_range, export_data_to_csv

st.set_page_config(page_title="詳細數據表格", page_icon="📋", layout="wide")

def format_currency(value):
    """格式化貨幣顯示"""
    if pd.isna(value) or value == 0:
        return "NT$ 0"
    return f"NT$ {value:,.0f}"

def format_percentage(value):
    """格式化百分比顯示"""
    if pd.isna(value):
        return "0.00%"
    return f"{value:.2f}%"

def format_number(value):
    """格式化數字顯示"""
    if pd.isna(value):
        return "0"
    return f"{value:,.0f}"

def calculate_derived_metrics(df):
    """計算衍生指標"""
    if df is None or df.empty:
        return df

    df_calc = df.copy()

    # 計算轉換率
    if '購買次數' in df_calc.columns and '觸及人數' in df_calc.columns:
        df_calc['轉換率 (%)'] = (df_calc['購買次數'] / df_calc['觸及人數'].replace(0, 1)) * 100

    # 計算每千次曝光購買數
    if '購買次數' in df_calc.columns and '曝光次數' in df_calc.columns:
        df_calc['每千次曝光購買數'] = (df_calc['購買次數'] / df_calc['曝光次數'].replace(0, 1)) * 1000

    # 計算投放天數
    if '開始' in df_calc.columns and '結束時間' in df_calc.columns:
        df_calc['投放天數'] = (df_calc['結束時間'] - df_calc['開始']).dt.days + 1
        df_calc['投放天數'] = df_calc['投放天數'].fillna(1)

    # 計算日均花費
    if '花費金額 (TWD)' in df_calc.columns and '投放天數' in df_calc.columns:
        df_calc['日均花費 (TWD)'] = df_calc['花費金額 (TWD)'] / df_calc['投放天數']

    # 計算日均觸及
    if '觸及人數' in df_calc.columns and '投放天數' in df_calc.columns:
        df_calc['日均觸及人數'] = df_calc['觸及人數'] / df_calc['投放天數']

    # 表現評級
    if '購買 ROAS（廣告投資報酬率）' in df_calc.columns:
        def get_performance_grade(roas):
            if pd.isna(roas):
                return '未知'
            elif roas >= 3.0:
                return '優秀'
            elif roas >= 2.0:
                return '良好'
            elif roas >= 1.0:
                return '一般'
            else:
                return '需改善'

        df_calc['表現評級'] = df_calc['購買 ROAS（廣告投資報酬率）'].apply(get_performance_grade)

    return df_calc

def create_summary_statistics(df):
    """創建摘要統計"""
    if df is None or df.empty:
        return {}

    numeric_columns = df.select_dtypes(include=[np.number]).columns

    summary_stats = {}

    for col in numeric_columns:
        if df[col].notna().sum() > 0:  # 只計算有數據的欄位
            summary_stats[col] = {
                '總計': df[col].sum(),
                '平均': df[col].mean(),
                '中位數': df[col].median(),
                '最大值': df[col].max(),
                '最小值': df[col].min(),
                '標準差': df[col].std()
            }

    return summary_stats

def create_correlation_matrix(df):
    """創建相關性矩陣"""
    if df is None or df.empty:
        return None

    # 選擇關鍵數值欄位
    key_columns = [
        '花費金額 (TWD)', '購買次數', '購買 ROAS（廣告投資報酬率）',
        'CTR（全部）', '每次購買的成本', '觸及人數', '曝光次數'
    ]

    available_columns = [col for col in key_columns if col in df.columns]

    if len(available_columns) < 2:
        return None

    correlation_matrix = df[available_columns].corr()

    fig = go.Figure(data=go.Heatmap(
        z=correlation_matrix.values,
        x=correlation_matrix.columns,
        y=correlation_matrix.columns,
        colorscale='RdBu',
        zmid=0,
        text=correlation_matrix.round(2).values,
        texttemplate="%{text}",
        textfont={"size": 10},
        hoverongaps=False
    ))

    fig.update_layout(
        title='關鍵指標相關性分析',
        width=600,
        height=500
    )

    return fig

def apply_data_filters(df, filters):
    """應用數據篩選器"""
    if df is None or df.empty:
        return df

    filtered_df = df.copy()

    # ROAS 篩選
    if filters.get('min_roas') is not None:
        filtered_df = filtered_df[filtered_df['購買 ROAS（廣告投資報酬率）'] >= filters['min_roas']]

    if filters.get('max_roas') is not None:
        filtered_df = filtered_df[filtered_df['購買 ROAS（廣告投資報酬率）'] <= filters['max_roas']]

    # 花費篩選
    if filters.get('min_spend') is not None:
        filtered_df = filtered_df[filtered_df['花費金額 (TWD)'] >= filters['min_spend']]

    if filters.get('max_spend') is not None:
        filtered_df = filtered_df[filtered_df['花費金額 (TWD)'] <= filters['max_spend']]

    # 活動名稱篩選
    if filters.get('campaign_names'):
        filtered_df = filtered_df[filtered_df['行銷活動名稱'].isin(filters['campaign_names'])]

    # 目標篩選
    if filters.get('audiences') and '目標' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['目標'].isin(filters['audiences'])]

    # 表現評級篩選
    if filters.get('performance_grades') and '表現評級' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['表現評級'].isin(filters['performance_grades'])]

    return filtered_df

def main():
    st.title("📋 詳細數據表格")
    st.markdown("完整的 Meta 廣告數據檢視與分析工具")

    # 載入數據
    df = load_meta_ads_data()

    if df is None:
        st.error("❌ 無法載入數據，請檢查數據檔案")
        return

    # 計算衍生指標
    df_enhanced = calculate_derived_metrics(df)

    # 側邊欄篩選器
    st.sidebar.header("🔍 數據篩選器")

    # 日期範圍篩選
    if '開始' in df_enhanced.columns:
        min_date = df_enhanced['開始'].min().date() if df_enhanced['開始'].notna().any() else datetime.now().date()
        max_date = df_enhanced['開始'].max().date() if df_enhanced['開始'].notna().any() else datetime.now().date()

        date_range = st.sidebar.date_input(
            "選擇日期範圍",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

        if len(date_range) == 2:
            df_enhanced = filter_data_by_date_range(df_enhanced, date_range[0], date_range[1])

    # 其他篩選器
    filters = {}

    # ROAS 篩選
    if '購買 ROAS（廣告投資報酬率）' in df_enhanced.columns:
        roas_range = st.sidebar.slider(
            "ROAS 範圍",
            min_value=0.0,
            max_value=10.0,
            value=(0.0, 10.0),
            step=0.1
        )
        filters['min_roas'] = roas_range[0]
        filters['max_roas'] = roas_range[1]

    # 花費篩選
    if '花費金額 (TWD)' in df_enhanced.columns:
        max_spend = int(df_enhanced['花費金額 (TWD)'].max()) if df_enhanced['花費金額 (TWD)'].max() > 0 else 10000
        spend_range = st.sidebar.slider(
            "花費範圍 (TWD)",
            min_value=0,
            max_value=max_spend,
            value=(0, max_spend),
            step=100
        )
        filters['min_spend'] = spend_range[0]
        filters['max_spend'] = spend_range[1]

    # 活動篩選
    if '行銷活動名稱' in df_enhanced.columns:
        unique_campaigns = df_enhanced['行銷活動名稱'].dropna().unique()
        selected_campaigns = st.sidebar.multiselect(
            "選擇廣告活動",
            options=unique_campaigns,
            default=unique_campaigns[:10] if len(unique_campaigns) > 10 else unique_campaigns
        )
        if selected_campaigns:
            filters['campaign_names'] = selected_campaigns

    # 表現評級篩選
    if '表現評級' in df_enhanced.columns:
        unique_grades = df_enhanced['表現評級'].dropna().unique()
        selected_grades = st.sidebar.multiselect(
            "選擇表現評級",
            options=unique_grades,
            default=unique_grades
        )
        if selected_grades:
            filters['performance_grades'] = selected_grades

    # 應用篩選器
    filtered_df = apply_data_filters(df_enhanced, filters)

    # 主要內容
    tab1, tab2, tab3, tab4 = st.tabs(["📊 數據表格", "📈 統計分析", "🔗 相關性分析", "📥 數據匯出"])

    with tab1:
        st.subheader("📊 詳細數據表格")

        if filtered_df.empty:
            st.warning("⚠️ 沒有符合篩選條件的數據")
        else:
            # 顯示篩選後的數據筆數
            st.info(f"📋 顯示 {len(filtered_df)} 筆數據（原始數據：{len(df_enhanced)} 筆）")

            # 選擇要顯示的欄位
            all_columns = list(filtered_df.columns)
            default_columns = [
                '行銷活動名稱', '開始', '結束時間', '花費金額 (TWD)',
                '購買次數', '購買 ROAS（廣告投資報酬率）', 'CTR（全部）',
                '每次購買的成本', '觸及人數', '表現評級'
            ]

            available_default_columns = [col for col in default_columns if col in all_columns]

            selected_columns = st.multiselect(
                "選擇要顯示的欄位",
                options=all_columns,
                default=available_default_columns
            )

            if selected_columns:
                display_df = filtered_df[selected_columns].copy()

                # 格式化特定欄位
                for col in display_df.columns:
                    if 'TWD' in col or '成本' in col or '花費' in col:
                        display_df[col] = display_df[col].apply(format_currency)
                    elif '%' in col or 'CTR' in col:
                        display_df[col] = display_df[col].apply(format_percentage)
                    elif col in ['觸及人數', '曝光次數', '購買次數']:
                        display_df[col] = display_df[col].apply(format_number)

                # 顯示表格
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    height=600
                )

                # 快速統計
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    total_spend = filtered_df['花費金額 (TWD)'].sum() if '花費金額 (TWD)' in filtered_df.columns else 0
                    st.metric("總花費", format_currency(total_spend))

                with col2:
                    total_purchases = filtered_df['購買次數'].sum() if '購買次數' in filtered_df.columns else 0
                    st.metric("總購買次數", format_number(total_purchases))

                with col3:
                    avg_roas = filtered_df['購買 ROAS（廣告投資報酬率）'].mean() if '購買 ROAS（廣告投資報酬率）' in filtered_df.columns else 0
                    st.metric("平均 ROAS", f"{avg_roas:.2f}")

                with col4:
                    total_reach = filtered_df['觸及人數'].sum() if '觸及人數' in filtered_df.columns else 0
                    st.metric("總觸及人數", format_number(total_reach))

    with tab2:
        st.subheader("📈 統計分析")

        if filtered_df.empty:
            st.warning("⚠️ 沒有數據可供分析")
        else:
            # 創建摘要統計
            summary_stats = create_summary_statistics(filtered_df)

            if summary_stats:
                st.write("### 📊 描述性統計")

                # 選擇要分析的指標
                available_metrics = list(summary_stats.keys())
                key_metrics = [
                    '花費金額 (TWD)', '購買次數', '購買 ROAS（廣告投資報酬率）',
                    'CTR（全部）', '每次購買的成本', '觸及人數'
                ]

                selected_metrics = st.multiselect(
                    "選擇要分析的指標",
                    options=available_metrics,
                    default=[metric for metric in key_metrics if metric in available_metrics]
                )

                if selected_metrics:
                    # 創建統計表格
                    stats_df = pd.DataFrame({
                        metric: summary_stats[metric] for metric in selected_metrics
                    }).round(2)

                    st.dataframe(stats_df, use_container_width=True)

                    # 分布圖
                    st.write("### 📊 數據分布")

                    cols = st.columns(2)
                    for i, metric in enumerate(selected_metrics[:4]):  # 顯示前4個指標的分布
                        with cols[i % 2]:
                            if metric in filtered_df.columns:
                                fig = px.histogram(
                                    filtered_df,
                                    x=metric,
                                    title=f"{metric} 分布",
                                    nbins=20
                                )
                                st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("🔗 相關性分析")

        if filtered_df.empty:
            st.warning("⚠️ 沒有數據可供分析")
        else:
            # 顯示相關性矩陣
            correlation_fig = create_correlation_matrix(filtered_df)

            if correlation_fig:
                st.plotly_chart(correlation_fig, use_container_width=True)

                # 相關性洞察
                st.write("### 💡 相關性洞察")

                key_columns = [
                    '花費金額 (TWD)', '購買次數', '購買 ROAS（廣告投資報酬率）',
                    'CTR（全部）', '每次購買的成本', '觸及人數'
                ]

                available_columns = [col for col in key_columns if col in filtered_df.columns]

                if len(available_columns) >= 2:
                    correlation_matrix = filtered_df[available_columns].corr()

                    insights = []

                    # 尋找強相關性
                    for i in range(len(correlation_matrix.columns)):
                        for j in range(i+1, len(correlation_matrix.columns)):
                            corr_value = correlation_matrix.iloc[i, j]
                            col1 = correlation_matrix.columns[i]
                            col2 = correlation_matrix.columns[j]

                            if abs(corr_value) > 0.7:
                                if corr_value > 0:
                                    insights.append(f"🔴 **強正相關**：{col1} 與 {col2} (r={corr_value:.2f})")
                                else:
                                    insights.append(f"🔵 **強負相關**：{col1} 與 {col2} (r={corr_value:.2f})")
                            elif abs(corr_value) > 0.5:
                                if corr_value > 0:
                                    insights.append(f"🟡 **中等正相關**：{col1} 與 {col2} (r={corr_value:.2f})")
                                else:
                                    insights.append(f"🟡 **中等負相關**：{col1} 與 {col2} (r={corr_value:.2f})")

                    if insights:
                        for insight in insights:
                            st.markdown(f"- {insight}")
                    else:
                        st.info("📊 指標間沒有發現明顯的強相關性")

    with tab4:
        st.subheader("📥 數據匯出")

        if filtered_df.empty:
            st.warning("⚠️ 沒有數據可供匯出")
        else:
            st.write(f"準備匯出 {len(filtered_df)} 筆資料")

            # 匯出格式選擇
            export_format = st.selectbox(
                "選擇匯出格式",
                ["CSV", "Excel"]
            )

            # 匯出欄位選擇
            export_columns = st.multiselect(
                "選擇要匯出的欄位",
                options=list(filtered_df.columns),
                default=list(filtered_df.columns)
            )

            if export_columns:
                export_df = filtered_df[export_columns].copy()

                # 生成檔案名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename_prefix = f"meta_ads_data_{timestamp}"

                if export_format == "CSV":
                    csv_data, filename = export_data_to_csv(export_df, filename_prefix)

                    st.download_button(
                        label="📥 下載 CSV 檔案",
                        data=csv_data,
                        file_name=filename,
                        mime="text/csv",
                        use_container_width=True
                    )

                elif export_format == "Excel":
                    # 創建 Excel 檔案
                    from io import BytesIO

                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        export_df.to_excel(writer, sheet_name='廣告數據', index=False)

                        # 添加摘要統計頁
                        if summary_stats := create_summary_statistics(filtered_df):
                            stats_df = pd.DataFrame(summary_stats).round(2)
                            stats_df.to_excel(writer, sheet_name='統計摘要')

                    buffer.seek(0)

                    st.download_button(
                        label="📥 下載 Excel 檔案",
                        data=buffer.getvalue(),
                        file_name=f"{filename_prefix}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

                # 匯出預覽
                st.write("### 👀 匯出預覽")
                st.dataframe(export_df.head(10), use_container_width=True)
                st.caption(f"顯示前 10 筆資料，共 {len(export_df)} 筆將被匯出")

    # 使用說明
    with st.expander("📖 使用說明", expanded=False):
        st.markdown("""
        ### 🎯 功能說明

        **數據表格**
        - 檢視完整的廣告數據，支援欄位自定義
        - 實時篩選和排序功能
        - 格式化顯示貨幣和百分比

        **統計分析**
        - 描述性統計：平均值、中位數、標準差等
        - 數據分布視覺化
        - 異常值識別

        **相關性分析**
        - 關鍵指標間的相關性熱力圖
        - 自動識別強相關性並提供洞察
        - 支援多種指標組合分析

        **數據匯出**
        - 支援 CSV 和 Excel 格式匯出
        - 可選擇性匯出特定欄位
        - 包含統計摘要（Excel 格式）

        ### 💡 使用技巧

        - 使用側邊欄篩選器縮小分析範圍
        - 結合多個篩選條件進行深度分析
        - 定期匯出數據進行離線分析
        - 關注相關性分析中的異常模式
        """)

if __name__ == "__main__":
    main()